"""
generator.py — LawAgent AI Backend API

"""

import os
import re
import time
import argparse
import logging
from typing import Optional, Dict, Any, List, Tuple
from contextlib import asynccontextmanager
from pathlib import Path
from collections import defaultdict
from datetime import datetime

from dotenv import load_dotenv
from groq import Groq, APIStatusError, APITimeoutError, RateLimitError
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from retriever import LegalRetriever

# Logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("LawAgent.Generator.v5.8")

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
MODEL_NAME = "llama-3.3-70b-versatile"

if not GROQ_API_KEY:
    log.warning("GROQ_API_KEY bulunamadı! .env dosyasını kontrol et.")


# Session Memory


class ConversationMemory:
    def __init__(self, max_memory: int = 4):
        self.memory: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        self.last_chunks: Dict[str, List[Dict]] = defaultdict(list)
        self.max_memory = max_memory

    def add_exchange(self, session_id: str, user_msg: str, assistant_msg: str):
        if session_id not in self.memory:
            self.memory[session_id] = []
        self.memory[session_id].append(
            {
                "role": "user",
                "content": user_msg,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self.memory[session_id].append(
            {
                "role": "assistant",
                "content": assistant_msg,
                "timestamp": datetime.now().isoformat(),
            }
        )
        if len(self.memory[session_id]) > self.max_memory * 2:
            self.memory[session_id] = self.memory[session_id][-(self.max_memory * 2) :]

    def save_chunks(self, session_id: str, chunks: List[Dict]):
        self.last_chunks[session_id] = chunks

    def get_chunks(self, session_id: str) -> List[Dict]:
        return self.last_chunks.get(session_id, [])

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        return self.memory.get(session_id, [])

    def get_context_string(self, session_id: str) -> str:
        history = self.get_history(session_id)
        if not history:
            return ""
        context_lines = ["--- ÖNCEKI BAĞLAM ---"]
        for msg in history[-4:]:
            role = "Kullanıcı" if msg["role"] == "user" else "Asistan"
            context_lines.append(f"{role}: {msg['content'][:300]}")
        return "\n".join(context_lines) + "\n\n"


# Hukuki Filtre

_HUKUK_DISI = {
    "hava",
    "yemek",
    "müzik",
    "film",
    "spor",
    "oyun",
    "minecraft",
    "magazin",
    "haber",
    "gündem",
    "sağlık",
    "doktor",
    "ilaç",
    "matematik",
    "fizik",
    "kimya",
}
_HUKUKI_SINYALLER = {
    "nedir",
    "nasıl",
    "hak",
    "kanun",
    "madde",
    "dava",
    "sözleşme",
    "tazminat",
    "kira",
    "borç",
    "alacak",
    "fesih",
    "temerrüt",
    "cayma",
    "garanti",
    "tahliye",
    "tbk",
    "tkhk",
    "ttk",
    "6098",
    "6502",
    "6102",
    "mahkeme",
    "icra",
    "ipotek",
    "miras",
    "velayet",
}


def is_legal_query(sorgu: str) -> bool:
    s = sorgu.lower()
    if any(hd in s.split() for hd in _HUKUK_DISI):
        return False
    return any(sig in s for sig in _HUKUKI_SINYALLER) or len(sorgu.split()) >= 3


# İçtihat Talebi Kontrolü

_ICTIHAT_ISTEGI_KELIMELERI = {
    "evet",
    "isterim",
    "istiyorum",
    "göster",
    "gösterin",
    "bakalım",
    "emsal",
    "karar",
    "içtihat",
    "yargıtay",
    "lütfen",
    "tabii",
    "tabi",
    "olur",
    "harika",
    "güzel",
}
# ✅ Daha esnek tetikleyici: "emsal karar" - prompt'taki cümleyle birebir uyumlu
_ICTIHAT_SORUSU_TETIKLEYICI = "emsal karar"


def is_ictihat_request(sorgu: str, history: List[Dict]) -> bool:
    if not history:
        return False
    last_msg = history[-1]
    if last_msg.get("role") != "assistant":
        return False
    if _ICTIHAT_SORUSU_TETIKLEYICI not in last_msg.get("content", "").lower():
        return False
    sorgu_temiz = sorgu.lower().strip()
    return any(kelime in sorgu_temiz for kelime in _ICTIHAT_ISTEGI_KELIMELERI)


# Query Intent Router


class QueryIntentRouter:
    INTENT_DEFINITIONS = {
        "INFO_RETRIEVAL": {
            "keywords": ["nedir", "ne", "neyin", "nasıl", "hangi", "kaç"],
            "retrieval_k": 7,
        },
        "COMPARISON": {
            "keywords": ["fark", "arasında", "farklı", "ne kadar", "vs", "karşılaştır"],
            "retrieval_k": 10,
        },
        "PROCEDURE": {
            "keywords": ["süre", "yapılır", "adım", "işlem", "başvuru", "başvur"],
            "retrieval_k": 8,
        },
        "RIGHTS_OBLIGATION": {
            "keywords": ["hak", "sorumluluk", "yükümlülük", "ödeme", "iade"],
            "retrieval_k": 7,
        },
        "CONSEQUENCE": {
            "keywords": ["sonuç", "ceza", "para", "tazminat", "zarar", "risiko"],
            "retrieval_k": 6,
        },
    }

    def __init__(self, client: Groq):
        self.client = client

    def detect_intent(self, sorgu: str) -> Tuple[str, int]:
        sorgu_lower = sorgu.lower()
        best_intent = "INFO_RETRIEVAL"
        best_score = 0
        for intent, config in self.INTENT_DEFINITIONS.items():
            score = sum(1 for kw in config["keywords"] if kw in sorgu_lower)
            if score > best_score:
                best_score = score
                best_intent = intent
        recommended_k = self.INTENT_DEFINITIONS[best_intent]["retrieval_k"]
        log.info(f"Intent Detection: {best_intent} (k={recommended_k})")
        return best_intent, recommended_k


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


# Query Rewrite

_MADDE_REF_RE = re.compile(
    r"\b(tbk|tkhk|ttk)\s*(?:m\.|madde)?\s*\d+\b|\b(6098|6502|6102)\b|\b(?:madde|m\.)\s*\d+\b",
    re.IGNORECASE,
)
_REWRITE_SYSTEM = "Sen Türk hukuku uzmanısın. Kullanıcının sorusunu, anlamını bozmadan akademik hukuk terimleriyle yeniden yaz. Kanun kısaltmalarını (TBK, TKHK, TTK) koru. Sadece yeniden yazılmış soruyu döndür, açıklama ekleme."


def has_madde_ref(sorgu: str) -> bool:
    return bool(_MADDE_REF_RE.search(sorgu))


def rewrite_query(client: Groq, sorgu: str) -> str:
    if has_madde_ref(sorgu):
        return sorgu
    if len(sorgu.split()) < 4 or len(sorgu.split()) > 30:
        return sorgu
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": _REWRITE_SYSTEM},
                {"role": "user", "content": f"Soru: {sorgu}\n\nYeniden yazılmış hali:"},
            ],
            temperature=0.0,
            max_tokens=100,
        )
        yeni = resp.choices[0].message.content.strip()
        return yeni if yeni and len(yeni) <= 300 else sorgu
    except Exception as e:
        log.warning(f"Query rewrite hatası: {e}")
        return sorgu


