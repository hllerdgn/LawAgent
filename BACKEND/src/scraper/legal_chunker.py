import json
import os
import re
from dataclasses import asdict
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper.models import Chunk
from scraper.preprocessing import count_tokens

# ─── İÇ YARDIMCILAR ───────────────────────────────────────────────────────────


def _get_overlap_text(sentences: list[str], overlap_tokens: int) -> str:
    """Cümle listesinin sonundan geriye doğru overlap_tokens kadar metin döndürür."""
    result, total = [], 0
    for s in reversed(sentences):
        t = count_tokens(s)
        if total + t > overlap_tokens:
            break
        result.insert(0, s)
        total += t
    return " ".join(result)


def _get_overlap_words(words: list[str], overlap_tokens: int) -> list[str]:
    """Kelime listesinin sonundan geriye doğru overlap_tokens kadar kelime döndürür."""
    result, total = [], 0
    for w in reversed(words):
        t = count_tokens(w)
        if total + t > overlap_tokens:
            break
        result.insert(0, w)
        total += t
    return result


def _split_into_windows(
    text: str,
    min_tokens: int = 180,
    max_tokens: int = 250,
    overlap_ratio: float = 0.0,
) -> list[str]:
    """Metni token bazlı kayan pencerelere böler."""
    cumleler = re.split(r"(?<=[.!?])\s+", text.strip())
    cumleler = [c.strip() for c in cumleler if c.strip()]

    chunks = []
    current_sentences = []
    current_tokens = 0
    overlap_tokens = int(max_tokens * overlap_ratio)

    for cumle in cumleler:
        t = count_tokens(cumle)

        if t > max_tokens:
            if current_sentences:
                chunks.append(" ".join(current_sentences))
                overlap_text = _get_overlap_text(current_sentences, overlap_tokens)
                current_sentences = [overlap_text] if overlap_text else []
                current_tokens = count_tokens(" ".join(current_sentences))

            kelimeler = cumle.split()
            buf, buf_t = [], 0
            for kelime in kelimeler:
                kt = count_tokens(kelime)
                if buf_t + kt > max_tokens and buf_t >= min_tokens:
                    chunks.append(" ".join(buf))
                    overlap_k = _get_overlap_words(buf, overlap_tokens)
                    buf = overlap_k
                    buf_t = count_tokens(" ".join(buf))
                buf.append(kelime)
                buf_t += kt
            if buf:
                current_sentences = [" ".join(buf)]
                current_tokens = count_tokens(" ".join(current_sentences))
            continue

        if current_tokens + t > max_tokens and current_tokens >= min_tokens:
            chunks.append(" ".join(current_sentences))
            overlap_text = _get_overlap_text(current_sentences, overlap_tokens)
            current_sentences = [overlap_text] if overlap_text else []
            current_tokens = count_tokens(" ".join(current_sentences))

        current_sentences.append(cumle)
        current_tokens += t

    if current_sentences:
        son = " ".join(current_sentences)
        if count_tokens(son) >= 50 or not chunks:
            chunks.append(son)
        elif count_tokens(chunks[-1]) + count_tokens(son) <= max_tokens:
            chunks[-1] = chunks[-1] + " " + son
        else:
            chunks.append(son)

    return [c for c in chunks if c.strip()]


_BENT_RE = re.compile(r"(?=\s[a-zçğışöü]\)\s)", re.IGNORECASE)
_FIKRA_RE = re.compile(r"(?=\(\s*\d+\s*\))")


def _split_by_fikra(text: str) -> list[str]:
    """Metni fıkra ve bent sınırlarına böler."""
    fikralar = [p.strip() for p in _FIKRA_RE.split(text) if p.strip()]
    sonuc = []
    for fikra in fikralar:
        bentler = [b.strip() for b in _BENT_RE.split(fikra) if b.strip()]
        sonuc.extend(bentler)
    return sonuc if sonuc else [text.strip()]


# ─── AYARLAR VE HARİTALAR ──────────────────────────────────────────────────

