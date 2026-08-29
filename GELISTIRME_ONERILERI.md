# LawAgent AI — Kapsamlı Güncelleme, Performans ve Geliştirme Öneri Raporu

**Rapor Türü:** Teknik İyileştirme Yol Haritası  
**Kaynak Proje:** `PROJE_AKADEMIK_RAPORU.md` — LawAgent AI v6.0  
**Hazırlayan:** Kıdemli Yazılım Mimarı & NLP / LegalTech Uzmanı  
**Tarih:** Ağustos 2026  
**Kapsam:** Veri Katmanı · Embedding · Retrieval · Reranker · LLM · API · Frontend · DevOps

---

## İÇİNDEKİLER

1. [Veri Mühendisliği Güncellemeleri](#1-veri-mühendisliği-güncellemeleri)
2. [Embedding ve Vektör Katmanı İyileştirmeleri](#2-embedding-ve-vektör-katmanı-i̇yileştirmeleri)
3. [Hibrit Retrieval Performans Yükseltmeleri](#3-hibrit-retrieval-performans-yükseltmeleri)
4. [Reranker ve Bağlam Seçim Geliştirmeleri](#4-reranker-ve-bağlam-seçim-geliştirmeleri)
5. [Hukuki Niyet ve Kapsam Motoru Geliştirmeleri](#5-hukuki-niyet-ve-kapsam-motoru-geliştirmeleri)
6. [LLM Üretim Katmanı İyileştirmeleri](#6-llm-üretim-katmanı-i̇yileştirmeleri)
7. [Backend API Mimarisi Yükseltmeleri](#7-backend-api-mimarisi-yükseltmeleri)
8. [Frontend ve UX Geliştirmeleri](#8-frontend-ve-ux-geliştirmeleri)
9. [DevOps, Gözlemlenebilirlik ve Güvenlik](#9-devops-gözlemlenebilirlik-ve-güvenlik)
10. [Yeni Özellik Fikirleri](#10-yeni-özellik-fikirleri)
11. [Gelişmiş Proje Geliştirme Promptu](#11-gelişmiş-proje-geliştirme-promptu)

---

## 1. VERİ MÜHENDİSLİĞİ GÜNCELLEMELERİ

### 1.1. 🔴 Kritik — Otomatik Mevzuat Güncelleme Döngüsü

**Mevcut Durum:** Veri kazıma tek seferlik bir işlem (`run_pipeline.sh`). TBK/TTK/TKHK'da yapılan resmi değişiklikler (fıkra eklenmesi, kaldırılması, geçici madde eklenmesi) sisteme otomatik yansımıyor.

**Önerilen Geliştirme:**
```python
# ÖNERI: incremental_updater.py
class IncrementalMevzuatUpdater:
    """
    mevzuat.gov.tr RSS feed veya değişiklik loglarını
    haftalık periyotla kontrol eder; yalnızca değişen
    maddeleri yeniden embed eder.
    """
    def check_changes(self) -> List[ChangedArticle]:
        # Kanun değişiklik tarihi karşılaştırması
        # Sadece delta → yeniden vektörleştirme
        pass

    def upsert_to_qdrant(self, article: ChangedArticle):
        # Eski vektörü sil, yeni vektörü ekle
        self.qdrant.delete(filter={"article_no": article.no})
        self.qdrant.upsert(points=[new_vector])
```

**Beklenen Kazanım:** Verinin her zaman güncel kalması; yürürlükten kaldırılan maddeler üzerinden yanlış yanıt riskinin sıfırlanması.

---

### 1.2. 🟡 Orta — Kanun Kapsamının Genişletilmesi

**Mevcut Durum:** TBK, TTK, TKHK ve Yargıtay emsal kararları.

**Önerilen Ek Kaynaklar:**

| Yeni Kaynak | Kanun No | Kapsam |
|---|---|---|
| Türk Medeni Kanunu (TMK) | 4721 | Aile, miras, kişiler, eşya |
| Hukuk Muhakemeleri Kanunu (HMK) | 6100 | Yargılama usulü ve süreler |
| İcra ve İflas Kanunu (İİK) | 2004 | İcra takibi, iflas prosedürü |
| İş Kanunu (İK) | 4857 | İşçi-işveren ilişkileri |
| Kişisel Verilerin Korunması Kanunu (KVKK) | 6698 | Veri sorumluluğu |

**Uygulama:** Her yeni kanun için ayrı bir Scrapy spider + yeni Qdrant filtre parametresi.

---

### 1.3. 🟢 Düşük — Parent-Child (Hiyerarşik Parça) Alım Stratejisi

**Mevcut Durum:** Her fıkra bağımsız chunk. Retriever fıkra bazında getiriyor; ancak üst madde başlığı (madde adı + kanun bağlamı) bazen kaybolabiliyor.

**Önerilen Geliştirme — Parent Retrieval:**
```
Depolama yapısı:
  PARENT:  TBK Madde 117 — tam metin (büyük, Qdrant'ta saklanır)
  CHILD_1: TBK 117/f1 — küçük fıkra parçası (vektörleştirilen)
  CHILD_2: TBK 117/f2

Retrieval sırası:
  1. CHILD parçayı vektör aramasıyla bul (küçük → hassas eşleşme)
  2. Bulunan CHILD'ın parent_id'si ile PARENT metni çek
  3. LLM'e tam madde metnini (PARENT) ver → daha zengin bağlam
```

**Beklenen Kazanım:** LLM bağlamına daha eksiksiz madde metni girmesi, anlam kayıplarının önlenmesi.

---

## 2. EMBEDDING VE VEKTÖR KATMANI İYİLEŞTİRMELERİ

### 2.1. 🔴 Kritik — INT8'den GGUF/ONNX Formatına Geçiş

**Mevcut Durum:** PyTorch dinamik INT8 kuantizasyonu (`mursit_int8.pt`, 622 MB). Dinamik INT8, çıkarım sırasında her aktivasyon için kuantizasyon/dekuantizasyon yaparak CPU yükü yaratır.

**Önerilen Geliştirme — Static INT8 veya ONNX:**
```python
# ÖNERI: ONNX Runtime export — ~2-3x daha hızlı CPU inference
from optimum.onnxruntime import ORTModelForFeatureExtraction

model = ORTModelForFeatureExtraction.from_pretrained(
    "fine_tuned_mursit",
    export=True,
    provider="CPUExecutionProvider"
)
# Static INT8 quantization ile birleştirince:
# - Disk: ~310 MB (dinamik INT8'in yarısı)
# - Throughput: +60-80% artış (CPU'da)
```

**Beklenen Kazanım:** Embedding gecikme süresi `~80ms → ~30ms`, batch embedding throughput'u 2-3x artış.

---

### 2.2. 🟡 Orta — HyDE (Hypothetical Document Embedding) Entegrasyonu

**Mevcut Durum:** Kullanıcı sorgusu doğrudan vektörleştiriliyor. Ancak kısa, muğlak sorgular için vektör uzayındaki temsil yeterli değil.

**Önerilen Geliştirme — HyDE:**
```
Kullanıcı: "kira sözleşmesi bitmeden çıkmak istiyorum"
    ↓
HyDE: Groq compound-mini ile hayali yanıt üret:
  "Kiracının kira süresinden önce taşınması TBK m.325 kapsamında
   erken tahliye hakkı doğurur. Ancak geri kalan kira bedelinden
   sorumlu olabilir..."
    ↓
Hayali yanıtı vektörleştir + orijinal sorgu vektörünü ağırlıkla birleştir:
  query_vec = 0.8 * hyde_vec + 0.2 * original_vec
    ↓
Bu bileşik vektör ile Qdrant araması → çok daha hedefe yakın sonuçlar
```

**Not:** `generator.py`'de `HYDE_WEIGHT: 0.80` parametresi zaten `settings.py`'de mevcut — aktive edilmeyi bekliyor.

---

### 2.3. 🟢 Düşük — Qdrant Scalar + Product Quantization

**Mevcut Durum:** Qdrant, ham float32 vektörler depoluyor.

**Önerilen Geliştirme:**
```python
# Qdrant koleksiyon tanımına quantization config ekle
from qdrant_client.models import ScalarQuantization, ScalarQuantizationConfig

client.recreate_collection(
    collection_name="lawagent_mursit",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    quantization_config=ScalarQuantization(
        scalar=ScalarQuantizationConfig(
            type=ScalarType.INT8,
            quantile=0.99,
            always_ram=True,  # Quantized vektörler RAM'de, ham disk'te
        )
    )
)
```

**Beklenen Kazanım:** Vektör depolama boyutu %75 azalma (float32 → int8), ANN arama hızı %20-30 artış.

---

## 3. HİBRİT RETRIEVAL PERFORMANS YÜKSELTMELERİ

### 3.1. 🔴 Kritik — BM25 İndeksini Disk'e Kalıcı Kaydetme

**Mevcut Durum:** `retriever_cache.pkl` (5.9 MB) — BM25 indeksi pickle olarak kaydedilmiş. Ancak her API yeniden başlatmasında bu indeks yeniden kurulabiliyor.

**Önerilen Geliştirme — Önbellekli BM25 ile Lazy Load:**
```python
class BM25Plus:
    def load_or_build(self, docs: List[str], cache_path: Path) -> None:
        if cache_path.exists():
            with open(cache_path, "rb") as f:
                state = pickle.load(f)
            self.__dict__.update(state)
            log.info(f"[BM25+] İndeks önbellekten yüklendi: {cache_path}")
        else:
            self.index(docs)
            with open(cache_path, "wb") as f:
                pickle.dump({k: v for k, v in self.__dict__.items()}, f)
            log.info(f"[BM25+] İndeks oluşturuldu ve önbelleğe alındı")
```

---

### 3.2. 🟡 Orta — Türkçe Morfoloji Tabanlı BM25 Tokenizer

**Mevcut Durum:** BM25 tokenizer yalnızca basit lowercase + regex ayırma yapıyor. "Temerrüt", "temerrüde", "temerrüdü" üç farklı token olarak işleniyor; oysa aynı kavramı temsil ediyorlar.

**Önerilen Geliştirme — Zemberek-Python Entegrasyonu:**
```python
# pip install zemberek-python
from zemberek import TurkishMorphology

morphology = TurkishMorphology.create_with_defaults()

def _tokenize_morphological(self, text: str) -> List[str]:
    tokens = []
    for word in text.lower().split():
        analysis = morphology.analyze(word)
        if analysis.analysis_results:
            # Köke indir: "temerrüdü" → "temerrüt"
            stem = analysis.analysis_results[0].get_stem()
            tokens.append(stem)
        else:
            tokens.append(word)
    return tokens
```

**Beklenen Kazanım:** Türkçe morfolojik çeşitlilik nedeniyle kaçırılan eşleşmelerde %15-25 recall artışı.

---

### 3.3. 🟡 Orta — Dinamik Alfa Kalibrasyonu — Makine Öğrenmesi ile Öğrenilebilir Alfa

**Mevcut Durum:** Alfa değerleri statik olarak kod içinde tanımlanmış (0.45, 0.68, 0.72).

**Önerilen Geliştirme — Logistic Regression ile Öğrenilebilir Alfa:**
```python
# Gerçek soru-cevap verilerinden alfa optimizasyonu
from sklearn.linear_model import LogisticRegression

features = [
    has_madde_ref,       # 0/1
    has_law_name,        # 0/1
    query_token_count,   # int
    domain_score,        # float
]

# Etiket: bu sorgu için optimal alfa hangi aralık?
# Eğitim: küçük insan etiketli dataset (100-200 sorgu yeterli)
alpha_classifier = LogisticRegression()
alpha_classifier.fit(X_train, y_alpha_bins)
```

---

### 3.4. 🟢 Düşük — Reciprocal Rank Fusion (RRF) Alternatif Füzyon

**Mevcut Durum:** Min-max normalizasyon + lineer ağırlıklı ortalama.

**Önerilen Alternatif — RRF:**
```
RRF_Score(d) = Σ 1 / (k + rank_i(d))    k = 60 (sabit)
```

RRF, min-max'a göre skor ölçeğinden bağımsız ve daha stabil davranır. Özellikle BM25 ve Dense skorlarının farklı ölçeklerde olduğu durumlarda min-max normalizasyonu hatalı davranabilir.

---

## 4. RERANKER VE BAĞLAM SEÇİM GELİŞTİRMELERİ

### 4.1. 🔴 Kritik — Türkçe Hukuk Özelleştirilmiş Cross-Encoder Fine-Tuning

**Mevcut Durum:** `BAAI/bge-reranker-base` — genel İngilizce reranker, Türkçe hukuk için ince ayarsız.

**Önerilen Geliştirme:**
```python
# Fine-tuning pipeline (Sentence-Transformers CrossEncoder ile)
from sentence_transformers.cross_encoder import CrossEncoder
from sentence_transformers.cross_encoder.evaluation import CECorrelationEvaluator

model = CrossEncoder("BAAI/bge-reranker-base")

# Eğitim verisi: (sorgu, madde_metni, relevance_score) üçlüleri
# Kaynak: mevcut retrieval loglarından human-in-the-loop etiketleme

train_samples = [
    ("kiracı erken çıkabilir mi", "TBK m.325 kiracı erken tahliye...", 0.95),
    ("kiracı erken çıkabilir mi", "TBK m.200 kefalet sözleşmesi...", 0.05),
    ...
]

model.fit(
    train_dataloader=DataLoader(train_samples, batch_size=16),
    epochs=3,
    warmup_steps=100,
    output_path="fine_tuned_reranker_tr_law"
)
```

**Beklenen Kazanım:** Reranker NDCG@7 skoru mevcut ~0.72'den ~0.84'e çıkabilir.

---

### 4.2. 🟡 Orta — Bağlam Penceresini Akıllı Genişletme (Contextual Compression)

**Mevcut Durum:** Reranker sonrası Top-7 chunk doğrudan LLM'e gönderiliyor.

**Önerilen Geliştirme — LLM Tabanlı Bağlam Sıkıştırma:**
```python
# Her chunk için: "Bu metin sorguya ne kadar doğrudan yanıt veriyor?"
# Kompakt özet çıkar, gereksiz metni at → daha az token, daha odaklı bağlam

def compress_context(chunk_text: str, query: str) -> str:
    prompt = f"""Sorgu: {query}
Metin: {chunk_text}
Görev: Metni yalnızca sorguyla doğrudan ilgili kısımları koruyarak özetle.
Yanıt:"""
    return groq_compound_mini(prompt)  # Düşük maliyetli model
```

---

## 5. HUKUKİ NİYET VE KAPSAM MOTORU GELİŞTİRMELERİ

### 5.1. 🔴 Kritik — Çok Hukuk Alanı Tespiti (Multi-Label Domain)

**Mevcut Durum:** `legal_intent.py` tek bir alan döndürüyor (`borclar_hukuku` VEYA `tuketici_hukuku`).

**Problem:** Gerçek davalar sıkça çakışır. "Tüketici olan kiracının iade talebi" hem TKHK hem TBK kapsamındadır.

**Önerilen Geliştirme — Multi-Label Sınıflandırma:**
```python
@dataclass
class LegalQueryAnalysis:
    # Mevcut: domain: str → TEK alan
    # Önerilen:
    domains: List[str]           # ["borclar_hukuku", "tuketici_hukuku"]
    domain_scores: Dict[str, float]  # {"borclar": 0.8, "tuketici": 0.5}
    primary_domain: str          # En yüksek skorlu alan
```

**Retrieval Etkisi:** Her tespit edilen domain için ayrı retrieval → sonuçlar birleştirme → LLM'e çok kanunlu bağlam.

---

### 5.2. 🟡 Orta — Aktif Açıklık İsteme (Clarification Request Engine)

**Mevcut Durum:** `requires_clarification: bool` alanı mevcut ama sistemin aktif açıklık istemesi geliştirilmemiş.

**Önerilen Geliştirme:**
```python
class ClarificationEngine:
    CLARIFICATION_TEMPLATES = {
        "rol_belirsiz": (
            "Bu sorunu daha doğru yanıtlayabilmem için: "
            "Siz bu ilişkide **{detected_options}** taraflarından hangisisiniz?"
        ),
        "konu_belirsiz": (
            "Sorunuz birden fazla hukuki alanla ilgili görünüyor. "
            "Temel uyuşmazlık **{domain_a}** mı, yoksa **{domain_b}** mi?"
        ),
    }

    def should_clarify(self, analysis: LegalQueryAnalysis) -> Optional[str]:
        if analysis.requires_clarification:
            return self.CLARIFICATION_TEMPLATES[analysis.ambiguity_type].format(...)
        return None
```

---

### 5.3. 🟢 Düşük — Konuşma Bağlamı Tabanlı Niyet Takibi

**Mevcut Durum:** Her sorgu bağımsız analiz ediliyor. `memory.py` oturum geçmişini tutuyor ama `legal_intent.py` bunu kullanmıyor.

**Önerilen Geliştirme — Diyalog Durumu Takibi:**
```python
def analyze_legal_query(query: str, history: List[Dict] = None) -> LegalQueryAnalysis:
    analysis = _analyze_standalone(query)
    
    if history and len(history) >= 2:
        # Önceki turdan alan ve sıfat bilgisini devral
        prev_analysis = history[-1].get("legal_analysis")
        if prev_analysis and analysis.domain == "bilinmiyor":
            analysis.domain = prev_analysis.get("domain", "bilinmiyor")
        if prev_analysis and analysis.legal_role == "belirsiz":
            analysis.legal_role = prev_analysis.get("legal_role", "belirsiz")
    
    return analysis
```

---

## 6. LLM ÜRETİM KATMANI İYİLEŞTİRMELERİ

### 6.1. 🔴 Kritik — Yapılandırılmış Çıktı Formatı (Structured Output / JSON Mode)

**Mevcut Durum:** LLM yanıtı ham Markdown metin. Frontend Regex ile kaynak etiketlerini parse ediyor — kırılgan bir yapı.

**Önerilen Geliştirme — Pydantic + Groq JSON Mode:**
```python
from pydantic import BaseModel, Field
from typing import List

class LegalSource(BaseModel):
    tag:        str   # "K1"
    law:        str   # "TBK"
    article_no: str   # "117"
    title:      str
    excerpt:    str   # Kullanılan metin parçası

class LegalAnswer(BaseModel):
    answer:          str            # Markdown yanıt metni
    sources:         List[LegalSource]
    confidence:      float          # 0.0 - 1.0
    requires_lawyer: bool           # "Profesyonel avukat tavsiye edilir" flag
    follow_up:       Optional[str]  # Yönlendirici soru

# Groq structured output
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=messages,
    response_format={"type": "json_object"},
)
answer = LegalAnswer.model_validate_json(response.choices[0].message.content)
```

**Beklenen Kazanım:** Frontend'de brittle Regex'in ortadan kalkması, tip güvenli API yanıtları.

---

### 6.2. 🟡 Orta — Prompt Versiyonlama ve A/B Test Altyapısı

**Mevcut Durum:** `prompts.py`'de tek bir aktif prompt versiyonu (v2.3).

**Önerilen Geliştirme:**
```python
# services/prompt_registry.py
PROMPT_VERSIONS = {
    "v2.3": SISTEM_PROMPT_TEMPLATE_V23,  # Mevcut
    "v2.4": SISTEM_PROMPT_TEMPLATE_V24,  # Deney
}

def get_prompt(version: str = None) -> str:
    """A/B testi: %10 trafiği v2.4'e yönlendir."""
    import random
    if version is None:
        version = "v2.4" if random.random() < 0.10 else "v2.3"
    return PROMPT_VERSIONS[version]
```

---

### 6.3. 🟡 Orta — Cevap Güven Skoru ve "Avukata Yönlendir" Mekanizması

**Mevcut Durum:** Her sorguya yanıt üretiliyor; sistemin güvensiz olduğunu bildirme mekanizması yok.

**Önerilen Geliştirme:**
```python
def compute_confidence(
    reranker_scores: List[float],
    is_fully_grounded: bool,
    retrieved_k: int,
) -> float:
    """
    Güven skoru hesaplama:
    - Reranker top-1 skoru yüksekse: güven artar
    - Tüm atıflar doğrulanmışsa: güven artar
    - Yeterli kaynak yoksa: güven düşer
    """
    base = max(reranker_scores) if reranker_scores else 0.0
    grounding_bonus = 0.15 if is_fully_grounded else -0.2
    k_penalty = max(0, (3 - retrieved_k) * 0.1)  # Az kaynak → düşük güven
    return max(0.0, min(1.0, base + grounding_bonus - k_penalty))

# Yanıta ekle:
if confidence < 0.55:
    answer += "\n\n⚠️ **Not:** Bu konu karmaşık hukuki değerlendirme gerektirmektedir. Profesyonel avukatlık desteği almanız tavsiye edilir."
```

---

### 6.4. 🟢 Düşük — Streaming Response (Akış Yanıtı)

**Mevcut Durum:** Yanıt tek seferde (`~400ms`) döndürülüyor. Kullanıcı boş ekran bekliyor.

**Önerilen Geliştirme — Server-Sent Events (SSE):**
```python
@app.post("/ask/stream")
async def ask_stream(req: AskRequest):
    async def event_generator():
        async for chunk in groq_client.stream(req.query):
            yield f"data: {json.dumps({'delta': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Beklenen Kazanım:** Algılanan gecikme süresi `400ms → <100ms` (ilk token), kullanıcı deneyimi büyük iyileşme.

---

## 7. BACKEND API MİMARİSİ YÜKSELTMELERİ

### 7.1. 🔴 Kritik — Rate Limiting ve Throttling

**Mevcut Durum:** Groq RateLimit hatası yakalanıyor ama istemci tarafında rate limiting yok. Kötü niyetli veya hatalı istemciler API'yi aşırı yükleyebilir.

**Önerilen Geliştirme — slowapi ile Endpoint Başına Rate Limiting:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/ask")
@limiter.limit("20/minute")  # IP başına 20 sorgu/dakika
async def ask(request: Request, req: AskRequest, ...):
    ...
```

---

### 7.2. 🔴 Kritik — Redis Tabanlı Oturum Yönetimi ve Önbellekleme

**Mevcut Durum:** `memory.py` oturum geçmişini in-memory Python dict'te tutuyor. API yeniden başlatıldığında TÜM oturumlar siliniyor.

**Önerilen Geliştirme — Redis Kalıcı Oturum:**
```python
import redis
import json

class RedisConversationMemory:
    def __init__(self, redis_url: str, ttl_seconds: int = 86400):
        self.r = redis.from_url(redis_url)
        self.ttl = ttl_seconds

    def get_history(self, session_id: str) -> List[Dict]:
        raw = self.r.get(f"session:{session_id}")
        return json.loads(raw) if raw else []

    def add_message(self, session_id: str, role: str, content: str):
        history = self.get_history(session_id)
        history.append({"role": role, "content": content, "ts": datetime.utcnow().isoformat()})
        self.r.setex(f"session:{session_id}", self.ttl, json.dumps(history))
```

**Beklenen Kazanım:** API yeniden başlatmalarında oturum kaybı yok, yatay ölçeklenme (birden fazla API instance) desteği.

---

### 7.3. 🟡 Orta — API Versiyonlama ve Swagger Belgesi

**Mevcut Durum:** `/ask` ve `/v1/ask` alias olarak mevcut. Ancak resmi API versiyonlama stratejisi yok.

**Önerilen Geliştirme:**
```python
# v1 router
v1_router = APIRouter(prefix="/v1", tags=["v1"])

@v1_router.post("/ask")
async def ask_v1(req: AskRequest, ...): ...

# v2 router (yeni özellikler)
v2_router = APIRouter(prefix="/v2", tags=["v2"])

@v2_router.post("/ask")
async def ask_v2(req: AskRequestV2, ...):  # Streaming + confidence + structured output
    ...

app.include_router(v1_router)
app.include_router(v2_router)
```

---

### 7.4. 🟢 Düşük — Async PDF İşleme (Arkaplan Görevi)

**Mevcut Durum:** `POST /upload-document` PDF'i senkron işliyor. Büyük belgeler için HTTP timeout riski var.

**Önerilen Geliştirme — Celery/ARQ ile Arkaplan Kuyruğu:**
```python
@app.post("/upload-document")
async def upload_document(file: UploadFile, _: None = Depends(verify_admin_key)):
    contents = await file.read()
    task_id = str(uuid4())
    
    # Arkaplan kuyruğuna ekle (anında yanıt ver)
    await task_queue.enqueue(
        process_pdf_task,
        task_id=task_id,
        file_content=contents,
        filename=file.filename
    )
    
    return {"status": "queued", "task_id": task_id, "message": "İşlem arka planda devam ediyor."}

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """PDF işleme durumunu sorgula."""
    ...
```

---

## 8. FRONTEND VE UX GELİŞTİRMELERİ

### 8.1. 🔴 Kritik — Chatbot Yanıt Akışı (Token Streaming)

**Mevcut Durum:** Tüm yanıt yüklendikten sonra gösteriliyor. `ChatbotWidget.tsx` (55KB) bu akışı desteklemiyor.

**Önerilen Geliştirme:**
```tsx
// ChatbotWidget.tsx'e SSE desteği ekle
const streamAnswer = async (query: string) => {
  const response = await fetch(`${API_URL}/ask/stream`, {
    method: 'POST',
    body: JSON.stringify({ query, session_id: sessionId }),
  });
  
  const reader = response.body!.getReader();
  let buffer = '';
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += new TextDecoder().decode(value);
    // Her chunk geldiğinde UI'ı güncelle
    setCurrentAnswer(prev => prev + parseChunk(buffer));
  }
};
```

---

### 8.2. 🟡 Orta — Mobil Responsive Chatbot Widget

**Mevcut Durum:** Widget sabit konumlandırılmış, küçük ekranlarda görünüm sorunları olabilir.

**Önerilen Geliştirme:** Tam ekran mobil görünüm, `swipe-down` kapatma jesti, `safe-area-inset` iOS uyumu.

---

### 8.3. 🟡 Orta — Soru Geçmişi ve Favoriler (Kullanıcı Persistansı)

**Mevcut Durum:** Oturum geçmişi memory'de. Kullanıcı sayfayı yenilediğinde sohbet kayboluyor.

**Önerilen Geliştirme:**
```tsx
// localStorage ile kalıcı soru geçmişi
const usePersistentHistory = (sessionId: string) => {
  const KEY = `lawagent_history_${sessionId}`;
  
  const save = (messages: Message[]) =>
    localStorage.setItem(KEY, JSON.stringify(messages.slice(-50))); // Son 50 mesaj
  
  const load = (): Message[] => {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : [];
  };
  
  return { save, load };
};
```

---

### 8.4. 🟢 Düşük — Karanlık Tema (Dark Mode) Desteği

**Mevcut Durum:** Tüm temalar açık renkli. `prefers-color-scheme: dark` medya sorgusuna yanıt yok.

**Önerilen Geliştirme:**
```css
/* tokens.css'e dark variant ekle */
@media (prefers-color-scheme: dark) {
  :root[data-theme="lumen"] {
    --color-paper:   oklch(15% 0.01 250);
    --color-ink:     oklch(93% 0.005 95);
    --color-border:  oklch(25% 0.015 250);
    --color-accent:  oklch(65% 0.18 265);
  }
}
```

---

## 9. DEVOPS, GÖZLEMLENEBİLİRLİK VE GÜVENLİK

### 9.1. 🔴 Kritik — Yapılandırılmış Loglama (Structured Logging)

**Mevcut Durum:** `core/logging.py` temel Python logging. Loglar düz metin; araştırma, filtreleme ve uyarı oluşturma zor.

**Önerilen Geliştirme — structlog + JSON Çıktı:**
```python
import structlog

log = structlog.get_logger()

# Her log kaydı JSON formatında → Elastic/Loki/Grafana'ya beslenebilir
log.info(
    "retrieval_complete",
    query=query[:100],
    session_id=session_id,
    k_returned=len(results),
    dense_top_score=results[0]["dense_score"] if results else 0,
    rerank_ms=elapsed_ms,
    domain=analysis.domain,
)
```

---

### 9.2. 🔴 Kritik — OpenTelemetry Distributed Tracing

**Mevcut Durum:** Sentry error tracking aktif ama her isteğin içindeki retrieval → rerank → LLM süre dağılımı görünmüyor.

**Önerilen Geliştirme:**
```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

tracer = trace.get_tracer("lawagent")
FastAPIInstrumentor.instrument_app(app)

# generator.py'de span'lar
with tracer.start_as_current_span("hybrid_retrieval") as span:
    span.set_attribute("query.length", len(query))
    span.set_attribute("retrieval.k", k)
    results = retriever.retrieve(query)
    span.set_attribute("retrieval.count", len(results))

with tracer.start_as_current_span("cross_encoder_rerank"):
    reranked = reranker.rerank(results)

with tracer.start_as_current_span("llm_generation"):
    answer = call_groq(...)
```

**Görselleştirme:** Jaeger veya Grafana Tempo → her isteğin tam ömür analizi.

---

### 9.3. 🟡 Orta — Input Sanitizasyon ve Prompt Injection Koruması

**Mevcut Durum:** Kullanıcı girdisi doğrudan prompt'a enjekte ediliyor. Prompt injection riski mevcut.

**Önerilen Geliştirme:**
```python
def sanitize_query(query: str) -> str:
    """Prompt injection ve berbat girdi koruması."""
    # Uzunluk sınırı
    query = query[:1000]
    
    # Açık injection kalıpları
    injection_patterns = [
        r"ignore (all )?previous instructions",
        r"sistem promptunu (unut|yok say)",
        r"<\|?(system|assistant)\|?>",
        r"---(END|STOP|IGNORE)---",
    ]
    for pattern in injection_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            raise HTTPException(status_code=400, detail="Geçersiz sorgu formatı.")
    
    return query.strip()
```

---

### 9.4. 🟢 Düşük — Docker Multi-Stage Build ile İmaj Boyutu Optimizasyonu

**Mevcut Durum:** Tek aşamalı Dockerfile — build araçları ve dev bağımlılıkları final imajda kalıyor.

**Önerilen Geliştirme:**
```dockerfile
# Aşama 1: Build
FROM python:3.11 AS builder
RUN pip install --user -r requirements.txt

# Aşama 2: Production (ince imaj)
FROM python:3.11-slim AS production
COPY --from=builder /root/.local /root/.local
COPY . /app
WORKDIR /app
CMD ["python", "main.py", "--api"]
```

**Beklenen Kazanım:** Docker imaj boyutu ~4GB → ~1.5GB.

---

## 10. YENİ ÖZELLİK FİKİRLERİ

### 10.1. 💡 Dava Belgesi Analiz Modu (Document Q&A)
Kullanıcı kendi sözleşmesini veya hukuki belgesini yükleyebilir, sistem bu belgeyle kanun maddeleri arasında çapraz analiz yapabilir.

### 10.2. 💡 Süre Hesaplayıcı (Hukuki Süre Asistanı)
"İhtar gönderdim, kaç gün içinde cevap bekliyorum?" → TBK'ya göre süre hesaplama ve takvim görünümü.

### 10.3. 💡 Çok Dilli Destek (Kürtçe, Arapça, İngilizce)
Türkiye'deki yabancı uyruklular ve azınlık toplulukları için temel hukuki bilgilere erişim.

### 10.4. 💡 Hukuki Uyarı Skorlaması
"Bu sözleşmede riskli maddeler var mı?" → Sözleşme metni yüklendiğinde TBK/TKHK kapsamında şüpheli fıkralar renk kodlu olarak işaretlenir.

### 10.5. 💡 Anonimleştirilmiş Sorgu Analitik Paneli
En çok sorulan konular, bölgesel dağılım, kapsam dışı sorgu oranı → Sürekli iyileştirme için veriye dayalı içgörüler.

---

## 11. GELİŞMİŞ PROJE GELİŞTİRME PROMPTU

Aşağıdaki prompt, bu proje için herhangi bir özellik, katman veya bileşenin geliştirilmesinde maksimum teknik derinliği elde etmek üzere tasarlanmıştır.

---

```
Sen; Yapay Zeka (NLP, RAG, IR), Hukuk Teknolojileri (LegalTech) ve Full-Stack Mühendislik alanlarında uzmanlaşmış, üretim deneyimi olan kıdemli bir yazılım mimarısın.

PROJE BAĞLAMI:
"LawAgent AI" — Türk Hukuku'na özel Hibrit RAG Sistemi (v6.0)
─────────────────────────────────────────────────────────────
Mevcut Mimari Katmanları:
1. Veri Toplama: Scrapy (mevzuat.gov.tr + yargitay.gov.tr)
2. Chunking: Hiyerarşik madde/fıkra bazlı parçalama
3. Embedding: Fine-Tuned Mursit-Base-TR (768-dim, INT8 quantized, PyTorch)
4. VektörDB: Qdrant (lawagent_mursit + site_corpus koleksiyonları, HNSW)
5. Retrieval: Hibrit (Dense + BM25+, k1=1.6, b=0.68, δ=1.0)
6. Fusion: Density-Aware Dynamic Alpha (0.45/0.68/0.72) + Madde Boost + Diversity Penalty
7. Reranker: BAAI/bge-reranker-base Cross-Encoder (Top-30→Top-7)
8. Intent: legal_intent.py — <1ms, regex/keyword, 4 boyutlu (domain/intent/role/concept)
9. Kapsam: scope_checker.py — Hukuk dışı filtre
10. Query Rewrite: query_processor.py — Akademik terminoloji dönüşümü
11. LLM: Groq Llama-3.3-70B-Versatile (temp=0.1, max_tokens=2500)
12. Atıf Motoru: citation_engine.py — [K1][K2] XML bağlam + deterministik doğrulama
13. Normalizasyon: legal_normalizer.py — Terminoloji + Markdown temizliği
14. API: FastAPI v6.0 (async, lru_cache singleton, ThreadPool, Sentry, X-Admin-Key)
15. Frontend: React 18 + Vite + Tailwind v4 + Hallmark 5-Tema Sistemi (OKLCH tokens)
16. Admin: PDF sürükle-bırak yükleme → anlık Qdrant vektörleştirme
17. DevOps: Docker-Compose, Vercel CDN, GitHub Actions Keep-Alive cron

Kanun Kapsamı: TBK (6098) · TTK (6102) · TKHK (6502) · Yargıtay İçtihadı

GÖREVİN:
[BURAYA SPESIFIK GÖREVİ YAZ]
Örnek görevler:
  - "Bu sisteme Redis tabanlı kalıcı oturum yönetimi ekle"
  - "BM25 tokenizer'ı Zemberek-Python ile morfoloji tabanlı hale getir"
  - "ChatbotWidget'a SSE token streaming desteği ekle"
  - "Üretim Cross-Encoder'ı Türkçe hukuk çifti veriyle fine-tune et"
  - "citation_engine.py'e güven skoru hesaplama ve 'avukata yönlendir' bayrağı ekle"

GELİŞTİRME İLKELERİ:
1. MEVCUT MİMARİYİ BOZMADAN geliştir — geriye dönük uyumluluk zorunlu.
2. Her değişiklik için ÖNCE etkilenen modülleri listele, SONRA kod yaz.
3. Yeni özellikler için unit test taslağı sun.
4. Performans değişikliklerinde ÖNCE/SONRA metriklerini tahmin et.
5. Shadow Model Registry mantığını koru — üretim izolasyonu asla bozulmasın.
6. Halüsinasyon sıfırlama ve deterministik atıf — bu iki temel kural hiçbir geliştirmede gevşetilmez.
7. Türk hukuku terminolojisi resmi kanun adlarıyla (6098 TBK, 6102 TTK vb.) korunmalıdır.
8. API geriye dönük uyumlu → /v1/ask yanıt formatı korunur, yeni özellikler /v2'ye eklenir.

ÇIKTI FORMATI:
- Hangi dosyalar değişiyor / yeni oluşturuluyor → tam dosya yolu listesi
- Değişiklik gerekçesi (neden + beklenen kazanım)
- Tam, çalışır durumdaki kod (yorum satırları dahil)
- requirements.txt / package.json güncelleme (varsa)
- Doğrulama adımları (nasıl test edilir)
```

---

## ÖZET — ÖNCELİK MATRİSİ

| # | Geliştirme | Katman | Öncelik | Zorluk | Beklenen Etki |
|---|---|---|---|---|---|
| 1 | Otomatik mevzuat güncelleme döngüsü | Veri | 🔴 Kritik | Orta | Veri güncelliği |
| 2 | ONNX Runtime embedding | Embedding | 🔴 Kritik | Düşük | +60% hız |
| 3 | Streaming yanıt (SSE) | API + Frontend | 🔴 Kritik | Orta | UX devrim |
| 4 | Redis oturum kalıcılığı | API | 🔴 Kritik | Düşük | Veri kaybı önleme |
| 5 | Rate Limiting (slowapi) | API | 🔴 Kritik | Düşük | Güvenlik |
| 6 | Türkçe Reranker fine-tune | Reranker | 🔴 Kritik | Yüksek | +12% NDCG@7 |
| 7 | Morfoloji tabanlı BM25 tokenizer | Retrieval | 🟡 Orta | Orta | +15% recall |
| 8 | Multi-label domain tespiti | Intent | 🟡 Orta | Düşük | Doğruluk |
| 9 | Yapılandırılmış JSON output | LLM | 🟡 Orta | Düşük | Tip güvenliği |
| 10 | OpenTelemetry tracing | DevOps | 🟡 Orta | Orta | Gözlemlenebilirlik |
| 11 | Parent-child retrieval | Retrieval | 🟢 Düşük | Yüksek | Bağlam kalitesi |
| 12 | Dark mode desteği | Frontend | 🟢 Düşük | Düşük | UX |
| 13 | Kanun kapsamı genişletme (TMK, HMK) | Veri | 🟢 Düşük | Orta | Kapsam |

---

*Bu rapor, LawAgent AI v6.0'ın tüm katmanlarını analiz ederek somut, uygulanabilir ve önceliklendirilmiş teknik geliştirme önerilerini sunmaktadır.*
