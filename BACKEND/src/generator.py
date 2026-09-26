"""
generator.py — LawAgent AI RAG Orchestration
=============================================
LegalGenerator sınıfı: Groq LLM + Qdrant retrieval pipeline yöneticisi.
API katmanı api/app.py içinde tanımlıdır.
"""

import os
import re
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from collections import defaultdict
from datetime import datetime

from dotenv import load_dotenv
from groq import Groq, APIStatusError, APITimeoutError, RateLimitError

from src.retriever import LegalRetriever
from src.legal_normalizer import full_post_process, normalize_legal_terminology, sanitize_markdown_typography
from src.citation_engine import build_grounded_context, validate_and_extract_citations
from src.legal_intent import analyze_legal_query, build_legal_role_context, get_concept_distinction_rule
from src.memory import ConversationMemory
from src.scope_checker import is_legal_query, is_in_scope_llm, get_route, KAPSAM_DISI_YANITI as _KAPSAM_DISI_YANITI
from src.pipeline.documents.doc_store import list_documents
from src.query_processor import is_ictihat_request, QueryIntentRouter, rewrite_query
from services.prompts import (
    SISTEM_PROMPT_TEMPLATE as _SISTEM_PROMPT_TEMPLATE,
    ICTIHAT_PROMPT_TEMPLATE as _ICTIHAT_PROMPT_TEMPLATE,
    SITE_SISTEM_PROMPT_TEMPLATE as _SITE_SISTEM_PROMPT_TEMPLATE,
)
from core.logging import log

# Env

_ENV_ADAYLARI = [
    Path("/content/drive/MyDrive/lawagent/.env"),
    Path(__file__).resolve().parent.parent.parent / ".env",
    Path(__file__).resolve().parent.parent / ".env",
    Path(__file__).resolve().parent / ".env",
]
for env_path in _ENV_ADAYLARI:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        log.info(f".env yüklendi: {env_path}")
        break

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
_DEFAULT_CONFIG_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

GROQ_FALLBACK_MODELS = [
    _DEFAULT_CONFIG_MODEL,
    "llama-3.3-70b-versatile",
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "groq/compound-mini",
]
_SEEN_MODELS = set()
GROQ_CANDIDATE_MODELS = []
for _m in GROQ_FALLBACK_MODELS:
    if _m and _m not in _SEEN_MODELS:
        _SEEN_MODELS.add(_m)
        GROQ_CANDIDATE_MODELS.append(_m)

_CURRENT_WORKING_MODEL = GROQ_CANDIDATE_MODELS[0]
MODEL_NAME = _CURRENT_WORKING_MODEL


def clean_llm_response(text: str) -> str:
    if not text:
        return ""
    # Strip closed <think>...</think> reasoning traces (multi-line)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Strip unclosed <think>... blocks (model forgot closing tag)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Strip any remaining stray tags
    text = re.sub(r"</think>", "", text, flags=re.IGNORECASE)
    return text.strip()


