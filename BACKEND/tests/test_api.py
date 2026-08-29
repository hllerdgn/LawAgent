"""
tests/test_api.py — API endpoint entegrasyon testleri
======================================================
Gerçek Groq/Qdrant bağlantısı gerektirmez (mock'lanmış).
"""

import pytest


pytestmark = pytest.mark.asyncio


# ── GET /health ───────────────────────────────────────────────────────────────

async def test_health_returns_200(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


# ── POST /ask — Başarılı yanıt ───────────────────────────────────────────────

async def test_ask_success(client):
    response = await client.post("/ask", json={
        "query": "Kira sözleşmesi nasıl feshedilir?",
        "session_id": "test-session",
        "k": 5,
    })
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert isinstance(data["sources"], list)


# ── POST /ask — Validation hataları ─────────────────────────────────────────

async def test_ask_empty_query_returns_422(client):
    """Boş query Pydantic min_length=2 ile 422 döndürmeli."""
    response = await client.post("/ask", json={"query": ""})
    assert response.status_code == 422


async def test_ask_single_char_query_returns_422(client):
    """1 karakter query 422 döndürmeli."""
    response = await client.post("/ask", json={"query": "a"})
    assert response.status_code == 422


async def test_ask_k_too_large_returns_422(client):
    """k > 20 → 422."""
    response = await client.post("/ask", json={"query": "test sorusu", "k": 100})
    assert response.status_code == 422


async def test_ask_k_zero_returns_422(client):
    """k < 1 → 422."""
    response = await client.post("/ask", json={"query": "test sorusu", "k": 0})
    assert response.status_code == 422


# ── POST /ask — Rate limit 429 ────────────────────────────────────────────────

async def test_ask_rate_limit_returns_429(client, mock_generator):
    """generate() 'rate_limit' hatası döndürünce /ask 429 vermeli."""
    original = mock_generator.generate.return_value
    mock_generator.generate.return_value = {
        "answer": "Kota aşıldı.",
        "sources": [],
        "error": "rate_limit",
    }
    response = await client.post("/ask", json={"query": "test sorusu"})
    assert response.status_code == 429
    # Sonraki testler için reset
    mock_generator.generate.return_value = original


# ── POST /ask — Timeout 408 ──────────────────────────────────────────────────

async def test_ask_timeout_returns_408(client, mock_generator):
    """generate() 'timeout' hatası döndürünce /ask 408 vermeli."""
    original = mock_generator.generate.return_value
    mock_generator.generate.return_value = {
        "answer": "Zaman aşımı.",
        "sources": [],
        "error": "timeout",
    }
    response = await client.post("/ask", json={"query": "test sorusu"})
    assert response.status_code == 408
    mock_generator.generate.return_value = original


# ── Admin endpoint'leri — Auth yokken 403 ────────────────────────────────────

async def test_upload_without_admin_key_returns_403(client, monkeypatch):
    """
    ADMIN_API_KEY ayarlıyken X-Admin-Key header olmadan 403 dönmeli.
    """
    from config import settings as settings_module
    monkeypatch.setattr(settings_module.settings, "ADMIN_API_KEY", "secret-key")

    # httpx ile multipart/form-data gönderi
    response = await client.post(
        "/upload-document",
        files={"file": ("test.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert response.status_code == 403


async def test_admin_stats_without_key_returns_403(client, monkeypatch):
    """ADMIN_API_KEY ayarlıyken /admin/stats → 403."""
    from config import settings as settings_module
    monkeypatch.setattr(settings_module.settings, "ADMIN_API_KEY", "secret-key")

    response = await client.get("/admin/stats")
    assert response.status_code == 403


async def test_admin_documents_list_without_key_returns_403(client, monkeypatch):
    """/admin/documents → 403."""
    from config import settings as settings_module
    monkeypatch.setattr(settings_module.settings, "ADMIN_API_KEY", "secret-key")

    response = await client.get("/admin/documents")
    assert response.status_code == 403


# ── Admin endpoint'leri — Doğru key ile 200 ──────────────────────────────────

async def test_admin_documents_list_with_valid_key(client, monkeypatch):
    """Doğru X-Admin-Key ile /admin/documents → 200."""
    from config import settings as settings_module
    monkeypatch.setattr(settings_module.settings, "ADMIN_API_KEY", "test-secret")

    response = await client.get(
        "/admin/documents",
        headers={"X-Admin-Key": "test-secret"},
    )
    assert response.status_code == 200
    assert "documents" in response.json()


# ── GET /health ───────────────────────────────────────────────────────────────

async def test_metrics_endpoint(client):
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "lawagent_sessions_total" in response.text
