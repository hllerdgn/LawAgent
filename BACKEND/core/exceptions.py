"""
core/exceptions.py — LawAgent AI Özel İstisna Sınıfları
======================================================
"""

class LawAgentException(Exception):
    """Tüm LawAgent istisnalarının temel sınıfı."""
    pass

class ConfigurationError(LawAgentException):
    """Eksik veya hatalı konfigürasyon hatası."""
    pass

class RetrievalError(LawAgentException):
    """Retrieval aşamasında (Qdrant/BM25/Reranker) oluşan hata."""
    pass

class LLMProviderError(LawAgentException):
    """LLM servisinden yanıt alınamadığında veya kota aşıldığında oluşan hata."""
    pass

class CitationValidationError(LawAgentException):
    """Atıf doğrulama veya kaynak eşleme hatası."""
    pass

class DocumentProcessingError(LawAgentException):
    """PDF işleme ve chunking hatası."""
    pass
