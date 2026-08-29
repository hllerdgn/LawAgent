"""
tests/test_hallucination_validator.py — HallucinationValidator birim testleri
=============================================================================
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# src/ ve BACKEND/ path
_BACKEND = str(Path(__file__).resolve().parent.parent)
_SRC = str(Path(__file__).resolve().parent.parent / "src")
for _p in [_BACKEND, _SRC]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src.generator import HallucinationValidator


@pytest.fixture
def validator():
    mock_client = MagicMock()
    return HallucinationValidator(client=mock_client)


def test_extract_article_refs(validator):
    text = "TBK m.117 uyarınca borçlu temerrüde düşer. Madde 120 ve m. 52 kapsamında..."
    refs = validator.extract_article_refs(text)
    assert "117" in refs
    assert "120" in refs
    assert "52" in refs


def test_validate_faithfulness_out_of_scope_laws(validator):
    answer = "Bu durum TMK uyarınca velayet hakkını etkiler."
    chunks = [{"article_no": "117", "text": "...", "law": "TBK"}]
    is_faithful, warning, articles = validator.validate_faithfulness(answer, chunks)
    assert is_faithful is False
    assert "uzmanlık alanım dışındaki kanunlara" in warning


def test_validate_faithfulness_unsupported_article_number(validator):
    answer = "TBK m. 999 uyarınca tazminat ödenir."
    chunks = [{"article_no": "117", "text": "...", "law": "TBK"}]
    is_faithful, warning, articles = validator.validate_faithfulness(answer, chunks)
    assert is_faithful is False
    assert "m. 999" in warning


def test_validate_faithfulness_success(validator):
    answer = "TBK m. 117 gereğince temerrüt gerçekleşir."
    chunks = [{"article_no": "117", "text": "...", "law": "TBK"}]
    is_faithful, warning, articles = validator.validate_faithfulness(answer, chunks)
    assert is_faithful is True
    assert warning == ""
    assert "117" in articles
