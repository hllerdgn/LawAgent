# LawAgent Retrieval Degerlendirme Raporu v2

**Olusturma Tarihi:** 2026-07-24 16:03:35  
**Metodoloji Versiyonu:** eval_v2.py  
**k=10 | Bootstrap N=1000 | CI=%95**

## Pipeline Konfigurasyonu

| Parametre | Deger |
|-----------|-------|
| HyDE | Kapali |
| LLM Reranker | Kapali |
| Cross-Encoder | Kapali |
| Contextual Prefix | Aktif (chunk_corpus_enriched.json) |
| BM25+ Hybrid | Aktif (alpha dinamik) |

## 1. Genel Metrikler - Gold vs Held-Out

> NOT: Gold set (38 sorgu), _KEYWORD_TO_ARTICLE boost tablosu ve sinonim enrichment
> ile kalibre edilmistir. Gercek genelleme performansi icin Held-Out seti baz alinmalidir.

| Metrik | Gold Set (n=38) [95% CI] | Held-Out (n=45) [95% CI] | Overfitting Gap |
|--------|--------------------------|--------------------------|-----------------|
| **Hit@1** | - | 0.400 [0.267, 0.533] | -0.400 [OVERFITTING] |
| **Hit@3** | - | 0.622 [0.467, 0.756] | -0.622 [OVERFITTING] |
| **Hit@5** | - | 0.711 [0.578, 0.844] | -0.711 [OVERFITTING] |
| **Hit@10** | - | 0.844 [0.733, 0.933] | -0.844 [OVERFITTING] |
| **MRR** | - | 0.536 [0.425, 0.660] | -0.536 [OVERFITTING] |
| avg_latency_ms | - ms | 2346.0 ms | - |

> **OVERFITTING UYARISI:** Gold vs Held-Out arasindaki fark %15'i asiyor: Hit@1, Hit@3, Hit@5, Hit@10, MRR
> Bu, modelin gold set'e ozgu kurallara overfitting yaptigini gosteriyor.
> Gercek performans held-out metrikleri ile degerlendirilmelidir.

## 2. Kategori Bazli Kirilim

> NOT: Kucuk n'li kategorilerde (n<=5) yuzde yuz gibi sonuclar yaniltici olabilir.

### 2a. Gold Set Kategorileri

| Kategori | n | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR | Uyari |
|----------|---|-------|-------|-------|--------|-----|-------|

### 2b. Held-Out Set Kategorileri

| Kategori | n | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR | Uyari |
|----------|---|-------|-------|-------|--------|-----|-------|
| semantic_tbk | 19 | 0.4211 | 0.6316 | 0.6842 | 0.8947 | 0.548 |  |
| semantic_tkhk | 11 | 0.4545 | 0.5455 | 0.6364 | 0.6364 | 0.5227 |  |
| semantic_ttk | 13 | 0.3846 | 0.7692 | 0.8462 | 0.9231 | 0.5815 |  |
| yargitay_intent | 2 | 0.0 | 0.0 | 0.5 | 1.0 | 0.1964 | Kucuk n |

## 3. Hata Analizi Ozeti

Detayli hata analizi icin failure_analysis.json dosyasina bakin.

| Set | Toplam | Basarisiz | Recall Hatasi | Reranking Hatasi | Basari Orani |
|-----|--------|-----------|---------------|-----------------|--------------|
| Held-Out (45) | 45 | 27 | 7 | 20 | 40.0% |

## 4. Determinizm Testi

> LLM adimi (HyDE / LLM Reranker) aktif degil. Embedding+BM25 pipeline'i tamamen deterministiktir — test atlandi.

## 5. Versiyon Karsilastirma Tablosu

| Versiyon | Tarih | Set | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR | Not |
|----------|-------|-----|-------|-------|-------|--------|-----|-----|
| v1.0 (baseline) | 2025-06 | gold (38) | 0.605 | 0.789 | 0.868 | 0.921 | 0.697 | Dense-only, alpha=0.5 |
| v1.3 | 2025-07 | gold (38) | 0.763 | 0.868 | 0.921 | 0.947 | 0.815 | BM25+ Hybrid, BOOST_KANUN=6 |
| v1.4 | 2025-07 | gold (38) | 0.842 | 0.921 | 0.974 | 1.0 | 0.886 | _KEYWORD_TO_ARTICLE x25, 60+ kural |
| v1.6 | 2025-07 | gold (38) | 0.947 | 1.0 | 1.0 | 1.0 | 0.974 | Contextual prefix, HyDE, sinonim genişletme |
| v1.6 | 2025-07 | held-out (45) | 0.4 | 0.6 | 0.711 | 0.867 | 0.542 | Baseline held-out — OVERFITTING TESPİTİ |
| v1.7 (reranker) | 2025-07 | held-out (45) | 0.489 | 0.822 | 0.867 | 0.911 | 0.652 | LLM Reranker (Groq Llama-3.3-70B) aktif |
| **v2.0 (eval_v2)** | 2026-07 | held-out (45) | 0.4 | 0.6222 | 0.7111 | 0.8444 | 0.5359 | vanilla |

## 6. Metodoloji Notlari

### Hit@k Tanimi
Dogru hukuki madde (law + article_no eslesme) ilk k sonuc icinde varsa Hit=1.
Yargitay sorgularinda herhangi bir yargitay chunk'i first k'da ise Hit=1.

### MRR (Mean Reciprocal Rank)
MRR = (1/n) x Sigma (1/rank_i). Dogru sonuc top-k'ya hic girmemisse rank=inf, 1/rank=0.

### Bootstrap CI
1000 bootstrap iterasyonu, seed=42, CI=%95. Kucuk setlerde (n<50) CI genis olabilir.

### Overfitting Gap
Gold - Held-Out farki >%15 ise [OVERFITTING] isaretlenir.

### Recall vs Reranking Hatasi
- recall_failure: Hit@10=False — dogru madde top-10 adayina hic girmemis.
- reranking_failure: Hit@10=True ama Hit@1=False — madde havuzda var ama siralamasi yanlis.