# Sistem Promptları
_SISTEM_PROMPT_TEMPLATE = """Sen sadece Türk Borçlar Kanunu (TBK), Türk Ticaret Kanunu (TTK) ve Tüketicinin Korunması Hakkında Kanun (TKHK) alanlarında uzmanlaşmış bir AI Hukuk Asistanısın.

BAĞLAM (SADECE BURADAKİ BİLGİLERİ KULLAN - Yargıtay kararı içermez):
{context}

GÖREVLERİN:
1. **İki Aşamalı Yanıt:** Kullanıcıya önce sadece 'Hukuki Değerlendirme' ve 'Dayanak Mevzuat' bölümlerini sun.
2. **Kapatış Sorusu:** Yanıtın en sonuna kesinlikle şu cümleyi ekle: "Bu konuyla ilgili daha fazla bilgi veya emsal karar görmek ister misiniz?" (Kapsam dışı durumda ekleme.)
3. **İçtihat Yasağı:** Bu yanıtta Yargıtay kararı, esas/karar numarası veya daire adı ASLA YAZMA.
4. **Madde Numarası Kullanımı (KRİTİK):**
   - **Sadece BAĞLAM içinde geçen madde numaralarını kullan.** Bağlamda yoksa hiçbir madde numarası yazma.
   - Her cümlende madde belirtmek zorunda değilsin. Sadece bir maddeye atıf yapacaksan, mutlaka bağlamda olmalı.
   - Format: (TBK m. 117), (TKHK m. 11), (TTK m. 18).
5. **KAPSAM DIŞI DURUMU:** Eğer kullanıcının sorusu (boşanma, ceza, miras, velayet, iş hukuku gibi) TBK/TTK/TKHK dışındaysa, doğrudan şunu söyle: "Üzgünüm, veri tabanım sadece TBK, TTK ve TKHK konularını kapsamaktadır. Sorunuzdaki konu uzmanlık alanım dışındadır." **Bu durumda kapatış sorusunu ekleme.**
6. **ASLA UYDURMA:** Bağlamda kesinlikle yer almayan hiçbir madde numarasını yazma. Kanun adı (örneğin TMK, CMK, HMK) asla kullanma.

YANIT FORMATI:
**Hukuki Değerlendirme**
[Analiz]

**Dayanak Mevzuat**
- [Kanun] m.[No]: [Madde Özeti]

---
Bu konuyla ilgili daha fazla bilgi veya emsal karar görmek ister misiniz?
"""

