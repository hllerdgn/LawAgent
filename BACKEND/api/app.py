"""
api/app.py — LawAgent AI FastAPI Uygulaması ve Router Kaydı
===========================================================
"""

import json
from datetime import datetime
from functools import lru_cache
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from fastapi import FastAPI, Request, Response, UploadFile, File, Depends, HTTPException, Security
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from config.settings import settings
from core.logging import log
from api.schemas import AskRequest, AskResponse
from src.generator import LegalGenerator, get_retriever
import src.pdf_processor as pdf_processor


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
    """LegalGenerator singleton'ı döndürür — test'lerde override edilebilir."""
    return LegalGenerator(k=settings.DEFAULT_ASK_K)


# ── Admin Authentication ──────────────────────────────────────────────────────

_admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


async def verify_admin_key(key: Optional[str] = Security(_admin_key_header)) -> None:
    """
    X-Admin-Key header ile admin işlemlerini korur.
    ADMIN_API_KEY ayarlanmamışsa admin endpoint'leri korumasız çalışır (dev modu).
    """
    if not settings.ADMIN_API_KEY:
        # Dev ortamı: anahtar ayarlanmamış → izin ver (ama startup'ta uyarı verildi)
        return
    if key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Geçersiz admin anahtarı.")


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
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

    # ── CORS Middleware ───────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def handle_options(request: Request, call_next):
        if request.method == "OPTIONS":
            return Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                },
            )
        return await call_next(request)

    # ── Global Exception Handler ──────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        log.exception(f"[GlobalHandler] Beklenmeyen hata: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Sunucu hatası. Lütfen tekrar deneyin."},
        )

    # ── Multi-Tenant / Client Endpoints ───────────────────────────────────────
    def _load_clients_json() -> Dict[str, Any]:
        clients_file = settings.CLIENTS_FILE
        if clients_file.exists():
            try:
                with open(clients_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                log.error(f"clients.json okunurken hata: {e}")
        return {}

    @app.get("/clients", tags=["Clients"])
    async def get_clients():
        """Tüm kayıtlı kurumsal istemcileri döndürür."""
        clients = _load_clients_json()
        return {"clients": list(clients.values())}

    @app.get("/clients/{client_id}", tags=["Clients"])
    async def get_client_config(client_id: str):
        """Belirtilen client_id için marka yapılandırmasını döndürür."""
        clients = _load_clients_json()
        if client_id in clients:
            return clients[client_id]
        if "lawagent-demo" in clients:
            return clients["lawagent-demo"]
        raise HTTPException(status_code=404, detail=f"Client '{client_id}' bulunamadı.")

    # ── RAG Generation Endpoints (Root & v1 Versioning) ───────────────────────
    @app.post("/ask", response_model=AskResponse, tags=["RAG"])
    @app.post("/v1/ask", response_model=AskResponse, tags=["RAG"], include_in_schema=True)
    async def ask(req: AskRequest, gen: LegalGenerator = Depends(get_generator)):
        """Kullanıcının hukuki sorusunu yanıtlar (v1 API)."""
        # CPU-bound generate() → threadpool (event loop serbest kalır)
        result = await run_in_threadpool(gen.generate, req.query, req.session_id, req.k)

        error = result.get("error")
        if error == "rate_limit":
            raise HTTPException(status_code=429, detail=result.get("answer", "Kota aşıldı, lütfen bekleyin."))
        if error == "timeout":
            raise HTTPException(status_code=408, detail=result.get("answer", "Sunucu yanıt vermedi."))
        if error and error not in ("", None):
            raise HTTPException(status_code=500, detail=result.get("answer", "Teknik hata."))

        return result

    # ── Belge / PDF Yönetimi (Admin Korumalı) ────────────────────────────────
    @app.post("/upload-document", tags=["Documents"])
    async def upload_document(
        file: UploadFile = File(...),
        _: None = Depends(verify_admin_key),
    ):
        """Kurumsal PDF belgesi yükler ve vektörleştirir. [Admin]"""
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Sadece PDF dosyaları desteklenmektedir.")
        try:
            contents = await file.read()
            retriever = get_retriever()
            added_chunks = pdf_processor.process_and_index_pdf(
                contents,
                file.filename,
                retriever.embedder,
                retriever.qdrant,
            )
            return {"status": "ok", "message": f"{file.filename} işlendi.", "chunks_added": added_chunks}
        except Exception as e:
            log.exception("PDF işleme hatası")
            raise HTTPException(status_code=500, detail=f"Dosya işlenirken hata: {str(e)}")

    @app.get("/admin/documents", tags=["Documents"])
    async def list_documents(_: None = Depends(verify_admin_key)):
        """Yüklenmiş kurumsal belgeleri listeler. [Admin]"""
        docs = pdf_processor.get_uploaded_documents()
        return {"documents": docs}

    @app.delete("/admin/documents/{filename}", tags=["Documents"])
    async def delete_document(filename: str, _: None = Depends(verify_admin_key)):
        """Yüklenmiş bir kurumsal belgeyi siler. [Admin]"""
        retriever = get_retriever()
        success = pdf_processor.delete_document(filename, retriever.qdrant)
        if success:
            return {"status": "ok", "message": f"{filename} silindi."}
        raise HTTPException(status_code=500, detail="Silme işlemi başarısız oldu.")

    # ── Health & Stats ────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health():
        """Hafif uptime denetim endpointi."""
        return {"status": "ok", "version": "6.0"}

    @app.get("/memory/{session_id}", tags=["Memory"])
    async def get_memory(session_id: str, gen: LegalGenerator = Depends(get_generator)):
        """Oturum hafızasını döndürür."""
        history = gen.memory.get_history(session_id)
        return {
            "session_id": session_id,
            "message_count": len(history),
            "history": history,
        }

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
            for i in range(len(messages)):
                if messages[i]["role"] == "user":
                    total_questions += 1
                    ans = "Cevaplanmadı."
                    if i + 1 < len(messages) and messages[i + 1]["role"] == "assistant":
                        ans_text = messages[i + 1]["content"]
                        ans = ans_text[:220] + "..." if len(ans_text) > 220 else ans_text

                    raw_ts = messages[i]["timestamp"]
                    formatted_date = raw_ts
                    try:
                        dt = datetime.fromisoformat(raw_ts)
                        formatted_date = dt.strftime("%d-%m-%Y %H:%M")
                    except Exception:
                        pass

                    recent_queries.append({
                        "name": f"Oturum #{session_id[:6]}",
                        "subject": messages[i]["content"],
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

    # ── Prometheus-style Metrics ──────────────────────────────────────────────
    @app.get("/metrics", tags=["Health"])
    async def metrics(gen: LegalGenerator = Depends(get_generator)):
        """
        Temel Prometheus text formatında metrikler.
        Üretim ortamında prometheus-client entegrasyonu ile genişletilebilir.
        """
        total_sessions = len(gen.memory.memory)
        total_messages = sum(len(msgs) for msgs in gen.memory.memory.values())
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
