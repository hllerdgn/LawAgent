# ⚖️ LawAgent AI — Türk Hukuku RAG Sistemi

> Türk Borçlar Kanunu (TBK), Türk Ticaret Kanunu (TTK), Tüketicinin Korunması Hakkında Kanun (TKHK) ve Yargıtay emsal kararlarını kapsayan, yapay zeka destekli akıllı hukuk asistanı projesidir.

---

## 🏛️ Mimari ve Bileşenler

Proje iki ana katmandan oluşmaktadır:

1. **BACKEND (FastAPI & Hibrit RAG):** 
   - **Retriever:** Mürşit-Base-TR-Retrieval (Dense Vektör) + BM25+ (Sparse Keyword) + Density-Aware Hybrid Fusion.
   - **Reranker:** Cross-Encoder (BAAI/bge-reranker-base) ile yüksek hassasiyetli yeniden sıralama.
   - **Generator:** Llama-3.3-70b (Groq API) ile deterministik [K1], [K2] atıflı hukuki yanıt üretimi.
   - **Legal Intent:** Sıfır gecikmeli hukuki niyet, sıfat ve kavram türü (Hak/Yükümlülük/Sorumluluk/Yetki) analiz motoru.
   - **Citation Engine:** Üretilen yanıtları kaynak maddelerle deterministik olarak doğrulayan ve filtreleyen atıf motoru.

2. **FRONTEND (React 18 & Vite & Tailwind v4):** 
   - Çoklu tema motoru (Hallmark Design System: Lumen, Cobalt, Carnival, Grid, Hum), interaktif sohbet arayüzü ve yönetici paneli.

---

## 🚀 Hızlı Başlangıç

### 1. Ön Koşullar
- **Python 3.10+**
- **Node.js 18+**
- **Groq API Anahtarı:** [console.groq.com](https://console.groq.com) üzerinden temin edilebilir.
- **Qdrant Vektör Veritabanı:** Yerel Docker veya Qdrant Cloud.

---

### 2. Backend Kurulumu ve Başlatılması

```bash
cd BACKEND

# 1. Sanal ortamı hazırlayın
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

# 2. Bağımlılıkları yükleyin
pip install -r requirements.txt

# 3. Ortam değişkenlerini ayarlayın
cp .env.example .env
# .env dosyasına GROQ_API_KEY ve varsa QDRANT_URL bilgilerinizi ekleyin.

# 4. Sunucuyu başlatın
python main.py --api
# veya interaktif CLI modunda test etmek için:
python main.py --interactive
```

---

### 3. Frontend Kurulumu ve Başlatılması

Yeni bir terminal penceresinde:

```bash
cd FRONTEND

# 1. Bağımlılıkları yükleyin
npm install

# 2. Geliştirme sunucusunu başlatın
npm run dev
```

Arayüze `http://localhost:5173` adresinden erişebilirsiniz.

---

## 📦 Proje Dizin Yapısı

```text
Bitirme-projesi/
├── BACKEND/                        # Python Backend Katmanı
│   ├── config/                     # settings.py & embedding_models.py
│   ├── core/                       # logging.py & exceptions.py
│   ├── infrastructure/             # groq_client.py & qdrant_client.py
│   ├── services/                   # prompts.py & reranker.py
│   ├── api/                        # schemas.py & app.py (FastAPI)
│   ├── src/                        # Çekirdek RAG motoru (retriever, generator, legal_intent)
│   ├── main.py                     # Kanonik giriş noktası
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
│
├── FRONTEND/                       # React 18 + Vite + Tailwind v4 Web Arayüzü
│   ├── src/
│   │   ├── app/pages/              # Web sayfaları (Home, Admin, Blog, vb.)
│   │   ├── themes/                 # Hallmark çoklu tema sistemi
│   │   └── config/                 # Multi-tenant yapılandırması
│   └── package.json
│
├── docs/                           # Sistem ve Mimari Dokümantasyonu
│   ├── uptime-monitoring.md        # Uptime ve Keep-Alive izleme rehberi
│   └── retrieval_mimarisi_kapsamli.md # Kapsamlı RAG mimarisi teknik dokümanı
│
├── .github/workflows/              # HF Space 7/24 Keep-Alive iş akışı
├── .env.example                    # Örnek ortam değişkenleri
└── .gitignore                      # Git takip kuralları
```

---

## 📚 Dokümantasyon

* [Kapsamlı Retrieval ve RAG Mimarisi](docs/retrieval_mimarisi_kapsamli.md): Hybrid retrieval, density-aware alpha, Cross-Encoder reranking ve deterministik atıf motoru detayları.
* [Uptime & Keep-Alive Monitoring](docs/uptime-monitoring.md): Hugging Face Spaces sunucusunun 7/24 uyanık ve kesintisiz tutulması için GitHub Actions izleme rehberi.

---

## 📄 Lisans
Bu proje Bitirme Projesi kapsamında geliştirilmiştir.
