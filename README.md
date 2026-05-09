# ⚖️ LawAgent AI — Türk Hukuku RAG Sistemi

> TÜBİTAK 2209/A kapsamında geliştirilen, Türk Borçlar Kanunu (TBK), Türk Ticaret Kanunu (TTK), Tüketici Kanunu (TKHK) ve Yargıtay kararlarını kapsayan yapay zeka destekli hukuk asistanı.

## 🏗️ Mimari

```
LawAgent/
├── BACKEND/
│   ├── src/
│   │   ├── scraper_mevzuat/    # mevzuat.gov.tr spider (Scrapy)
│   │   ├── scraper_yargi/      # yargitay.gov.tr spider (Scrapy)
│   │   ├── scraper/            # preprocessing + legal_chunker
│   │   ├── data/               # corpus JSON + Qdrant storage (gitignore'da)
│   │   ├── embedder.py         # Mursit-Base-TR-Retrieval embedding
│   │   ├── retriever.py        # BM25 + Dense hybrid retrieval
│   │   └── generator.py        # Groq LLM (Llama-3.3-70b) API
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── setup.ps1               # Windows ilk kurulum
│   ├── run_pipeline.ps1        # Windows pipeline
│   └── run_pipeline.sh         # Linux/Docker pipeline
└── FRONTEND/                   # React + Vite + TypeScript
```

## 🚀 Hızlı Başlangıç

### Ön Koşullar
- Python 3.11+
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Docker yöntemi için)
- Groq API anahtarı: https://console.groq.com

---

## 🪟 Yöntem 1: PowerShell (Windows — Önerilen)

```powershell
# 1. Repoyu klonlayın
git clone https://github.com/KULLANICI_ADI/LawAgent.git
cd LawAgent/BACKEND

# 2. İlk kurulum (venv + bağımlılıklar + klasörler)
.\setup.ps1

# 3. .env dosyasını düzenleyin
notepad .env
# GROQ_API_KEY ve QDRANT_URL değerlerini girin

# 4. Pipeline'ı çalıştırın (veri topla → işle → vektörleştir)
.\run_pipeline.ps1

# Scraping'i atlayıp mevcut verilerle başlamak için:
.\run_pipeline.ps1 -SkipScrape

# 5. API'yi başlatın
python src/generator.py --api
# → http://localhost:8000
```

---

## 🐧 Yöntem 2: Bash (Linux / macOS / WSL)

```bash
# 1. Repoyu klonlayın
git clone https://github.com/KULLANICI_ADI/LawAgent.git
cd LawAgent/BACKEND

# 2. Sanal ortam
python -m venv .venv && source .venv/bin/activate

# 3. Bağımlılıklar
pip install -r requirements.txt

# 4. .env oluşturun
cp ../.env.example .env
nano .env  # API anahtarlarını girin

# 5. Pipeline çalıştırın
bash run_pipeline.sh

# Scraping'i atlamak için:
bash run_pipeline.sh --skip-scrape

# 6. API başlatın
python src/generator.py --api
```

---

## 🐳 Yöntem 3: Docker (Tüm Platformlar)

```bash
# 1. Repoyu klonlayın
git clone https://github.com/KULLANICI_ADI/LawAgent.git
cd LawAgent/BACKEND

# 2. .env oluşturun
cp ../.env.example .env
# .env içinde GROQ_API_KEY ve diğer değerleri doldurun

# 3. Sadece pipeline çalıştır (veri topla + işle + vektörleştir)
docker-compose run --rm pipeline

# 4. API başlat
docker-compose up api

# 3+4 birlikte (pipeline bitince API otomatik başlar):
docker-compose up
```

---

## 📊 Pipeline Adımları

| # | Script | Girdi | Çıktı |
|---|--------|-------|-------|
| 1 | `scrapy crawl mevzuat` | mevzuat.gov.tr | `src/data/mevzuat_corpus.json` |
| 2 | `scrapy crawl yargitay` | yargitay.gov.tr | `src/data/yargitay_corpus.json` |
| 3 | `scraper/preprocessing.py` | corpus JSON'ları | Temizlenmiş corpus |
| 4 | `scraper/legal_chunker.py` | Temizlenmiş corpus | `src/data/chunk_corpus.json` |
| 5 | `embedder.py` | chunk_corpus.json | Qdrant vektör DB |
| 6 | `retriever.py` | Qdrant | `src/data/retriever_cache.pkl` |
| → | `generator.py --api` | Retriever + Groq | FastAPI `localhost:8000` |

---

## ⚙️ Ortam Değişkenleri

`.env.example` dosyasını kopyalayarak `.env` oluşturun:

```bash
cp .env.example .env  # Linux/Mac
copy ..\.env.example .env  # Windows
```

| Değişken | Açıklama | Nereden Alınır |
|----------|----------|----------------|
| `GROQ_API_KEY` | Groq LLM API anahtarı | https://console.groq.com |
| `QDRANT_URL` | Qdrant sunucu adresi | Docker: `http://localhost:6333` |
| `ENV` | Ortam (`development`/`production`) | - |
| `NGROK_AUTH_TOKEN` | Ngrok tünel tokeni (isteğe bağlı) | https://dashboard.ngrok.com |

---

## 📦 Teknolojiler

| Bileşen | Teknoloji |
|---------|-----------|
| Web Scraping | Scrapy + BeautifulSoup4 |
| Text Chunking | LegalChunker (özel algoritma) |
| Embedding | `newmindai/Mursit-Base-TR-Retrieval` |
| Vektör DB | Qdrant (local veya cloud) |
| Retrieval | BM25 + Dense Hybrid |
| LLM | Groq / Llama-3.3-70b |
| API | FastAPI + Uvicorn |
| Frontend | React + Vite + TypeScript |

---

## 📄 Lisans

Bu proje TÜBİTAK 2209/A akademik araştırma projesi kapsamında geliştirilmiştir.
