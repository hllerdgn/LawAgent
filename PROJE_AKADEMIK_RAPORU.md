# LawAgent AI — Türk Hukuku İleri Düzey Hibrit RAG ve Çoklu Temalı Yönetim Sistemi

## Kapsamlı Teknik ve Akademik Proje Raporu

**Proje Türü:** Üniversite Bitirme Projesi  
**Alan:** Yapay Zeka / Doğal Dil İşleme / Hukuk Teknolojileri (LegalTech)  
**Teknoloji Yığını:** Python 3.11 · FastAPI · PyTorch · Qdrant · Groq LLM · React 18 · Vite · Tailwind CSS v4  
**Versiyon:** 6.0 (Stable)

---

## İÇİNDEKİLER

1. [Giriş ve Problem Tanımı](#1-giriş-ve-problem-tanımı)  
2. [Veri Mühendisliği ve İngestion](#2-veri-mühendisliği-ve-ingestion)  
3. [Vektör Temsili ve Gömme (Embedding)](#3-vektör-temsili-ve-gömme-embedding)  
4. [Çift Aşamalı Bilgi Getirme (Two-Stage Retrieval)](#4-çift-aşamalı-bilgi-getirme-two-stage-retrieval)  
5. [Hukuki Niyet ve Kapsam Analizi (Sıfır Gecikme)](#5-hukuki-niyet-ve-kapsam-analizi-sıfır-gecikme)  
6. [Üretim, Güvenlik ve Deterministik Atıf Motoru](#6-üretim-güvenlik-ve-deterministik-atıf-motoru)  
7. [Full-Stack Mimari ve Yönetici Paneli](#7-full-stack-mimari-ve-yönetici-paneli)  
8. [Dağıtım ve Kesintisizlik (DevOps)](#8-dağıtım-ve-kesintisizlik-devops)  
9. [Değerlendirme ve Sonuç](#9-değerlendirme-ve-sonuç)

---

## 1. GİRİŞ VE PROBLEM TANIMI

### 1.1. Genel Bağlam: Büyük Dil Modellerinin Hukuktaki Sınırları

Büyük Dil Modelleri (Large Language Models — LLM), son yıllarda doğal dil anlama ve üretme görevlerinde insan başarısına yaklaşan performans sergilemiştir. Ancak bu modellerin genel-amaçlı mimarisi, **profesyonel hukuk pratiği** gibi hassas ve yüksek güvenilirlik gerektiren alanlarda ciddi zaaflar barındırmaktadır.

Türk Hukuku özelinde bu zaaflar şu dört başlık altında somutlaşmaktadır:

#### 1.1.1. Halüsinasyon (Factual Hallucination)
LLM'ler, eğitim verilerindeki korelasyonlara dayanarak istatistiksel olarak tutarlı ancak olgusal olarak yanlış çıktılar üretebilmektedir. Hukuk bağlamında bu durum şu biçimlerde tezahür eder:

- **Sahte kanun maddesi:** Model, var olmayan veya yürürlükten kaldırılmış bir madde numarası üretebilir. Örneğin "TBK Madde 310/A", kodun mevcut yapısında bulunmayan kurgusal bir referanstır.
- **Uydurulmuş Yargıtay kararı:** "Yargıtay 13. HD 2018/4521 E., 2019/1234 K." gibi biçimsel olarak doğru görünen ancak gerçekte var olmayan esas-karar numarası atfı yapılabilmektedir.
- **Hatalı tarihsel bilgi:** TBK, 818 sayılı eski Borçlar Kanunu'nu yürürlükten kaldırmıştır; ancak modeller bu geçiş tarihlerini ve kapsam değişikliklerini çoğu zaman doğru aktaramamaktadır.

#### 1.1.2. Çeviri ve Terminoloji Bozulması
Türk hukuku terminolojisi, Almanca ve Fransız hukuk sistemlerinden alınan kavramları Türkçe sentaksla harmanlayan kendine özgü bir söylem yapısına sahiptir. Genel amaçlı LLM'lerin eğitim verilerindeki oransız İngilizce baskınlığı, Türkçe çıktılarda aşağıdaki bozulmalara yol açmaktadır:

| Modelin Ürettiği Hatalı İfade | Resmi Karşılığı |
|---|---|
| *"Türk Konsum Kanunu"* | 6502 sayılı Tüketicinin Korunması Hakkında Kanun (TKHK) |
| *"Borçlar Hukuku Kanunu"* | 6098 sayılı Türk Borçlar Kanunu (TBK) |
| *"Ticaret Hukuku Kanunu"* | 6102 sayılı Türk Ticaret Kanunu (TTK) |
| *"Medeni Hukuk Kanunu"* | 4721 sayılı Türk Medeni Kanunu (TMK) |

Bu terminoloji bozulmaları yalnızca biçimsel bir problem değildir; bir avukatın ya da hâkimin resmi yazışmalarında bu ifadeleri kullanması ağır pratik ve etik sonuçlar doğurabilir.

#### 1.1.3. Rol ve Sıfat Karışıklığı
Türk Borçlar Hukuku'nda aynı olay içindeki tarafların sahip olduğu hak ve yükümlülükler taban tabana zıttır. Bir kiracının sahip olduğu tahliyeye karşı savunma hakları, kiraya verene zarar veren kullanım nedeniyle taşınmazını boşaltma talebinde bulunma hakkıyla özdeşleştirilemez. Genel LLM'ler kullanıcının sıfatını varsayarak yanlış tarafın haklarını sunan bir yanıt üretebilir; bu da doğrudan maddi zarara neden olabilir.

#### 1.1.4. Denetlenebilirlik ve Kaynak Doğrulaması Eksikliği
Bir hukuki argümanın geçerliliği, atıfta bulunulan kaynağın gerçek ve doğrulanabilir olmasına bağlıdır. Standart LLM çıktılarında "kaynak gösterme" isteğe bağlı ve çoğunlukla kurgusal bir süreçtir. Hangi maddenin hangi iddiayı desteklediği, metnin son işleme safhasında mekanik ve doğrulanabilir biçimde kanıtlanmıyorsa, o çıktı profesyonel hukuk pratiğinde kullanılamaz.

### 1.2. LawAgent AI'nin Önerdiği Çözüm: RAG + Hibrit Retrieval Mimarisi

LawAgent AI, yukarıdaki dört problemi çözmek üzere **Retrieval-Augmented Generation (RAG)** çerçevesini temel alır ve bunu üç katmanlı özgün mühendislik katkısıyla genişletir:

1. **Alan-Özel İnce Ayarlı Gömme:** Türk Hukuku terminolojisine özel fine-tuned anlamsal vektör temsili.
2. **Çift Aşamalı Hibrit Getirme:** Dense vektör araması ve BM25+ anahtar kelime aramasının dinamik füzyonu + Cross-Encoder yeniden sıralama.
3. **Deterministik Atıf Doğrulama:** Yanıtta fiilen atıf yapılan kaynakları algoritmik olarak doğrulayan ve yalnızca bunları listeleyen özel bir doğrulama motoru.

### 1.3. Kapsam

| Yasal Kaynak | Kanun No | Kapsamı |
|---|---|---|
| Türk Borçlar Kanunu (TBK) | 6098 | Sözleşme, tazminat, temerrüt, haksız fiil, kefalet, kira |
| Türk Ticaret Kanunu (TTK) | 6102 | A.Ş., Ltd. Şti., kıymetli evrak, kambiyo |
| Tüketicinin Korunması Hakkında Kanun (TKHK) | 6502 | Cayma hakkı, ayıplı mal, tüketici kredisi |
| Yargıtay Emsal Kararları (İçtihat) | — | Hukuki ilke içtihadı, daire kararları |
| Özel Kurumsal Belgeler | — | Admin panelinden yüklenen şirket sözleşmeleri ve yönetmelikleri |

---

## 2. VERİ MÜHENDİSLİĞİ VE İNGESTION

### 2.1. Mimari Akış

```
mevzuat.gov.tr                    karararama.yargitay.gov.tr
       │                                       │
       ▼                                       ▼
┌──────────────────┐              ┌────────────────────────┐
│ Scrapy MevzuatSpider│            │ Scrapy YargitaySpider  │
│ (HTTP + XPath/CSS) │            │ (HTTP + Regex Parsing)  │
└────────┬─────────┘              └───────────┬────────────┘
         │                                    │
         ▼                                    ▼
 mevzuat_corpus.json               yargitay_corpus.json
         │                                    │
         └────────────────┬───────────────────┘
                          ▼
               preprocessing.py
          (HTML temizleme, encoding normalizasyonu)
                          │
                          ▼
              legal_chunker.py
       (Hiyerarşik parçalama + metadata etiketleme)
                          │
                          ▼
          chunk_corpus_enriched.json
          (3.67 MB, madde ve fıkra bütünlüklü)
                          │
                          ▼
              embedder.py → Qdrant
           (768-dim vektörler, lawagent_mursit)
```

### 2.2. Scrapy Web Kazıma Örümcekleri

#### 2.2.1. Mevzuat Spider
`mevzuat.gov.tr` portalının XML ve HTML yapısından otomatik olarak madde metinleri çekilmektedir. Spider şu bilgileri ayıklar:

- Kanun adı ve numarası
- Kısım, bölüm ve madde hiyerarşisi
- Madde başlığı (var ise)
- Madde metni (fıkralar ve bentler dahil)
- Ek fıkra ve değişiklik tarihleri

#### 2.2.2. Yargıtay Spider
`karararama.yargitay.gov.tr` arayüzünden arama API'si üzerinden emsal kararlar çekilmektedir:

- Daire adı (Hukuk Genel Kurulu, 3. HD, 4. HD vb.)
- Esas numarası ve karar numarası
- Karar tarihi
- Gerekçe metni ve hüküm

### 2.3. Hiyerarşik Hukuki Parçalama (Legal Chunking)

Genel amaçlı metin parçalama stratejileri (sabit karakter uzunluğu, cümle sonuna kesme vb.) hukuk metinleri için yetersizdir. Bir fıkranın ortasından kesilmesi, o fıkradaki istisna ya da şartın bulunduğu bölümü komşu parçadan koparabilir.

LawAgent AI, buna karşın **iki seviyeli hiyerarşik parçalama** kullanmaktadır:

1. **Birincil Birim — Tam Madde:** Her kanun maddesi kendi içinde bağımsız bir chunk oluşturur.
2. **İkincil Bölüm — Uzun Madde Parçalama:** Yapılandırılmış uzun maddeler (≥ 1000 karakter), fıkra sınırlarına saygı gösterilerek bölünür. Fıkra ortasından kesim **asla** yapılmaz.

Her parçanın metadata şeması:

```json
{
  "chunk_id":    "TBK_117_fk2",
  "law":         "TBK",
  "article_no":  "117",
  "title":       "Borçlunun Temerrüdü",
  "source":      "MEVZUAT",
  "text":        "Muaccel bir borcun borçlusu, alacaklının ihtarıyla temerrüde düşer...",
  "fused_score": 0.0,
  "chunk_index": 2,
  "total_chunks": 3
}
```

---

## 3. VEKTÖR TEMSİLİ VE GÖMME (EMBEDDING)

### 3.1. Model Seçiminin Gerekçesi: Fine-Tuned Mürşit-Base-TR-Retrieval

Genel amaçlı çok dilli embedding modelleri (örn: `multilingual-e5-large`, `paraphrase-multilingual-mpnet`), Türkçe hukuk terminolojisi için yetersiz kalır. Temel neden, bu modellerin eğitim verilerinde Türkçe hukuki metinlerin son derece düşük temsil oranına sahip olmasıdır.

**newmindai/Mursit-Base-TR-Retrieval** modeli, Türkçe metin retrieval görevi için özel olarak eğitilmiş bir encoder mimarisidir. LawAgent AI ise bunu daha ileri götürerek:

- **Eğitim Verisi:** Türk Hukuku sorgu-madde çiftlerinden oluşan domain-specific contrastive pair'lar.
- **Eğitim Yöntemi:** Contrastive Learning ile in-batch negative sampling.
- **Erken Durdurma:** Aşırı öğrenmeyi önlemek için epoch 2'de erken durdurma.
- **Held-Out Benchmark Sonuçları:** `Hit@1 = 0.733` · `MRR = 0.800`.

### 3.2. INT8 Dinamik Kuantizasyon

Üretim ortamında bellek verimliliğini ve çıkarım hızını artırmak amacıyla model **PyTorch dinamik INT8 kuantizasyonu** ile sıkıştırılmıştır:

```python
# Kuantizasyon akışı (embedder.py'den özet)
import torch

quantized_model = torch.quantization.quantize_dynamic(
    model,
    {torch.nn.Linear},        # Hedef katman türü
    dtype=torch.qint8          # INT8 ağırlıklar
)
torch.save(quantized_model.state_dict(), "mursit_int8.pt")  # 622 MB
```

Kuantizasyon öncesi FP32 model yaklaşık 1.2 GB yer kaplarken, INT8 modelinin disk boyutu **622 MB**'dır. Çıkarım gecikmesi %30–40 oranında düşmüştür.

### 3.3. Shadow Model Registry Mimarisi

Üretim modelini güncellerken sistem güvenilirliğini korumak için **Shadow Model Registry** adı verilen izolasyon mimarisi geliştirilmiştir.

**Temel Kural:** Üretim servis yolu (`retriever.py`, `generator.py`) her zaman **yalnızca `active: True`** olan kayıtı kullanır. Shadow modeller bu yola asla dahil edilmez.

**Promosyon Prosedürü (manuel):**
1. Shadow model, tutulan test setinde üretim modelini net biçimde geçmiştir.
2. `shadow_x → active: True` / `production → active: False` değişikliği yapılır.
3. FastAPI servisi yeniden başlatılır; yeni model otomatik olarak yüklenir.

```python
# config/embedding_models.py — Kayıt örneği
EMBEDDING_MODEL_REGISTRY = {
    "production": {
        "model_id":   "newmindai/Mursit-Base-TR-Retrieval",
        "vector_dim": 768,
        "active":     True,     # Tek kayıt active=True olabilir
        "quantize":   True,
        "notes":      "Hit@1=0.733, MRR=0.800. PROD model."
    },
    "shadow_mursit_large": {
        "model_id":   "newmindai/Mursit-Large-TR-Retrieval",
        "vector_dim": 1024,     # ModernBERT-large
        "active":     False,    # Asla True yapma — yalnızca eval
    },
    "shadow_bge_m3": {
        "model_id":   "BAAI/bge-m3",
        "vector_dim": 1024,
        "active":     False,
    }
}
```

### 3.4. Qdrant Vektör Veritabanı

**Qdrant**, yüksek boyutlu vektörler için HNSW (Hierarchical Navigable Small World) indeksi kullanan açık kaynaklı bir vektör veritabanıdır.

| Koleksiyon | İçerik | Vektör Boyutu | Mesafe Metriği |
|---|---|---|---|
| `lawagent_mursit` | TBK, TTK, TKHK maddeleri + Yargıtay kararları | 768 | Cosine |
| `site_corpus` | Admin panelinden yüklenen kurumsal PDF'ler | 768 | Cosine |

---

## 4. ÇİFT AŞAMALI BİLGİ GETİRME (TWO-STAGE RETRIEVAL)

### 4.1. Tasarım Gerekçesi: Neden Hibrit?

**Dense-Only Retrieval** güçlü anlamsal temsil sağlar; ancak "TBK Madde 117" veya "6502 sayılı Kanun'un 11. maddesi" gibi kesin anahtar kelime sorgularında başarısız olabilir. Vektör uzayında "117" sayısı anlamsal komşuluğu belirlemez.

**Sparse-Only (BM25)** ise kesin terim eşleşmelerinde üstün olmakla birlikte eş anlamlılar, dil çeşitlemeleri ve morfolojik çekim farklılıklarını (Türkçe'nin zengin çekim yapısı) göremez.

**Hibrit yaklaşım**, her iki yöntemin tamamlayıcı güçlü yanlarını birleştirir.

### 4.2. Aşama 1a: BM25+ Sparse Retrieval

Klasik BM25'in uzun dökümanları orantısız biçimde cezalandırma hatasını düzelten **BM25+** varyantı uygulanmıştır. Formül:

$$\text{BM25+}(D, Q) = \sum_{t \in Q} \text{IDF}(t) \cdot \left( \frac{f(t,D) \cdot (k_1 + 1)}{f(t,D) + k_1 \cdot \left(1 - b + b \cdot \dfrac{|D|}{\text{avgdl}}\right)} + \delta \right)$$

Burada:
- $f(t,D)$: $t$ teriminin $D$ dokümanındaki frekansı
- $|D|$: Doküman uzunluğu (token sayısı)
- $\text{avgdl}$: Koleksiyonun ortalama doküman uzunluğu
- $k_1 = 1.6$: Terim doygunluk faktörü
- $b = 0.68$: Uzunluk normalleştirme faktörü
- $\delta = 1.0$: BM25+ alt sınır sabiti (sıfır skoru önler)

**Türkçe'ye özel tokenizer:** Model, Türkçe morfolojisini göz önünde bulundurarak noktalama işaretlerini, özel karakterleri ve tek karakterli tokenleri eler:

```python
def _tokenize(self, text: str) -> List[str]:
    text = text.replace("\u0307", "")               # Nokta üstü birleştirici kaldır
    text = re.sub(r"[^\w\s]", " ", text.lower())    # Noktalama → boşluk
    return [t for t in text.split() if len(t) > 1]  # ≥ 2 char filtresi
```

### 4.3. Aşama 1b: Dense Retrieval (Mürşit)

Kullanıcı sorgusu `"query: "` ön ekiyle vektörleştirilerek Qdrant'ta yakın komşu araması yapılır:

```
Query: "ev sahibi haklı sebep olmadan beni çıkarabilir mi"
    → Encode: Mürşit("query: ev sahibi haklı sebep ...")
    → 768-dim float32 vektör
    → Qdrant HNSW ANN Search (top_k=200, cosine)
    → Dense Hit List [{chunk_id, dense_score}, ...]
```

### 4.4. Density-Aware Dynamic Hybrid Fusion

İki arama sonucu **min-max normalizasyon** ardından doğrusal ağırlıklı ortalama ile birleştirilir:

$$\text{Score}_{\text{Hybrid}} = \alpha \cdot S_{\text{Dense}}^{\text{norm}} + (1 - \alpha) \cdot S_{\text{BM25+}}^{\text{norm}}$$

**Dinamik $\alpha$ (alfa) katsayısı — kontrol tablosu:**

| Sorgu Tipi | Alfa Değeri | Gerekçe |
|---|---|---|
| Soyut kavram / Doktrin | $\alpha = 0.72$ | Anlamsal ağırlık |
| Varsayılan / Karma | $\alpha = 0.68$ | Dengeli |
| Kesin madde referansı | $\alpha = 0.45$ | BM25 anahtar kelime önceliği |
| Tek kanun baskınlığı durumu | $\alpha_{\text{base}} + 0.10$ | Yoğunluk adaptasyonu |

**Hukuki Boosting:** Sorguya eşleşen kanun numarası veya madde no varsa, ilgili parçanın hibrit skoru sabit bir ek puanla artırılır:

| Eşleşme Türü | Ek Puan |
|---|---|
| Madde no tam eşleşmesi (`TBK 117`, `Madde 117`) | $+35.0$ |
| Yargıtay içtihat | $+6.0$ |
| Kanun adı eşleşmesi | $+6.0$ |

**Kanun-İçi Diversity Penalty:** Tek bir kanunun ardışık maddelerinin bağlamı tekeline almasını engellemek için kademeli ceza uygulanır:

```
Sıralama: TBK-117, TBK-118, TBK-119, TTK-25, TBK-120
Ceza:         0.00    0.05    0.10    0.00    0.15
```

**Max Same Article Limiti ($k=1$):** Aynı maddenin farklı parçaları artık ayrı ayrı listeyi dolduramaz; madde bazında yalnızca en yüksek skora sahip parça tutulur.

### 4.5. Aşama 2: Cross-Encoder Reranker

Bi-Encoder modeller sorgu ve dokümanı **ayrı ayrı** kodlar; bu nedenle sorgu-doküman çapraz etkileşimini doğrudan modelleyemez. Cross-Encoder mimarisinde sorgu ve doküman **birlikte** encoder'a sokulur:

```
Input:  [CLS] sorgu metni [SEP] madde metni [SEP]
Output: Alaka skoru ∈ ℝ (sigmoid → [0,1])
```

**Model:** `BAAI/bge-reranker-base` (Alternatif: `cross-encoder/ms-marco-MiniLM-L-6-v2`)

**İşlem akışı:**
```
Hibrit Fusion Çıktısı (Top-30 aday)
          │
          ▼
  Cross-Encoder (sorgu + her aday)
          │
  Her adaya ∈ [-10, +10] skor
          │
          ▼
     Top-7 seçimi
          │
          ▼
  LLM Bağlamı (citation_engine.py)
```

---

## 5. HUKUKİ NİYET VE KAPSAM ANALİZİ (SIFIR GECİKME)

### 5.1. Tasarım Kararı: LLM'siz Niyet Tespiti

Geleneksel yaklaşımda kullanıcının niyeti (intent) tespit edilmek için bir LLM çağrısı yapılır. Bu hem ekstra gecikme hem de ekstra API maliyeti anlamına gelir. LawAgent AI, bu aşamada **sıfır LLM çağrısı** ilkesiyle tasarlanmış **<1ms deterministik regex/keyword motoru** kullanmaktadır.

### 5.2. `legal_intent.py` — Dört Boyutlu Analiz

Her sorgu için `LegalQueryAnalysis` veri yapısı doldurulur:

```python
@dataclass
class LegalQueryAnalysis:
    domain:                str   # "borclar_hukuku" | "tuketici_hukuku" | "ticaret_hukuku"
    intent:                str   # "hak_aciklama" | "yukumluluk_sorgusu" | "prosedur" | ...
    legal_role:            str   # "alacakli" | "borclu" | "kiraci" | "tuketici" | ...
    concept_type:          str   # "hak" | "yukumluluk" | "sorumluluk" | "yetki"
    requires_clarification: bool
    explicit_article:      Optional[str]  # Örn: "117"
    explicit_law:          Optional[str]  # Örn: "TBK"
```

**Boyutlar ve amaçları:**

| Boyut | Tespit Edilen Değerler | Sistem Etkisi |
|---|---|---|
| **Alan** | TBK, TKHK, TTK, bilinmiyor | Vektör araması filtre ağırlıkları |
| **Niyet** | hak_aciklama, prosedur, ictihat_talebi | Retrieval k parametresi, prompt tipi |
| **Hukuki Sıfat** | alacakli, borclu, kiraci, tuketici, kefil, tacir... | Prompt'ta rol bağlamı, yanıt çerçevesi |
| **Kavram Türü** | HAK, YÜKÜMLÜLÜK, SORUMLULUK, YETKİ | Prompt'taki kavram ayrımı kuralı |

**Kavram Türü Ayrımı — Kritik Güvenlik Kuralı:**
```
Madde: TBK 369 — İşverenin Talimat Verme Yetkisi
                      ↓
Kavram Türü Tespiti: YETKİ
                      ↓
LLM Kural: "Borçlunun 'temel haklar' sorusuna
             bu madde DOĞRUDAN CEVAP DEĞİLDİR."
```

### 5.3. `scope_checker.py` — Kapsam Dışı Filtreleme

Hukuk dışı sorguların LLM'e ulaşmadan elenmesi iki katmanda gerçekleşir:

**Katman 1 — Kural Tabanlı Anlık Kontrol:** Hukuki anahtar kelime varlığı, bilinen kapsam dışı kalıplar (yemek, yazılım, spor vb.).
**Katman 2 — LLM Sınıflandırma (Opsiyonel):** Katman 1'in belirsiz bulduğu sorgular için hafif bir LLM değerlendirmesi.

Kapsam dışı sorgular şu sabit yanıtla karşılanır:
> *"Bu soru, Türk Borçlar Kanunu, Türk Ticaret Kanunu ve Tüketicinin Korunması Hakkında Kanun kapsamındaki hukuki konularla ilgili görünmemektedir..."*

### 5.4. `query_processor.py` — Akademik Sorgu Yeniden Yazımı

Kullanıcının günlük dildeki sorusu, doğrudan madde referansı içermiyorsa akademik hukuk diline dönüştürülür:

```
Girdi: "ev sahibim haklı sebep olmadan beni çıkarmaya çalışıyor"
         │
    has_madde_ref() → False
         │
    rewrite_query() via Groq (compound-mini, low-cost)
         │
Çıktı: "Kiraya verenin gereksinim sebebi dışında tahliye davası
        açma şartları TBK 347-354"
```

---

## 6. ÜRETİM, GÜVENLİK VE DETERMİNİSTİK ATIF MOTORU

### 6.1. LLM Entegrasyonu — Groq LPU Altyapısı

**Model:** `llama-3.3-70b-versatile`  
**Altyapı:** Groq LPU™ (Language Processing Unit) — özelleştirilmiş donanım hızlandırıcısı.  
**Gecikme:** ~400ms tam yanıt (8K token çıktı dahil).  
**Parametreler:** `temperature=0.1` (yüksek determinizm, sıfır yaratıcı uydurma), `max_tokens=2500`.

**Yedek Model Havuzu ve Otomatik Devir:**
```python
GROQ_CANDIDATE_MODELS = [
    "llama-3.3-70b-versatile",     # Birincil
    "qwen/qwen3.6-27b",            # 1. Yedek
    "openai/gpt-oss-120b",         # 2. Yedek
    "openai/gpt-oss-20b",          # 3. Yedek
    "groq/compound-mini",          # 4. Yedek (düşük gecikme, düşük maliyet)
]
```

Birincil model RateLimit (429) veya Timeout aldığında sistem **sıfır kullanıcı hatası** ile bir sonraki modele otomatik geçer.

### 6.2. Sistem Promptu Mimarisi (v2.3)

Sistem promptu üç dinamik bölümden oluşur:

```
SISTEM_PROMPT_TEMPLATE
├── {context}             → citation_engine.py'den gelen XML bağlam
├── {legal_role_context}  → legal_intent.py'den gelen sıfat/niyet bilgisi
└── {concept_distinction_rule} → Kavram ayrımı güvenlik kuralı
```

Promptun 10 zorunlu kuralı, güvenilirliği algoritmik olarak zorlamaktadır:

1. **Yalnızca Sağlanan Kaynakları Kullan** — Hafıza bilgisinden kesin yasak
2. **Kaynak Seçiciliği** — Her kaynak için "Doğrudan cevap veriyor mu?" iç değerlendirmesi
3. **Kanun ve Madde Uydurma Yasağı**
4. **Resmi Kanun Terminolojisi Zorunluluğu**
5. **Metin İçi Atıf Kuralı** — `[K1]`, `[K2]` etiket zorunluluğu
6. **Taraflı Yorum Yasağı**
7. **Hukuki Sıfat Varsayma Yasağı**
8. **Kavram Ayrımı** (HAK ≠ YETKİ ≠ SORUMLULUK)
9. **Kaynak Yoksa Açıkça Belirtme Zorunluluğu**
10. **Genel Doktrinsel Sorularda Yapılandırılmış Yanıt**

### 6.3. `citation_engine.py` — Deterministik Atıf Motoru

#### Aşama 1: XML Bağlam Oluşturma
```xml
<HUKUKI_KAYNAKLAR>
[KAYNAK K1]
Tür: Kanun Maddesi
Kanun: 6098 sayılı Türk Borçlar Kanunu (TBK)
Madde: 117
Metin: Muaccel bir borcun borçlusu, alacaklının ihtarıyla...

[KAYNAK K2]
Tür: Yargıtay Emsal Kararı
Karar Künyesi: Yargıtay 13. HD — E.2019/1234 / K.2020/5678
Hukuki İlke: Temerrüt faizinin başlangıç tarihine ilişkin...

[KAYNAK K3]
Tür: Kanun Maddesi
Kanun: 6098 sayılı Türk Borçlar Kanunu (TBK)
Madde: 118
...
</HUKUKI_KAYNAKLAR>
```

#### Aşama 2: LLM Yanıt Üretimi
LLM, yalnızca `[K1]`, `[K2]`, `[K3]` etiketlerini kullanarak yanıt üretir:
> "Temerrüt hükümleri uyarınca [K1] borçlunun alacaklı tarafından ihtara muhatap kılınması şarttır. Yargıtay bu konuda [K2] sayılı kararında..."

#### Aşama 3: Deterministik Doğrulama
```python
def validate_and_extract_citations(answer, source_map, fallback_chunks=None):
    # Yanıtta geçen tüm [K\d+] etiketlerini bul
    found_tags = set(re.findall(r"\[(K\d+)\]", answer))  # → {"K1", "K2"}
    
    validated_sources = []
    for tag in sorted(found_tags):
        if tag in source_map:
            validated_sources.append(source_map[tag])  # Doğrulanmış kaynak
        # K3 kullanılmadıysa → API çıktısına dahil edilmez
    
    return sanitized_answer, validated_sources, is_fully_grounded
```

**Sonuç:** API yanıtındaki `sources` listesi yalnızca metinde `[K1]` ve `[K2]` etiketiyle atıf yapılan 2 kaynağı içerir. `[K3]` metinde geçmediği için listeden çıkarılır.

### 6.4. `legal_normalizer.py` — Post-Processing

```python
CANONICAL_LAW_NAMES = {
    "TKHK": "6502 sayılı Tüketicinin Korunması Hakkında Kanun",
    "TBK":  "6098 sayılı Türk Borçlar Kanunu",
    "TTK":  "6102 sayılı Türk Ticaret Kanunu",
    "TMK":  "4721 sayılı Türk Medeni Kanunu",
    "İİK":  "2004 sayılı İcra ve İflas Kanunu",
    "HMK":  "6100 sayılı Hukuk Muhakemeleri Kanunu",
}

TERMINOLOGY_REPLACEMENTS = [
    (re.compile(r"\bTürk\s+Konsum\s+Kanunu\b", re.I),
     "6502 sayılı Tüketicinin Korunması Hakkında Kanun (TKHK)"),
    (re.compile(r"\bBorçlar\s+Hukuku\s+Kanunu\b", re.I),
     "6098 sayılı Türk Borçlar Kanunu (TBK)"),
    # ... 14 örüntü daha
]
```

---

## 7. FULL-STACK MİMARİ VE YÖNETİCİ PANELİ

### 7.1. FastAPI Backend Mimarisi

**Tasarım Kararları:**
- `asynccontextmanager` ile lifespan yönetimi (startup/shutdown kaynakları)
- `lru_cache` singleton pattern ile `LegalGenerator` ve `LegalRetriever` yeniden kullanımı
- CPU-bound `generate()` işlemi `run_in_threadpool` ile async event loop'u bloklamadan çalışır

**API Yüzey Haritası:**

```
POST /ask               → Hukuki soru yanıtlama (temel uç nokta)
POST /v1/ask            → Sürümlü alias
GET  /health            → Uptime denetimi
GET  /metrics           → Prometheus text formatı metrikleri
GET  /memory/{sid}      → Oturum konuşma geçmişi
GET  /clients           → Multi-tenant istemci listesi
GET  /clients/{id}      → Belirli istemci marka yapılandırması

[Admin — X-Admin-Key zorunlu]
POST   /upload-document           → PDF yükle ve vektörleştir
GET    /admin/documents           → Yüklenmiş belgeleri listele
DELETE /admin/documents/{filename}→ Belge ve vektörleri sil
GET    /admin/stats               → Sistem kullanım istatistikleri
```

**Güvenlik katmanı:**
```python
_admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)

async def verify_admin_key(key: Optional[str] = Security(...)) -> None:
    if not settings.ADMIN_API_KEY:
        return  # Dev ortamı — uyarı verildi ama izin ver
    if key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Geçersiz admin anahtarı.")
```

### 7.2. Frontend — React 18 + Hallmark Tasarım Sistemi

#### Hallmark Tema Motoru (Multi-Tenant)
Beş farklı kurumsal tema, tasarım tokenleri (CSS Custom Properties) aracılığıyla çalışma zamanında uygulanır:

```
src/themes/
├── ThemeProvider.tsx    → Tema bağlamı ve token enjeksiyonu
├── registry.ts          → Tema meta-veri kayıt defteri
├── types.ts             → Theme tipleymeleri (TypeScript)
└── themes/
    ├── lumen.ts         → Serin kemik + lacivert — Editoryal, günlük
    ├── cobalt.ts        → Gece mavisi — Kurumsal, minimal
    ├── carnival.ts      → Sıcak dinamik — Erişilebilir, enerjik
    ├── grid.ts          → Mühendislik cetvelsi — Teknik hukuk
    └── hum.ts           → Sakın editoryal — Yüksek tipografi
```

Her tema, OKLCH renk uzayında tanımlanmış token setinden oluşur:

```css
/* Lumen Day Foundry — tokens.css örneği */
:root[data-theme="lumen"] {
  --color-paper:          oklch(98% 0.005 95);    /* Serin kemik zemin */
  --color-ink:            oklch(22% 0.02 250);    /* Derin indigo metin */
  --color-ink-light:      oklch(50% 0.015 250);
  --color-border:         oklch(90% 0.008 250);
  --color-accent:         oklch(55% 0.18 265);    /* Canlı indigo vurgu */
  --font-display:         "Instrument Serif", serif;
  --font-body:            "Geist", sans-serif;
  --font-mono:            "JetBrains Mono", monospace;
}
```

#### Sayfa Mimarisi (React Router v7)

```
/                       → Ana Sayfa (Marquee Hero, Uzmanlık Alanları)
/practice-areas         → Çalışma Alanları Listesi
/practice-areas/:slug   → Çalışma Alanı Detayı
/about                  → Hakkımızda (Avukat Profilleri)
/work-principles        → Çalışma İlkelerimiz
/blog                   → Makale Listesi
/blog/:slug             → Makale Detayı
/contact                → İletişim ve Randevu Formu
/cerez-politikasi       → Çerez Politikası
/kvkk                   → KVKK Aydınlatma Metni
/yasal-uyari            → Yasal Uyarı

[Admin — Protected]
/admin                  → Dashboard
/admin/documents        → PDF Belge Yönetimi
/admin/blog             → Blog Yönetimi
/admin/practice-areas   → Çalışma Alanı Yönetimi
/admin/settings         → Site ve Tema Ayarları
```

#### Chatbot Widget (`ChatbotWidget.tsx` — 55KB)
- Sayfanın sağ alt köşesine sabitlenmiş, açılır-kapanır panel.
- Hızlı soru çipleri: `Borçlar Hukuku`, `Ticaret Hukuku`, `Tüketici Hakları`.
- Yanıt içinde **etkileşimli kaynak kartları:** Kanun adı, madde no, metin özeti ve kopyalama butonu.
- **Oturum hafızası:** `session_id` (UUID) ile çok turlu konuşma yönetimi.
- **Kapsam Bilgisi:** Asistan kendi sınırlarını (yalnızca TBK, TTK, TKHK) açıkça ifade eder.

#### Admin Paneli
- **`AdminDashboard.tsx` (13 KB):** Toplam soru sayısı, aktif oturum, indeksli kanun/belge sayıları ve son 10 sorgu listesi.
- **`AdminDocuments.tsx` (11.6 KB):** Sürükle-bırak PDF yükleme; arka planda `pdf_processor.py` → metin ayıklama → Mürşit ile vektörleştirme → Qdrant `site_corpus` koleksiyonuna ekleme.
- **`AdminBlog.tsx` (17.5 KB):** Hukuki makale CRUD yönetimi, önizleme, yayın durumu.
- **`AdminSettings.tsx` (15 KB):** Aktif tema seçimi, chatbot görünürlüğü, iletişim bilgileri, KVKK/çerez metin yönetimi.

---

## 8. DAĞITIM VE KESİNTİSİZLİK (DEVOPS)

### 8.1. Konteynerizasyon

```dockerfile
# Dockerfile — Özet
FROM python:3.11-slim

# C++ build bağımlılıkları (FAISS, PyTorch native ops)
RUN apt-get install -y build-essential libffi-dev

# Bağımlılıklar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodu
COPY . /app
WORKDIR /app

# Hugging Face Spaces uyumlu port
EXPOSE 7860
CMD ["python", "main.py", "--api"]
```

```yaml
# docker-compose.yml — Servisler
services:
  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - ./src/data/qdrant_storage:/qdrant/storage
    ports:
      - "6333:6333"

  api:
    build: .
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - QDRANT_URL=http://qdrant:6333
    depends_on: [qdrant]
    ports:
      - "7860:7860"
```

### 8.2. Dağıtım Noktaları

| Katman | Platform | Yöntem |
|---|---|---|
| Frontend | Vercel (Küresel CDN) | `npx vercel --prod` |
| Backend API | Hugging Face Spaces | GitHub Actions otomatik deploy |
| Vektör DB | Qdrant Cloud / Docker | Persistent volume mount |

### 8.3. GitHub Actions Keep-Alive Boru Hattı

Ücretsiz barındırma platformlarının uyku moduna geçmesini önlemek için periyodik ping iş akışı:

```yaml
# .github/workflows/keep_alive.yml
name: LawAgent Keep-Alive
on:
  schedule:
    - cron: '*/5 * * * *'  # Her 5 dakikada bir

jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Health Check
        run: |
          curl -sf ${{ secrets.API_URL }}/health || \
          echo "Servis yanıt vermedi"
```

### 8.4. Sentry Error Tracking

```python
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.2,
        environment=settings.ENV,
    )
```

---

## 9. DEĞERLENDİRME VE SONUÇ

### 9.1. Retrieval Performansı

Held-out test seti üzerinde yürütülen benchmark sonuçları:

| Metrik | Değer |
|---|---|
| Hit@1 (İlk sonuç doğruluk oranı) | **0.733** |
| MRR (Mean Reciprocal Rank) | **0.800** |
| Top-5 Recall | ~0.91 |

### 9.2. Projenin Özgün Mühendislik Katkıları

1. **Domain-Specific Fine-Tuning:** Genel amaçlı embedding'in ötesinde, Türk Hukuku sorgu-madde çiftleriyle ince ayarlı retrieval modeli.
2. **Density-Aware Dynamic Alpha Fusion:** Sorgu tipine göre otomatik alfa katsayısı adaptasyonu; statik alfa'ya göre +12% Hit@1 artışı.
3. **<1ms Legal Intent Engine:** LLM çağrısı olmadan hukuki alan, sıfat ve kavram türünü tespit eden kural motoru.
4. **Deterministik Atıf Süzgeci:** Yalnızca metinde fiilen kullanılan kaynakların API çıktısına dahil edilmesi — hukukta yanlış atıf riskini algoritmik olarak sıfırlar.
5. **Shadow Model Registry:** Üretim stabilitesini bozmadan paralel model değerlendirme altyapısı.
6. **Multi-Tenant Hallmark Design Engine:** Tek bir kod tabanından 5 farklı kurumsal kimliği destekleyen tema sistemi.

### 9.3. Sistem Mimarisi Özet Tablosu

| Katman | Bileşen | Teknoloji / Yöntem | Çıktı |
|---|---|---|---|
| Veri Toplama | Scrapy örümcekleri | HTTP + XPath | 2.3 MB kanun + 0.6 MB içtihat |
| Parçalama | legal_chunker.py | Hiyerarşik bölüm | 3.67 MB enriched corpus |
| Embedding | Fine-Tuned Mürşit INT8 | PyTorch, CL | 768-dim vektörler |
| Vektör DB | Qdrant | HNSW, Cosine | ANN araması <50ms |
| Sparse Retrieval | BM25+ (k1=1.6, δ=1.0) | Özel tokenizer | Top-200 aday |
| Hibrit Fusion | Density-Aware Dinamik α | Min-max norm | Tek sıralı liste |
| Reranker | BAAI/bge-reranker-base | Cross-Encoder | Top-30 → Top-7 |
| Niyet | legal_intent.py | Regex/<1ms | Alan+sıfat+kavram |
| Kapsam | scope_checker.py | Kural+LLM | Hukuk dışı eleme |
| LLM | Llama-3.3-70B (Groq) | RAG prompt | Atıflı yanıt metni |
| Atıf Doğrulama | citation_engine.py | Regex | Doğrulanmış kaynaklar |
| Normalizasyon | legal_normalizer.py | Regex | Temiz resmi metin |
| API | FastAPI v6.0 | Async, ThreadPool | REST JSON |
| Frontend | React 18 + Vite | Hallmark | 5 temalı web UI |
| Admin | Dashboard + PDF | Dynamic Indexing | Anlık vektörleştirme |
| DevOps | Docker + Vercel | CI/CD | 7/24 kesintisiz servis |

---

*Bu rapor, LawAgent AI Bitirme Projesi'nin tüm teknik adımlarını, algoritmik kararlarını, matematiksel temellerini ve uygulama mimarisini eksiksiz biçimde belgelemektedir.*
