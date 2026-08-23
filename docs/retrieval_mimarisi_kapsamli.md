# LawAgent — Modern Legal RAG Retrieval Mimarisi Araştırma Raporu

> **Mevcut Sistem:** Hit@1=0.711 | MRR=0.761 | Dense+BM25 Hybrid | 3.791 chunk | Groq/Llama 3.3
> **Temel Problem:** Çok kanunlu kavramlarda metadata filtering yetersiz kaliyor.

---

## BÖLÜM 1: Metadata Filtering'in Sınırlamaları

### 1.1 Yapısal Problemler

```
Problem 1: Kavram-Kanun Belirsizliği (Concept-Law Ambiguity)
─────────────────────────────────────────────────────────────
"Temerrüt" kavramı:
  → TBK m.117  (borçlunun temerrüdü — genel hüküm)
  → TBK m.106  (alacaklının temerrüdü)
  → TKHK m.33  (konut finansmanı temerrüt — özel hüküm)
  → İİK m.67   (itirazın iptali davasında temerrüt)
  → TTK m.1456 (sigorta sözleşmesinde temerrüt)

Metadata filter {"law": "TBK"} → TKHK m.33'ü kaçırır
Metadata filter {"law": "TKHK"} → TBK m.117'yi kaçırır
Filter yok → her ikisi gelir ama sıralama rastgele
```

| Kavram | Kaçan Kanunlar |
|--------|----------------|
| Temerrüt | TBK, TKHK, İİK, TTK |
| Ayıplı mal | TBK (genel), TKHK (tüketici) |
| Zamanaşımı | TBK, TTK, HMK, CMK |
| Tazminat | TBK (haksız fiil), İş K., TKHK |
| Kira | TBK (genel), İİK (icra) |
| Ticaret | TTK (genel), TBK (ticari sözleşme) |

### 1.2 Teknik Sınırlamalar

| Sorun | Açıklama | LawAgent'ta Görülme |
|-------|----------|---------------------|
| **False Positive Filter** | Yanlış kanun filtresi → doğru madde elenir | TBK filter → TKHK m.33 kayıp |
| **Filter Rigidity** | Binary filtre — ya içerir ya dışarıda bırakır | Prob. ağırlık yok |
| **Morphology Blindness** | "azli" ≠ "azil", "temerrüde" ≠ "temerrüt" | Eval'de 6 başarısız sorgu |
| **Label Dependency** | Metadata manuel/otomatik etiket doğruluğuna bağımlı | Scraper hataları propagate eder |
| **Cross-Reference Blindness** | "TKHK m.33 uygulanmazsa TBK m.117" atıf ilişkisi görülmez | Atıf ağı yok |

---

## BÖLÜM 2: Modern Retrieval Yaklaşımları (20 Strateji)

---

### 2.1 Semantic Retrieval (Anlamsal Retrieval)

**Çalışma Prensibi:**
Sorgu ve dokümanları aynı vektör uzayına gömüp kosinüs benzerliğiyle eşleştirmek. Metadata label'ına gerek yok — anlam doğrudan vektörden çıkar.

```
embed("Kiracı ödeme yapmadı ne olur?") → [0.23, -0.11, 0.67, ...]
embed("TBK m.117 borçlunun temerrüdü") → [0.21, -0.13, 0.65, ...]
cosine_similarity = 0.94 → Yüksek eşleşme
```

**Metadata Problemine Çözümü:**
Kanun adını bilmeden semantik anlam üzerinden doğru maddeye ulaşır. "Temerrüt" sorgusunda TBK ve TKHK maddelerinin her ikisi de vektör uzayında yakın olduğundan ikisi de getirilir.

**Avantajları:**
- Metadata gerektirmez
- Eş anlamlı ve bağlamsal eşleşme yapar
- Çapraz kanun eşleşmesi doğal

**Dezavantajları:**
- Exact keyword (madde numarası) eşleşmesinde zayıf
- Embedding kalitesi dile ve domain'e bağlı
- Türkçe hukuk domain için özel model gerekiyor

**Hukuk Veri Kümesi Uygunluğu:** ⭐⭐⭐⭐ — Mevzuat metni yapısal ama semantik bağ güçlü  
**LawAgent Uygulanabilirliği:** ✅ Zaten uygulanmış (Mursit-Base-TR + Qdrant)

---

### 2.2 Dense Vector Search

**Çalışma Prensibi:**
Tüm dokümanların dense embedding'lerini önceden hesaplayıp HNSW (Hierarchical Navigable Small World) gibi ANN (Approximate Nearest Neighbor) indeksleriyle milisaniyede arama.