_KANUN_NO_MAP = {
    "6098": "TBK",
    "6102": "TTK",
    "6502": "TKHK",
}

_HEDEF_KANUNLAR = {"TBK", "TTK", "TKHK"}

BOLUM_ANAHTARLARI = (
    "HÜKÜM",
    "KARAR",
    "SONUÇ",
    "GEREKÇE",
    "DELİLLER",
    "DAVA",
    "YANIT",
    "İNCELEME",
    "İSTEM",
    "ÖZET",
    "TALEP",
    "TÜRK MİLLETİ ADINA",
    "UYUŞMAZLIK",
    "SÜRECİ",
    "TEMYİZ",
)


MADDE_PATTERNS = [
    (
        "fmt1",
        re.compile(
            r"(?P<kanun>TBK|TTK|TKHK)\s+(?:m\.|madde)\s*(?P<madde>\d+[A-Za-z]*(?:/\d+)?)",
            re.IGNORECASE,
        ),
    ),
    (
        "fmt2",
        re.compile(
            r"(?P<kanun>TBK|TTK|TKHK)'[a-zçğıöşü]{1,5}\s+(?P<madde>\d+(?:/\d+)?)[.]",
            re.IGNORECASE,
        ),
    ),
    (
        "fmt3",
        re.compile(
            r"\(\s*(?P<kanun>TBK|TTK|TKHK),\s*m\.\s*(?P<madde>\d+[A-Za-z]*(?:/\d+)?)\s*\)",
            re.IGNORECASE,
        ),
    ),
    (
        "fmt4",
        re.compile(
            r"(?P<kanun_no>6098|6102|6502)\s+say[ıi]l[ıi][^.]{0,50}?madde\s+(?P<madde>\d+[A-Za-z]*(?:/\d+)?)",
            re.IGNORECASE,
        ),
    ),
    (
        "fmt5",
        re.compile(
            r"(?P<kanun>TBK|TTK|TKHK)\s+(?P<madde>\d+)(?:/(?P<fikra>\d+))?\b(?=[.\s,)])",
            re.IGNORECASE,
        ),
    ),
    (
        "fmt6",
        re.compile(
            r"\(\s*(?P<kanun>TBK|TTK|TKHK)\s+(?P<madde>\d+(?:/\d+)?)\s*\)",
            re.IGNORECASE,
        ),
    ),
    # fmt_uzun: "6102 sayılı Türk Ticaret Kanunu'nun 1057. maddesi"
    (
        "fmt_uzun",
        re.compile(
            r"(?P<kanun_no>6098|6102|6502)\s+sayılı\s+[^.]{0,100}?(?:madde|m\.)\s*(?P<madde>\d+[A-Za-z]*)",
            re.IGNORECASE,
        ),
    ),
    # fmt_kisa_noktali: "TTK. md 1057" veya "TTK. m. 1057"
    (
        "fmt_kisa_noktali",
        re.compile(
            r"(?P<kanun>TBK|TTK|TKHK)\.?\s+(?:md\.?|m\.?|madde)\s*(?P<madde>\d+[A-Za-z]*)",
            re.IGNORECASE,
        ),
    ),
    # fmt_fikra_detay: "TTK 1057/2-a" (Fıkra ve bend detayıyla)
    (
        "fmt_fikra_detay",
        re.compile(
            r"(?P<kanun>TBK|TTK|TKHK)\s+(?P<madde>\d+)/(?P<fikra>\d+)(?:-(?P<bent>[a-zçğışöü]))?",
            re.IGNORECASE,
        ),
    ),
]


def _normalize_madde(madde: str) -> str:
    if not madde:
        return ""
    parca = madde.split("/")
    if len(parca) == 2 and parca[1].isdigit():
        return parca[0]
    return madde


