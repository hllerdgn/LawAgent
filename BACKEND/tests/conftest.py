"""
tests/conftest.py — Test fikstürleri ve mock kurulumu
======================================================
Groq ve Qdrant gibi harici servisler mock'lanır,
böylece testler ağ bağlantısı gerektirmeden çalışır.
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# BACKEND kök dizinini path'e ekle
_BACKEND = str(Path(__file__).resolve().parent.parent)
_SRC = str(Path(__file__).resolve().parent.parent / "src")
for _p in [_BACKEND, _SRC]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ── Mock LegalGenerator ───────────────────────────────────────────────────────

def _make_mock_generator() -> MagicMock:
    """LegalGenerator'ın minimal mock'unu oluşturur."""
    gen = MagicMock()
    gen.memory = MagicMock()
    gen.memory.get_history.return_value = []
    gen.memory.memory = {}
    gen.generate.return_value = {
        "answer": "Mock hukuki yanıt.",
        "sources": [{"kanun": "TBK", "madde": "117", "ozet": "...", "tip": "mevzuat"}],
        "intent": "INFO_RETRIEVAL",
        "query_rewritten": None,
        "hallucination_check": {"is_faithful": True, "warning": "", "is_grounded": True},
        "sure_ms": 100,
        "filtered": False,
        "error": None,
    }
    return gen


def _make_mock_retriever() -> MagicMock:
    """LegalRetriever'ın minimal mock'unu oluşturur."""
    retriever = MagicMock()
    retriever.qdrant = MagicMock()
    retriever.qdrant.count.return_value = MagicMock(count=42)
    retriever.embedder = MagicMock()
    return retriever


# ── App Fixture ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def mock_generator():
    return _make_mock_generator()


@pytest.fixture(scope="session")
def mock_retriever():
    return _make_mock_retriever()


@pytest.fixture(scope="session")
def app(mock_generator, mock_retriever):
    """
    Test için FastAPI uygulaması — Groq ve Qdrant mock'lanmış.
    get_generator() ve get_retriever() dependency'leri override edilir.
    """
    # Heavy imports'ları mock'la — model yüklemeyi engelle
    with patch.dict("sys.modules", {
        "sentence_transformers": MagicMock(),
        "torch": MagicMock(),
        "transformers": MagicMock(),
        "qdrant_client": MagicMock(),
        "groq": MagicMock(),
    }):
        from api.app import create_application, get_generator, get_retriever

        application = create_application()

        # DI override
        application.dependency_overrides[get_generator] = lambda: mock_generator
        application.dependency_overrides[get_retriever] = lambda: mock_retriever

        yield application


@pytest_asyncio.fixture(scope="session")
async def client(app):
    """AsyncClient ile test HTTP istemcisi."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