```
Offline: corpus → embed() → HNSW index
Online:  query → embed() → HNSW.search(top_k=500) → kandidatlar
```

**Metadata Problemine Çözümü:**
Pre-filtering yerine post-filtering yapılabilir: önce top-500 getir, sonra metadata ile filtrele. Bu "filter first" yerine "retrieve first, filter after" paradigması.

**Hukuk Veri Kümesi Uygunluğu:** ⭐⭐⭐⭐⭐ — Qdrant HNSW milisaniyede çalışır  
**LawAgent Uygulanabilirliği:** ✅ Zaten uygulanmış (CFG.TOP_K_DENSE=200)

---

### 2.3 Hybrid Retrieval — BM25 + Dense

**Çalışma Prensibi:**
İki retrieval sinyalini normalize edip ağırlıklı birleştirmek:

```
Fused Score = α × Dense_Norm + (1-α) × BM25_Norm

α = 0.72 (semantic heavy) → belirsiz doğal dil sorguları
α = 0.45 (keyword heavy) → exact madde no sorguları
```

**Metadata Problemine Çözümü:**
BM25 tam kelime eşleşmesi yaparken dense semantik bağlamı yakalar. "TBK m.117" sorgusunda BM25 exact match yapar; "kiracı ödeme yapmadı" sorgusunda dense semantic match yapar. İkisi birlikte metadata'ya gerek bırakmaz.

**LawAgent Uygulanabilirliği:** ✅ Tam uygulanmış — `hybrid_fuse()` + `BM25Plus` sınıfı  
**Mevcut Eksik:** Sparse vector (SPLADE) entegrasyonu yok, sadece in-memory BM25

---

### 2.4 Query Expansion (Sorgu Genişletme)

**Çalışma Prensibi:**
Kullanıcının kısa sorgusunu eş anlamlı terimler, ilgili maddeler ve teknik terimlerle genişletmek:

```python
# Mevcut LawAgent:
_ESANLAMLILAR = {
    "temerrüt": "temerrüd borçlu gecikme ihtar TBK Madde 117 119",
    "gabin": "aşırı oransızlık sömürme 28",
    ...
}

# Sorgu: "Kiracı kira ödemiyor"
# Genişletilmiş: "Kiracı kira ödemiyor temerrüd borçlu tahliye TBK 117 299 347 349"
```

**Metadata Problemine Çözümü:**
Genişletilmiş sorguda hem kanun numarası hem kavramsal terimler var → BM25 hem exact match hem semantik eşleşme yapabilir.

**Gelişmiş Yöntem — Pseudo Relevance Feedback (PRF):**
```
1. Sorgu ile ilk top-5 dokümanı getir
2. Bu dokümanlardan ortak anahtar kelimeleri çıkar
3. Sorguyu bu kelimelerle yeniden genişlet
4. Yeniden arama yap
```

**LawAgent Uygulanabilirliği:** ✅ Kısmen var (`_ESANLAMLILAR`), genişletilebilir  
**Maliyet:** Çok Düşük | **Etki:** +5–10%

---

### 2.5 Query Rewriting (LLM Tabanlı Sorgu Yeniden Yazma)

**Çalışma Prensibi:**
Kullanıcının doğal dil sorgusunu retrieval için optimize edilmiş teknik forma dönüştürmek:

```
Kullanıcı: "Kiramı artırabilir mi ev sahibim?"
↓ LLM Rewriting
"Kira sözleşmesinde artış oranı yasal sınır TBK madde 344 
 tüketici fiyat endeksi TÜFE yıllık artış üst sınır"
```

**Teknikler:**

| Teknik | Açıklama | Hukuki Kullanım |
|--------|----------|-----------------|
| **Step-back** | Genel kavrama yükselt | "Kiracı sorunum" → "Kira hukukunda genel hükümler" |
| **HyDE** | Hipotez belge üret | "Bu konuda kanun maddesi nasıl olur?" şeklinde metin üret, onu embed et |
| **Multi-query** | 3 farklı ifadeyle arama | Türkçe + teknik terim + madde no kombinasyonu |
| **Chain-of-thought** | Adım adım analiz | "Bu soru hangi kanun dalıyla ilgili?" → sonra retrieval |

**HyDE (Hypothetical Document Embedding) — LawAgent için En Güçlü:**
```python
def hyde_retrieve(query: str, embedder, qdrant):
    # Adım 1: Groq ile hipotetik belge üret
    hyp_doc = groq.generate(f"""
    Türk hukuku kapsamında '{query}' sorusuna cevap veren
    kanun maddesi metni şöyle olurdu:
    """)
    
    # Adım 2: Bu belgeyi embed et (sorgu değil belge)
    hyp_vec = embedder.embed(hyp_doc)
    
    # Adım 3: Bu vektörle arama yap
    results = qdrant.search(collection="lawagent_mursit", 
                            query_vector=hyp_vec, limit=20)
    return results
```

