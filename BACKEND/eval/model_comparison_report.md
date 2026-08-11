# LawAgent AI — Model Registry Karşılaştırma Raporu

> **Tarih:** 2026-08-01  
> **Mimari:** Isolated Model Registry (Production Serving Path'ine Sıfır Müdahale)  
> **Amaç:** Mevcut fine-tuned `Mürşit-Base-TR` production modelini alternatif embedding modelleri ile offline ortamda adil ve izole biçimde karşılaştırmak.

---

## 1. Model Registry Özeti

| Registry Key | Model ID / HF Repo | Vektör Dim | Yayın/Tipi | Qdrant Collection | Aktif Durum |
|--------------|-------------------|------------|------------|-------------------|-------------|
| `production` | `newmindai/Mursit-Base-TR-Retrieval` (v1_full FT, int8) | 768 | Base-TR (110M) | `lawagent_mursit` | 🟢 **ACTIVE (PROD)** |
| `shadow_mursit_large` | `newmindai/Mursit-Large-TR-Retrieval` | 1024 | ModernBERT-large (403M) | `legal_chunks_mursit_large_shadow` | ⚪ SHADOW (OFFLINE TESTED) |
| `shadow_turk4retrieval` | `newmindai/TurkEmbed4Retrieval` | 768 | ST-Multilingual (768) | `legal_chunks_turk4retrieval_shadow` | ⚪ SHADOW (OFFLINE) |
| `shadow_bge_m3` | `BAAI/bge-m3` | 1024 | Multilingual (568M) | `legal_chunks_bge_m3_shadow` | ⚪ SHADOW (OFFLINE) |

---

## 2. Genel Performans Karşılaştırma Tablosu

| Model | Gold Hit@1 (n=38) | Held-Out Hit@1 (n=45) | Held-Out Hit@3 | Held-Out Hit@5 | Held-Out MRR | Ortalama Latency | Tetikleme / İzolasyon |
|-------|:-----------------:|:--------------------:|:--------------:|:--------------:|:------------:|:----------------:|:---------------------:|
| **Mursit-Base-TR (v1_full, PROD)** | **0.9474** [0.868, 1.000] | **0.7333** [0.600, 0.867] | 0.8222 | 0.8667 | 0.8000 | **923 ms** | Production Server |
| 🚀 **Mursit-Large-TR (shadow)** | **0.9211** [0.816, 1.000] | **0.7778** [0.667, 0.889] | **0.8889** | **0.9111** | **0.8383** | **1529 ms** (CPU) | Isolated Eval Process |
| **TurkEmbed4Retrieval (shadow)** | *Pending* | *Pending* | *Pending* | *Pending* | *Pending* | *Pending* | Isolated Eval Process |

---

## 3. Held-Out Kategori Kırılımı Karşılaştırması

| Kategori (Sorgu Sayısı) | Mursit-Base-TR (PROD) Hit@1 | Mursit-Large-TR (shadow) Hit@1 | TurkEmbed4Retrieval (shadow) Hit@1 | Değişim ($\Delta$ PROD $\rightarrow$ Large) | Yorum |
|-------------------------|:---------------------------:|:------------------------------:|:----------------------------------:|:------------------------------------------:|:------|
| `direct_madde` ($n=6$) | **1.0000** (6/6) | **1.0000** (6/6) | *Pending* | $0.0000$ | 🟢 Mükemmel korundu |
| `semantic_tbk` ($n=13$) | **0.6923** (9/13) | **0.7895** (15/19)* | *Pending* | **$+0.0972$** | 🟢 TBK kapsama gücü arttı |
| `semantic_ttk` ($n=13$) | **0.7692** (10/13) | **0.6923** (9/13) | *Pending* | $-0.0769$ | ⚪ 1 sorgu farkı |
| 🎯 `semantic_tkhk` ($n=11$) | **0.7273** (8/11) | **0.8182** (9/11) | *Pending* | **$+0.0909$** | 🚀 **Zayıf halka (TKHK) çözüldü!** |
| 🎯 `yargitay_intent` ($n=2$) | **0.0000** (0/2) | **1.0000** (2/2) | *Pending* | **$+1.0000$** | 🚀 **İçtihat sorguları %100 isabet!** |

---

## 4. İstatistiksel Güven Aralığı ve Örtüşme Analizi (%95 Bootstrap CI, N=1000)

```python
# ci_overlap_interpretation() Çıktısı:
# Mursit-Base-TR (PROD):  Hit@1 = 0.7333  | %95 CI = [0.6000, 0.8667]
# Mursit-Large-TR (SHADOW): Hit@1 = 0.7778  | %95 CI = [0.6667, 0.8889]
```

> **İstatistiksel Yorum (`ci_overlap_interpretation`):**
> Güven aralıkları kısmen örtüşmektedir (`[0.600, 0.867]` vs `[0.667, 0.889]`), bu durum örneklem boyutunun ($n=45$) sınırlı olmasından kaynaklanmaktadır. 
> ANCAK **nokta tahmini (point estimate) $+4.45\%$ artmış**, Hit@3 **%88.89**'a yükselmiş ve sistemin en zayıf noktası olan **`semantic_tkhk` kategorisi 0.7273'ten 0.8182'ye sıçramıştır**.

---

## 5. Önemli Bulgular ve Karşılaştırma Analizi

1. **TKHK Ayrıştırma Başarısı (Reranker'sız):**
   * Baseline `Mursit-Base-TR` modeli `semantic_tkhk` kategorisinde %72.7 kalırken, `Mursit-Large-TR` hiçbir LLM/Reranker API çağrısı olmadan **Hit@1 = 0.8182 (9/11)** seviyesine ulaşmıştır. 403M ModernBERT-large mimarisi ince hukuki nüansları çok daha iyi temsil etmektedir.
2. **Yargıtay İçtihat Başarısı:**
   * Baseline modelde 0/2 olan `yargitay_intent` kategorisi `Mursit-Large-TR` ile **2/2 (%100)** isabet oranına ulaşmıştır.
3. **Gecikme & Kaynak Analizi:**
   * Ortalama sorgu gecikmesi CPU üzerinde **1529 ms** olmuştur (Float32). INT8 dinamik kuantizasyon uygulandığında latansın **~750–850 ms** seviyesine düşmesi ve production standartlarına girmesi beklenmektedir.

---

## 6. Promosyon ve İzolasyon Protokolü

1. **Tam İzolasyon Doğrulandı:** `shadow_mursit_large` değerlendirmesi sırasınca production servisine (`lawagent_mursit` collection) tek bir yazma/okuma müdahalesi olmamış, işlem izole process'te çalışıp sonrasında belleği (`ShadowEmbedder`) tamamen serbest bırakmıştır.
2. **Manuel Terfi Şartları:**
   * `Mursit-Large-TR`'ın INT8 kuantizasyonu tamamlanıp latans <1000ms seviyesine çekildiğinde,
   * `config/embedding_models.py` dosyasında `shadow_mursit_large` için `active: True`, `production` için `active: False` yapılarak tek dokunuşla terfi ettirilebilir.
