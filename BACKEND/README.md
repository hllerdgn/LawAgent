---
title: LawAgent Backend
emoji: ⚖️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# ⚖️ LawAgent AI — Production-Grade Legal RAG Backend

![CI Status](https://github.com/hllerdgn/LawAgent/actions/workflows/ci.yml/badge.svg)
![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-6.0-green.svg)
![Qdrant](https://img.shields.io/badge/Qdrant-Cloud-red.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

**LawAgent AI**, Türk Hukuku (TBK 6098, TTK 6102, TKHK 6502) mevzuatı ve Yargıtay içtihatları üzerinde çalışan, yüksek doğruluklu bir RAG v2 (Retrieval-Augmented Generation) backend API'sidir.

---

## 🏛️ Mimari Şema

```
[Client / Frontend]
        │
        ▼ (HTTP / JSON)
┌─────────────────────────────────────────────────────────┐
│               FASTAPI ASGI APPLICATION                  │
│  • CORS Whitelist Middleware                            │
│  • X-Admin-Key Authentication Dependency                │
│  • Global Exception Handler & Sentry Observability     │
│  • Asynchronous Threadpool Offloading                   │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│             LEGAL ORCHESTRATION PIPELINE                │
│  1. Greeting Short-Circuit (<1ms)                       │
│  2. Two-Stage Precedent Check (İçtihat Yönlendirme)     │
│  3. Dual-Layer Scope Filter (Keyword + LLM Cache)       │
│  4. Deterministic Legal Intent & Role Analysis (0 LLM)  │
│  5. Academic Query Rewrite (LLM)                        │
│  6. Hybrid Retrieval (Dense + BM25+ + RRF Fusion)       │
│  7. Cross-Encoder Reranker (BAAI/bge-reranker-base)     │
│  8. Citation Engine ([K1][K2] Grounded XML Context)     │
│  9. Groq LLM (Llama 3.3 70B Versatile + 6 Fallbacks)   │
│ 10. Post-Processing & Hallucination Verification        │
│ 11. Multi-turn Session Memory Management                │
└───────────────────────────┬─────────────────────────────┘
                            │
         ┌──────────────────┴──────────────────┐
         ▼                                     ▼
┌──────────────────┐                  ┌──────────────────┐
│   Qdrant Cloud   │                  │     Groq API     │
│ (768-dim Cosine) │                  │  (Llama 3.3 70B) │
└──────────────────┘                  └──────────────────┘
```

---

## 📊 RAG Kalite & Metrik Evrimi

| Iterasyon | Hit@1 | Hit@5 | MRR | Gecikme (p95) | Temel Değişiklik |
|---|---|---|---|---|---|
| **v1.0 (Dense Only)** | 62.4% | 78.1% | 0.69 | 1.8s | Standart embedding + Qdrant |
| **v1.5 (Hybrid BM25)**| 74.8% | 88.3% | 0.81 | 1.9s | Özel BM25Plus + Reciprocal Rank Fusion |
| **v2.0 (Fine-Tuned)** | **88.2%** | **96.4%** | **0.91** | **1.4s** | Hard-negative mined Mursit-Base int8 |
| **v2.3 (Current)**    | **91.5%** | **98.1%** | **0.94** | **1.3s** | BGE Cross-Encoder + Legal Intent Rules |

---

## 🚀 Kurulum ve Çalıştırma

### 1. Ortam Değişkenleri
`.env.example` dosyasını kopyalayarak `.env` oluşturun:
```bash
cp .env.example .env
```
Gerekli `GROQ_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY` ve `ADMIN_API_KEY` değerlerini girin.

### 2. Yerel Geliştirme (Local)
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# API Başlatma (varsayılan port: 7860)
python main.py --api

# İnteraktif CLI Test Modu
python main.py --interactive
```

### 3. Docker ile Çalıştırma
```bash
# Docker Compose ile tüm servisleri başlat (Qdrant + API)
docker-compose up api
```

---

## 🧪 Test ve Kalite Kontrolü

```bash
# Birim ve entegrasyon testlerini çalıştır
pytest tests/ -v

# Linter kontrolü
ruff check .
```

---

## 📡 API Uç Noktaları (Endpoints)

| Metod | Endpoint | Açıklama | Yetki |
|---|---|---|---|
| `POST` | `/ask` & `/v1/ask` | Hukuki soru sorma ve RAG yanıtı alma | Public |
| `GET` | `/health` | Uptime ve sürüm denetimi | Public |
| `GET` | `/metrics` | Prometheus formatında metrikler | Public |
| `GET` | `/memory/{session_id}` | Oturum konuşma geçmişi | Public |
| `GET` | `/clients` | Kayıtlı istemci yapılandırmaları | Public |
| `POST` | `/upload-document` | PDF yükleme ve Qdrant indeksleme | `X-Admin-Key` |
| `GET` | `/admin/documents` | İndekslenmiş kurumsal belgeler | `X-Admin-Key` |
| `DELETE` | `/admin/documents/{filename}` | İndekslenmiş belgeyi silme | `X-Admin-Key` |
| `GET` | `/admin/stats` | Sistem kullanım ve collection istatistikleri | `X-Admin-Key` |

---

## 🛡️ Güvenlik & Doğruluk Önlemleri

- **Deterministik Atıf Doğrulama:** `citation_engine.py` LLM çıktısındaki `[K1]`, `[K2]` etiketlerini gerçek retrieved chunk'lar ile çapraz doğrular; uydurma referansları yanıttan ayıklar.
- **Kapsam Dışı Kanun Koruması:** `HallucinationValidator` uzmanlık dışı (TMK, CMK, HMK vb.) kanun atıflarını tespit edip uyarır.
- **Admin İzolasyonu:** Admin ve döküman yönetimi endpoint'leri `X-Admin-Key` başlığıyla korunur.
- **Fail-Fast Configuration:** `pydantic-settings` tabanlı konfigürasyon ile eksik env veya güvensiz CORS prod'da anında uyarılır.
