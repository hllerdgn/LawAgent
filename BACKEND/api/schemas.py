"""
api/schemas.py — LawAgent AI API Pydantic Şemaları
==================================================
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Soru-cevap istek gövdesi."""
    query: str = Field(..., description="Kullanıcının hukuki sorusu")
    k: int = Field(default=7, description="Retrieved chunk sayısı")
    session_id: str = Field(default="default", description="Oturum kimliği")
    client_id: Optional[str] = Field(default="lawagent-demo", description="Multi-tenant müşteri kimliği")


class AskResponse(BaseModel):
    """Soru-cevap yanıt modeli."""
    answer: str = Field(..., description="LLM tarafından üretilmiş hukuki yanıt")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Doğrulanmış kaynaklar")
    intent: Optional[str] = Field(default=None, description="Tespit edilen niyet")
    query_rewritten: Optional[str] = Field(default=None, description="Yeniden yazılmış sorgu")
    hallucination_check: Optional[Dict[str, Any]] = Field(default=None, description="Sadakat/halüsinasyon denetimi")
    sure_ms: int = Field(default=0, description="Toplam işlem süresi (milisaniye)")
    filtered: bool = Field(default=False, description="Kapsam dışı veya filtrelenmiş mi?")
    error: Optional[str] = Field(default=None, description="Hata mesajı (varsa)")


class DocumentUploadResponse(BaseModel):
    """PDF yükleme yanıtı."""
    status: str
    message: str
    chunks_added: int


class ClientConfigResponse(BaseModel):
    """Müşteri yapılandırma yanıtı."""
    id: str
    name: str
    theme: Optional[str] = "lumen"
    logo_url: Optional[str] = None
    welcome_message: Optional[str] = None