def build_atif_haritasi(yargitay_corpus: list) -> dict:
    gecici_harita: dict[str, dict[str, str]] = {}

    for kayit in yargitay_corpus:
        decision_id = str(kayit.get("decision_id") or "").strip()
        text = kayit.get("text") or ""

        if not decision_id or not text:
            continue

        bolum = _tespit_bolum(text)

        for _, pattern in MADDE_PATTERNS:
            for eslesme in pattern.finditer(text):
                d = eslesme.groupdict()

                # ── KANUN resolve (safe)
                kanun = None

                raw_kanun = d.get("kanun")
                if raw_kanun:
                    kanun = raw_kanun.upper()

                else:
                    kanun_no = d.get("kanun_no")
                    if kanun_no:
                        kanun = _KANUN_NO_MAP.get(str(kanun_no))

                if kanun not in _HEDEF_KANUNLAR:
                    continue

                # ── MADDE resolve (safe)
                madde = d.get("madde")
                if not madde:
                    continue

                madde = _normalize_madde(madde)
                if not madde:
                    continue

                anahtar = f"{kanun}_{madde}"

                if anahtar not in gecici_harita:
                    gecici_harita[anahtar] = {}

                # decision limit (20)
                if decision_id not in gecici_harita[anahtar]:
                    if len(gecici_harita[anahtar]) < 20:
                        gecici_harita[anahtar][decision_id] = bolum

    return {
        anahtar: [{"decision_id": d_id, "bolum": b} for d_id, b in kararlar.items()]
        for anahtar, kararlar in gecici_harita.items()
    }


def _tespit_bolum(text: str) -> str:
    """Metin parçasının hangi hukuki bölüme ait olduğunu tespit eder."""
    text_upper = text.upper()

    # Tanımladığımız anahtarları metnin başında arıyoruz
    for anahtar in BOLUM_ANAHTARLARI:
        # Bölüm başlıkları genellikle satır başında veya metnin ilk 50 karakterinde olur
        if anahtar in text_upper[:100]:
            return anahtar

    return "KÜNYE/GİRİŞ"


# ─── ANA SINIF ────────────────────────────────────────────────────────────────