**Neden Güçlü?** Embedding modelinin "kanun maddesi" tarzı metinleri iyi temsil ettiği biliniyor. Sorgu yerine beklenen cevap tarzı metin aranır → domain shift azalır.

**LawAgent Uygulanabilirliği:** ⭐⭐⭐⭐⭐ — Groq API mevcut, 20 satır kod  
**Maliyet:** Düşük (+1 LLM çağrısı, ~200ms) | **Etki:** +10–20%

---

### 2.6 Query Decomposition (Sorgu Ayrıştırma)

**Çalışma Prensibi:**
Karmaşık çok bileşenli soruları alt sorgulara bölerek her birini ayrı retrieval ile çözmek:

```
Kullanıcı: "Tüketiciyim, ayıplı ürünü iade edemiyorum ve satıcı 
            beni tehdit ediyor, ne yapabilirim?"

Decompose:
  Alt sorgu 1: "Ayıplı malda tüketici seçimlik hakları TKHK"
  Alt sorgu 2: "İkrah tehdit ile yapılan işlemin iptali TBK"
  Alt sorgu 3: "Tüketici şikayeti başvuru yolları hakem heyeti"

Her alt sorgu ayrı retrieve → sonuçlar birleştirilir
```

**Metadata Problemine Çözümü:**
Her alt sorgu tek bir kavramı hedeflediğinden metadata belirsizliği azalır. "Ayıplı ürün" alt sorgusu TKHK'yı, "tehdit" alt sorgusu TBK'yı getirir.

**LawAgent Uygulanabilirliği:** ⭐⭐⭐ — Groq ile uygulanabilir ama latency artar  
**Maliyet:** Orta | **Etki:** +15–25% karmaşık sorgularda

---

### 2.7 Self-Query Retriever

**Çalışma Prensibi:**
LLM'in sorgudan yapılandırılmış metadata filter üretmesini sağlamak:

```
Kullanıcı: "2022 sonrası TKHK mesafeli satış hükümleri"

LLM → Structured Query:
{
  "query": "mesafeli satış cayma hakkı teslim",
  "filter": {
    "law": {"$eq": "TKHK"},
    "article_no": {"$in": ["47", "48", "49", "50"]},
    "year": {"$gte": 2022}
  }
}

Qdrant → Bu filtreyle arama
```

**Metadata Problemine Çözümü:**
Kullanıcının doğal dilini, LLM otomatik olarak doğru metadata filtresine çevirir. "TKHK" veya "TBK" yazmaları gerekmiyor.

**LangChain SelfQueryRetriever** ile hazır implementasyon mevcut.

**LawAgent Uygulanabilirliği:** ⭐⭐⭐⭐ — Groq structured output gerekiyor  
**Maliyet:** Orta | **Etki:** +12–18% karmaşık sorgu-filtre kombinasyonlarında

---

### 2.8 LLM-based Retrieval Routing

**Çalışma Prensibi:**
Sorguyu farklı retrieval stratejilerine yönlendiren akıllı router:

```python
def llm_router(query: str) -> RetrievalPlan:
    plan = llm.generate(f"""
    Aşağıdaki hukuki sorgu için retrieval stratejisi belirle:
    Sorgu: {query}
    
    Yanıt formatı JSON:
    {{
      "strateji": "direct_lookup | hybrid | yargitay_focus | multi_kanun",
      "kanunlar": ["TBK", "TKHK"],
      "alpha": 0.6,
      "top_k": 20
    }}
    """)
    return execute_plan(plan, query)
```

**Routing Stratejileri:**

| Sorgu Tipi | Route | Açıklama |
|------------|-------|----------|
| "TBK m.344 nedir?" | `direct_lookup` | Madde no extract → direkt getir |
| "Kiracı hakları?" | `hybrid_tbk` | TBK ağırlıklı hybrid |
| "Yargıtay ne dedi?" | `yargitay_only` | Sadece içtihat corpus |
| "TBK mi TKHK mi geçerli?" | `multi_kanun` | İkisinden de al, karşılaştır |
| "Sözleşme nedir?" | `broad_semantic` | Geniş arama, filtre yok |

**LawAgent Uygulanabilirliği:** ⭐⭐⭐⭐⭐ — `detect_kanun()` + `detect_source_intent()` genişletilerek  
**Maliyet:** Düşük | **Etki:** +8–15%

---

### 2.9 Agentic Retrieval

**Çalışma Prensibi:**
LLM'in retrieval sürecini iteratif olarak yönetmesi:

