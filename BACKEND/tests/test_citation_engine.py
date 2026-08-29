"""
tests/test_citation_engine.py — citation_engine modülü birim testleri
=====================================================================
Deterministik fonksiyonlar oldukları için LLM/DB mock gerektirmez.
"""

import sys
from pathlib import Path

import pytest

# src/ ve BACKEND/ path
_BACKEND = str(Path(__file__).resolve().parent.parent)
_SRC = str(Path(__file__).resolve().parent.parent / "src")
for _p in [_BACKEND, _SRC]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from citation_engine import (
    build_grounded_context,
    validate_and_extract_citations,
    get_canonical_law_title,
)


# ── get_canonical_law_title ───────────────────────────────────────────────────

def test_canonical_title_tbk():
    assert "6098" in get_canonical_law_title("TBK")


def test_canonical_title_tkhk():
    assert "6502" in get_canonical_law_title("TKHK")


def test_canonical_title_unknown_returns_raw():
    result = get_canonical_law_title("XYZ")
    assert result == "XYZ"


def test_canonical_title_empty():
    result = get_canonical_law_title("")
    assert isinstance(result, str)


# ── build_grounded_context ────────────────────────────────────────────────────

def test_build_context_assigns_k1_k2():
    chunks = [
        {"law": "TBK", "article_no": 117, "text": "Temerrüt...", "source": "mevzuat"},
        {"law": "TBK", "article_no": 118, "text": "Alacaklı...", "source": "mevzuat"},
    ]
    context_str, source_map = build_grounded_context(chunks)
    assert "K1" in source_map
    assert "K2" in source_map
    assert "[KAYNAK K1]" in context_str
    assert "[KAYNAK K2]" in context_str


def test_build_context_yargitay_chunk():
    chunks = [
        {"source": "YARGITAY", "decision_id": "3. HD E.2021/100 K.2021/200", "text": "Emsal..."},
    ]
    context_str, source_map = build_grounded_context(chunks)
    assert "K1" in source_map
    assert "Yargıtay" in context_str or "YARGITAY" in context_str


def test_build_context_empty_chunks():
    context_str, source_map = build_grounded_context([])
    assert source_map == {}
    assert "HUKUKI_KAYNAKLAR" in context_str


# ── validate_and_extract_citations ───────────────────────────────────────────

def _make_source_map():
    return {
        "K1": {"law": "TBK", "article_no": 117, "text": "Borçlu temerrüdü...", "source": "mevzuat"},
        "K2": {"law": "TKHK", "article_no": 11, "text": "Ayıplı mal...", "source": "mevzuat"},
    }


def test_valid_citations_returned():
    answer = "TBK m.117 uyarınca [K1] borçlu temerrüde düşer. Ayrıca [K2] geçerlidir."
    source_map = _make_source_map()
    sanitized, sources, is_grounded = validate_and_extract_citations(answer, source_map)
    assert is_grounded is True
    assert len(sources) == 2
    assert any(s["madde"] == "117" for s in sources)


def test_fake_citation_removed():
    """[K99] source_map'te yok → yanıttan temizlenmeli, is_grounded=False."""
    answer = "Bu maddeye göre [K99] sorumluluk doğar."
    source_map = _make_source_map()
    sanitized, sources, is_grounded = validate_and_extract_citations(answer, source_map)
    assert "[K99]" not in sanitized
    assert is_grounded is False


def test_no_citations_in_answer():
    answer = "Borçlu temerrüde düşebilir."
    source_map = _make_source_map()
    sanitized, sources, is_grounded = validate_and_extract_citations(answer, source_map)
    # Etiket yok → grounded sayılır (invalid tag yok)
    assert is_grounded is True


def test_empty_answer():
    sanitized, sources, is_grounded = validate_and_extract_citations("", {})
    assert sanitized == ""
    assert sources == []
    assert is_grounded is False


def test_partial_grounding():
    """K1 geçerli, K3 geçersiz → is_grounded=False."""
    answer = "Yanıt [K1] ve [K3] dayanır."
    source_map = _make_source_map()
    sanitized, sources, is_grounded = validate_and_extract_citations(answer, source_map)
    assert is_grounded is False
    assert "[K3]" not in sanitized
    assert len(sources) >= 1
