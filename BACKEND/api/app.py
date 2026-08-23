"""
api/app.py — LawAgent AI FastAPI Uygulaması ve Router Kaydı
===========================================================
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.settings import settings
from core.logging import log
from api.schemas import AskRequest, AskResponse
from src.generator import LegalGenerator, get_retriever
import src.pdf_processor as pdf_processor


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_retriever()
    log.info("[Startup] LawAgent AI API başlatıldı.")
    yield
    from src.generator import _retriever_instance
    if _retriever_instance and hasattr(_retriever_instance, "qdrant"):
        _retriever_instance.qdrant.close()
    log.info("[Shutdown] LawAgent AI API kapatıldı.")


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

    gen = LegalGenerator(k=settings.DEFAULT_ASK_K)

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
        return JSONResponse(status_code=404, content={"detail": f"Client '{client_id}' bulunamadı."})

    # ── RAG Generation Endpoint ───────────────────────────────────────────────
    @app.post("/ask", response_model=AskResponse, tags=["RAG"])
    async def ask(req: AskRequest):
        """Kullanıcının hukuki sorusunu yanıtlar."""
        if not req.query.strip():
            return JSONResponse(status_code=400, content={"detail": "Sorgu boş olamaz."})
        result = gen.generate(req.query, session_id=req.session_id, k=req.k)
        return result

    # ── Belge / PDF Yönetimi ──────────────────────────────────────────────────
    @app.post("/upload-document", tags=["Documents"])
    async def upload_document(file: UploadFile = File(...)):
        """Kurumsal PDF belgesi yükler ve vektörleştirir."""
        if not file.filename.lower().endswith(".pdf"):
            return JSONResponse(status_code=400, content={"detail": "Sadece PDF dosyaları desteklenmektedir."})
        try:
            contents = await file.read()
            retriever = get_retriever()
            added_chunks = pdf_processor.process_and_index_pdf(
                contents,
                file.filename,
                retriever.embedder,
                retriever.qdrant
            )
            return {"status": "ok", "message": f"{file.filename} işlendi.", "chunks_added": added_chunks}
        except Exception as e:
            log.exception("PDF işleme hatası")
            return JSONResponse(status_code=500, content={"detail": f"Dosya işlenirken hata: {str(e)}"})

    @app.get("/admin/documents", tags=["Documents"])
    async def list_documents():
        """Yüklenmiş kurumsal belgeleri listeler."""
        docs = pdf_processor.get_uploaded_documents()
        return {"documents": docs}

    @app.delete("/admin/documents/{filename}", tags=["Documents"])
    async def delete_document(filename: str):
        """Yüklenmiş bir kurumsal belgeyi siler."""
        retriever = get_retriever()
        success = pdf_processor.delete_document(filename, retriever.qdrant)
        if success:
            return {"status": "ok", "message": f"{filename} silindi."}
        return JSONResponse(status_code=500, content={"detail": "Silme işlemi başarısız oldu."})

    # ── Health & Stats ────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health():
        """Hafif uptime denetim endpointi."""
        return {"status": "ok", "version": "6.0"}

    @app.get("/memory/{session_id}", tags=["Memory"])
    async def get_memory(session_id: str):
        """Oturum hafızasını döndürür."""
        history = gen.memory.get_history(session_id)
        return {
            "session_id": session_id,
            "message_count": len(history),
            "history": history,
        }

    @app.get("/admin/stats", tags=["Admin"])
    async def get_admin_stats():
        """Sistem kullanım istatistiklerini döndürür."""
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
                    if i + 1 < len(messages) and messages[i+1]["role"] == "assistant":
                        ans_text = messages[i+1]["content"]
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
                        "raw_date": raw_ts
                    })

        recent_queries.sort(key=lambda x: x["raw_date"], reverse=True)

        return {
            "site_docs": site_docs_count,
            "law_docs": law_docs_count,
            "total_questions": total_questions,
            "recent_queries": recent_queries[:10]
        }

    return app
