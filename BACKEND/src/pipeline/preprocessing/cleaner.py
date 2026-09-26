"""
src/pipeline/preprocessing/cleaner.py — Ham JSON Temizleyici
=============================================================
Saf fonksiyon: ham dict alır, temiz dict döndürür.
Dosyaya yazmaz (storage.py yazar).

Sorumluluk sınırı:
  - law_scraper.py  → ham metin çıkarmak + kaba madde ayrımı (dipnotlar dahil)
  - cleaner.py      → dipnot ayıklama + whitespace normalize + madde no standart
                      + satır sarması birleştirme + tekrar tespiti + alt başlık koruması
"""

import re
from datetime import datetime, timezone
from html import unescape
from typing import Optional

from core.logging import log


# ── Dipnot Kalıpları ─────────────────────────────────────────────────────────
_DIPNOT_PATTERNS = [
    # Parantez içi değişiklik notları: (Değişik: ...), (Ek: ...), (Mülga: ...)
    re.compile(r"\((?:Değişik|Ek|Mülga|Bent|Fıkra|Kaldırılan)[^)]{0,300}\)"),
    # Numeral + tarih formatı: "6 2/7/2018 tarihli ve..."
    re.compile(r"^\d{1,2}\s+\d{1,2}/\d{1,2}/\d{4}[^\n]{0,300}", re.MULTILINE),
    # Resmi Gazete referansları: "3 30/6/2012-6362/146 md." vb.
    re.compile(r"^\d{1,2}\s+(?:\d+/\d+-\d+|RG)[^\n]{0,300}", re.MULTILINE),
    # KHK şerhleri: "sayılı KHK'nin ... maddesiyle..."
    re.compile(r"\d+\s+say\u0131l\u0131\s+KHK[^\n]{0,200}", re.MULTILINE),
]

# ── Yapısal Başlıklar (Bölüm / Kısım / Alt Başlık) ───────────────────────────
# Maddenin sonuna karışmış olabilecek sonraki madde veya bölüm başlıkları
_STRUCTURAL_HEADING_PATTERNS = [
    re.compile(
        r"^(?:BİRİNCİ|İKİNCİ|ÜÇÜNCÜ|DÖRDÜNCÜ|BEŞİNCİ|ALTINCI|YEDİNCİ|SEKİZİNCİ|DOKUZUNCU|ONUNCU)\s+(?:KİTAP|KISIM|BÖLÜM|AYIRIM).*",
        re.IGNORECASE,
    ),
    re.compile(r"^\d+\.\s+[A-ZÇĞİÖŞÜ].*"),       # "3. Ortak hükümler", "1. Federasyon"
    re.compile(r"^[A-ZÇĞİÖŞÜ]\.\s+.*"),         # "A. Genel olarak", "B. Hukukî ilişkiler..."
    re.compile(r"^[IVXLCDM]+\.\s+.*"),          # "I. Hak ehliyeti", "II. ..."
    re.compile(r"^[A-ZÇĞİÖŞÜ\s]{4,}$"),         # "KİŞİLER HUKUKU", "GERÇEK KİŞİLER"
]


# ── Yardımcı Fonksiyonlar ────────────────────────────────────────────────────

def _clean_footnotes(text: str) -> str:
    """
    Madde metnine gömülü dipnot ve değişiklik notlarını ayıklar.
    """
    for pattern in _DIPNOT_PATTERNS:
        text = pattern.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _strip_html(text: str) -> str:
    """HTML tag'lerini kaldırır, HTML entity'lerini çözer."""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return text


def _normalize_whitespace(text: str) -> str:
    """Fazla boşluk, tab ve yeni satırları normalize eder."""
    text = re.sub(r"[ \t]+", " ", text)    # yatay boşluklar → tek boşluk
    text = re.sub(r"\n{3,}", "\n\n", text) # 3+ newline → 2 newline
    return text.strip()


def _normalize_madde_no(no: str) -> str:
    """
    Madde numarasını standart formata getirir.
    Örn: "MADDE 4-" → "4", "Md. 12:" → "12", "  MADDE 7  " → "7"
    """
    no = no.strip()
    no = re.sub(r"(?i)^(madde|md\.?)\s*", "", no)
    no = re.sub(r"[:\-–—]+$", "", no)
    return no.strip()