```python
def agentic_retrieve(query: str, max_iter=3):
    context = []
    for i in range(max_iter):
        # LLM bağlamı değerlendirir
        assessment = llm.assess(f"""
        Soru: {query}
        Mevcut bağlam: {context}
        
        Bu bağlam soruyu yanıtlamak için yeterli mi?
        Eksik bilgi varsa ne aramalıyız?
        """)
        
        if assessment.is_sufficient:
            break
            
        # Yeni alt sorgu üret ve ara
        new_results = retrieve(assessment.follow_up)
        context.extend(new_results)
    
    return context
```

**Metadata Problemine Çözümü:**
Retrieval yetersizse LLM farklı kanunu sorgular — "TBK'da bulamadım, TKHK'ya bak."

**Dezavantajları:**
- Latency 3–5x artar (3 LLM round-trip)
- Groq rate-limit riski
- Ucu açık döngü riski

**LawAgent Uygulanabilirliği:** ⭐⭐ — Demo için güçlü, production için riskli  
**Maliyet:** Yüksek | **Etki:** +20–35% karmaşık, -10% basit sorgu

---

### 2.10 Multi-Stage Retrieval

**Çalışma Prensibi:**
```
Aşama 1: Coarse Retrieval     → Top-500 (hızlı, yaklaşık)
Aşama 2: Lexical Refilter     → Top-100 (BM25 re-score)
Aşama 3: Metadata Filter      → Kanun bazlı daraltma
Aşama 4: Cross-Encoder Rerank → Top-10 (yavaş, kesin)
Aşama 5: Diversity Filter     → Aynı maddeden max 1 chunk
```

**LawAgent Mevcut:** Aşama 1+2+3+5 var. **Aşama 4 (Cross-Encoder) yok.**

---

### 2.11 Retrieve → Rerank Mimarisi

**Çalışma Prensibi:**
Bi-encoder hız için, cross-encoder doğruluk için kullanılır:

```
Bi-encoder (retrieve):  ~1ms   → Top-100 kandidat (yaklaşık)
Cross-encoder (rerank): ~100ms → Top-10 final (kesin)
```

**Fark Ne?**
- **Bi-encoder:** Sorgu ve dokümanı ayrı ayrı embed et → nokta çarpımı → HIZLI ama yaklaşık
- **Cross-encoder:** Sorgu+doküman çiftini birlikte encode et → tam dikkat → YAVAŞ ama kesin

```
Sorgu: "Temerrüde düşen kiracı"
Bi-encoder → [TBK m.106, TBK m.117, TBK m.299, TKHK m.33] (karma sıra)
Cross-encoder → TBK m.117 (ödeme yükümlülüğü + temerrüt = kesin eşleşme)
```

---

### 2.12 Cross-Encoder Reranking ⭐ EN KRİTİK EKSİK

**Çalışma Prensibi:**
Hem sorguyu hem chunk'ı birlikte [SEP] ile concatenate edip sınıflandırma yapan model:

```
Input:  [CLS] sorgu [SEP] chunk [SEP]
Output: Relevance score [0, 1]
```

**Metadata Problemine Çözümü:**
Cross-encoder sorguyu chunk ile birlikte analiz ederek:
- "Bu chunk bu soruya cevap veriyor mu?" → 0.9
- "Bu chunk aynı kelimeyi içeriyor ama farklı bağlamda" → 0.2

Kanun adı bilmeden içerik tabanlı alaka tespiti yapar.

**Türkçe Cross-Encoder Seçenekleri:**

| Model | Boyut | Türkçe Kalite | LawAgent Uyumu |
|-------|-------|---------------|----------------|
| `dbmdz/bert-base-turkish-cased` | 110M | ⭐⭐⭐⭐ | Fine-tune gerekir |
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | 22M | ⭐⭐ (İngilizce) | Transfer öğrenme |
| `intfloat/multilingual-e5-large` | 560M | ⭐⭐⭐⭐ | Ağır |
| **Groq LLM-as-Reranker** | API | ⭐⭐⭐⭐⭐ | **Hemen kullanılabilir** |

**LLM-as-Reranker (LawAgent için En Pratik):**
```python
def llm_rerank(query: str, chunks: list[dict], top_k: int = 10):
    chunk_texts = "\n---\n".join([
        f"[{i+1}] Kaynak: {c['law']} m.{c['article_no']}\n{c['text'][:300]}"
        for i, c in enumerate(chunks[:20])
    ])
    
    prompt = f"""Aşağıdaki hukuki sorgu için en ilgili metin parçalarını 
    1'den (en az ilgili) 10'a (en ilgili) kadar puanla.
    
    Sorgu: {query}
    
    Parçalar:
    {chunk_texts}
    
    Puanlar JSON formatında (chunk_no: puan):"""
    
    scores = json.loads(groq.generate(prompt))
    
    return sorted(
        chunks[:20],
        key=lambda c: scores.get(str(chunks.index(c)+1), 5),
        reverse=True
    )[:top_k]
```

