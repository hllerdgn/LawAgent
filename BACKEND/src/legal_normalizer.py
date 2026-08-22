"""
legal_normalizer.py — LawAgent AI Kanun ve Terminoloji Normalizasyonu
======================================================================
Bu modül, model çıktılarında oluşabilecek gayriresmi terimleri, çeviri
bozulmalarını (ör. 'Konsum Kanunu') ve Markdown biçimlendirme hatalarını
deterministik olarak düzeltir.
"""

import re
from typing import Dict, List, Tuple

# ── Canonical Law Mappings ───────────────────────────────────────────────────
CANONICAL_LAW_NAMES: Dict[str, str] = {
    "TKHK": "6502 sayılı Tüketicinin Korunması Hakkında Kanun",
    "TBK": "6098 sayılı Türk Borçlar Kanunu",
    "TTK": "6102 sayılı Türk Ticaret Kanunu",
    "TMK": "4721 sayılı Türk Medeni Kanunu",
    "İİK": "2004 sayılı İcra ve İflas Kanunu",
    "IIK": "2004 sayılı İcra ve İflas Kanunu",
    "HMK": "6100 sayılı Hukuk Muhakemeleri Kanunu",
}

# Yanlış / Gayriresmi terimlerin resmi karşılıkları
TERMINOLOGY_REPLACEMENTS: List[Tuple[re.Pattern, str]] = [
    # Çeviri / LLM Bozulmaları
    (re.compile(r"\bTürk\s+Konsum\s+Kanunu\b", re.IGNORECASE), "6502 sayılı Tüketicinin Korunması Hakkında Kanun (TKHK)"),
    (re.compile(r"\bKonsum\s+Kanunu\b", re.IGNORECASE), "Tüketicinin Korunması Hakkında Kanun"),
    (re.compile(r"\bTüketiciyi\s+Koruma\s+Kanunu\b", re.IGNORECASE), "6502 sayılı Tüketicinin Korunması Hakkında Kanun (TKHK)"),
    (re.compile(r"\bTüketici\s+Kanunu\b", re.IGNORECASE), "6502 sayılı Tüketicinin Korunması Hakkında Kanun (TKHK)"),
    (re.compile(r"\bBorçlar\s+Hukuku\s+Kanunu\b", re.IGNORECASE), "6098 sayılı Türk Borçlar Kanunu (TBK)"),
    (re.compile(r"\bTicaret\s+Hukuku\s+Kanunu\b", re.IGNORECASE), "6102 sayılı Türk Ticaret Kanunu (TTK)"),
    (re.compile(r"\bMedeni\s+Hukuk\s+Kanunu\b", re.IGNORECASE), "4721 sayılı Türk Medeni Kanunu (TMK)"),
]

# Liste ve Tipografi Temizliği
TYPOGRAPHY_REPLACEMENTS: List[Tuple[re.Pattern, str]] = [
    # Bitişik bullet temizliği: "•6502" -> "- 6502"
    (re.compile(r"^[•·\*]\s*(\d{4})", re.MULTILINE), r"- \1"),
    (re.compile(r"^[•·]\s*", re.MULTILINE), "- "),
    # Bozuk çift parantez veya boşluklar
    (re.compile(r"\(\s*\)"), ""),
    (re.compile(r"[ \t]+$"), ""),
]


def normalize_legal_terminology(text: str) -> str:
    """Metindeki tüm hatalı hukuk terimlerini resmi canonical karşılıklarıyla değiştirir."""
    if not text:
        return ""
    
    normalized = text
    for pattern, replacement in TERMINOLOGY_REPLACEMENTS:
        normalized = pattern.sub(replacement, normalized)
        
    return normalized


def sanitize_markdown_typography(text: str) -> str:
    """Markdown liste imlerini, tireleme ve satır sonu boşluklarını temizler."""
    if not text:
        return ""
        
    cleaned = text
    for pattern, replacement in TYPOGRAPHY_REPLACEMENTS:
        cleaned = pattern.sub(replacement, cleaned)
        
    # Çoklu ardışık boş satırları en fazla 2'ye indir
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def full_post_process(text: str) -> str:
    """Terminoloji ve tipografi normalizasyonunu birlikte çalıştırır."""
    text = normalize_legal_terminology(text)
    text = sanitize_markdown_typography(text)
    return text