_ICTIHAT_PROMPT_TEMPLATE = """Sen Türk Borçlar, Ticaret ve Tüketici Hukuku alanlarında uzmanlaşmış bir AI Hukuk Asistanısın.

BAĞLAM (SADECE BURADAKİ İÇTİHATLARI KULLAN):
{context}

GÖREVİN:
Yalnızca sana verilen bağlamdaki Yargıtay kararlarını aşağıdaki formatta özetle.
- Karar künyeleri (esas/karar no, daire) AYNEN koru.
- Her karardan çıkan hukuki ilkeyi 1-2 cümleyle açıkla.
- Eğer bağlamda içtihat yoksa "Bu konuya dair veri tabanımda emsal karar bulunmamaktadır." de.

YANIT FORMATI:
**Emsal Yargıtay Kararları**

### [Konu Başlığı]
- **Künye:** [Daire] — [Esas No] / [Karar No]
- **Hukuki İlke:** [Karardan çıkan temel kural]
"""


def build_context(chunks: list, source_filter: Optional[str] = None) -> str:
    satirlar = []
    for i, c in enumerate(chunks, 1):
        source_type = str(c.get("source", "Mevzuat")).upper()
        if source_filter and source_type != source_filter.upper():
            continue
        satirlar.append(
            f"--- KAYNAK {i} ---\n"
            f"KANUN: {c.get('law', '?')}\n"
            f"MADDE: {c.get('article_no', '?')}\n"
            f"METİN: {c.get('text', '')}"
        )
    return "\n\n".join(satirlar)


# Singleton Retriever

_retriever_instance: Optional[LegalRetriever] = None