**LawAgent Uygulanabilirliği:** ⭐⭐⭐⭐⭐ — Groq API mevcut  
**Maliyet:** Düşük (+1 Groq çağrısı, ~300ms) | **Etki:** +20–30% MRR

---

### 2.13 ColBERT — Late Interaction Modeli

**Çalışma Prensibi:**
Klasik bi-encoder tüm dokümanı tek vektöre sıkıştırır. ColBERT her token'ı ayrı vektör olarak saklar:

```
Bi-encoder:  sorgu → [1×768]     ·    doküman → [1×768]
ColBERT:     sorgu → [n_q×768]   ⋈    doküman → [n_d×768]
             MaxSim: her sorgu token'ının en iyi doküman token'ıyla skoru
```

**Avantajı:** Bi-encoder hassasiyeti + cross-encoder yorumlanabilirliği  
**Dezavantajı:** Storage 10x artar (her token için vektör)

**Türkçe Hukuk için ColBERT:**
- `colbert-ir/colbertv2.0` (İngilizce, fine-tune gerekir)
- Türkçe ColBERT modeli henüz yaygın değil

**LawAgent Uygulanabilirliği:** ⭐ — Türkçe model yok, yüksek depolama maliyeti  
**Maliyet:** Çok Yüksek | **Etki:** +25–40% (gerçekleşirse)

---

### 2.14 Knowledge Graph Retrieval

**Çalışma Prensibi:**
Hukuki varlıklar ve ilişkileri bir grafik yapısında modeller:

```
Graf Düğümleri: Kanun maddeleri, hukuki kavramlar, kararlar
Graf Kenarları: ATIF_YAPAR, ÖZEL_HÜKÜMDEĞİŞTİRİR, TAMAMLAR, İSTİSNA

(TKHK m.33) --[ÖZEL_HÜKÜM]--> (TBK m.117)
"Tüketici sözleşmelerinde TKHK m.33 geçerli,
 aksi belirtilmedikçe TBK m.117 uygulanmaz."

(TBK m.117) --[BAĞLI]--> (TBK m.118)
(TBK m.117) --[BAĞLI]--> (TBK m.119)
```

**Retrieval:**
```
Sorgu: "Temerrüt" → Graf traversal → m.117 → komşular m.118, m.119
```

**Metadata Problemine Çözümü:**
"TKHK m.33 veya TBK m.117" sorusu grafta ÖZEL_HÜKÜM kenarıyla zaten çözülmüş.

**LawAgent Uygulanabilirliği:** ⭐⭐ — Atıf grafiği oluşturma büyük iş  
**Maliyet:** Çok Yüksek | **Etki:** +25–40%

---

### 2.15 GraphRAG (Microsoft, 2024)

**Çalışma Prensibi:**
Dokümanlardan otomatik varlık grafiği çıkar, topluluk tespiti yap, özet oluştur:

```
Offline:
  1. LLM → Dokümanlardan entity extract (kavramlar, maddeler, kararlar)
  2. LLM → İlişkileri extract
  3. Leiden Algorithm → Topluluk tespiti
  4. Her topluluk için özet üret

Online:
  Sorgu → Graph traversal + community summaries → Context
```

**Metadata Problemine Çözümü:**
"Temerrüt" topluluğu TBK+TKHK+İİK maddelerini otomatik birleştirir.

**LawAgent Uygulanabilirliği:** ⭐ — Üretim maliyeti + Türkçe entity extraction riski  
**Maliyet:** Çok Yüksek | **Etki:** +30–50%

---

### 2.16 Hierarchical Retrieval (Parent-Child Retrieval)

**Çalışma Prensibi:**
```
Parent (geniş bağlam):  TBK Bölüm 10 — Borçlunun Temerrüdü (m.117–m.126)
Child  (spesifik):      TBK m.117 fıkra 1 (ihtar şartı)

Retrieval:
  1. Child chunk ile embed → küçük, spesifik → hassas eşleşme
  2. Eşleşen child'ın parent'ını getir → geniş bağlam → LLM'e ver
```

**Neden Önemli?**
Chunking sırasında bağlamı yitirir. m.117 chunk'ı "Borçlunun temerrüdü — Genel" başlığını kaybetmiş olabilir. Parent chunk bu başlığı içerir.

