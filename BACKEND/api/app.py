"""
api/app.py — LawAgent AI FastAPI Uygulaması
============================================
"""

from datetime import datetime
from functools import lru_cache
from typing import Optional
from contextlib import asynccontextmanager

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from fastapi import FastAPI, Request, UploadFile, File, Depends, HTTPException, Security
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import APIKeyHeader

from config.settings import settings
from core.logging import log
from api.schemas import AskRequest, AskResponse
from src.generator import LegalGenerator, get_retriever
from src.admin.auth import verify_admin_key, check_admin_key_at_startup
from src.admin.routes import router as admin_router
from src.admin.document_routes import router as document_router


# ── Sentry Monitoring ─────────────────────────────────────────────────────────
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.2,
        environment=settings.ENV,
    )
    log.info("[Sentry] Error tracking aktif.")


# ── Dependency Injection ──────────────────────────────────────────────────────

@lru_cache()
def get_generator() -> LegalGenerator:
    """LegalGenerator singleton — testlerde override edilebilir."""
    return LegalGenerator(k=settings.DEFAULT_ASK_K)


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    check_admin_key_at_startup()   # Production'da key yoksa burada RuntimeError
    get_retriever()
    get_generator()
    log.info("[Startup] LawAgent AI API başlatıldı (v6.0).")
    yield
    from src.generator import _retriever_instance
    if _retriever_instance and hasattr(_retriever_instance, "qdrant"):
        _retriever_instance.qdrant.close()
    log.info("[Shutdown] LawAgent AI API kapatıldı.")


# ── Application Factory ───────────────────────────────────────────────────────

def create_application() -> FastAPI:
    """FastAPI uygulamasını oluşturur ve tüm middleware/route'ları bağlar."""
    app = FastAPI(
        title="LawAgent AI API",
        version="6.0",
        description="Türk Borçlar, Ticaret ve Tüketici Hukuku Asistanı API",
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Admin Router ─────────────────────────────────────────────────────────
    app.include_router(admin_router, prefix="/admin", tags=["Admin"])
    app.include_router(document_router, prefix="/admin", tags=["Documents"])
    # ── Global Exception Handler ──────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        log.exception(f"[GlobalHandler] Beklenmeyen hata: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Sunucu hatası. Lütfen tekrar deneyin."},
        )

    # ── RAG / Soru-Cevap ──────────────────────────────────────────────────────
    @app.post("/ask", response_model=AskResponse, tags=["RAG"])
    async def ask(req: AskRequest, gen: LegalGenerator = Depends(get_generator)):
        """Kullanıcının hukuki sorusunu yanıtlar."""
        result = await run_in_threadpool(gen.generate, req.query, req.session_id, req.k)

        error = result.get("error")
        if error == "rate_limit":
            raise HTTPException(status_code=429, detail=result.get("answer", "Kota aşıldı, lütfen bekleyin."))
        if error == "timeout":
            raise HTTPException(status_code=408, detail=result.get("answer", "Sunucu yanıt vermedi."))
        if error and error not in ("", None):
            raise HTTPException(status_code=500, detail=result.get("answer", "Teknik hata."))

        return result

    # ── Admin İstatistikleri ──────────────────────────────────────────────────
    @app.get("/admin/stats", tags=["Admin"])
    async def get_admin_stats(
        _: None = Depends(verify_admin_key),
        gen: LegalGenerator = Depends(get_generator),
    ):
        """Sistem kullanım istatistiklerini döndürür. [Admin]"""
        retriever = get_retriever()

        site_docs_count = 0
        try:
            site_docs_count = retriever.qdrant.count(settings.SITE_COLLECTION_NAME).count
        except Exception:
            pass

        law_docs_count = 0
        try:
            law_docs_count = retriever.qdrant.count(settings.COLLECTION_NAME).count
        except Exception:
            pass

        total_questions = 0
        recent_queries = []
        for session_id, messages in gen.memory.memory.items():
            for i, msg in enumerate(messages):
                if msg["role"] == "user":
                    total_questions += 1
                    ans = "Cevaplanmadı."
                    if i + 1 < len(messages) and messages[i + 1]["role"] == "assistant":
                        ans_text = messages[i + 1]["content"]
                        ans = ans_text[:220] + "..." if len(ans_text) > 220 else ans_text

                    raw_ts = msg["timestamp"]
                    formatted_date = raw_ts
                    try:
                        formatted_date = datetime.fromisoformat(raw_ts).strftime("%d-%m-%Y %H:%M")
                    except Exception:
                        pass

                    recent_queries.append({
                        "name": f"Oturum #{session_id[:6]}",
                        "subject": msg["content"],
                        "answer": ans,
                        "date": formatted_date,
                        "raw_date": raw_ts,
                    })

        recent_queries.sort(key=lambda x: x["raw_date"], reverse=True)

        return {
            "site_docs": site_docs_count,
            "law_docs": law_docs_count,
            "total_questions": total_questions,
            "recent_queries": recent_queries[:10],
        }

    # ── Oturum Hafızası ───────────────────────────────────────────────────────
    @app.get("/memory/{session_id}", tags=["Memory"])
    async def get_memory(session_id: str, gen: LegalGenerator = Depends(get_generator)):
        """Belirtilen oturumun konuşma geçmişini döndürür."""
        history = gen.memory.get_history(session_id)
        return {
            "session_id": session_id,
            "message_count": len(history),
            "history": history,
        }

    # ── Health & Metrics ──────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health():
        """Hafif uptime denetim endpointi."""
        return {"status": "ok", "version": "6.0"}

    @app.get("/metrics", tags=["Health"])
    async def metrics(gen: LegalGenerator = Depends(get_generator)):
        """Temel Prometheus text formatında metrikler."""
        total_sessions = len(gen.memory.memory)
        total_questions = sum(
            sum(1 for m in msgs if m["role"] == "user")
            for msgs in gen.memory.memory.values()
        )
        lines = [
            "# HELP lawagent_sessions_total Toplam oturum sayısı",
            "# TYPE lawagent_sessions_total gauge",
            f"lawagent_sessions_total {total_sessions}",
            "# HELP lawagent_questions_total Toplam soru sayısı",
            "# TYPE lawagent_questions_total counter",
            f"lawagent_questions_total {total_questions}",
        ]
        return Response(content="\n".join(lines), media_type="text/plain")

    return app