def get_retriever() -> LegalRetriever:
    global _retriever_instance
    if _retriever_instance is None:
        log.info("[Startup] Retriever yükleniyor...")
        _retriever_instance = LegalRetriever()
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
            context = build_context(ictihat_chunks)
            ictihat_prompt = _ICTIHAT_PROMPT_TEMPLATE.format(context=context)
            try:
                resp = self.client.chat.completions.create(
                    model=MODEL_NAME,
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
                yanit = resp.choices[0].message.content.strip()
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
                    "ozet": (c.get("text") or "")[:200] + "...",
                    "tip": "mevzuat",
                }
            )
        for c in ictihat_chunks:
            combined_sources.append(
                {
                    "kanun": "Yargıtay",
                    "madde": c.get("decision_id", ""),
                    "ozet": (c.get("text") or "")[:200] + "...",
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

        # 3. HUKUKİ FİLTRE (kısa onaylar buraya düşmez çünkü Aşama 2 onları yakalar)
        if not is_legal_query(sorgu):
            filtered = "Ben bir Türk hukuk asistanıyım. Lütfen Türk Borçlar, Ticaret veya Tüketici hukukuyla ilgili bir soru sorunuz."
            self.memory.add_exchange(session_id, sorgu, filtered)
            return {
                "answer": filtered,
                "sources": [],
                "filtered": True,
                "sure_ms": int((time.time() - t0) * 1000),
            }

        try:
            # Intent ve K
            intent, recommended_k = self.intent_router.detect_intent(sorgu)
            k = k or recommended_k or self.default_k

            # Query rewrite
            yeni_sorgu = rewrite_query(self.client, sorgu)

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

            # Fallback
            if len(chunks) < 3 and yeni_sorgu != sorgu:
                ek = self.retriever.retrieve(sorgu, k=k)
                mevcut = {c["chunk_id"] for c in chunks}
                for c in ek:
                    if c["chunk_id"] not in mevcut:
                        chunks.append(c)
                chunks = chunks[:k]

            # Alaka kontrolü (kapsam dışı kelimeler)
            kapsam_disi_kelimeler = [
                "boşan",
                "nafaka",
                "velayet",
                "miras",
                "hapis",
                "suç",
                "öldür",
                "yarala",
            ]
            if any(kelime in sorgu_temiz for kelime in kapsam_disi_kelimeler):
                is_relevant = any(
                    any(
                        kw in str(c.get("text", "")).lower()
                        for kw in kapsam_disi_kelimeler
                    )
                    for c in chunks
                )
                if not is_relevant:
                    chunks = []
                    log.info(
                        f"[Alaka Kontrolü] Kapsam dışı sorgu: '{sorgu_temiz}' → chunks temizlendi."
                    )

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

            # Mevzuat odaklı yanıt
            context = build_context(chunks)
            sistem_prompt = _SISTEM_PROMPT_TEMPLATE.format(context=context)

            resp = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": sistem_prompt},
                    {"role": "user", "content": f"SORU: {sorgu}"},
                ],
                temperature=0.2,
                max_tokens=1000,
            )
            yanit = resp.choices[0].message.content.strip()

            # Hallüsinasyon kontrolü
            is_faithful, validation_warning, _ = (
                self.hallucination_validator.validate_faithfulness(yanit, chunks)
            )
            if not is_faithful:
                yanit = yanit + f"\n\n{validation_warning}"

            log.info(
                f"[Aşama 1] Başarılı: intent={intent}, k={k}, faithful={is_faithful}, sources={len(chunks)}"
            )
            self.memory.add_exchange(session_id, sorgu, yanit)

            # Kaynak listesi (sadece mevzuat)
            sources = []
            for c in chunks:
                if str(c.get("source", "")).lower() != "yargitay":
                    sources.append(
                        {
                            "kanun": c.get("law") or "",
                            "madde": (
                                str(c.get("article_no"))
                                if c.get("article_no") is not None
                                else ""
                            ),
                            "ozet": (c.get("text") or "")[:200] + "...",
                        }
                    )

            return {
                "answer": yanit,
                "sources": sources,
                "intent": intent,
                "query_rewritten": yeni_sorgu if yeni_sorgu != sorgu else None,
                "hallucination_check": {
                    "is_faithful": is_faithful,
                    "warning": validation_warning,
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


# FastAPI Entegrasyon


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_retriever()
    log.info("[Startup] Uygulama başladı (v5.8)")
    yield
    global _retriever_instance
    if _retriever_instance and hasattr(_retriever_instance, "qdrant"):
        _retriever_instance.qdrant.close()
    log.info("[Shutdown] Uygulama kapatıldı")


def create_app() -> FastAPI:
    app = FastAPI(
        title="LawAgent AI API",
        version="5.8",
        description="Türk Hukuku Asistanı (Düzeltilmiş İçtihat Sırası + Esnek Tetikleyici)",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                },
            )
        return await call_next(request)

    class AskRequest(BaseModel):
        query: str
        k: int = 7
        session_id: str = "default"

    class AskResponse(BaseModel):
        answer: str
        sources: List[Dict[str, str]]
        intent: Optional[str] = None
        query_rewritten: Optional[str] = None
        hallucination_check: Optional[Dict] = None
        sure_ms: int = 0
        filtered: bool = False

    gen = LegalGenerator()

    @app.post("/ask", response_model=AskResponse)
    async def ask(req: AskRequest):
        if not req.query.strip():
            return JSONResponse(status_code=400, content={"detail": "Sorgu boş."})
        result = gen.generate(req.query, session_id=req.session_id, k=req.k)
        return result

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "version": "5.8",
            "features": [
                "Düzeltilmiş içtihat talebi sırası",
                "Esnek tetikleyici (emsal karar)",
                "Gelişmiş Madde Kontrolü",
                "İki Aşamalı İçtihat",
                "Alaka Kontrolü",
            ],
        }

    @app.get("/memory/{session_id}")
    async def get_memory(session_id: str):
        history = gen.memory.get_history(session_id)
        return {
            "session_id": session_id,
            "message_count": len(history),
            "history": history,
        }

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", action="store_true", help="FastAPI sunucusu başlat")
    parser.add_argument("--interactive", action="store_true", help="İnteraktif CLI mod")
    args = parser.parse_args()

    if args.api:
        _port = int(os.getenv("PORT", 7860))
        print(f"FastAPI sunucusu başlatılıyor... (port={_port})")
        import uvicorn

        app = create_app()
        uvicorn.run(app, host="0.0.0.0", port=_port, log_level="info")

    elif args.interactive:
        gen = LegalGenerator()
        session = "cli_session"
        print("\n" + "=" * 70)
        print("LawAgent AI v5.8 - Düzeltilmiş İçtihat Sırası + Esnek Tetikleyici")
        print("=" * 70)
        print(
            "Soru sor → Mevzuat gelir → 'Evet' de → İçtihat + Mevzuat kaynakları birlikte gelir."
        )
        print("'quit' ile çıkış.\n")
        while True:
            sorgu = input("Soru: ").strip()
            if sorgu.lower() in {"quit", "q", "çık"}:
                break
            if not sorgu:
                continue
            result = gen.generate(sorgu, session_id=session)
            print("\n" + "-" * 70)
            print(f"[{result.get('intent', 'UNKNOWN')}] Yanıt:\n")
            print(result["answer"])
            if result.get("hallucination_check", {}).get("warning"):
                print(f"\n⚠️ {result['hallucination_check']['warning']}")
            if result.get("sources"):
                print(f"\n📚 Kaynaklar ({len(result['sources'])} adet):")
                for i, src in enumerate(result["sources"], 1):
                    print(f"  {i}. {src.get('kanun', '')} {src.get('madde', '')}")
            print(f"\n⏱️ İşlem Süresi: {result.get('sure_ms', 0)}ms\n")
    else:
        parser.print_help()