**LawAgent'a Uygulanması:**
```python
# Mevcut chunk metadata:
{"chunk_id": "TBK_117_0", "law": "TBK", "article_no": "117", ...}

# Parent chunk ekle:
{"chunk_id": "TBK_BOLUM10", "law": "TBK", "bolum": "Borçlunun Temerrüdü",
 "article_range": [117, 126], "text": "Bölüm özeti + m.117-126 birleşik metin"}
```

**LawAgent Uygulanabilirliği:** ⭐⭐⭐ — Chunker yeniden düzenleme gerekiyor  
**Maliyet:** Orta | **Etki:** +8–15%

---

### 2.17 Contextual Retrieval (Anthropic, 2024)

**Çalışma Prensibi:**
Her chunk'a embed etmeden önce LLM ile bağlamsal açıklama ekle:

```
Orijinal chunk:
"Madde 117 – Borçlunun temerrüdü
İfa edilebilir bir borç için borçlu, alacaklının ihtarıyla
temerrüde düşer."

Contextual chunk:
"TBK İkinci Kısım, Bölüm 10 (Borçlunun Temerrüdü) kapsamındaki m.117,
genel temerrüt hükmünü düzenler; ihtar gereği ve istisnalarını içerir.
TKHK m.33 gibi özel hükümler varsa TBK m.117 değil özel hüküm uygulanır.
---
Madde 117 – Borçlunun temerrüdü
İfa edilebilir bir borç için borçlu..."
```

**Anthropic Ölçümü:** Retrieval recall +35–49%.

**LawAgent Uygulanabilirliği:** ⭐⭐⭐ — Tüm corpus yeniden embed edilmeli  
**Maliyet:** Orta-Yüksek | **Etki:** +15–25%

---

### 2.18 Learning to Rank (LTR)

**Çalışma Prensibi:**
Retrieval sıralamasını bir supervised ML modeli olarak öğrenmek:

```
Özellikler:
  f1: dense cosine score
  f2: BM25 score
  f3: kanun eşleşmesi (0/1)
  f4: madde no eşleşmesi (0/1)
  f5: sorgu uzunluğu
  f6: chunk uzunluğu
  f7: yargıtay kararı mı? (0/1)

Label: Relevanslı mı? (gold set'ten)
Model: LambdaMART, RankNet, XGBoost-rank
```

**Metadata Problemine Çözümü:**
Kanun eşleşmesi bir *özellik* olur — mutlak filtre değil. Model "bu chunk TBK olmasına rağmen ilgili" öğrenebilir.

**LawAgent Uygulanabilirliği:** ⭐⭐⭐ — Gold set büyüdükçe güçlenir (şu an 38 sorgu az)  
**Maliyet:** Orta | **Etki:** +10–15% (yeterli etiketli veriyle)

---

### 2.19 Neural Information Retrieval (Dense Passage Retrieval)

**Çalışma Prensibi:**
(Sorgu, pozitif chunk, negatif chunk) üçlüleriyle bi-encoder fine-tune etmek:

```python
# DPR Training
loss = -log(
    exp(sim(q, pos)) / 
    (exp(sim(q, pos)) + Σ exp(sim(q, neg_i)))
)
```

**LawAgent için Özel Fine-Tune:**
```
Eğitim verisi:
  (Sorgu: "Kiracı temerrüdü", Pos: TBK m.117, Neg: TBK m.299)
  (Sorgu: "Ayıplı mal seçimlik hak", Pos: TKHK m.11, Neg: TBK m.219)
```

**LawAgent Uygulanabilirliği:** ⭐⭐ — Fine-tune için çok daha fazla etiketli veri gerekiyor  
**Maliyet:** Yüksek | **Etki:** +20–30% (gerçekleşirse)

---

### 2.20 Probabilistic Law Weighting (LawAgent'a Özgü)

**Çalışma Prensibi:**
Tek kanun seçimi yerine, olasılık dağılımı tabanlı çoklu corpus araması:

```python
def detect_kanun_probabilities(query: str) -> dict:
    q = query.lower()
    probs = defaultdict(float)
    
    # Temerrüt: TBK 60%, TKHK 35%, TTK 5%
    if "temerrüt" in q or "temerrüde" in q:
        probs["TBK"] += 0.6
        probs["TKHK"] += 0.35
        probs["TTK"] += 0.05
    
    if "tüketici" in q:
        probs["TKHK"] += 0.7
        probs["TBK"] += 0.3
    
    # Normalize
    total = sum(probs.values()) or 1
    return {k: v/total for k, v in probs.items()}

def weighted_retrieve(query: str):
    weights = detect_kanun_probabilities(query)
    all_results = []
    for kanun, weight in weights.items():
        results = retrieve(query, law_filter=kanun, top_k=50)
        for r in results:
            r["skor"] *= weight
        all_results.extend(results)
    return dedupe_and_sort(all_results)[:10]
```

