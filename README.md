# ⚖️ LawAgent AI — Türk Hukuku RAG Sistemi

> TÜBİTAK 2209/A kapsamında geliştirilen, Türk Borçlar Kanunu (TBK), Türk Ticaret Kanunu (TTK), Tüketici Kanunu (TKHK) ve Yargıtay kararlarını kapsayan yapay zeka destekli akıllı hukuk asistanı projesidir.

Bu proje iki ana bileşenden oluşmaktadır:
1. **BACKEND (FastAPI & RAG):** Hukuki metinleri işleyen, vektör tabanlı arama yapan ve yapay zeka entegrasyonu sağlayan Python sunucusu.
2. **FRONTEND (React & Vite):** Kullanıcıların hukuk asistanıyla etkileşime girebileceği modern ve dinamik arayüz.

---

## ⚠️ ÖNEMLİ BİLGİ: GitHub'dan İndirilen Dosyalar Hakkında

Bu projeyi GitHub'dan indirdiğinizde, `.gitignore` kuralları gereği **hukuki veri seti (`.json` dosyaları) ve vektör veritabanı (Qdrant) indirilmez.** Bu dosyalar boyutu çok büyük olduğu için Git'te takip edilmez. 

**Bu nedenle projeyi ilk kez kurduğunuzda öncelikle veri kazıma (scraping) ve vektör oluşturma (embedding) ardışık düzenini (pipeline) çalıştırmanız ZORUNLUDUR.** Aksi halde API sunucusu eksik veri hatası vererek çalışmayacaktır.

---

## 🚀 Kurulum ve Çalıştırma Rehberi

Projeyi yerel bilgisayarınızda ayağa kaldırmak için aşağıdaki adımları sırasıyla izleyin.

### 1. Ön Koşullar
- **Python 3.11+** (Backend için)
- **Node.js 18+** (Frontend için)
- **Groq API Anahtarı:** LLM (Llama-3) kullanımı için [console.groq.com](https://console.groq.com) üzerinden ücretsiz bir API anahtarı almanız gerekir.

### 2. Repoyu Klonlayın
```bash
git clone https://github.com/KULLANICI_ADI/LawAgent.git
cd LawAgent
```

### 3. Backend Kurulumu ve Veri Tabanının Hazırlanması

Öncelikle sanal ortamı kurup veritabanını sıfırdan oluşturmalıyız.

```bash
cd BACKEND

# 1. Sanal ortam (venv) oluşturun ve aktif edin
python -m venv .venv
# Windows için: .venv\Scripts\activate
# Mac/Linux için: source .venv/bin/activate

# 2. Bağımlılıkları yükleyin
pip install -r requirements.txt

# 3. Ortam değişkenlerini yapılandırın
# .env.example dosyasının bir kopyasını alıp adını .env yapın.
cp .env.example .env
# Oluşturulan .env dosyasını bir metin editörüyle açıp GROQ_API_KEY bilginizi ekleyin.

# 4. VERİ TABANINI OLUŞTURUN (ZORUNLU İLK ADIM)
# Mevzuat ve Yargıtay sitelerinden güncel veriler çekilecek, parçalanacak ve vektörleştirilecektir.
# İşlem internet hızınıza ve bilgisayarınıza bağlı olarak birkaç dakika sürebilir.
# Windows PowerShell için:
.\run_pipeline.ps1

# Linux/Mac Bash için:
bash run_pipeline.sh

# 5. Sunucuyu başlatın
python src/generator.py --api
```
*(Sunucu başarıyla başlatıldığında `http://localhost:8000` portunda çalışacaktır. Bu terminali kapatmayın.)*

### 4. Frontend Kurulumu ve Başlatılması

Backend çalışmaya devam ederken, **yeni bir terminal penceresi açın** ve kullanıcı arayüzünü ayağa kaldırın.

```bash
cd FRONTEND

# 1. Gerekli kütüphaneleri yükleyin
npm install

# 2. Geliştirme ortamı yapılandırması (Opsiyonel)
# Eğer Backend localhost:8000 portunda çalışıyorsa Vite yapılandırması genellikle sorunsuz çalışır.
# Sorun yaşarsanız FRONTEND dizinine bir .env dosyası oluşturup aşağıdaki değeri ekleyebilirsiniz:
# VITE_API_URL=http://localhost:8000

# 3. Arayüzü başlatın
npm run dev
```
*(Terminalde beliren `http://localhost:5173` bağlantısına tıklayarak LawAgent web arayüzüne ulaşabilirsiniz.)*

---

## 📦 Mimari Yapı ve Teknolojiler

```
LawAgent/
├── BACKEND/
│   ├── src/
│   │   ├── scraper_mevzuat/    # mevzuat.gov.tr veri kazıma (Scrapy)
│   │   ├── scraper_yargi/      # yargitay.gov.tr veri kazıma (Scrapy)
│   │   ├── scraper/            # Ön işleme (preprocessing) ve parçalama (chunking)
│   │   ├── data/               # (İndirilmez!) Corpus JSON'ları ve Qdrant DB burada oluşur
│   │   ├── embedder.py         # Mursit-Base-TR-Retrieval vektörleştirme
│   │   ├── retriever.py        # BM25 + Dense hybrid arama motoru
│   │   └── generator.py        # FastAPI Sunucusu & Llama-3 (Groq) entegrasyonu
│   └── run_pipeline.ps1/sh     # Tüm veri akışını otomatize eden betikler
└── FRONTEND/
    ├── src/
    │   ├── app/pages/          # Web arayüzü ana sayfaları (Home, About, vb.)
    │   └── app/components/     # UI Bileşenleri
    └── package.json            # Node.js yapılandırması
```

| Bileşen | Teknoloji |
|---------|-----------|
| **Frontend** | React, Vite, TypeScript, TailwindCSS |
| **API Server** | FastAPI, Uvicorn |
| **Web Scraping**| Scrapy, BeautifulSoup4 |
| **Vektör DB** | Qdrant (Local) |
| **LLM (Model)** | Llama-3.3-70b (Groq Üzerinden) |

---

## 📄 Lisans
Bu proje Bitirme Projesi kapsamında geliştirilmiştir.
