"""
infrastructure/groq_client.py — LawAgent Groq LLM İstemcisi ve Fallback Yönetimi
================================================================================
"""

import re
import time
from typing import List, Dict, Optional
from groq import Groq, APIStatusError, APITimeoutError, RateLimitError

from config.settings import settings
from core.logging import log
from core.exceptions import LLMProviderError


class GroqClientProvider:
    """
    Groq LLM istemcisi, reasoning tag temizleyici ve çoklu model fallback yöneticisi.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        if not self.api_key:
            log.warning("[GroqClient] GROQ_API_KEY tanımlı değil!")
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        
        # Benzersiz fallback model listesi
        seen = set()
        self.candidate_models = []
        for m in settings.GROQ_FALLBACK_MODELS:
            if m and m not in seen:
                seen.add(m)
                self.candidate_models.append(m)
                
        self.current_model = self.candidate_models[0] if self.candidate_models else "llama-3.3-70b-versatile"

    @staticmethod
    def clean_llm_response(text: str) -> str:
        """<think>...</think> reasoning bloklarını ve artık etiketleri temizler."""
        if not text:
            return ""
        # Kapalı think bloklarını temizle
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        # Kapanmamış think bloklarını temizle (token limiti nedeniyle)
        text = re.sub(r"<think>.*", "", text, flags=re.DOTALL | re.IGNORECASE)
        # Stray kapatma taglerini temizle
        text = re.sub(r"</think>", "", text, flags=re.IGNORECASE)
        return text.strip()

    def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2500,
    ) -> str:
        """
        Mesaj listesini Groq API'ye gönderir. Model hatası veya kota aşımında
        yedek modelleri sırayla dener.
        """
        if not self.client:
            raise LLMProviderError("GROQ_API_KEY bulunamadı, LLM çağrısı yapılamıyor.")

        models_to_try = [self.current_model] + [
            m for m in self.candidate_models if m != self.current_model
        ]

        last_err = None
        for model in models_to_try:
            for attempt in range(2):
                try:
                    resp = self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    if model != self.current_model:
                        log.info(f"[GroqClient] Aktif model güncellendi: {model}")
                        self.current_model = model

                    raw = resp.choices[0].message.content or ""
                    cleaned = self.clean_llm_response(raw)
                    if cleaned:
                        return cleaned
                    # Eğer think bloğu temizlenince içerik boş kaldıysa sonraki modele geç
                    log.warning(f"[GroqClient] Model '{model}' boş yanıt üretti, fallback deneniyor...")
                    break
                except RateLimitError as rle:
                    log.warning(f"[GroqClient] Model '{model}' kota aşımı (429): {rle}")
                    last_err = rle
                    time.sleep(1.0)
                    if attempt == 1:
                        break
                except APITimeoutError as toe:
                    log.warning(f"[GroqClient] Model '{model}' zaman aşımı: {toe}")
                    last_err = toe
                    time.sleep(0.5)
                    break
                except (APIStatusError, Exception) as e:
                    err_msg = str(e).lower()
                    if any(term in err_msg for term in ["not exist", "decommissioned", "not found", "404", "400", "invalid_request_error", "rate_limit", "429", "tokens per minute"]):
                        log.warning(f"[GroqClient] Model '{model}' kullanılamadı ({e}), alternatif deneniyor...")
                        last_err = e
                        break
                    raise LLMProviderError(f"Groq API kritik hata: {e}") from e

        if last_err:
            raise LLMProviderError(f"Tüm Groq modelleri başarısız oldu. Son hata: {last_err}")
        raise LLMProviderError("Uygun bir Groq modeli bulunamadı.")


# Singleton instance
_groq_provider: Optional[GroqClientProvider] = None

def get_groq_provider() -> GroqClientProvider:
    global _groq_provider
    if _groq_provider is None:
        _groq_provider = GroqClientProvider()
    return _groq_provider