def _is_structural_heading(line: str) -> bool:
    """Satırın bir bölüm/alt başlık satırı olup olmadığını kontrol eder."""
    s = line.strip()
    if not s:
        return False
    # Cümle sonu noktalaması varsa ve standart başlık formatı değilse başlık değildir
    if re.search(r"[!?:;]\s*$", s):
        return False
    if re.search(r"\.\s*$", s) and not re.match(r"^(?:\d+|[A-ZÇĞİÖŞÜ]|[IVXLCDM]+)\.\s+", s):
        return False
    return any(p.match(s) for p in _STRUCTURAL_HEADING_PATTERNS)


def _extract_trailing_headings(text: str) -> tuple[str, Optional[str]]:
    """
    Madde metninin sonuna karışmış bölüm/alt başlık satırlarını ayıklar.
    Örn: "3. Ortak hükümler" gibi satırlar gövde metninden ayrılıp alt_baslik olarak döndürülür.
    """
    lines = text.split("\n")
    trailing_headings = []

    idx = len(lines) - 1
    while idx >= 0:
        line = lines[idx].strip()
        if not line:
            idx -= 1
            continue
        if _is_structural_heading(line):
            trailing_headings.insert(0, line)
            idx -= 1
        else:
            break

    if trailing_headings:
        clean_text = "\n".join(lines[: idx + 1]).strip()
        alt_baslik = "\n".join(trailing_headings)
        return clean_text, alt_baslik
    return text.strip(), None


def _deduplicate_lines(text: str, madde_no: str = "") -> tuple[str, int, list[str]]:
    """
    Art arda gelen iki satır birebir aynıysa VE aralarında başka metin yoksa,
    ikincisini siler. Sayaçla ve logla takip edilir.
    """
    lines = text.split("\n")
    deduped = []
    removed_count = 0
    removed_lines = []

    for line in lines:
        s = line.strip()
        if not s:
            deduped.append(line)
            continue
        if deduped and deduped[-1].strip() == s:
            removed_count += 1
            removed_lines.append(s)
            log.warning(f"[Cleaner] Tekrar satır temizlendi (madde {madde_no}): {s[:80]}")
            continue
        deduped.append(line)

    return "\n".join(deduped).strip(), removed_count, removed_lines


def _merge_wrapped_lines(text: str) -> str:
    """
    Satır birleştirme kuralı:
    Bir satır nokta/iki nokta/ünlem/soru işareti/noktalı virgül gibi cümle sonu
    noktalamasıyla BİTMİYORSA ([^.!?:;]$) VE bir sonraki satır küçük harfle
    (^[a-zçğıöşü]) başlıyorsa iki satırı boşlukla birleştirir.
    """
    lines = [l.strip() for l in text.split("\n")]
    merged = []

    for line in lines:
        if not line:
            if merged and merged[-1] != "":
                merged.append("")
            continue

        if not merged or merged[-1] == "":
            merged.append(line)
            continue

        prev = merged[-1]
        # Regex kuralı: prev [^.!?:;]$ VE curr ^[a-zçğıöşü]
        if re.search(r"[^.!?:;]$", prev) and re.match(r"^[a-zçğıöşü]", line):
            merged[-1] = f"{prev} {line}"
        else:
            merged.append(line)

    return "\n".join(merged).strip()


