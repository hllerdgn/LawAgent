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
import pdf_processor
from legal_normalizer import full_post_process, normalize_legal_terminology, sanitize_markdown_typography
from citation_engine import build_grounded_context, validate_and_extract_citations

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
_DEFAULT_CONFIG_MODEL = os.getenv("GROQ_MODEL", "groq/compound-mini")

GROQ_FALLBACK_MODELS = [
    _DEFAULT_CONFIG_MODEL,
    "groq/compound-mini",
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
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

# Kesin kapsam dışı konular — bu kelimeler sorguda geçerse direkt reddedilir
_KESIN_KAPSAM_DISI = [
    # Vergi hukuku
    "vergi", "kdv", "gelir vergisi", "kurumlar vergisi", "mtv", "ötv", "stopaj",
    # Ceza hukuku
    "suç", "ceza", "hapis", "tutuklama", "gözaltı", "savcı", "müdahil", "beraat",
    "uyuşturucu", "kaçakçılık", "dolandırıcılık", "sahte", "hırsız",
    # Aile hukuku
    "boşan", "boşama", "boşamak", "nafaka", "velayet", "evlilik",
    # İdare hukuku
    "belediye", "ruhsat", "ihale", "kamu ihale",
    # Diğer kapsam dışı
    "pasaport", "vize", "vatandaşlık", "askerlik",
]
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
    # Kesin kapsam dışı konular → False
    if any(kd in s for kd in _KESIN_KAPSAM_DISI):
        return False
    return any(sig in s for sig in _HUKUKI_SINYALLER) or len(sorgu.split()) >= 3


_KAPSAM_DISI_YANITI = (
    "Üzgünüm, bu konu uzmanlık alanım olan TBK (Türk Borçlar Kanunu), "
    "TTK (Türk Ticaret Kanunu) ve TKHK (Tüketicinin Korunması Hakkında Kanun) "
    "dışında kalmaktadır. Bu alanlarda yardımcı olmaktan memnuniyet duyarım."
)

# LLM Tabanlı Kapsam Kontrolü

_KAPSAM_KONTROL_SISTEM = (
    "Sen bir Türk hukuku kapsam denetçisisin. "
    "Görevin: kullanıcının sorusunun yalnızca şu üç kanun kapsamında olup olmadığını belirlemek: "
    "Türk Borçlar Kanunu (TBK), Türk Ticaret Kanunu (TTK), Tüketicinin Korunması Hakkında Kanun (TKHK). "
    "Selamlama ve genel sohbet mesajları da KAPSAM İÇİ say. "
    "Yalnızca 'EVET' veya 'HAYIR' olarak yanıt ver. Başka hiçbir şey yazma."
)

# Aynı sorgu için tekrar LLM çağrısı yapılmasın (128 sorgu önbelleği)
_scope_cache: Dict[str, bool] = {}


def is_in_scope_llm(client: Groq, sorgu: str) -> bool:
    """LLM ile kapsam kontrolü.
    True  = TBK/TTK/TKHK kapsamında → işleme devam et
    False = Kapsam dışı → reddet
    Hata durumunda keyword tabanlı is_legal_query() fallback olarak kullanılır.
    """
    cache_key = sorgu.lower().strip()

    # Önbellek kontrolü — aynı sorgu için LLM'e gitme
    if cache_key in _scope_cache:
        log.info(f"[Kapsam Kontrol / Cache] '{sorgu[:60]}' → {'İçi' if _scope_cache[cache_key] else 'Dışı'}")
        return _scope_cache[cache_key]

    # Önce açıkça kapsam dışı kelimelere hızlı bak (maliyet sıfır)
    s = cache_key
    if any(kd in s for kd in _KESIN_KAPSAM_DISI):
        log.info(f"[Kapsam Kontrol / Keyword] Kapsam dışı: '{sorgu[:60]}'")
        _scope_cache[cache_key] = False
        return False
    if any(hd in s.split() for hd in _HUKUK_DISI):
        log.info(f"[Kapsam Kontrol / Keyword] Hukuk dışı konu: '{sorgu[:60]}'")
        _scope_cache[cache_key] = False
        return False

    # LLM ile derin kapsam analizi
    try:
        yanit = call_groq_completion(
            client=client,
            messages=[
                {"role": "system", "content": _KAPSAM_KONTROL_SISTEM},
                {
                    "role": "user",
                    "content": f"Soru: {sorgu}\n\nBu soru TBK, TTK veya TKHK kapsamında mı? (EVET/HAYIR)",
                },
            ],
            temperature=0.0,
            max_tokens=400,  # Reasoning modelleri <think> bloğu açar; 5 token yetmez
        )
        karar = yanit.strip().upper()
        # Yanıt içinde EVET veya HAYIR ara (startswith() yerine — model prefix ekleyebilir)
        if re.search(r"\bEVET\b", karar):
            kapsam_ici = True
        elif re.search(r"\bHAYIR\b", karar):
            kapsam_ici = False
        else:
            # Belirsiz yanıt → güvenli taraf: kapsam içi say, retrieval'a bırak
            log.warning(f"[Kapsam Kontrol / LLM] Belirsiz yanıt '{karar[:30]}', kapsam içi varsayıldı")
            kapsam_ici = True
        log.info(f"[Kapsam Kontrol / LLM] '{sorgu[:60]}' → {karar[:20]} → {'İçi' if kapsam_ici else 'Dışı'}")
        # Önbelleğe kaydet (max 128 kayıt)
        if len(_scope_cache) >= 128:
            _scope_cache.pop(next(iter(_scope_cache)))
        _scope_cache[cache_key] = kapsam_ici
        return kapsam_ici
    except Exception as e:
        log.warning(f"[Kapsam Kontrol / LLM] Hata, keyword fallback devreye girdi: {e}")
        return is_legal_query(sorgu)


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
        yeni = call_groq_completion(
            client=client,
            messages=[
                {"role": "system", "content": _REWRITE_SYSTEM},
                {"role": "user", "content": f"Soru: {sorgu}\n\nYeniden yazılmış hali:"},
            ],
            temperature=0.0,
            max_tokens=100,
        )
        return yeni if yeni and len(yeni) <= 300 else sorgu
    except Exception as e:
        log.warning(f"Query rewrite hatası: {e}")
        return sorgu


# Sistem Promptları
_SISTEM_PROMPT_TEMPLATE = """Sen, Türk Hukuku alanında uzmanlaşmış, yalnızca sağlanan yasal kaynaklara dayanarak bilgi veren profesyonel bir Yapay Zeka Hukuk Asistanısın.

GÖREVİN:
Kullanıcının sorusunu, aşağıda <HUKUKI_KAYNAKLAR> bloğu içerisinde verilen resmi kanun maddeleri ve içtihat metinlerini temel alarak yanıtlamaktır.

TEMEL VE KESİN KURALLAR:
1. SADECE SAĞLANAN KAYNAKLARI KULLAN: Cevabındaki her hukuki tespiti doğrudan <HUKUKI_KAYNAKLAR> içindeki metinlere dayandır. Kaynaklarda açıkça yer almayan hiçbir kanun hükmünü, ilkeyi, istisnayı veya mahkeme kararını parametrik hafızandan EKLEME.
2. KAYNAK YOKSA AÇIKÇA BELİRT: Eğer kullanıcının sorusuna cevap vermek için sağlanan kaynaklar yetersizse, kesin hukuki çıkarım yapma; "Sunulan yasal kaynaklar çerçevesinde bu soruya dair doğrudan bir hüküm bulunmamaktadır." ifadesini kullan.
3. KANUN VE MADDE UYDURMA YASAĞI: Kaynak listesinde bulunmayan hiçbir kanun adını (TMK, CMK, HMK vb.) veya madde numarasını kesinlikle yanıta dahil etme.
4. RESMİ KANUN TERMİNOLOJİSİ: Kanun isimlerini ilk kullanımda tam ve resmi adıyla, kısaltmasını parantez içinde vererek kullan:
   - "6502 sayılı Tüketicinin Korunması Hakkında Kanun (TKHK)"
   - "6098 sayılı Türk Borçlar Kanunu (TBK)"
   - "6102 sayılı Türk Ticaret Kanunu (TTK)"
   Asla "Türk Konsum Kanunu", "Tüketici Kanunu", "Borçlar Hukuku Kanunu" gibi gayriresmi veya uydurma tabirler kullanma.
5. METİN İÇİ ATIF KURALI (CITATION): Kaynaktan aldığın her bilginin hemen sonuna kaynak etiketini [K1], [K2] şeklinde iliştir. (Örnek: "Tüketici, mesafeli sözleşmelerde on dört gün içinde herhangi bir gerekçe göstermeksizin cayma hakkına sahiptir [K1].")
6. TARAFLI / GENEL YORUM YASAĞI: Kaynak metninde yazmayan subjektif yorumlar ("bu hak tüketiciler için harika bir avantajdır" vb.) ekleme; nesnel, duru ve akademik bir Türk hukuku üslubu kullan.
7. GENEL VE SOYUT SORULAR (SIFAT BELİRSİZLİĞİ): Eğer kullanıcı "Borçlar hukuku kapsamında temel haklarım nelerdir?" gibi genel bir soru soruyorsa ve sıfatı (alacaklı mı, borçlu mu vb.) belirtilmemişse: Borçlar hukukunda tek bir soyut "temel haklar listesi" bulunmadığını, hakların borç ilişkisindeki alacaklı (ifa talebi, temerrüt ve seçimlik haklar, tazminat) veya borçlu (def'i hakları, ifa, aşırı ifa güçlüğü / uyarlama) konumuna göre belirlendiğini izah ederek sağlanan kaynaklar çerçevesinde yapılandırılmış bir açıklama sun.

YANIT PLANI:
### Hukuki Değerlendirme
[Kullanıcının sorusuna doğrudan, net ve kaynaklara dayalı hukuki analiz. İlgili yerlerde [K1], [K2] etiketleri kullanılır.]

### Dayanak Hükümler
- [Resmi Kanun Adı] m. [Madde No]: [Maddenin olaya uygulanan temel kuralının 1 cümlelik özeti]

---
[Gerekiyorsa konuya uygun etkileşimli tek bir profesyonel yönlendirme sorusu]
"""

_ICTIHAT_PROMPT_TEMPLATE = """Sen Türk Borçlar, Ticaret ve Tüketici Hukuku alanlarında uzmanlaşmış, profesyonel bir Yapay Zeka Hukuk Asistanısın.

BAĞLAM (KULLANILACAK EMSAL KARARLAR):
{context}

TEMEL İLKELER VE GÖREVLER:
Yalnızca sana sağlanan bağlamdaki Yargıtay kararlarını inceleyerek, aşağıdaki profesyonel formatta özetle.
- Karar künyelerini (Esas ve Karar numaraları ile Daire bilgisini) hiçbir değişiklik yapmadan, aynen koru.
- Her bir Yargıtay kararından çıkarılması gereken temel hukuki ilkeyi 1 veya 2 cümle ile öz, net ve profesyonel bir dille ifade et.
- Eğer sağlanan bağlamda herhangi bir içtihat (emsal karar) bulunmuyorsa, sadece şu ifadeyi kullan: "Bu uyuşmazlığa ilişkin veri tabanımda kayıtlı emsal bir karar bulunmamaktadır."

YANIT FORMATI:
**Emsal Yargıtay Kararları**

### [Hukuki Uyuşmazlık Konusu]
- **Karar Künyesi:** [Daire Adı] — E. [Esas No] / K. [Karar No]
- **Hukuki İlke:** [Karardan çıkarılan bağlayıcı hukuki kural]
"""


_SITE_SISTEM_PROMPT_TEMPLATE = """Sen, kendisine sağlanan kurumsal belgeler üzerinden kullanıcılara doğru ve net bilgi vermekle görevli, profesyonel bir Yapay Zeka Asistanısın.

BAĞLAM (REFERANS ALINACAK BİLGİ KAYNAĞI):
{context}

TEMEL İLKELER VE GÖREVLER:
1. Dil Zorunluluğu: Yanıtlarını her zaman SADECE TÜRKÇE olarak oluştur. Yabancı dilde veya farklı alfabelerde (ör. Çince vb.) hiçbir ifade kullanma.
2. Bağlama Sadakat: Yanıtlarını KESİNLİKLE sadece sana sağlanan BAĞLAM içerisindeki verilere dayanarak oluştur. Kendi ön bilgilerini, genel kültürünü veya dış kaynaklı bilgileri yanıtına ASLA dahil etme.
3. Bilgi Eksikliği Durumu: Eğer kullanıcının sorduğu soruya dair bağlamda herhangi bir bilgi bulunmuyorsa, sadece şu ifadeyi kullan: "İncelediğim belgeler içerisinde bu konu hakkında herhangi bir bilgi bulunmamaktadır." Bu ifadenin dışına çıkma.
4. Kimlik Soruları: "Sen kimsin?" veya benzeri kimlik sorularına, "Sisteme yüklenen belgeler üzerinden size yardımcı olmak üzere tasarlanmış bir yapay zeka asistanıyım." şeklinde profesyonel ve kısa bir yanıt ver; bu tür sorularda dayanak belge gösterme.
5. Etkileşimli Kapanış: Yanıtını tamamladıktan sonra, bir alt satıra geçerek kullanıcıyı iletişime teşvik eden şu nazik kapanış sorusunu mutlaka ekle: "Bu belge içeriğiyle ilgili sormak istediğiniz başka bir konu var mı?"

YANIT FORMATI:
[Profesyonel, net ve bağlama sadık cevabın]

**Dayanak Belge**
- [Bağlamda belirtilen BELGE ismi]: [Yanıtı destekleyen kısa alıntı]

---
Bu belge içeriğiyle ilgili sormak istediğiniz başka bir konu var mı?
"""

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

        # 3. ÖN KAPSAM KONTROLÜ — Retrieval'dan ÖNCE, LLM ile kapsam dışı sorguları tespit et
        if not is_in_scope_llm(self.client, sorgu):
            log.info(f"[Ön Filtre / LLM] Kapsam dışı sorgu reddedildi: '{sorgu_temiz}'")
            self.memory.add_exchange(session_id, sorgu, _KAPSAM_DISI_YANITI)
            return {
                "answer": _KAPSAM_DISI_YANITI,
                "sources": [],
                "filtered": True,
                "intent": "OUT_OF_SCOPE",
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

            # Site document kontrolü
            has_site_doc = any(c.get("source") == "site_document" for c in chunks)

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
                sistem_prompt = _SISTEM_PROMPT_TEMPLATE.format(context=context_str)

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
    # CORS — ALLOWED_ORIGINS env var varsa kullan, yoksa ["*"] fallback
    # Örnek: ALLOWED_ORIGINS=https://lawagent.vercel.app,http://localhost:5173
    _raw_origins = os.getenv("ALLOWED_ORIGINS", "")
    _origins = [o.strip() for o in _raw_origins.split(",") if o.strip()] or ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
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

    class AskRequest(BaseModel):
        query: str
        k: int = 7
        session_id: str = "default"
        client_id: Optional[str] = "lawagent-demo"

    class AskResponse(BaseModel):
        answer: str
        sources: List[Dict[str, str]]
        intent: Optional[str] = None
        query_rewritten: Optional[str] = None
        hallucination_check: Optional[Dict] = None
        sure_ms: int = 0
        filtered: bool = False
        error: Optional[str] = None

    gen = LegalGenerator()

    # ── CLIENT / MULTI-TENANT ENDPOINTS ───────────────────────────────────────
    def _load_clients_json() -> Dict[str, Any]:
        clients_file = Path(__file__).resolve().parent / "clients.json"
        if clients_file.exists():
            try:
                with open(clients_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                log.error(f"clients.json okunurken hata: {e}")
        return {}

    @app.get("/clients")
    async def get_clients():
        """Sistemdeki tüm kayıtlı client/tenant yapılandırmalarını döndürür."""
        clients = _load_clients_json()
        return {"clients": list(clients.values())}

    @app.get("/clients/{client_id}")
    async def get_client_config(client_id: str):
        """Belirtilen client_id için public yapılandırmayı döndürür."""
        clients = _load_clients_json()
        if client_id in clients:
            return clients[client_id]
        # Fallback default
        if "lawagent-demo" in clients:
            return clients["lawagent-demo"]
        return JSONResponse(status_code=404, content={"detail": f"Client '{client_id}' bulunamadı."})

    @app.post("/ask", response_model=AskResponse)
    async def ask(req: AskRequest):
        if not req.query.strip():
            return JSONResponse(status_code=400, content={"detail": "Sorgu boş."})
        result = gen.generate(req.query, session_id=req.session_id, k=req.k)
        return result


    from fastapi import UploadFile, File
    @app.post("/upload-document")
    async def upload_document(file: UploadFile = File(...)):
        if not file.filename.lower().endswith(".pdf"):
            return JSONResponse(status_code=400, content={"detail": "Sadece PDF dosyaları desteklenmektedir."})
        try:
            contents = await file.read()
            # Embedder ve Qdrant instance'larını retriever'dan alıyoruz
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
            return JSONResponse(status_code=500, content={"detail": f"Dosya işlenirken hata oluştu: {str(e)}"})

    @app.get("/admin/documents")
    async def list_documents():
        docs = pdf_processor.get_uploaded_documents()
        return {"documents": docs}
        
    @app.delete("/admin/documents/{filename}")
    async def delete_document(filename: str):
        retriever = get_retriever()
        success = pdf_processor.delete_document(filename, retriever.qdrant)
        if success:
            return {"status": "ok", "message": f"{filename} silindi."}
        else:
            return JSONResponse(status_code=500, content={"detail": "Silme işlemi başarısız oldu."})

    @app.get("/health")
    async def health():
        # Uptime monitoring için minimal, güvenli endpoint.
        # ❌ Groq API çağrısı yapılmaz
        # ❌ Qdrant'a istek gönderilmez
        # ❌ Embedding model yüklenmez
        # ✅ Sadece FastAPI process'inin çalıştığını doğrular
        return {"status": "ok"}

    @app.get("/memory/{session_id}")
    async def get_memory(session_id: str):
        history = gen.memory.get_history(session_id)
        return {
            "session_id": session_id,
            "message_count": len(history),
            "history": history,
        }

    @app.get("/admin/stats")
    async def get_admin_stats():
        retriever = get_retriever()
        
        site_docs_count = 0
        try:
            site_docs_count = retriever.qdrant.count("site_corpus").count
        except Exception:
            pass
            
        law_docs_count = 0
        try:
            from embedder import COLLECTION_NAME
            law_docs_count = retriever.qdrant.count(COLLECTION_NAME).count
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
                    
                    # Format date: "2026-05-21T15:30:58" -> "21-05-2026 15:30"
                    raw_ts = messages[i]["timestamp"]
                    formatted_date = raw_ts
                    try:
                        dt = datetime.fromisoformat(raw_ts)
                        formatted_date = dt.strftime("%d-%m-%Y %H:%M")
                    except:
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