class LegalChunker:
    def __init__(
        self,
        min_tokens: int = 150,
        max_tokens: int = 400,
        overlap_ratio: float = 0.20,
        min_chunk_tokens: int = 60,
    ):
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.overlap_ratio = overlap_ratio
        self.min_chunk_tokens = min_chunk_tokens

    def chunk_mevzuat(
        self, kayit: dict, atif_haritasi: dict | None = None
    ) -> list[Chunk]:
        text = kayit.get("text", "").strip()
        if not text:
            return []

        law = kayit.get("law", "")
        article_no = str(kayit.get("article_no", ""))
        atiflar = atif_haritasi.get(f"{law}_{article_no}", []) if atif_haritasi else []

        ham_parcalar = _split_by_fikra(text)
        gruplar = self._group_legal_sections(ham_parcalar)

        final_chunks = []
        for i, grup_text in enumerate(gruplar):
            t_count = count_tokens(grup_text)
            if t_count > self.max_tokens:
                sub_parcalar = _split_into_windows(
                    grup_text,
                    min_tokens=self.min_tokens,
                    max_tokens=self.max_tokens,
                    overlap_ratio=self.overlap_ratio,
                )
                for j, sub_text in enumerate(sub_parcalar):
                    chunk = self._create_and_configure_chunk(
                        sub_text,
                        kayit,
                        law,
                        article_no,
                        f"{i}_{j}",
                        len(sub_parcalar),
                        atiflar,
                    )
                    final_chunks.append(chunk)
            else:
                chunk = self._create_and_configure_chunk(
                    grup_text, kayit, law, article_no, i, len(gruplar), atiflar
                )
                final_chunks.append(chunk)
        self._set_total(final_chunks)
        return final_chunks

    def _group_legal_sections(self, parcalar: list[str]) -> list[str]:
        gruplar = []
        buffer = []
        current_tokens = 0

        for p in parcalar:
            p_tokens = count_tokens(p)
            if p_tokens > self.max_tokens:
                if buffer:
                    gruplar.append(" ".join(buffer))
                    buffer, current_tokens = [], 0
                gruplar.append(p)
                continue

            if current_tokens + p_tokens > self.max_tokens:
                gruplar.append(" ".join(buffer))
                buffer = [p]
                current_tokens = p_tokens
            else:
                buffer.append(p)
                current_tokens += p_tokens

        if buffer:
            if current_tokens < self.min_chunk_tokens and gruplar:
                gruplar[-1] = gruplar[-1] + " " + " ".join(buffer)
            else:
                gruplar.append(" ".join(buffer))
        return gruplar

    def _create_and_configure_chunk(
        self, text, kayit, law, article_no, index, total, atiflar
    ):
        c = self._make_chunk(
            text=text,
            source="mevzuat",
            law=law,
            law_no=kayit.get("law_no"),
            article_no=article_no,
            index=index,
            total=total,
        )
        c.atiflar = atiflar
        return c

    def chunk_yargitay(self, kayit: dict) -> list[Chunk]:
        text = kayit.get("text", "").strip()
        if not text:
            return []

        decision_id = str(kayit.get("decision_id", ""))

        # 1. Künye Çıkarımı
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        kunye_base = " ".join(lines[:2])
        kunye = (kunye_base[:120] + "..") if len(kunye_base) > 120 else kunye_base

        # 2. Hiyerarşik Bölümleme
        # Bayrağı (?mi) yani multiline ve ignorecase olarak stringin en başına alıyoruz
        # Parantezi regex grubunun içine taşıyarak Warning hatasını çözüyoruz
        combined_pattern = (
            rf"(?mi)^(?:\s*)(?:[IVX]+\.\s+|)(?:{'|'.join(BOLUM_ANAHTARLARI)})(?:\s*:?)"
        )

        # re.split kullanırken uyarı almamak için pattern'i parantez içine almadan bölüyoruz
        # Ancak başlıkları kaybetmemek için finditer ile manuel bölmek en temizi:
        ayraclar = list(re.finditer(combined_pattern, text))

        bolum_yapisi = []
        if ayraclar:
            # İlk ayraçtan öncesi (Künye/Giriş)
            if text[: ayraclar[0].start()].strip():
                bolum_yapisi.append(
                    ("KÜNYE/GİRİŞ", text[: ayraclar[0].start()].strip())
                )

            for i in range(len(ayraclar)):
                start = ayraclar[i].end()
                end = ayraclar[i + 1].start() if i + 1 < len(ayraclar) else len(text)

                baslik = ayraclar[i].group().strip().upper()
                # Başlıktaki Roma rakamlarını ve gereksiz karakterleri temizle
                baslik = re.sub(r"[^A-ZÇĞİÖŞÜ\s]+", "", baslik).strip()

                icerik = text[start:end].strip()
                if icerik:
                    bolum_yapisi.append((baslik, icerik))
        else:
            bolum_yapisi.append(("TÜM METİN", text))

        processed_parcalar = []
        for baslik, icerik in bolum_yapisi:
            if count_tokens(icerik) > self.max_tokens:
                sub_parcalar = _split_into_windows(
                    icerik, self.min_tokens, self.max_tokens, self.overlap_ratio
                )
                for p in sub_parcalar:
                    processed_parcalar.append(f"[{kunye}] Bölüm: {baslik}\n{p}")
            else:
                processed_parcalar.append(f"[{kunye}] Bölüm: {baslik}\n{icerik}")

        # 3. Kısa Parçaları Birleştir (Chunk Glue)
        final_texts = []
        if processed_parcalar:
            current_p = processed_parcalar[0]
            for next_p in processed_parcalar[1:]:
                if count_tokens(current_p) < self.min_chunk_tokens:
                    current_p += "\n" + next_p
                else:
                    final_texts.append(current_p)
                    current_p = next_p
            final_texts.append(current_p)

        # 4. Nesneleştirme
        chunks = [
            self._make_chunk(
                p,
                "yargitay",
                kayit.get("query"),
                None,
                None,
                i,
                len(final_texts),
                decision_id=decision_id,
            )
            for i, p in enumerate(final_texts)
        ]
        self._set_total(chunks)
        return chunks

    def chunk_resmigazete(
        self, kayit: dict, atif_haritasi: dict | None = None
    ) -> list[Chunk]:
        chunks = []
        rg_sayi = kayit.get("rg_sayi", "")
        law = kayit.get("kanunlar", [None])[0]

        for madde in kayit.get("degisen_maddeler", []):
            text = madde.get("icerik", "").strip()
            madde_no = str(madde.get("madde_no", ""))
            if not text:
                continue

            atiflar = (
                atif_haritasi.get(f"{law}_{madde_no}", [])
                if atif_haritasi and law
                else []
            )

            if count_tokens(text) <= self.max_tokens:
                c = self._make_chunk(
                    text, "resmigazete", law, law, madde_no, 0, 1, rg_sayi=rg_sayi
                )
                c.atiflar = atiflar
                chunks.append(c)
            else:
                parcalar = _split_into_windows(
                    text, self.min_tokens, self.max_tokens, self.overlap_ratio
                )
                for i, p in enumerate(parcalar):
                    c = self._make_chunk(
                        p,
                        "resmigazete",
                        law,
                        law,
                        madde_no,
                        i,
                        len(parcalar),
                        rg_sayi=rg_sayi,
                    )
                    c.atiflar = atiflar
                    chunks.append(c)
        self._set_total(chunks)
        return chunks

    def _make_chunk(
        self,
        text,
        source,
        law,
        law_no,
        article_no,
        index,
        total,
        rg_sayi=None,
        decision_id=None,
    ) -> Chunk:
        ref_id = article_no if article_no else (decision_id if decision_id else "x")
        base = f"{law or source}_{ref_id}_{index}"
        chunk_id = re.sub(r"[^A-Za-z0-9_]", "_", base)

        return Chunk(
            chunk_id=chunk_id,
            source=source,
            law=law,
            law_no=law_no,
            article_no=article_no,
            chunk_index=index,
            chunk_total=total,
            token_len=count_tokens(text),
            text=text,
            rg_sayi=rg_sayi,
            decision_id=decision_id,
            atiflar=[],
        )

    def _set_total(self, chunks: list[Chunk]) -> None:
        total = len(chunks)
        for i, c in enumerate(chunks):
            c.chunk_total = total
            c.chunk_index = i
            base = f"{c.law or c.source}_{c.article_no or c.decision_id or 'x'}_{i}"
            c.chunk_id = re.sub(r"[^A-Za-z0-9_]", "_", base)

    def _merge_short_sections(self, parcalar: list[str]) -> list[str]:
        if not parcalar:
            return parcalar
        result = [parcalar[0]]
        current_len = count_tokens(parcalar[0])
        for p in parcalar[1:]:
            p_len = count_tokens(p)
            if current_len + p_len <= self.max_tokens or p_len < self.min_chunk_tokens:
                result[-1] = result[-1] + " " + p
                current_len += p_len
            else:
                result.append(p)
                current_len = p_len
        return result