def _clean_article(article: dict) -> dict:
    """Tek bir madde dict'ini tam temizlik pipeline'ından geçirir."""
    madde_no = _normalize_madde_no(article.get("no", ""))
    metin_raw = article.get("metin", "")
    baslik_raw = article.get("baslik", "")

    metin = _strip_html(metin_raw)
    baslik = _strip_html(baslik_raw).strip()

    # Dipnot ve değişiklik notlarını ayıkla
    metin = _clean_footnotes(metin)

    # Başlık kontrolü: Eğer başlık yarım cümle başlangıcı ise (noktalama yok ve metin küçük harfle devam ediyor)
    # başlık metnin ilk satırına katılır
    if baslik and re.search(r"[^.!?:;]$", baslik) and re.match(r"^[a-zçğıöşü]", metin.strip()):
        metin = f"{baslik}\n{metin}"
        baslik = ""
    else:
        baslik = _normalize_whitespace(baslik)

    # 1. Alt başlık ayrıştırma: Madde sonuna karışmış bölüm başlıklarını ayıkla
    metin, alt_baslik = _extract_trailing_headings(metin)

    # 2. Tekrar tespiti: Art arda gelen aynı satırları sil ve sayaç tut
    metin, dup_count, _ = _deduplicate_lines(metin, madde_no=madde_no)

    # 3. Satır sarması birleştirme: Cümle sonu olmayan ve küçük harfle devam eden satırları birleştir
    metin = _merge_wrapped_lines(metin)

    # 4. Whitespace normalizasyonu
    metin = _normalize_whitespace(metin)

    return {
        "no": madde_no,
        "baslik": baslik,
        "metin": metin,
        "alt_baslik": alt_baslik,
        "duplicate_lines_removed": dup_count,
    }


# ── Ana Fonksiyon ─────────────────────────────────────────────────────────────

def clean_raw(raw_data: dict) -> dict:
    """
    Scraper'dan gelen ham dict'i temizleyip normalize edilmiş dict döndürür.
    Dosyaya yazmaz (storage.py yazar).

    Pipeline:
      1. HTML entity/tag temizle
      2. Dipnot ve değişiklik notlarını ayıkla
      3. Bölüm/alt başlıkları metinden ayıkla
      4. Tekrar eden satırları temizle ve sayaç tut
      5. Satır sarmalarını (PDF wrap) birleştir
      6. Whitespace normalize ve madde no standartlaştır
      7. Boş metin fallback (tek cümlelik madde başlığa girdiyse metne aktar)
      8. Boş maddeleri filtrele ve dropped_articles olarak kaydet

    Args:
        raw_data: scrape_law() çıktısı — dipnotlar ham halde

    Returns:
        {
            "law_id": str,
            "law_name": str,
            "source_url": str,
            "scraped_at": str,
            "cleaned_at": str (ISO 8601),
            "article_count": int,
            "duplicate_lines_removed": int,
            "dropped_article_count": int,
            "dropped_article_nos": list[str],
            "articles": [{"no": str, "baslik": str, "metin": str, "alt_baslik": Optional[str], "duplicate_lines_removed": int}]
        }
    """
    if not raw_data or "articles" not in raw_data:
        raise ValueError("Geçersiz ham veri: 'articles' alanı bulunamadı.")

    cleaned_articles = []
    dropped_articles = []
    total_dup_removed = 0

    for a in raw_data["articles"]:
        if a.get("metin", "").strip() or a.get("baslik", "").strip():
            cleaned = _clean_article(a)

            if not cleaned["metin"] and cleaned.get("baslik"):
                # Tek cümlelik madde: scraper içeriği yanlışlıkla baslik alanına koymuş olabilir
                cleaned["metin"] = cleaned["baslik"]
                cleaned["baslik"] = ""  # artık gerçek başlık değil, temizle
                log.warning(
                    f"[cleaner] Madde {cleaned['no']}: metin boştu, baslik'tan aktarıldı "
                    f"(içerik: {cleaned['metin'][:50]}...)"
                )

            if cleaned["metin"]:
                total_dup_removed += cleaned.get("duplicate_lines_removed", 0)
                cleaned_articles.append(cleaned)
            else:
                # HALA boşsa (örn. gerçek mülga madde) — SESSİZCE ATMA, işaretle
                log.warning(f"[cleaner] Madde {cleaned['no']}: metin hala boş, listeye eklenmiyor")
                dropped_articles.append(cleaned["no"])

    return {
        "law_id": raw_data.get("law_id", ""),
        "law_name": _normalize_whitespace(raw_data.get("law_name", "")),
        "source_url": raw_data.get("url", ""),
        "scraped_at": raw_data.get("scraped_at", ""),
        "cleaned_at": datetime.now(timezone.utc).isoformat(),
        "article_count": len(cleaned_articles),
        "duplicate_lines_removed": total_dup_removed,
        "dropped_article_count": len(dropped_articles),
        "dropped_article_nos": dropped_articles,
        "articles": cleaned_articles,
    }