**LawAgent Uygulanabilirliği:** ⭐⭐⭐⭐⭐ — 30 satır kod, mevcut altyapıya eklenebilir  
**Maliyet:** Çok Düşük | **Etki:** +8–15% çok kanunlu kavramlarda

---

## BÖLÜM 3: "Metadata Kullanmadan Doğru Kanunu Nasıl Buluruz?"

**Soru:** Kanun adı veya hukuk alanı gibi manuel metadata bilgilerine güvenmeden, kullanıcının doğal dilde sorduğu sorudan doğru kanun maddesi ve doğru içtihadı nasıl otomatik olarak bulabiliriz?

**Cevap — 4 Katmanlı Yaklaşım:**

```
Katman 1: Embedding uzayı zaten semantik ayrıştırma yapar
─────────────────────────────────────────────────────────
embed("Ayıplı mal tüketici seçimlik") → TKHK bölgesi
embed("Ayıplı mal satıcı genel")      → TBK bölgesi
İyi fine-tune edilmiş model metadata'ya gerek bırakmaz.

Katman 2: BM25 exact keyword kanalı
────────────────────────────────────
"TKHK", "6502", "tüketici" → otomatik TKHK eşleşmesi
Kullanıcı "TKHK" yazmasa bile chunk içinde geçiyor.

Katman 3: LLM semantic filtering
─────────────────────────────────
"Bu chunk bu soruyu yanıtlıyor mu?" → Cross-encoder veya LLM-as-reranker
Kanun adı değil içerik alaka skoru.

Katman 4: Atıf bağı (gelecek)
──────────────────────────────
"Özel hüküm genel hükmü bertaraf eder" → Graf kenarı
Sorgu + bağlam → otomatik hukuki hiyerarşi
```

---

## BÖLÜM 4: LawAgent İçin Önerilen Yeni Retrieval Mimarisi

### Mevcut Mimari
```
Query → Embedding → [Metadata Filter] → Qdrant ANN → BM25 → Fusion → LLM
```

### Önerilen 5 Katmanlı Mimari

```
╔══════════════════════════════════════════════════════════════════╗
║                    LawAgent v2 Retrieval                         ║
╠══════════════════════════════════════════════════════════════════╣
║  KATMAN 1: QUERY INTELLIGENCE                                    ║
║  ┌────────────────────────────────────────────────────────────┐  ║
║  │ a) Query Classifier  → direct_lookup / semantic / multi    │  ║
║  │ b) Kanun Weighter    → {"TBK":0.6, "TKHK":0.35} probs    │  ║
║  │ c) HyDE Rewriter     → Groq → hipotez belge üret          │  ║
║  │ d) Query Expander    → _ESANLAMLILAR + LLM                 │  ║
║  └────────────────────────────────────────────────────────────┘  ║
╠══════════════════════════════════════════════════════════════════╣
║  KATMAN 2: MULTI-SIGNAL RETRIEVAL (PARALEL)                      ║
║  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    ║
║  │ Dense    │  │ BM25Plus │  │ Keyword  │  │ Direct       │    ║
║  │ Qdrant   │  │ In-mem   │  │ Boost    │  │ Lookup       │    ║
║  │ top-200  │  │ top-200  │  │ ×35      │  │ (madde no)   │    ║
║  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘    ║
║       └─────────────┴─────────────┴────────────────┘            ║
╠══════════════════════════════════════════════════════════════════╣
║  KATMAN 3: PROBABILISTIC FUSION                                  ║
║  ┌────────────────────────────────────────────────────────────┐  ║
║  │ Kanun ağırlıklı birleştirme:                               │  ║
║  │   skor = (α·dense + β·bm25) × kanun_prob[chunk.law]       │  ║
║  │ Diversity filter: MAX_SAME_ARTICLE=1                        │  ║
║  │ Deduplification                                             │  ║
║  └────────────────────────────────────────────────────────────┘  ║
╠══════════════════════════════════════════════════════════════════╣
║  KATMAN 4: LLM RERANKING (YENİ)                                  ║
║  ┌────────────────────────────────────────────────────────────┐  ║
║  │ Input:  Top-20 chunk                                        │  ║
║  │ Model:  Groq/Llama 3.3 (zero-shot reranker)                │  ║
║  │ Output: Alaka skoru → yeniden sıralama → Top-8             │  ║
║  │ Latency: +200–400ms                                         │  ║
║  └────────────────────────────────────────────────────────────┘  ║
╠══════════════════════════════════════════════════════════════════╣
║  KATMAN 5: CONTEXT ASSEMBLY + LLM GENERATION                     ║
║  ┌────────────────────────────────────────────────────────────┐  ║
║  │ Context: mevzuat chunks + yargıtay içtihatları             │  ║
║  │ Generator: Groq/Llama 3.3                                   │  ║
║  │ Output: Yanıt + kaynak + madde referansları                 │  ║
║  └────────────────────────────────────────────────────────────┘  ║
╚══════════════════════════════════════════════════════════════════╝
```

