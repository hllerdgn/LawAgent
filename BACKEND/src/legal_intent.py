"""
legal_intent.py — LawAgent AI Hukuki Niyet ve Rol Tespiti
===========================================================
Kullanıcı sorgusundaki:
  - Hukuki alanı (TBK / TKHK / TTK / bilinmiyor)
  - Niyeti (hak açıklama, yükümlülük, prosedür, spesifik madde, genel)
  - Hukuki sıfatı (alacaklı, borçlu, kiracı, tüketici, belirsiz ...)
  - Kavram türü (HAK / YÜKÜMLÜLÜK / SORUMLULUK / YETKİ / GENEL)

Sıfır LLM çağrısı: keyword + regex tabanlı, < 1ms.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional, List

log = logging.getLogger("LawAgent.LegalIntent")

# ─────────────────────────────────────────────────────────────────────────────
# Veri Yapısı
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LegalQueryAnalysis:
    """Kullanıcı sorgusunun hukuki niyet ve sıfat analizi."""

    # Alan tespiti
    domain: str = "bilinmiyor"
    # "borclar_hukuku" | "tuketici_hukuku" | "ticaret_hukuku" | "bilinmiyor"

    # Niyet tespiti
    intent: str = "genel"
    # "hak_aciklama" | "yukumluluk_sorgusu" | "prosedur" | "spesifik_madde"
    # | "ictihat_talebi" | "tanim" | "genel"

    # Hukuki sıfat
    legal_role: str = "belirsiz"
    # "alacakli" | "borclu" | "sozlesme_tarafi" | "tuketici" | "satici"
    # | "isveren" | "isci" | "kiraci" | "kiraya_veren" | "kefil"
    # | "rehin_veren" | "ortak" | "belirsiz"

    # Kavram türü
    concept_type: str = "genel"
    # "hak" | "yukumluluk" | "sorumluluk" | "yetki" | "usuli_imkan" | "genel"

    # Belirsizlik
    requires_clarification: bool = False
    ambiguity_type: str = ""
    # "rol_belirsiz" | "konu_belirsiz" | ""

    # Spesifik madde referansı
    explicit_article: Optional[str] = None
    explicit_law: Optional[str] = None

    # Tespit edilen sinyal kelimeler (debug için)
    matched_signals: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Sinyal Sözlükleri
# ─────────────────────────────────────────────────────────────────────────────

_DOMAIN_SIGNALS = {
    "borclar_hukuku": [
        "borçlar hukuku", "borclar hukuku", "borçlar kanunu", "tbk",
        "6098", "ifa", "temerrüt", "temerrüd", "alacaklı", "borçlu",
        "sözleşme", "sözleşmeden", "haksız fiil", "vekalet", "vekâlet",
        "kefalet", "eser sözleşme", "satım sözleşme", "kira sözleşme",
        "müteselsil", "alacağın devri", "temlik", "borç", "tazminat",
        "sebepsiz zenginleşme",
    ],
    "tuketici_hukuku": [
        "tüketici", "tkhk", "6502", "cayma hakkı", "mesafeli",
        "ayıplı mal", "ayıplı hizmet", "garanti belgesi", "abonelik",
        "devre tatil", "paket tur", "hakem heyeti", "tüketici mahkemesi",
        "haksız şart", "tüketici kredisi", "konut finansmanı",
    ],
    "ticaret_hukuku": [
        "ticaret hukuku", "ttk", "6102", "anonim şirket", "limited şirket",
        "yönetim kurulu", "genel kurul", "pay devri", "bono", "poliçe",
        "çek", "kambiyo", "tacir", "ticaret sicil", "haksız rekabet",
    ],
}

_INTENT_SIGNALS = {
    "hak_aciklama": [
        "haklarım", "hakkım", "haklarımız", "hangi haklara", "sahip olduğum hak",
        "ne haklarım var", "haklarım neler", "haklarım nedir", "haklarım nelerdir",
        "haklarım nelerdi", "ne yapabilirim", "yapabilir miyim", "hak",
    ],
    "yukumluluk_sorgusu": [
        "yükümlülük", "yükümlülüğüm", "yükümlülüklerim", "borç altında",
        "borçluyum", "ödemek zorunda", "yapmak zorunda", "zorunlu",
        "mecburiyetim", "mükellef",
    ],
    "prosedur": [
        "nasıl yapılır", "nasıl başvurulur", "nasıl açılır", "adım",
        "süreç", "işlem", "başvuru", "dava açmak", "icra", "ihtar",
        "ihbar", "bildirim süresi",
    ],
    "spesifik_madde": [
        r"\btbk\s*m\.?\s*\d+",
        r"\btkhk\s*m\.?\s*\d+",
        r"\bttk\s*m\.?\s*\d+",
        r"\bmadde\s+\d+",
        r"\bm\.\s*\d+",
    ],
    "ictihat_talebi": [
        "yargıtay", "emsal", "içtihat", "karar", "daire",
    ],
    "tanim": [
        "nedir", "ne demek", "tanımı", "kavramı", "açıkla",
    ],
}

_ROLE_SIGNALS = {
    "alacakli": [
        "alacaklı olarak", "alacaklıyım", "alacaklıysam", "alacaklı sıfatıyla",
        "borcumu tahsil", "alacağımı", "para alacaklısı", "alacaklı taraf",
        "paramı alamıyorum", "alacağımı alamıyorum",
    ],
    "borclu": [
        "borçlu olarak", "borçluyum", "borçluysa", "borçlu sıfatıyla",
        "borcumu ödeyemiyorum", "borcumu ödemek", "borcum var",
        "ödeyemiyorum", "temerrüde düştüm",
    ],
    "kiraci": [
        "kiracı olarak", "kiracıyım", "kiracıysam", "kiracı sıfatıyla",
        "kiraladığım", "kira ödüyorum", "ev kiralıyorum",
    ],
    "kiraya_veren": [
        "kiraya veren", "ev sahibi olarak", "ev sahibiyim", "kiraya verdim",
        "kiracıma", "kiracı çıkarmak", "kiracıyı çıkarmak",
    ],
    "tuketici": [
        "tüketici olarak", "müşteri olarak", "satın aldım", "aldığım ürün",
        "aldığım hizmet", "tüketiciyim",
    ],
    "satici": [
        "satıcı olarak", "satıcıyım", "mal sattım", "hizmet verdim",
    ],
    "isveren": [
        "işveren olarak", "işverende", "işverenin", "işverenim", "çalışanıma",
        "personelime", "işçimi",
    ],
    "isci": [
        "işçi olarak", "işçiyim", "çalışanım", "işte çalışıyorum",
        "maaşımı alamıyorum", "ücretimi alamıyorum",
    ],
    "kefil": [
        "kefil olarak", "kefil oldum", "kefilim", "kefil sıfatıyla",
    ],
    "ortak": [
        "ortak olarak", "ortağım", "şirket ortağı",
    ],
}

_CONCEPT_SIGNALS = {
    "hak": [
        "hakkım", "haklarım", "hak sahibi", "hakkı var",
        "seçimlik hak", "talep hakkı", "dönme hakkı",
    ],
    "yukumluluk": [
        "yükümlülük", "borç altında", "mecbur", "zorunlu", "ödemek zorunda",
        "teslim etmek zorunda",
    ],
    "sorumluluk": [
        "sorumluluk", "sorumlu", "tazminat yükümlülüğü", "zarar sorumluluğu",
        "müteselsil sorumluluk",
    ],
    "yetki": [
        "yetki", "yetkisi", "talimat verme", "karar verme",
    ],
    "usuli_imkan": [
        "dava açabilir", "başvurabilir", "itiraz edebilir", "şikayette",
        "icra", "ihtar çekme",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# Belirsizlik tespiti — "haklarım nelerdir" + sıfat yok = rol_belirsiz
# ─────────────────────────────────────────────────────────────────────────────

_AMBIGUOUS_PATTERNS = [
    # Genel hak soruları — belirsiz sıfat
    r"hak(lar)?ım\s*(neler(dir)?|ne(dir)?)",
    r"ne\s*yapabilirim",
    r"genel\s+(hak|haklar)",
    r"temel\s+(hak|haklar)",
    r"hangi\s+haklara\s+sahibim",
]

# ─────────────────────────────────────────────────────────────────────────────
# Ana Analiz Fonksiyonu
# ─────────────────────────────────────────────────────────────────────────────

def analyze_legal_query(query: str) -> LegalQueryAnalysis:
    """
    Kullanıcı sorgusunu sıfır LLM çağrısıyla analiz eder.

    Döndürür:
        LegalQueryAnalysis — alan, niyet, sıfat, kavram türü ve belirsizlik bilgileri.
    """
    analysis = LegalQueryAnalysis()
    q = query.lower().strip()
    signals: List[str] = []

    # ── 1. Spesifik madde referansı ──────────────────────────────────────────
    _law_art_re = re.compile(
        r"\b(tbk|tkhk|ttk)\s*m\.?\s*(\d+)\b"
        r"|\b(?:madde|m\.)\s*(\d+)\b",
        re.IGNORECASE
    )
    m = _law_art_re.search(q)
    if m:
        analysis.intent = "spesifik_madde"
        if m.group(1):
            analysis.explicit_law = m.group(1).upper()
            analysis.explicit_article = m.group(2)
        elif m.group(3):
            analysis.explicit_article = m.group(3)
        signals.append(f"explicit_article={analysis.explicit_article}")

    # ── 2. Alan tespiti ───────────────────────────────────────────────────────
    domain_scores = {d: 0 for d in _DOMAIN_SIGNALS}
    for domain, kws in _DOMAIN_SIGNALS.items():
        for kw in kws:
            if kw in q:
                domain_scores[domain] += 1
                signals.append(f"domain:{domain}:{kw}")

    best_domain = max(domain_scores, key=domain_scores.get)
    if domain_scores[best_domain] > 0:
        analysis.domain = best_domain
    else:
        analysis.domain = "bilinmiyor"

    # ── 3. Niyet tespiti ──────────────────────────────────────────────────────
    if analysis.intent != "spesifik_madde":
        intent_scores = {i: 0 for i in _INTENT_SIGNALS if i != "spesifik_madde"}
        for intent, kws in _INTENT_SIGNALS.items():
            if intent == "spesifik_madde":
                continue
            for kw in kws:
                if re.search(kw, q):
                    intent_scores[intent] += 1
                    signals.append(f"intent:{intent}:{kw}")

        best_intent = max(intent_scores, key=intent_scores.get)
        if intent_scores[best_intent] > 0:
            analysis.intent = best_intent
        else:
            analysis.intent = "genel"

    # ── 4. Hukuki sıfat tespiti ───────────────────────────────────────────────
    role_scores = {r: 0 for r in _ROLE_SIGNALS}
    for role, kws in _ROLE_SIGNALS.items():
        for kw in kws:
            if kw in q:
                role_scores[role] += 1
                signals.append(f"role:{role}:{kw}")

    best_role = max(role_scores, key=role_scores.get)
    if role_scores[best_role] > 0:
        analysis.legal_role = best_role
    else:
        analysis.legal_role = "belirsiz"

    # ── 5. Kavram türü tespiti ────────────────────────────────────────────────
    concept_scores = {c: 0 for c in _CONCEPT_SIGNALS}
    for concept, kws in _CONCEPT_SIGNALS.items():
        for kw in kws:
            if kw in q:
                concept_scores[concept] += 1

    best_concept = max(concept_scores, key=concept_scores.get)
    if concept_scores[best_concept] > 0:
        analysis.concept_type = best_concept
    else:
        analysis.concept_type = "genel"

    # ── 6. Belirsizlik tespiti ────────────────────────────────────────────────
    is_ambiguous_pattern = any(
        re.search(pat, q) for pat in _AMBIGUOUS_PATTERNS
    )
    if is_ambiguous_pattern and analysis.legal_role == "belirsiz":
        analysis.requires_clarification = True
        analysis.ambiguity_type = "rol_belirsiz"
        signals.append("ambiguity:rol_belirsiz")
    elif analysis.intent == "genel" and analysis.legal_role == "belirsiz":
        analysis.requires_clarification = True
        analysis.ambiguity_type = "konu_belirsiz"
        signals.append("ambiguity:konu_belirsiz")

    analysis.matched_signals = signals

    log.debug(
        f"[LegalIntent] domain={analysis.domain} intent={analysis.intent} "
        f"role={analysis.legal_role} concept={analysis.concept_type} "
        f"clarification={analysis.requires_clarification} "
        f"signals={signals[:5]}"
    )

    return analysis


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Yardımcıları
# ─────────────────────────────────────────────────────────────────────────────

_ROLE_TR = {
    "alacakli": "Alacaklı",
    "borclu": "Borçlu",
    "kiraci": "Kiracı",
    "kiraya_veren": "Kiraya Veren / Ev Sahibi",
    "tuketici": "Tüketici",
    "satici": "Satıcı",
    "isveren": "İşveren",
    "isci": "İşçi / Çalışan",
    "kefil": "Kefil",
    "rehin_veren": "Rehin Veren",
    "ortak": "Şirket Ortağı",
    "belirsiz": "Belirsiz",
    "sozlesme_tarafi": "Sözleşme Tarafı",
}

_CONCEPT_TR = {
    "hak": "Hak (kullanıcı lehine, talep edilebilir pozitif imkân)",
    "yukumluluk": "Yükümlülük (kullanıcı aleyhine, yerine getirilmesi gereken edim)",
    "sorumluluk": "Sorumluluk (hukuki sonuç olarak tazminat/yaptırım yükümlülüğü)",
    "yetki": "Yetki (belirli bir kişiye tanınan, tek taraflı hukuki işlem yapma imkânı)",
    "usuli_imkan": "Usuli İmkân (dava, itiraz, başvuru gibi prosedürel adımlar)",
    "genel": "Genel (hak/yükümlülük/sorumluluk henüz tespit edilmedi)",
}


def build_legal_role_context(analysis: LegalQueryAnalysis) -> str:
    """
    LLM prompt'una enjekte edilecek hukuki rol ve kavram bağlamı metnini üretir.
    """
    role_tr = _ROLE_TR.get(analysis.legal_role, "Belirsiz")
    concept_tr = _CONCEPT_TR.get(analysis.concept_type, "Genel")

    lines = []
    lines.append(f"Kullanıcının Hukuki Sıfatı: {role_tr}")

    if analysis.legal_role == "belirsiz":
        lines.append(
            "⚠️  UYARI: Kullanıcının borç ilişkisindeki sıfatı (alacaklı/borçlu/kiracı vb.) "
            "belirtilmemiştir. Yanıtta bu sıfatı KESİNLİKLE varsayma. "
            "Genel bir çerçeve sun ve mümkünse kullanıcının sıfatını sor."
        )

    lines.append(f"Sorgunun Kavram Türü: {concept_tr}")

    if analysis.concept_type == "genel":
        lines.append(
            "⚠️  NOT: Sorgu henüz belirli bir hukuki kavram türüne atanmadı. "
            "Kaynakları değerlendirirken her maddenin HAK mı, YÜKÜMLÜLÜK mü, "
            "SORUMLULUK mu yoksa YETKİ mi düzenlediğini açıkça belirt. "
            "Bu kavramları birbirinin yerine KULLANMA."
        )

    if analysis.requires_clarification and analysis.ambiguity_type == "rol_belirsiz":
        lines.append(
            "📌 YANIT STRATEJİSİ: Önce borç ilişkisindeki hakların taraflara "
            "göre nasıl şekillendiğini genel hatlarıyla açıkla, ardından "
            "kullanıcının hangi sıfatla sorduğunu bir soru ile netleştir."
        )

    return "\n".join(lines)


def get_concept_distinction_rule() -> str:
    """
    Prompt'a eklenmek üzere HAK/YÜKÜMLÜLÜK/SORUMLULUK/YETKİ ayrım kuralını döndürür.
    """
    return (
        "KAVRAM AYRIMI KURALI:\n"
        "  HAK: Bir tarafın diğerinden talep edebileceği pozitif imkân (ör. ifa talebi, dönme).\n"
        "  YÜKÜMLÜLÜK: Bir tarafın yerine getirmesi gereken edim (ör. ödeme, teslim).\n"
        "  SORUMLULUK: Hukuka aykırı davranışın sonucunda ortaya çıkan tazminat/yaptırım yükü.\n"
        "  YETKİ: Belirli kişilere tanınan tek taraflı hukuki işlem yapma imkânı (ör. fesih yetkisi).\n"
        "  Bu kavramları birbirinin yerine kullanma. "
        "Bir madde 'sorumluluk' düzenliyorsa bunu 'hak' olarak sunma."
    )