def _get_default_path(filename: str) -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "data", filename)


def chunk_all_corpora(
    mevzuat_path: str = None,
    yargitay_path: str = None,
    rg_path: str = None,
    output_path: str = None,
) -> dict:
    mevzuat_path = mevzuat_path or _get_default_path("mevzuat_corpus.json")
    yargitay_path = yargitay_path or _get_default_path("yargitay_corpus.json")
    rg_path = rg_path or _get_default_path("resmigazete_corpus.json")
    output_path = output_path or _get_default_path("chunk_corpus.json")
    chunker = LegalChunker(min_tokens=200, max_tokens=350, overlap_ratio=0.15)
    tum_chunks: list[Chunk] = []
    stats: dict = {}

    atif_haritasi = {}
    yargitay_corpus = []

    if os.path.exists(yargitay_path):
        with open(yargitay_path, "r", encoding="utf-8") as f:
            yargitay_corpus = json.load(f)
        if isinstance(yargitay_corpus, dict):
            yargitay_corpus = list(yargitay_corpus.values())
        atif_haritasi = build_atif_haritasi(yargitay_corpus)

    if os.path.exists(mevzuat_path):
        with open(mevzuat_path, "r", encoding="utf-8") as f:
            mevzuat_corpus = json.load(f)
        kayitlar = (
            list(mevzuat_corpus.values())
            if isinstance(mevzuat_corpus, dict)
            else mevzuat_corpus
        )
        mevzuat_chunks = []
        for kayit in kayitlar:
            mevzuat_chunks.extend(chunker.chunk_mevzuat(kayit, atif_haritasi))
        for i, c in enumerate(mevzuat_chunks):
            c.chunk_id = f"mevzuat_{i:05d}"
        tum_chunks.extend(mevzuat_chunks)
        stats["mevzuat"] = _kaynak_stats(
            kayitlar, mevzuat_chunks, [c.token_len for c in mevzuat_chunks]
        )
        stats["mevzuat"]["toplam_atif"] = sum(len(c.atiflar) for c in mevzuat_chunks)

    if os.path.exists(rg_path):
        with open(rg_path, "r", encoding="utf-8") as f:
            rg_corpus = json.load(f)
        kayitlar = (
            list(rg_corpus.values()) if isinstance(rg_corpus, dict) else rg_corpus
        )
        rg_chunks = []
        for kayit in kayitlar:
            rg_chunks.extend(chunker.chunk_resmigazete(kayit, atif_haritasi))
        for i, c in enumerate(rg_chunks):
            c.chunk_id = f"resmigazete_{i:05d}"
        tum_chunks.extend(rg_chunks)
        stats["resmigazete"] = _kaynak_stats(
            kayitlar, rg_chunks, [c.token_len for c in rg_chunks]
        )
        stats["resmigazete"]["toplam_atif"] = sum(len(c.atiflar) for c in rg_chunks)

    if yargitay_corpus:
        yargitay_chunks = []
        for kayit in yargitay_corpus:
            yargitay_chunks.extend(chunker.chunk_yargitay(kayit))
        for i, c in enumerate(yargitay_chunks):
            c.chunk_id = f"yargitay_{i:05d}"
        tum_chunks.extend(yargitay_chunks)
        stats["yargitay"] = _kaynak_stats(
            yargitay_corpus, yargitay_chunks, [c.token_len for c in yargitay_chunks]
        )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in tum_chunks], f, ensure_ascii=False, indent=2)

    return stats