### Offline / Online Ayrımı

| Bileşen | Çalışma Zamanı | Frekans |
|---------|---------------|---------|
| Embedding (Mursit) | **Offline** | Corpus değiştiğinde |
| Qdrant HNSW index | **Offline** | Corpus değiştiğinde |
| BM25Plus index | **Offline** (cache.pkl) | Corpus değiştiğinde |
| _KEYWORD_TO_ARTICLE | **Offline** (kod) | Geliştirme sırasında |
| _ESANLAMLILAR | **Offline** (kod) | Geliştirme sırasında |
| Query classification | **Online** | Her sorgu |
| Kanun probability | **Online** | Her sorgu (kural bazlı, hızlı) |
| HyDE rewriting | **Online** | Sadece semantic sorguları |
| LLM Reranking | **Online** | Her sorgu |
| LLM Generation | **Online** | Her sorgu |

### Beklenen Performans

| Mimari | Hit@1 | MRR | Latency |
|--------|-------|-----|---------|
| Mevcut (v1) | 0.711 | 0.761 | 1.7s |
| + Kanun Weighting | ~0.78 | ~0.82 | 1.7s |
| + LLM Reranking | ~0.85 | ~0.90 | 2.1s |
| + HyDE | ~0.88 | ~0.92 | 2.5s |
| + Contextual Retrieval | ~0.91 | ~0.94 | 2.5s |
| + Cross-Encoder (fine-tune) | ~0.94 | ~0.96 | 3.0s |

---

## BÖLÜM 5: Kısa / Orta / Uzun Vadeli Yol Haritası

### 🟢 Kısa Vade — Bu Hafta (0 Maliyet, Max Etki)

```
1. Probabilistic Law Weighting          → +8–12% Hit@1
   detect_kanun() → olasılık dağılımı
   skor = base_skor × kanun_prob

2. LLM-as-Reranker (Groq API)          → +15–25% MRR  
   Top-20 chunk → Groq → relevance score → yeniden sırala
   
3. Turkish Morphology Fix               → +5–8%
   "temerrüde" → "temerrüt" için ek keyword
   "azli" → "azil" için ek keyword

4. Query Routing Genişletme             → +5–8%
   direct_lookup / semantic / yargitay / multi_kanun
   
Tahmini Toplam: Hit@1 ~0.85+
```

### 🟡 Orta Vade — 1–2 Hafta

```
5. HyDE Query Rewriting                 → +10–20% semantic
   Groq → hipotetik kanun maddesi üret → embed et → ara

6. Self-Query Retriever                 → +12–18% filtreli
   Groq structured output → dinamik Qdrant filter

7. Parent-Child Chunking                → +8–12%
   Bölüm düzeyi parent + madde düzeyi child

8. Yargıtay Corpus Büyütme             → güvenilirlik
   Spider: 35 → 500+ karar

Tahmini Toplam: Hit@1 ~0.90+
```

### 🔴 Uzun Vade — 1–2 Ay

```
9. Contextual Retrieval                 → +15–25%
   LLM context injection → tüm corpus yeniden embed
   
10. Turkish BERT Cross-Encoder          → +20–30%
    dbmdz/bert-base-turkish-cased fine-tune
    Gold set + negative sampling

11. Atıf Grafiği (Knowledge Graph)      → +20–35%
    Özel/Genel hüküm ilişkileri
    Kanunlar arası atıf ağı

12. DPR Fine-Tune                       → +20–30%
    Hukuki sorgu-madde çiftleriyle bi-encoder eğitimi

Tahmini Toplam: Hit@1 ~0.95+
```

---

## Sonuç

> Metadata filtering'in asıl sorunu kural tabanlı ve binary olması. Çözüm tek bir teknik değil, **anlam + istatistik + LLM muhakemesi** katmanlarını birleştirmek.
>
> LawAgent'ta Katman 1 ve 2 zaten mevcut. **Kritik eksik: Cross-Encoder/LLM Reranking ve Probabilistic Law Weighting.** Bu iki bileşen haftalar içinde eklenebilir ve Hit@1'i 0.711'den 0.85+'a çıkarabilir.
