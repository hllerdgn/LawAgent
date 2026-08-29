# ⚖️ LawAgent AI — Kapsamlı Proje Tanıtım, Mimari ve Teknik Raporu

**Proje Adı:** LawAgent AI (ve Kurumsal Türevi FEK Hukuk & Danışmanlık Platformu)  
**Türü:** Üniversite Bitirme Projesi / Üretim Seviyesi Yapay Zeka Hukuk Asistanı ve Yönetim Sistemi  
**Teknoloji Yığını:** Python (FastAPI, PyTorch, Scrapy, Sentence-Transformers, BM25+, Qdrant), Groq LLM (Llama-3.3-70B), React 18 (TypeScript, Vite, Tailwind CSS v4, Hallmark Design System)  
**Tarih:** 2026  

---

## 📑 İÇİNDEKİLER

1. [Projenin Amacı, Kapsamı ve Çözdüğü Problemler](#1-projenin-amacı-kapsamı-ve-çözdüğü-problemler)
2. [Sistem Mimarisi Genel Bakış](#2-sistem-mimarisi-genel-bakış)
3. [Veri Hazırlama ve Kazıma Katmanı (Data Ingestion & Pipeline)](#3-veri-hazırlama-ve-kazıma-katmanı-data-ingestion--pipeline)
4. [Vektörleştirme ve Temsil Katmanı (Embedding & Vector DB)](#4-vektörleştirme-ve-temsil-katmanı-embedding--vector-db)
5. [İleri Düzey Hibrit Bilgi Getirme Motoru (Hybrid Retrieval Engine)](#5-ileri-düzey-hibrit-bilgi-getirme-motoru-hybrid-retrieval-engine)
6. [İkinci Aşama Yeniden Sıralama (Cross-Encoder Reranker)](#6-ikinci-aşama-yeniden-sıralama-cross-encoder-reranker)
7. [Hukuki Niyet, Kapsam ve Ön İşleme Katmanı (Legal Intent & Scope)](#7-hukuki-niyet-kapsam-ve-ön-işleme-katmanı-legal-intent--scope)
8. [Yanıt Üretimi, Güvenlik ve Atıf Motoru (Generation & Citation Engine)](#8-yanıt-üretimi-güvenlik-ve-atıf-motoru-generation--citation-engine)
9. [Backend API Mimarisi ve Uç Noktalar (FastAPI)](#9-backend-api-mimarisi-ve-uç-noktalar-fastapi)
10. [Frontend Mimarisi ve Hallmark Tasarım Sistemi (React & Vite)](#10-frontend-mimarisi-ve-hallmark-tasarım-sistemi-react--vite)
11. [Yönetici (Admin) Paneli ve Dinamik Belge Yönetimi](#11-yönetici-admin-paneli-ve-dinamik-belge-yönetimi)
12. [DevOps, Dağıtım, Uptime ve İzleme Mimarisi](#12-devops-dağıtım-uptime-ve-izleme-mimarisi)
13. [Projenin Özgün Değeri ve Akademik Katkıları](#13-projenin-özgün-değeri-ve-akademik-katkıları)
14. [Özet ve Proje Çıktıları Tablosu](#14-özet-ve-proje-çıktıları-tablosu)

---

## 1. PROJENİN AMACI, KAPSAMI VE ÇÖZDÜĞÜ PROBLEMLER

### 1.1. Çıkış Noktası ve Problem Tanımı
Geleneksel Büyük Dil Modelleri (LLM), genel hukuk sorularına yanıt verirken şu kritik zaaflara sahiptir:
1. **Halüsinasyon (Uydurma):** Var olmayan kanun maddeleri, yürürlükten kalkmış fıkralar veya yanlış mahkeme kararları üretebilmektedir.
2. **Yerelleştirme ve Dil Yetersizliği:** Türk Hukuk terminolojisi (TBK, TTK, TKHK gibi kanunlar ve Yargıtay içtihat dili) kendine has ağır bir terminolojiye sahiptir. Standart modeller çeviriye dayalı hatalı ifadeler (örn: *"Konsum Kanunu"*, *"Borçlar Hukuku Kanunu"*) üretebilmektedir.
3. **Rol ve Sıfat Karışıklığı:** Hukukta aynı olayda alacaklının hakları ile borçlunun yükümlülükleri taban tabana zıttır. Standart modeller kullanıcının sıfatını varsayarak hatalı yönlendirme yapabilir.
4. **Denetlenebilirlik Eksikliği:** Verilen cevabın hangi yasal kaynağa, hangi fıkraya dayandığı ispatlanamadığı sürece profesyonel hukukta kullanılamaz.

### 1.2. LawAgent AI'nin Çözümü
LawAgent AI; Türk Hukuku'na özel olarak ince ayar (fine-tuning) yapılmış gömme modelleri, çift aşamalı hibrit arama (Dense + Sparse BM25+), Cross-Encoder yeniden sıralama, milisaniye altı niyet ve kavram tespiti, deterministik atıf doğrulama motoru ve modern web arayüzü ile donatılmış uçtan uca güvenilir bir hukuki RAG platformudur.

### 1.3. Yasal Kapsam
- **6098 Sayılı Türk Borçlar Kanunu (TBK)**
- **6102 Sayılı Türk Ticaret Kanunu (TTK)**
- **6502 Sayılı Tüketicinin Korunması Hakkında Kanun (TKHK)**
- **Yargıtay Emsal Kararları (İçtihat Külliyatı)**
- **Kullanıcı/Büro Tarafından Yüklenen Özel Kurumsal PDF Belgeleri (Sözleşmeler, Yönetmelikler)**

---

## 2. SİSTEM MİMARİSİ GENEL BAKIŞ

LawAgent AI, mikro-servis benzeri modüler katmanlara ayrılmış tam ölçekli bir mimariden oluşur:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             KULLANICI / MÜVEKKİL                            │
│                 (React 18 + Vite + Hallmark Tasarım Sistemi)                 │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP POST /ask (JSON)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI BACKEND KATMANI                            │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 1. GÜVENLİK & KAPSAM KONTROLÜ (ScopeChecker & CORS & RateLimit)         │ │
│ └────────────────────────────────────┬────────────────────────────────────┘ │
│                                      ▼                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 2. NİYET & KAVRAM ANALİZİ (legal_intent.py - Regex/Keyword < 1ms)       │ │
│ │    • Hukuki Alan (TBK / TTK / TKHK)                                     │ │
│ │    • Hukuki Sıfat (Kiracı / Alacaklı / Tüketici / Tacir...)             │ │
│ │    • Kavram Türü (Hak / Yükümlülük / Sorumluluk / Yetki)                │ │
│ └────────────────────────────────────┬────────────────────────────────────┘ │
│                                      ▼                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 3. HİBRİT RETRIEVAL (retriever.py)                                      │ │
│ │    ┌───────────────────────────┐     ┌───────────────────────────┐      │ │
│ │    │ Dense: Fine-Tuned Mürşit  │     │ Sparse: BM25+ (Custom     │      │ │
│ │    │ (Qdrant Vector DB, 768d)  │     │ Tokenizer, k1=1.6, b=0.68)│      │ │
│ │    └─────────────┬─────────────┘     └─────────────┬─────────────┘      │ │
│ │                  └──────────────┬──────────────────┘                    │ │
│ │                                 ▼                                       │ │
│ │                 Density-Aware Hybrid Fusion Formülü                     │ │
│ │             + Madde/Kanun/İçtihat Boosting + Diversity Penalty          │ │
│ └────────────────────────────────────┬────────────────────────────────────┘ │
│                                      ▼                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 4. RE-RANKING: BAAI/bge-reranker-base (Cross-Encoder, Top-30 -> Top-7)  │ │
│ └────────────────────────────────────┬────────────────────────────────────┘ │
│                                      ▼                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 5. DETERMINİSTİK BAĞLAM OLUŞTURMA (citation_engine.py -> [K1], [K2] XML)│ │
│ └────────────────────────────────────┬────────────────────────────────────┘ │
│                                      ▼                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 6. LLM GENERATION: Llama-3.3-70B-Versatile (Groq API, Temp=0.1)         │ │
│ └────────────────────────────────────┬────────────────────────────────────┘ │
│                                      ▼                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 7. POST-PROCESSING & DOĞRULAMA:                                         │ │
│ │    • Deterministik Atıf Denetimi (Yalnızca kullanılan kaynakları listele)│ │
│ │    • Terminoloji & Markdown Temizliği (legal_normalizer.py)              │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Doğrulanmış Yanıt + Atıflar
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            FRONTEND SUNUMU                                  │
│             (Etkileşimli Kaynak Kartları, Markdown, Chatbot UI)             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. VERİ HAZIRLAMA VE KAZIMA KATMANI (DATA INGESTION & PIPELINE)

### 3.1. Scrapy Tabanlı Otomatik Kazıma (Web Scraping)
- **Mevzuat Spider (`mevzuat.gov.tr`):** Resmi Gazete ve Mevzuat Bilgi Sistemi üzerinden TBK, TTK ve TKHK kanun metinlerini, fıkra ve bent hiyerarşisiyle çeker.
- **Yargıtay Spider (`karararama.yargitay.gov.tr`):** Yargıtay Hukuk Dairelerinin emsal nitelikteki ilamlarını, karar künyelerini (Esas No, Karar No, Daire) ve hüküm gerekçelerini çeker.

### 3.2. Hukuki Ön İşleme ve Parçalama (Legal Chunking)
Hukuk metinleri rastgele karakter sayısına (ör. 500 karakter) bölünemez; çünkü bir maddenin fıkrası veya istisnası bölündüğünde anlam tamamen bozulur.
- **Madde Bazlı Hiyerarşik Bölümleme:** Her kanun maddesi kendi içinde birincil bir birim olarak tutulur.
- **Uzun Maddelerin Fıkra Düzeyinde Parçalanması:** 1000 karakteri aşan maddeler, fıkra bütünlüğü korunarak mantıksal alt parçalara ayrılır.
- **Metadata Zenginleştirme:** Her parçaya `{ "law": "TBK", "article_no": "117", "title": "Temerrüt", "source": "MEVZUAT", "text": "..." }` üstverisi iliştirilir.
- **Çıktı Dosyaları:** `mevzuat_corpus.json`, `yargitay_corpus.json`, `chunk_corpus_enriched.json`.

---

## 4. VEKTÖRLEŞTİRME VE TEMSİL KATMANI (EMBEDDING & VECTOR DB)

### 4.1. Fine-Tuned Mürşit-Base-TR-Retrieval
- **Temel Model:** `newmindai/Mursit-Base-TR-Retrieval` (768 vektör boyutu).
- **İnce Ayar (Fine-Tuning):** Türk Hukuku sorgu-madde çiftleri üzerinde Contrastive Learning yöntemiyle eğitilmiştir.
- **Performans Değerleri:** Held-Out veri setinde **Hit@1 = 0.733**, **MRR = 0.800**.
- **PyTorch INT8 Kuantizasyon:** Üretim ortamında RAM kullanımını ve çıkarım gecikmesini düşürmek amacıyla model dinamik int8 (`mursit_int8.pt`, 622 MB) formatına kuantize edilmiştir.
- **Query Prefix:** Model mimarisi gereği arama sorguları `"query: "` ön ekiyle vektörleştirilirken, dokümanlar doğrudan indekslenir.

### 4.2. Model Registry ve İzolasyon Mimarisi (`config/embedding_models.py`)
Üretim ortamının stabilitesini bozmadan yeni modelleri test etmek için **Shadow Model Registry** kurulmuştur:
- `production`: `Mursit-Base-TR-Retrieval` (Aktif)
- `shadow_mursit_large`: `Mursit-Large-TR-Retrieval` (1024-dim ModernBERT, test amaçlı)
- `shadow_turk4retrieval`: `TurkEmbed4Retrieval` (768-dim)
- `shadow_bge_m3`: `BAAI/bge-m3` (1024-dim)

### 4.3. Qdrant Vektör Veritabanı
- **Koleksiyonlar:**
  - `lawagent_mursit`: 6098, 6102, 6502 sayılı kanunlar ve Yargıtay emsal kararları (Cosine Distance).
  - `site_corpus`: Admin panelinden dinamik olarak yüklenen kurumsal PDF sözleşmeler ve belgeler.

---

## 5. İLERİ DÜZEY HİBRİT BİLGİ GETİRME MOTORU (HYBRID RETRIEVAL ENGINE)

LawAgent AI'nin bilgi getirme başarısı, Dense (Anlamsal) ve Sparse (Anahtar Kelime) yöntemlerinin dinamik birleşimine dayanır.

### 5.1. BM25+ Sparse Algoritması
Geleneksel BM25'in uzun dokümanları cezalandırma hatasını önleyen **BM25+** varyantı kullanılmıştır:
$$\text{Score}(D, Q) = \sum_{t \in Q} \text{IDF}(t) \cdot \left( \frac{\text{TF}(t, D) \cdot (k_1 + 1)}{\text{TF}(t, D) + k_1 \cdot (1 - b + b \cdot \frac{|D|}{\text{avgdl}})} + \delta \right)$$
- **Parametreler:** $k_1 = 1.6$, $b = 0.68$, $\delta = 1.0$.
- Türkçe'ye özel noktalama ve stop-word arındırması yapan özel tokenizer içerir.

### 5.2. Density-Aware Dynamic Hybrid Fusion
Arama skorları normalize edilerek doğrusal birleşimle harmanlanır:
$$\text{Score}_{\text{Hybrid}} = \alpha \cdot \text{Dense}_{\text{Norm}} + (1 - \alpha) \cdot \text{BM25}_{\text{Norm}}$$
- **Dinamik Alfa ($\alpha$) Ayarlaması:**
  - *Varsayılan Sorgular:* $\alpha = 0.68$ (Anlamsal ağırlıklı).
  - *Doğrudan Madde / Kanun Numarası İçeren Sorgular:* $\alpha = 0.45$ (BM25 anahtar kelime ağırlıklı).
  - *Soyut / Doktrinel Hukuki Kavram Sorguları:* $\alpha = 0.72$ (Yoğun anlamsal ağırlıklı).
  - *Aynı Kanun Yoğunlaşması:* İlk sonuçlarda belirli bir kanun baskınsa $\alpha$'ya $+0.10$ eklenir.

### 5.3. Hukuki Boosting ve Çeşitlilik (Diversity) Kuralları
- **Madde No Eşleşme Boost'u:** Sorguda "TBK 117" veya "Madde 117" geçiyorsa ilgili maddeye $+35.0$ puan eklenir.
- **İçtihat Boost'u:** İçtihat taleplerinde Yargıtay kararlarına $+6.0$ puan eklenir.
- **Kanun-İçi Diversity Penalty:** Tek bir kanunun ardışık maddelerinin (örn: TBK m. 49, 50, 51...) bağlamı tekeline almasını engellemek için aynı kanundan gelen sonraki maddelere $0.05$ kademeli ceza uygulanır.
- **Max Same Article Limiti:** `MAX_SAME_ARTICLE: 1` ile aynı maddenin birden fazla fıkrasının ayrı ayrı listeyi doldurması önlenir.

---

## 6. İKİNCİ AŞAMA YENİDEN SIRALAMA (CROSS-ENCODER RERANKER)

Bi-Encoder modeller (Mürşit ve BM25), sorgu ve dokümanı ayrı ayrı vektörleştirir. Ancak en yüksek alaka düzeyini yakalamak için çapraz dikkat mekanizması gerekir.
- **Model:** `BAAI/bge-reranker-base` (Alternatif Fallback: `ms-marco-MiniLM-L-6-v2`).
- **Çalışma Prensibi:** Hibrit arama sonucunda gelen ilk **30 aday doküman**, sorgu ile çift olarak Cross-Encoder modeline sokulur. Model her adaya $[-10, +10]$ aralığında bir alaka skoru verir.
- **Sonuç:** En yüksek skorlu **Top-7** bağlam nihai üretim için seçilir. Bu sayede ilgisiz veya kenar maddeler elenir.

---

## 7. HUKUKİ NİYET, KAPSAM VE ÖN İŞLEME KATMANI (LEGAL INTENT & SCOPE)

### 7.1. Sıfır Gecikmeli Hukuki Niyet ve Sıfat Tespiti (`legal_intent.py`)
Milisaniye altı (<1ms) çalışan deterministik kural motoru, kullanıcının sorgusunu analiz ederek LLM için sistem bağlamını hazırlar:
- **Alan Tespiti:** `borclar_hukuku`, `tuketici_hukuku`, `ticaret_hukuku`.
- **Niyet Tespiti:** `hak_aciklama`, `yukumluluk_sorgusu`, `prosedur`, `spesifik_madde`, `ictihat_talebi`, `tanim`.
- **Hukuki Sıfat Tespiti:** `alacakli`, `borclu`, `sozlesme_tarafi`, `tuketici`, `satici`, `isveren`, `isci`, `kiraci`, `kiraya_veren`, `kefil`.
- **Kavram Türü Ayrımı:** `HAK`, `YÜKÜMLÜLÜK`, `SORUMLULUK`, `YETKİ`. (Örn: Sorumluluk düzenleyen bir maddeyi kullanıcıya "Bu sizin hakkınızdır" şeklinde sunmayı kesin olarak yasaklar).

### 7.2. Kapsam Denetimi (`scope_checker.py`)
Hukuk dışı (yemek tarifi, yazılım kodu, genel sohbet vb.) sorguları LLM'e göndermeden filtreler; hem API maliyetini düşürür hem de sistemin profesyonel sınırlarını korur.

### 7.3. Akademik Sorgu Yeniden Yazımı (`query_processor.py`)
Kullanıcının halk ağzıyla sorduğu sorular (örn: *"ev sahibi beni çıkarabilir mi"*), doğrudan madde referansı yoksa anlamı bozulmadan akademik hukuk terimlerine dönüştürülür (örn: *"Kiraya verenin gereksinim sebebiyle tahliye davası açma şartları TBK"*).

---

## 8. YANIT ÜRETİMİ, GÜVENLİK VE ATIF MOTORU (GENERATION & CITATION ENGINE)

### 8.1. Büyük Dil Modeli Entegrasyonu
- **Model:** `llama-3.3-70b-versatile` (Groq LPUs üzerinde süper hızlı çıkarım, ~400ms).
- **Yedek Model Havuzu:** Olası kota (429 RateLimit) veya zaman aşımı durumunda otomatik olarak `qwen/qwen3.6-27b`, `openai/gpt-oss-120b`, `groq/compound-mini` modellerine kesintisiz devir yapar.
- **Parametreler:** `Temperature: 0.1` (Yüksek determinizm, sıfır yaratıcı uydurma), `Max Tokens: 2500`.

### 8.2. Deterministik Atıf Motoru (`citation_engine.py`)
1. **XML Bağlam Formatlama:** Getirilen her kaynağa `[K1]`, `[K2]`, `[K3]` benzersiz etiketleri verilir.
2. **Atıf Doğrulama:** LLM yanıtı oluşturduktan sonra `validate_and_extract_citations` fonksiyonu yanıtı Regex ile tarar.
3. **Sahte Kaynak İzolasyonu:** Eğer model bağlamda sunulan 7 kaynaktan sadece `[K1]` ve `[K3]`'e atıf yaptıysa, API çıktısındaki `sources` listesine **yalnızca K1 ve K3 eklenir**. Atıf almayan veya uydurulan kaynaklar son kullanıcıya gösterilmez.

### 8.3. Hukuki Terminoloji ve Markdown Normalizasyonu (`legal_normalizer.py`)
Model çıktılarındaki olası çeviri bozuklukları regex ile resmi kanun adlarına dönüştürülür:
- *"Türk Konsum Kanunu"* $\rightarrow$ *"6502 sayılı Tüketicinin Korunması Hakkında Kanun (TKHK)"*
- *"Borçlar Hukuku Kanunu"* $\rightarrow$ *"6098 sayılı Türk Borçlar Kanunu (TBK)"*

---

## 9. BACKEND API MİMARİSİ VE UÇ NOKTALAR (FASTAPI)

FastAPI tabanlı modern RESTful API mimarisi:

| Metot | Uç Nokta | Açıklama | Yetki / Güvenlik |
|---|---|---|---|
| `POST` | `/ask` & `/v1/ask` | Hukuki soru sorma ve RAG yanıtı üretme | Genel Erişim / Rate Limit Korumalı |
| `GET` | `/clients` | Kayıtlı kurumsal istemcileri ve marka yapılandırmalarını listeler | Genel |
| `GET` | `/clients/{id}` | Belirli bir kurumsal temanın ayarlarını çeker | Genel |
| `POST` | `/upload-document`| Kurumsal PDF yükleme ve `site_corpus` koleksiyonuna vektörleştirme | Admin (`X-Admin-Key`) |
| `GET` | `/admin/documents`| Yüklenmiş kurumsal PDF belgelerini listeler | Admin (`X-Admin-Key`) |
| `DELETE`| `/admin/documents/{name}` | Yüklenen belgeyi ve vektörlerini siler | Admin (`X-Admin-Key`) |
| `GET` | `/admin/stats` | Toplam soru, oturum, belge sayıları ve son sorgular | Admin (`X-Admin-Key`) |
| `GET` | `/memory/{session_id}` | Çok turlu oturum sohbet geçmişi | Genel |
| `GET` | `/health` | Sunucu sağlık denetimi ve sürüm bilgisi | Genel |
| `GET` | `/metrics` | Prometheus formatında sistem metrikleri | İzleme |

---

## 10. FRONTEND MİMARİSİ VE HALLMARK TASARIM SİSTEMİ (REACT & VITE)

### 10.1. Modern Teknoloji Yığını
- **Çatı:** React 18, Vite, TypeScript.
- **Stil:** Tailwind CSS v4, Vanilla CSS Design Tokens (OKLCH renk uzayı).
- **Tipografi:** *Instrument Serif* (Klasik Hukuk Başlıkları), *Geist Sans* (Hümanist Okuma Metni), *JetBrains Mono* (Teknik Etiketler ve Künyeler).

### 10.2. Hallmark Tasarım Sistemi ve Çoklu Tema (Multi-Tenant Engine)
Uygulama, farklı avukatlık bürolarına ve kurumsal kimliklere tek tıkla uyum sağlayan 5 benzersiz temaya sahiptir:
1. **Lumen (Day Foundry):** Serin kemik zemin (`#F7F8F6`), derin lacivert/indigo mürekkep, iki register kuralı (küçük harf serif başlıklar, büyük harf mono etiketler).
2. **Cobalt:** Derin gece mavisi, modern kurumsal hatlar.
3. **Carnival:** Dinamik, sıcak ve enerjik renk paleti.
4. **Grid:** Mühendislik ve teknik hukuk estetiği, yapılandırılmış cetvel çizgileri.
5. **Hum:** Minimalist, editoryal ve sakin tasarım dili.

### 10.3. Sayfa Mimarisi
- **Ana Sayfa (`/`):** Marquee Hero, Uzmanlık Alanları, İstatistikler, Hukuki Süreç Adımları.
- **Hakkımızda (`/about`):** Avukat profilleri, vizyon, misyon ve yetkinlikler.
- **Çalışma Alanları (`/practice-areas` & `/practice-areas/:slug`):** TBK, TTK, TKHK ve özel alan detayları.
- **Çalışma İlkelerimiz (`/work-principles`):** Etik, gizlilik, şeffaflık kuralları.
- **Makaleler / Blog (`/blog` & `/blog/:slug`):** Hukuki inceleme yazıları, mevzuat değerlendirmeleri.
- **İletişim & Randevu (`/contact`):** İnteraktif form, ofis konumu, iletişim kanalları.
- **Yasal Sayfalar:** Çerez Politikası (`/cerez-politikasi`), KVKK Aydınlatma Metni (`/kvkk`), Yasal Uyarı (`/yasal-uyari`).

### 10.4. Akıllı Chatbot Asistan Widget'ı (`ChatbotWidget.tsx`)
- Sayfanın sağ alt köşesinde yer alan, istenildiğinde açılıp kapanabilen interaktif asistan.
- Hızlı soru çipleri (Borçlar, Ticaret, Tüketici).
- Yanıt içi madde kartları, kaynak gösterimi, kopyalama ve oturum sıfırlama butonları.

---

## 11. YÖNETİCİ (ADMIN) PANELİ VE DİNAMİK BELGE YÖNETİMİ

Yetkili avukatların veya site sahiplerinin sistemi teknik bilgiye ihtiyaç duymadan yönetebilmesini sağlar:
- **Admin Dashboard (`/admin`):** Soru trendleri, toplam soru sayısı, indeksli kanun ve özel belge istatistikleri.
- **Belge Yönetimi (`/admin/documents`):** Sürükle-bırak yöntemiyle PDF yükleme. Yüklenen PDF otomatik olarak metne ayrıştırılır, Mürşit ile vektörleştirilir ve Qdrant'a eklenir. Artık asistan bu PDF'deki kurumsal bilgilere de dayanarak cevap verir.
- **Blog Yönetimi (`/admin/blog`):** Yeni hukuki makale ekleme, düzenleme, silme.
- **Çalışma Alanları (`/admin/practice-areas`):** Hizmet alanlarını dinamik yönetme.
- **Site & Tema Ayarları (`/admin/settings`):** İletişim bilgileri, aktif tema seçimi, chatbot görünürlüğü.

---

## 12. DEVOPS, DAĞITIM, UPTIME VE İZLEME MİMARİSİ

### 12.1. Konteynerizasyon (Docker & Docker-Compose)
- **Dockerfile:** Python 3.11 tabanlı, C++ build bağımlılıkları ve Mürşit model ağırlıklarını barındıran optimize imaj.
- **Docker-Compose:** Qdrant Vektör Veritabanı ve FastAPI API sunucusunu tek komutla ayağa kaldırır.

### 12.2. Dağıtım Noktaları
- **Frontend:** Vercel üzerinde küresel CDN ile yüksek hızlı sunum (`npx vercel --prod`).
- **Backend API:** Hugging Face Spaces / Bulut Sunucuları üzerinde 7/24 barındırma.

### 12.3. Kesintisiz Uptime ve Keep-Alive İzleme (`.github/workflows`)
Ücretsiz bulut alanlarının (Hugging Face Spaces vb.) uyku moduna geçmesini engellemek için GitHub Actions iş akışı kurulmuştur:
- Her 5 dakikada bir otomatik curl isteği ile `/health` ucunu tetikler ve sunucuyu daima sıcak tutar.

---

## 13. PROJENİN ÖZGÜN DEĞERİ VE AKADEMİK KATKILARI

1. **Alan Odaklı İnce Ayar:** Genel amaçlı embedding modelleri yerine Türk Hukuk terminolojisine uyarlanmış Türkçe gömme modeli (Mürşit) kullanılmıştır.
2. **Çift Kademeli Bilgi Getirme (Two-Stage Retrieval):** Hibrit arama (Dense + Sparse BM25+) ile Cross-Encoder Reranker birleştirilerek alakasız sonuçlar elenmiştir.
3. **Milisaniye Altı Niyet ve Sıfat Analizi:** LLM'e ihtiyaç duymadan kullanıcının hukuki sıfatını (alacaklı/borçlu/kiracı) ve kavram türünü (hak/yükümlülük) analiz eden yenilikçi kural katmanı geliştirilmiştir.
4. **Sıfır Halüsinasyonlu Deterministik Atıf:** Yalnızca metinde gerçekten kullanılan kaynakların API çıktısına dahil edilmesi sağlanarak hukukta en kritik sorun olan sahte referans riski çözülmüştür.
5. **Uçtan Uca Bütünlük:** Sadece bir algoritma prototipi değil; admin paneli, çoklu kurumsal temaları, dinamik PDF indeksleme motoru ve responsive web arayüzü ile eksiksiz bir ürün ortaya konmuştur.

---

## 14. ÖZET VE PROJE ÇIKTILARI TABLOSU

| Katman | Kullanılan Teknolojiler / Yöntemler | Görevi / Sağladığı Çıktı |
|---|---|---|
| **Veri Toplama** | Scrapy, Python Regex | Mevzuat.gov.tr ve Yargıtay külliyatını hiyerarşik olarak kazıma |
| **Vektör Temsili** | Fine-Tuned Mürşit (PyTorch INT8), Qdrant | 768 boyutlu yoğun anlamsal temsil ve yüksek hızlı vektör araması |
| **Sparse Arama** | Custom BM25+ ($\delta=1.0$) | Kanun ve madde numarası gibi kesin anahtar kelime eşleşmeleri |
| **Hibrit Füzyon** | Density-Aware Fusion, Diversity Penalty | Anlamsal ve anahtar kelime skorlarını akıllı harmanlama |
| **Reranker** | Cross-Encoder (`bge-reranker-base`) | Top-30 adayı çapraz dikkat ile değerlendirip Top-7'ye indirme |
| **Niyet Motoru** | `legal_intent.py` (<1ms) | Hukuki alan, niyet, sıfat ve kavram türü tespiti |
| **Üretim (LLM)** | Groq LPU + Llama-3.3-70B | Hukuki gerekçeli, akademik üsluplu, [K1]-[K2] etiketli yanıt üretimi |
| **Atıf Doğrulama** | `citation_engine.py` | Sahte kaynak uydurmayı engelleyen deterministik atıf süzgeci |
| **Backend API** | FastAPI, Pydantic, Sentry | Asenkron, güvenli, thread-pool destekli REST API |
| **Frontend** | React 18, Vite, Tailwind v4, Hallmark | 5 temalı kurumsal tasarım, chatbot widget'ı, admin portali |
| **Yönetim** | Dynamic PDF Processor | Özel şirket/büro sözleşmelerini sisteme dinamik olarak dahil etme |

---
*Bu rapor, LawAgent AI Bitirme Projesi'nin tüm teknik adımlarını, mimari kararlarını ve kod tabanını eksiksiz olarak belgelemektedir.*