def call_groq_completion(
    client: Groq,
    messages: List[Dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 1000,
) -> str:
    global _CURRENT_WORKING_MODEL, MODEL_NAME
    models_to_try = [_CURRENT_WORKING_MODEL] + [
        m for m in GROQ_CANDIDATE_MODELS if m != _CURRENT_WORKING_MODEL
    ]

    last_err = None
    for model in models_to_try:
        for attempt in range(2):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                if model != _CURRENT_WORKING_MODEL:
                    log.info(f"Groq aktif modeli güncellendi: {model}")
                _CURRENT_WORKING_MODEL = model
                MODEL_NAME = model
                raw_content = resp.choices[0].message.content or ""
                return clean_llm_response(raw_content)
            except RateLimitError as rle:
                log.warning(f"Groq modeli '{model}' kota aşımı (429 RateLimit) aldı (deneme {attempt+1}): {rle}")
                last_err = rle
                time.sleep(1.0)
                if attempt == 1:
                    break
            except APITimeoutError as toe:
                log.warning(f"Groq modeli '{model}' zaman aşımına uğradı: {toe}")
                last_err = toe
                time.sleep(0.5)
                break
            except (APIStatusError, Exception) as e:
                err_msg = str(e).lower()
                if any(term in err_msg for term in ["not exist", "decommissioned", "not found", "404", "400", "invalid_request_error", "rate_limit", "429", "tokens per minute"]):
                    log.warning(f"Groq modeli '{model}' kullanılamadı ({e}), alternatif model deneniyor...")
                    last_err = e
                    break
                raise e

    if last_err:
        raise last_err
    raise RuntimeError("Uygun bir Groq modeli bulunamadı.")


if not GROQ_API_KEY:
    log.warning("GROQ_API_KEY bulunamadı! .env dosyasını kontrol et.")


# Hallüsinasyon Kontrolü


class HallucinationValidator:
    _MADDE_REF_PATTERN = re.compile(r"m(?:adde)?\.?\s*(\d+)", re.IGNORECASE)
    _KAPSAM_DISI_KANUNLAR = re.compile(
        r"\b(TMK|CMK|HMK|TCK|İYUK|İş\s*K\.?|4857|4721)\b", re.IGNORECASE
    )

    def __init__(self, client: Groq):
        self.client = client

    def extract_article_refs(self, text: str) -> List[str]:
        return [m.group(1) for m in self._MADDE_REF_PATTERN.finditer(text)]

    def extract_source_articles(self, chunks: List[Dict]) -> List[str]:
        return [str(c.get("article_no")).strip() for c in chunks if c.get("article_no")]

    def validate_faithfulness(
        self, answer: str, chunks: List[Dict]
    ) -> Tuple[bool, str, List[str]]:
        kapsam_disi = self._KAPSAM_DISI_KANUNLAR.findall(answer)
        if kapsam_disi:
            kanunlar = ", ".join(sorted(set(k.upper() for k in kapsam_disi)))
            return (
                False,
                f"⚠️ SİSTEM UYARISI: Yanıt, uzmanlık alanım dışındaki kanunlara ({kanunlar}) atıfta bulunuyor.",
                [],
            )
        if not chunks:
            return True, "", []
        source_articles = self.extract_source_articles(chunks)
        mentioned_articles = self.extract_article_refs(answer)
        if not source_articles:
            return True, "", mentioned_articles
        source_blob = " ".join(source_articles)
        for art in mentioned_articles:
            if art not in source_blob:
                return (
                    False,
                    f"⚠️ Uyarı: Yanıtta geçen madde numarası (m. {art}) veri tabanındaki kaynaklarda bulunamadı.",
                    [],
                )
        return True, "", mentioned_articles


def build_context(chunks: list, source_filter: Optional[str] = None) -> Tuple[str, Dict[str, Dict]]:
    return build_grounded_context(chunks, source_filter=source_filter)


# Singleton Retriever

_retriever_instance: Optional[LegalRetriever] = None


def get_retriever() -> LegalRetriever:
    global _retriever_instance
    if _retriever_instance is None:
        log.info("[Startup] Retriever yükleniyor (Quantized mode)...")
        _retriever_instance = LegalRetriever(quantize=True)
        log.info("[Startup] Retriever hazır.")
    return _retriever_instance


# Legal Generator


class LegalGenerator:
    def __init__(self, k: int = 7):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY bulunamadı.")
        self.client = Groq(api_key=GROQ_API_KEY)
        self.retriever = get_retriever()
        self.default_k = k
        self.memory = ConversationMemory(max_memory=4)
        self.intent_router = QueryIntentRouter(self.client)
        self.hallucination_validator = HallucinationValidator(self.client)

    # Aşama 2: İçtihat + Mevzuat kaynakları birlikte
    def _generate_ictihat_only(self, session_id: str) -> Dict[str, Any]:
        t0 = time.time()
        all_chunks = self.memory.get_chunks(session_id)
        ictihat_chunks = [
            c for c in all_chunks if str(c.get("source", "")).lower() == "yargitay"
        ]
        mevzuat_chunks = [
            c for c in all_chunks if str(c.get("source", "")).lower() != "yargitay"
        ]

        if ictihat_chunks:
            context_str, _ = build_context(ictihat_chunks)
            ictihat_prompt = _ICTIHAT_PROMPT_TEMPLATE.format(context=context_str)
            try:
                yanit = call_groq_completion(
                    client=self.client,
                    messages=[
                        {"role": "system", "content": ictihat_prompt},
                        {
                            "role": "user",
                            "content": "Lütfen ilgili Yargıtay kararlarını özetle.",
                        },
                    ],
                    temperature=0.1,
                    max_tokens=800,
                )
                yanit = full_post_process(yanit)
            except Exception as e:
                log.error(f"İçtihat üretim hatası: {e}")
                yanit = "İçtihat bilgilerini getirirken teknik bir sorun oluştu. Lütfen tekrar deneyin."
        else:
            yanit = "**Emsal Yargıtay Kararları**\n\nBu konuya dair veri tabanımda emsal karar bulunmamaktadır."

        combined_sources = []
        for c in mevzuat_chunks:
            combined_sources.append(
                {
                    "kanun": c.get("law") or "",
                    "madde": (
                        str(c.get("article_no"))
                        if c.get("article_no") is not None
                        else ""
                    ),
                    "ozet": c.get("text") or "",
                    "tip": "mevzuat",
                }
            )
        for c in ictihat_chunks:
            combined_sources.append(
                {
                    "kanun": "Yargıtay",
                    "madde": c.get("decision_id", ""),
                    "ozet": c.get("text") or "",
                    "tip": "ictihat",
                }
            )

        self.memory.add_exchange(session_id, "[İçtihat talebi]", yanit)
        return {
            "answer": yanit,
            "sources": combined_sources,
            "intent": "ICTIHAT_DETAIL",
            "sure_ms": int((time.time() - t0) * 1000),
            "filtered": False,
        }

    # Ana Generate
    def generate(
        self, sorgu: str, session_id: str = "default", k: Optional[int] = None
    ) -> Dict[str, Any]:
        t0 = time.time()
        sorgu_temiz = sorgu.lower().strip()
        history = self.memory.get_history(session_id)

        # 1. SELAMLAMA KONTROLÜ
        if sorgu_temiz in {"selam", "merhaba", "sa", "as", "günaydın", "iyi günler"}:
            greeting = (
                "Merhaba! Ben LawAgent AI. Türk Borçlar, Ticaret ve Tüketici Hukuku alanlarında size yardımcı olabilirim.\n\n"
                "**Size nasıl yardımcı olabilirim? Örneğin şunları sorabilirsiniz:**\n"
                "- 'Kira sözleşmemi nasıl feshedebilirim?'\n"
                "- 'İnternetten aldığım ürünü iade edebilir miyim?'\n"
                "- 'Borçlu temerrüdü nedir?'"
            )
            self.memory.add_exchange(session_id, sorgu, greeting)
            return {
                "answer": greeting,
                "sources": [],
                "filtered": False,
                "intent": "GREETING",
                "sure_ms": int((time.time() - t0) * 1000),
            }

        # 2. AŞAMA 2 KONTROLÜ (İçtihat talebi) – artık hukuki filtreden ÖNCE
        if is_ictihat_request(sorgu, history):
            log.info(f"[Aşama 2] İçtihat talebi yakalandı → session: {session_id}")
            return self._generate_ictihat_only(session_id)

        # Kayıtlı şirket dokümanlarını al
        company_docs = []
        try:
            company_docs = [d for d in list_documents() if d.status == "indexed"]
        except Exception as _de:
            log.warning(f"Doküman listesi alınamadı: {_de}")
        company_titles = [d.filename for d in company_docs]

        # 3. ÖN KAPSAM VE ROTA KONTROLÜ — LLM ile rota belirleme (company / legal / out_of_scope)
        route = get_route(self.client, sorgu, call_groq_completion, company_titles)
        if route == "out_of_scope":
            log.info(f"[Ön Filtre / Route] Kapsam dışı sorgu reddedildi: '{sorgu_temiz}'")
            self.memory.add_exchange(session_id, sorgu, _KAPSAM_DISI_YANITI)
            return {
                "answer": _KAPSAM_DISI_YANITI,
                "sources": [],
                "filtered": True,
                "intent": "OUT_OF_SCOPE",
                "sure_ms": int((time.time() - t0) * 1000),
            }

        # Şirket / büro belgesi rotası
        if route == "company":
            log.info(f"[Route] Şirket belgesi sorgusu yönlendirildi: '{sorgu_temiz}'")
            c_k = k or 5
            company_chunks = self.retriever.retrieve_company(sorgu, k=c_k)
            if not company_chunks:
                no_company_res = "Sorduğunuz konuyla ilgili şirket/avukat belgelerinde ilgili bir bilgi bulunamadı."
                self.memory.add_exchange(session_id, sorgu, no_company_res)
                return {
                    "answer": no_company_res,
                    "sources": [],
                    "intent": "COMPANY_DOCUMENTS",
                    "sure_ms": int((time.time() - t0) * 1000),
                    "filtered": False,
                }
            self.memory.save_chunks(session_id, company_chunks)
            context_str, source_map = build_context(company_chunks)
            sistem_prompt = _SITE_SISTEM_PROMPT_TEMPLATE.format(context=context_str)
            yanit = call_groq_completion(
                client=self.client,
                messages=[
                    {"role": "system", "content": sistem_prompt},
                    {"role": "user", "content": f"SORU: {sorgu}"},
                ],
                temperature=0.1,
                max_tokens=2500,
            )
            yanit = full_post_process(yanit)
            sanitized_yanit, validated_sources, is_grounded = validate_and_extract_citations(
                yanit, source_map, fallback_chunks=company_chunks
            )
            self.memory.add_exchange(session_id, sorgu, sanitized_yanit)
            return {
                "answer": sanitized_yanit,
                "sources": validated_sources,
                "intent": "COMPANY_DOCUMENTS",
                "sure_ms": int((time.time() - t0) * 1000),
                "filtered": False,
            }

        try:
            # Intent ve K
            intent, recommended_k = self.intent_router.detect_intent(sorgu)
            k = k or recommended_k or self.default_k

            # ── Legal Intent Analysis (sıfat, kavram, belirsizlik) ────────────
            legal_analysis = analyze_legal_query(sorgu)
            legal_role_ctx = build_legal_role_context(legal_analysis)
            concept_rule   = get_concept_distinction_rule()
            log.info(
                f"[LegalIntent] domain={legal_analysis.domain} "
                f"intent={legal_analysis.intent} role={legal_analysis.legal_role} "
                f"concept={legal_analysis.concept_type} "
                f"clarification={legal_analysis.requires_clarification}"
            )

            # Query rewrite
            yeni_sorgu = rewrite_query(self.client, sorgu, call_groq_completion)

            # Retrieval (doğrudan madde sorgusunda history devre dışı)
            history_context = self.memory.get_context_string(session_id)
            direct_article_match = re.search(
                r"(?:m\.|madde)?\s*\d+", sorgu, re.IGNORECASE
            )
            if direct_article_match:
                retrieval_sorgu = sorgu
                log.info(
                    "[Retrieval] Doğrudan madde sorgusu, history_context kullanılmadı."
                )
            else:
                retrieval_sorgu = (
                    f"{history_context}{sorgu}".strip() if history_context else sorgu
                )

            chunks = self.retriever.retrieve(retrieval_sorgu, k=k)

            # Hybrid Retrieval: Sadece sorguda şirket/avukat/büro sinyali varsa veya şirket dokümanı ismi geçiyorsa company_corpus'tan top-2 chunk eklenir
            is_hybrid_query = any(
                kw in sorgu.lower()
                for kw in ["avukat", "şirket", "büro", "müvekkil", "danışman", "tarafımız", "bizim", "iç tüzük", "politika"]
                + [t.lower() for t in company_titles]
            )
            if company_titles and is_hybrid_query:
                try:
                    comp_hybrid = self.retriever.retrieve_company(sorgu, k=2)
                    for ch in comp_hybrid:
                        if ch.get("skor", 0) > 0.35:
                            chunks.append(ch)
                except Exception as _he:
                    log.warning(f"Hybrid retrieval hatası: {_he}")

            # Fallback
            if len(chunks) < 3 and yeni_sorgu != sorgu:
                ek = self.retriever.retrieve(sorgu, k=k)
                mevcut = {c["chunk_id"] for c in chunks}
                for c in ek:
                    if c["chunk_id"] not in mevcut:
                        chunks.append(c)
                chunks = chunks[:k]

            # Site document kontrolü
            has_site_doc = any(c.get("source") in ("site_document", "company_document") for c in chunks)

            # OUT_OF_SCOPE
            if not chunks:
                no_result = (
                    "Üzgünüm, bu konu (Aile Hukuku/Ceza Hukuku vb.) uzmanlık alanım olan "
                    "TBK, TTK ve TKHK dışında kalmaktadır. Veri tabanımda bu konuya dair "
                    "bir madde bulunmadığı için hukuki değerlendirme yapamam."
                )
                self.memory.add_exchange(session_id, sorgu, no_result)
                return {
                    "answer": no_result,
                    "sources": [],
                    "intent": "OUT_OF_SCOPE",
                    "sure_ms": int((time.time() - t0) * 1000),
                    "filtered": False,
                }

            # Tüm chunk'ları belleğe kaydet (içtihat aşaması için)
            self.memory.save_chunks(session_id, chunks)

            # Mevzuat veya Site Belgesi odaklı yapılandırılmış bağlam
            context_str, source_map = build_context(chunks)
            if has_site_doc:
                sistem_prompt = _SITE_SISTEM_PROMPT_TEMPLATE.format(context=context_str)
            else:
                sistem_prompt = _SISTEM_PROMPT_TEMPLATE.format(
                    context=context_str,
                    legal_role_context=legal_role_ctx,
                    concept_distinction_rule=concept_rule,
                )

            yanit = call_groq_completion(
                client=self.client,
                messages=[
                    {"role": "system", "content": sistem_prompt},
                    {"role": "user", "content": f"SORU: {sorgu}"},
                ],
                temperature=0.1,
                max_tokens=2500,
            )

            # Yanıt boş geldiyse (think bloğu token limitini doldurdu) → sonraki modelle yeniden dene
            if not yanit.strip():
                log.warning("[Yanıt] Boş yanıt alındı, sonraki modelle yeniden deneniyor...")
                _next_models = [m for m in GROQ_CANDIDATE_MODELS if m != MODEL_NAME]
                for _fallback in _next_models:
                    try:
                        import groq as _groq_mod
                        _fb_client = _groq_mod.Groq(api_key=GROQ_API_KEY)
                        _fb_resp = _fb_client.chat.completions.create(
                            model=_fallback,
                            messages=[
                                {"role": "system", "content": sistem_prompt},
                                {"role": "user", "content": f"SORU: {sorgu}"},
                            ],
                            temperature=0.1,
                            max_tokens=2500,
                        )
                        _fb_yanit = clean_llm_response(_fb_resp.choices[0].message.content or "")
                        if _fb_yanit.strip():
                            yanit = _fb_yanit
                            log.info(f"[Yanıt] Fallback model '{_fallback}' ile yanıt alındı.")
                            break
                    except Exception as _fb_err:
                        log.warning(f"[Yanıt] Fallback '{_fallback}' başarısız: {_fb_err}")
                        continue

            # ── 1. Post-Processing (Terminoloji ve Tipografi Normalizasyonu) ──
            yanit = full_post_process(yanit)

            # ── 2. Deterministik Atıf Doğrulama & Kaynak Eşleme ─────────────
            sanitized_yanit, validated_sources, is_grounded = validate_and_extract_citations(
                yanit, source_map, fallback_chunks=chunks
            )
            yanit = sanitized_yanit

            # ── 3. Hallüsinasyon Kontrolü ────────────────────────────────────
            is_faithful, validation_warning, _ = (
                self.hallucination_validator.validate_faithfulness(yanit, chunks)
            )
            if not is_faithful and validation_warning:
                yanit = yanit + f"\n\n{validation_warning}"

            log.info(
                f"[Aşama 1] Başarılı: intent={intent}, k={k}, faithful={is_faithful}, sources={len(validated_sources)}"
            )
            self.memory.add_exchange(session_id, sorgu, yanit)

            return {
                "answer": yanit,
                "sources": validated_sources,
                "intent": intent,
                "query_rewritten": yeni_sorgu if yeni_sorgu != sorgu else None,
                "hallucination_check": {
                    "is_faithful": is_faithful,
                    "warning": validation_warning,
                    "is_grounded": is_grounded,
                },
                "sure_ms": int((time.time() - t0) * 1000),
                "filtered": False,
            }

        except RateLimitError:
            return {
                "answer": "Şu an çok fazla istek alıyorum, lütfen birkaç saniye sonra tekrar deneyin.",
                "sources": [],
                "error": "rate_limit",
            }
        except APITimeoutError:
            return {
                "answer": "Sunucu yanıt vermedi, lütfen tekrar deneyin.",
                "sources": [],
                "error": "timeout",
            }
        except Exception as e:
            log.exception(f"Kritik Hata: {e}")
            return {
                "answer": "Teknik bir aksaklık oluştu. Lütfen tekrar deneyin.",
                "sources": [],
                "error": str(e),
            }