def _kaynak_stats(kayitlar, chunks, token_lens) -> dict:
    return {
        "kayit_sayisi": len(kayitlar),
        "chunk_sayisi": len(chunks),
        "ort_token": round(sum(token_lens) / len(token_lens), 1) if token_lens else 0,
        "min_token": min(token_lens) if token_lens else 0,
        "max_token": max(token_lens) if token_lens else 0,
        "kisa_chunk": sum(1 for t in token_lens if t < 100),
        "hedef_aralik": sum(1 for t in token_lens if 180 <= t <= 250),
    }


def print_report(stats: dict, output_path: str) -> None:
    print("\n" + "=" * 55 + "\n LawAgent — Chunking Raporu\n" + "=" * 55)
    for kaynak, s in stats.items():
        print(
            f"\n [{kaynak.upper()}]\n Kayıt: {s['kayit_sayisi']} | Chunk: {s['chunk_sayisi']}"
        )
        print(f" Ort: {s['ort_token']} | Hedef (180-250): {s['hedef_aralik']}")
    print(
        f"\n{'-'*55}\n Toplam: {sum(s['chunk_sayisi'] for s in stats.values())}\n Çıktı: {output_path}\n"
        + "=" * 55
    )


if __name__ == "__main__":
    stats = chunk_all_corpora()
    if stats:
        print_report(stats, "data/chunk_corpus.json")
