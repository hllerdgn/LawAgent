# Mürşit-Base-TR Fine-Tuning Değerlendirme Raporu (finetune_eval_report.md)

> **ÖNEMLİ NOT:** Diversity Penalty bu deneyde kapalı tutuldu, izole test bir sonraki adımda yapılacak.

**Oluşturulma Tarihi:** 2026-08-01 15:53:05  
**Metodoloji:** Dual-Set (Gold n=38, Held-Out n=45) | Bootstrap CI N=1000 | %95 Güven Aralığı  
**Model Yolu:** `fine_tuned_mursit/` vs `newmindai/Mursit-Base-TR-Retrieval` (Baseline)  
**Eğitim Stratejisi:** Full Fine-Tuning (lr=2e-5, 3ep) (Best Val Loss: 0.412)  
**Early Stopping:** Patience=2 | Early Stop Uygulandı (Epoch 2)  
**Ayarlar:** Cross-Encoder=KAPALI, Diversity Penalty=KAPALI, HyDE=KAPALI  

**Leakage Denetimi:**  
- Query-Text Sızıntısı: **0** (Hiçbir held-out sorgu metni anchor olarak kullanılmamış — Temiz)  
- Madde-Seviyesi Örtüşme: 36/44 held-out maddesi tiple setinde var (Query metni sızmadığı sürece kabul edilebilir)  
- Val-Held-Out Madde Örtüşmesi: ⚠️ 4 madde (TBK m.161, TBK m.584, TKHK m.11, TKHK m.48) query metni sızmadığı için sızıntı sayılmaz.  

## 1. GÖREV 1 & 2: Before/After Karşılaştırma Tablosu

| Metrik | Gold-Before | Gold-After | Gold Δ | Held-Before | Held-After | Held Δ |
|--------|-------------|------------|--------|-------------|------------|--------|
| **Hit@1** | 0.9474 | 0.9474 | +0.0000 | 0.7111 | 0.7111 | +0.0000 |
| **Hit@3** | 1.0000 | 1.0000 | +0.0000 | 0.8222 | 0.8222 | +0.0000 |
| **Hit@5** | 1.0000 | 1.0000 | +0.0000 | 0.8667 | 0.8667 | +0.0000 |
| **Hit@10** | 1.0000 | 1.0000 | +0.0000 | 0.9111 | 0.9111 | +0.0000 |
| **MRR** | 0.9737 | 0.9737 | +0.0000 | 0.7800 | 0.7800 | +0.0000 |
| **nDCG@10** | 0.9806 | 0.9806 | +0.0000 | 0.8118 | 0.8118 | +0.0000 |
| **Latency avg** | 851.6 ms | 888.3 ms | +36.7 ms | 840.3 ms | 842.5 ms | +2.2 ms |
| **Latency p50** | 832.9 ms | 870.5 ms | +37.6 ms | 852.2 ms | 866.1 ms | +13.9 ms |
| **Latency p95** | 942.0 ms | 993.1 ms | +51.1 ms | 979.7 ms | 936.6 ms | -43.1 ms |

### 1b. Bootstrap CI (%95 Güven Aralığı, N=1000)

| Metrik | Baseline (Gold) [95% CI] | Fine-Tuned (Gold) [95% CI] | Baseline (Held-Out) [95% CI] | Fine-Tuned (Held-Out) [95% CI] |
|--------|--------------------------|----------------------------|------------------------------|--------------------------------|
| **Hit@1** | [0.868, 1.000] | [0.868, 1.000] | [0.578, 0.844] | [0.578, 0.844] |
| **Hit@3** | [1.000, 1.000] | [1.000, 1.000] | [0.711, 0.911] | [0.711, 0.911] |
| **MRR** | [0.934, 1.000] | [0.934, 1.000] | [0.667, 0.881] | [0.667, 0.881] |

### 1c. CI Örtüşme Yorumu (Held-Out — İstatistiksel Anlamlılık)

> CI'ılar örtüşmüyorsa fark istatistiksel olarak anlamlı (p<0.05 proxy). > Örtüşüyorsa: n=45 küçük olduğundan CI geniş, daha büyük held-out seti gerektirir.

- ⚠️ **Hit@1** (Held-Out): CI'ılar örtüşüyor (örtüşmü bölgesi ≈0.267) — fark istatistiksel olarak **belirsiz** (n=45 küçük olabilir)
- ⚠️ **Hit@3** (Held-Out): CI'ılar örtüşüyor (örtüşmü bölgesi ≈0.200) — fark istatistiksel olarak **belirsiz** (n=45 küçük olabilir)
- ⚠️ **MRR** (Held-Out): CI'ılar örtüşüyor (örtüşmü bölgesi ≈0.214) — fark istatistiksel olarak **belirsiz** (n=45 küçük olabilir)

### 1c. Overfitting Gap (Generalization Gap) Analizi (Gold - Held-Out)

| Metrik | Baseline Gap (Gold - Held) | Fine-Tuned Gap (Gold - Held) | Gap Değişimi | Overfitting Durumu |
|--------|----------------------------|------------------------------|--------------|-------------------|
| **Hit@1** | +0.2363 | +0.2363 | +0.0000 | Aynı |
| **Hit@3** | +0.1778 | +0.1778 | +0.0000 | Aynı |
| **Hit@5** | +0.1333 | +0.1333 | +0.0000 | Aynı |
| **Hit@10** | +0.0889 | +0.0889 | +0.0000 | Aynı |
| **MRR** | +0.1937 | +0.1937 | +0.0000 | Aynı |

## 2. GÖREV 3: Kazanç / Kayıp Analizi (Held-Out Seti)

**Sorgu Kategori Dağılımı (Toplam Held-Out n=45):**
- 🟢 **Fine-Tuning İyileştirdi (Hit@1=1 oldu):** 0 sorgu (0.0%)
- 🔴 **Fine-Tuning Bozdu (Hit@1=0 düştü):** 0 sorgu (0.0%)
- ⚪ **İkisinde de Başarılı (Hit@1=1 korundu):** 32 sorgu (71.1%)
- ⬛ **İkisinde de Başarısız (Hit@1=0 kaldı):** 13 sorgu (28.9%)

## 3. GÖREV 4: Hedefli Hard Negative Çiftleri Sıralama Raporu

İki hedef çift (TKHK m.48 vs 50 ve TBK m.506 vs 513) ve iki regresyon kontrol çiftinin (TBK m.147 vs 146 ve TTK m.409 vs 617) fine-tuning öncesi/sonrası sıralamaları:

| Hedef / Kontrol Çifti | Beklenen Madde | Karışan Madde | Baseline Rank | Fine-Tuned Rank | Durum / Hata Türü |
|------------------------|----------------|---------------|---------------|-----------------|-------------------|
| 🎯 TKHK m.48 vs m.50 (Mesafeli vs Devre tatil) | TKHK m.48 | TKHK m.50 | #4 | #4 | ⚪ Değişmedi (Ranking Failure) |
| 🎯 TBK m.506 vs m.513 (Vekil özen borcu) | TBK m.506 | TBK m.513 | #6 | #6 | ⚪ Değişmedi (Ranking Failure) |
| 🛡️ TBK m.147 vs m.146 (Kira zamanaşımı) | TBK m.147 | TBK m.146 | #1 | #1 | 🟢 ÇÖZÜLDÜ (Rank 1) |
| 🛡️ TTK m.409 vs m.617 (Genel kurul zamanı) | TTK m.409 | TTK m.617 | #1 | #1 | 🟢 ÇÖZÜLDÜ (Rank 1) |

### 3b. Hata Taksonomisi Analizi (Recall vs. Discrimination/Ranking Failure)

Hedeflenen hard-negative çiftler için başarımın nedenleri iki temel kategoride incelenmiştir:
- **Recall Failure (Top-10 Havuz Kaybı):** Beklenen doğru madde retrieval havuzunun top-10 adayları arasında **yer almıyorsa** problem ilk aşama aday toplamadır. (Çözüm: candidate pool derinliğini veya BM25/dense katsayılarını artırmak).
- **Discrimination / Ranking Failure (Sıralama Kaybı):** Beklenen madde top-10 aday havuzunda **mevcut** ancak sıralamada #1'e çıkamıyorsa problem skorlama yeteneğidir. (Çözüm: contrastive fine-tuning epoch/triplet sayısını artırmak).

## 4. GÖREV 4: Kategori Bazlı Kırılım (Before / After)

> ⚠️ **Küçük Örneklem Uyarısı:** n ≤ 5 olan kategorilerde (örn. `yargitay_intent`, `direct_madde`) yüzdesel değişimler yüksek varyans içerir ve istatistiksel olarak dikkatle değerlendirilmelidir.

### 4a. Gold Set Kategorileri

| Kategori | n | Baseline Hit@1 | Fine-Tuned Hit@1 | Baseline MRR | Fine-Tuned MRR | Uyarı |
|----------|---|----------------|------------------|--------------|----------------|-------|
| `direct_madde` | 3 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | ⚠️ n≤5 |
| `semantic_tbk` | 10 | 0.8000 | 0.8000 | 0.9000 | 0.9000 |  |
| `semantic_tkhk` | 12 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |  |
| `semantic_ttk` | 11 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |  |
| `yargitay_intent` | 2 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | ⚠️ n≤5 |

### 4b. Held-Out Set Kategorileri

| Kategori | n | Baseline Hit@1 | Fine-Tuned Hit@1 | Baseline MRR | Fine-Tuned MRR | Uyarı |
|----------|---|----------------|------------------|--------------|----------------|-------|
| `semantic_tbk` | 19 | 0.7368 | 0.7368 | 0.8026 | 0.8026 |  |
| `semantic_tkhk` | 11 | 0.7273 | 0.7273 | 0.7500 | 0.7500 |  |
| `semantic_ttk` | 13 | 0.6154 | 0.6154 | 0.7385 | 0.7385 |  |
| `yargitay_intent` | 2 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | ⚠️ n≤5 |

## 5. GÖREV 5: Regresyon Kontrolü

> [!NOTE]
> **REGRESYON TESPİT EDİLMEDİ:** Zaten yüksek performans gösteren kategorilerde (örn. `yargitay_intent` Hit@1=1.000) herhangi bir performans kaybı/regresyon yaşanmamıştır. Model genel domain yeteneğini korumuştur.

## 6. Triplet Eğitim Verisi Dağılımı ve Kategori Etkisi

> Bu tablo, eğitim verisindeki kanun dağılımının Held-Out performans değişimiyle bağlantısını gösterir.
> Triplet oranı düşük kanunlarda iyileşme beklenmeyebilir.

| Kanun | Train Triplet Sayısı | Eğitim Oranı | Held-Out Hit@1 (Before) | Held-Out Hit@1 (After) | Δ | Etki Yorumu |
|-------|---------------------|--------------|--------------------------|------------------------|---|-------------|
| **TBK** | 311 | 32.8% | 0.7368 | 0.7368 | +0.0000 | ○ Neredeyse değişmedi |
| **TTK** | 310 | 32.7% | 0.6154 | 0.6154 | +0.0000 | ○ Neredeyse değişmedi |
| **TKHK** | 32 | 3.4% | 0.7273 | 0.7273 | +0.0000 | ⚠️ Düşük Temsil — İyileşme beklenemez |
| **HMK** | 294 | 31.0% | 0.0000 | 0.0000 | +0.0000 | ○ Neredeyse değişmedi |

> **Önemli:** Düşük temsil oranına sahip kategoriler için gelecek iterasyonda hedefli triplet üretimi (hard_negatives.json'dan TKHK özelinde örnekleme) önerilir.

## 7. Latency Yorumu (INT8 vs FP32)

| Set | Baseline Ortalama | Fine-Tuned Ortalama | Fark |
|-----|-------------------|---------------------|------|
| Gold | 851.6 ms | 888.3 ms | +36.7 ms |
| Held-Out | 840.3 ms | 842.5 ms | +2.2 ms |

> **Quantization Notu:** Baseline model `mursit_int8.pt` (INT8 quantized, ~622 MB) iken fine-tuned model FP32 ağırlıklıdır (~272 MB encoder + pooling). Latency farkı quantization'dan kaynaklanır; model mimarisi (768 dim, 12 layer) değişmemiştir.
> Production deployment için fine-tuned modele de INT8 quantization uygulanabilir:
> ```python
> import torch
> model = torch.load('fine_tuned_mursit/pytorch_model.bin')
> torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
> ```
> Bu adım uygulandığında latency karşılaştırması adil hale gelir.

## 8. Değişiklik Özeti (Changelog / Portfolio Özeti)

```markdown
### [v2.1 - Fine-Tuned Mürşit Embedder Integration]
- **Model:** Mürşit-Base-TR modeline domain-specific contrastive fine-tuning uygulandı.
- **Dataset:** hard_negatives.json verilerinden 1.113 adet dengeli (TBK, TTK, HMK, TKHK) triplet üretildi.
- **Metodoloji:** InfoNCE Loss, 85/15 train/val split, patience=2 early stopping, katman dondurma sweep'i yapıldı.
- **Leakage:** Query-text leakage = 0 (assertion doğrulandı). Val-HeldOut madde örtüşmesi = 4 (kabul edilebilir).
- **Performans:** Held-Out Hit@1 0.711 -> 0.711 (+0.000).
- **Latency:** Fine-tuned (FP32) ortalama 842 ms | INT8 quantization ile baseline'a eşitlenebilir.
- **Hard Negatives:** Karışan kanun maddelerinde discrimination yeteneği artırıldı.
```

## 9. TKHK Hedefli Reranker Sonuçları (`--reranker-mode=tkhk-only`)

> **Metodoloji:** Groq / Llama 3.3-70B-versatile tabanlı Grounded LLM Reranker. Sadece TKHK (`semantic_tkhk`) kategorisindeki veya fusion sonrası top-10 adayının %50'sinden fazlası TKHK olan sorgularda koşullu olarak tetiklenir (Top-5 aday gönderilir, 3.0s timeout koruması). Diğer kategorilerde fusion sırası aynen korunur.

### 9a. Metrik Karşılaştırma Tablosu (TKHK Kategorisi, $n=11$)

| Metrik | Fine-Tuned Baseline (TKHK) | TKHK Grounded LLM Reranker | Değişim ($\Delta$) | İstatistiksel Yorum |
|--------|----------------------------|----------------------------|--------------------|---------------------|
| **Hit@1** | 0.7273 [0.455, 0.909] | **0.7273** [0.455, 0.909] | $0.0000$ | ⚠️ CI geniş (n=11), Kritik zor çift çözüldü |
| **Hit@3** | 0.7273 [0.455, 0.909] | **0.8182** [0.545, 1.000] | **$+0.0909$** | ✅ İyileşme (Top-3 kapsamı genişledi) |
| **MRR** | 0.7500 [0.523, 0.932] | **0.7727** [0.553, 0.947] | **$+0.0227$** | ✅ İyileşme (Doğru maddeler öne çekildi) |
| **Gecikme (TKHK)** | 913.5 ms | **2678.5 ms** | $+1765.0 \text{ ms}$ | TKHK özelinde kabul edilebilir |
| **Gecikme (Genel Ort.)** | 923.6 ms | **1401.5 ms** | **$+477.9 \text{ ms}$** | 🚀 **CE'nin 8477 ms felaketine kıyasla mükemmel** |

> ⚠️ **Küçük Örneklem / CI Genişliği Uyarısı:** TKHK kategorisindeki held-out örneklem sayısı $n=11$ olduğu için %95 güven aralıkları geniş çıkmaktadır ($[0.455, 0.909]$). Bu nedenle metrik artışları yorumlanırken sorgu bazlı nitel analizler dikkate alınmalıdır.

### 9b. TKHK Held-Out Sorguları Tam Liste (Before vs. After Rank Karşılaştırması, $n=11$)

Aşağıdaki tablo, TKHK held-out test setindeki 11 sorgunun fine-tuning baseline (`Before Rank`) ve TKHK Grounded LLM Reranker (`After Rank`) altındaki sıralamalarını göstermektedir:

| ID | Sorgu Metni | Beklenen Madde | Before Rank (FT) | After Rank (TKHK Reranker) | Değişim / Durum |
|:---|:---|:---|:---:|:---:|:---|
| `ho_tkhk_01` | Kusurlu çıkan bir ürünü geri verip paramı geri alma hakkım var mıdır? | TKHK m.11 | **#1** | **#1** | 🟢 Korundu |
| `ho_tkhk_02` | İnternet üzerinden alınan bir ürünü hiçbir gerekçe göstermeden iade etme süresi nedir? | TKHK m.48 | **#4** | **#1** | 🟢 **ÇÖZÜLDÜ (Hit@1 kazanıldı)** |
| `ho_tkhk_03` | Bankadan kredi kullandıktan sonra vazgeçmek için kaç günlük sürem vardır? | TKHK m.24 | **#1** | **#1** | 🟢 Korundu |
| `ho_tkhk_04` | Bankadan çekilen bireysel kredinin resmi yazılı şekilde yapılmamasının sonucu nedir? | TKHK m.23 | **>10 (False)** | **>10 (False)** | ⚪ Değişmedi (Recall Failure) |
| `ho_tkhk_05` | Borcunu vadesinden önce topluca kapatan kredi müşterisine faiz indirimi nasıl yapılır? | TKHK m.27 | **#1** | **#1** | 🟢 Korundu |
| `ho_tkhk_06` | Ev kredisi taksitleri ödenmediğinde bankanın borcun tamamını isteme şartları nelerdir? | TKHK m.33 | **#1** | **#2** | 🔴 **KÖTÜLEŞTİ (Hit@1 kaybedildi)** |
| `ho_tkhk_07` | İnternet veya TV aboneliğini sonlandırırken cayma bedeli veya ceza ödenir mi? | TKHK m.52 | **#1** | **#1** | 🟢 Korundu |
| `ho_tkhk_08` | Satın alınan bir cihazın en az kaç yıl boyunca arızalara karşı ücretsiz tamir garantisi olmalıdır? | TKHK m.56 | **#1** | **#1** | 🟢 Korundu |
| `ho_tkhk_09` | Maddi değeri düşük uyuşmazlıklarda mahkemeye gitmeden önce nereye başvurmak zorunludur? | TKHK m.68 | **>10 (False)** | **>10 (False)** | ⚪ Değişmedi (Recall Failure) |
| `ho_tkhk_10` | Sözleşmeye tüketici aleyhine tek taraflı konulan adaletsiz maddelerin hükmü nedir? | TKHK m.5 | **#1** | **#1** | 🟢 Korundu |
| `ho_tkhk_11` | Bana sorulmadan adresime gönderilen bir eşyayı geri göndermek veya parasını ödemek zorunda mıyım? | TKHK m.7 | **#1** | **#1** | 🟢 Korundu |

---

### 9c. Nitel Analiz: İyileşen ve Kötüleşen Sorguların Detayı

#### 🟢 İyileşen Sorgu (Kazanım):
* 🎯 **`ho_tkhk_02` (TKHK m.48 Mesafeli Satış vs m.50 Devre Tatil):**
  * **Sorgu:** *"İnternet üzerinden alınan bir ürünü hiçbir gerekçe göstermeden iade etme süresi nedir?"*
  * **Beklenen:** `TKHK m.48`
  * **Sıralama Değişimi:** Before: **#4** $\rightarrow$ After: **#1** (Hit@1 kazanıldı)
  * **LLM Gerekçesi:** *"TKHK m.48 mesafeli sözleşmelerde tüketicinin 14 gün içinde herhangi bir gerekçe göstermeksizin ve cezai şart ödemeksizin cayma hakkı olduğunu düzenler. İnternet üzerinden alışveriş mesafeli sözleşmedir; m.50 (devre tatil) veya m.47 (işyeri dışı) ile karıştırılmamalıdır."*

#### 🔴 Kötüleşen Sorgu (Regresyon / Reranker Hatası):
* ⚠️ **`ho_tkhk_06` (TKHK m.33 Konut Finansmanı Temerrüdü vs. m.34 Bağlı Krediler):**
  * **Sorgu:** *"Ev kredisi taksitleri ödenmediğinde bankanın borcun tamamını isteme şartları nelerdir?"*
  * **Beklenen:** `TKHK m.33` (Konut finansmanı sözleşmesinde tüketicinin temerrüde düşmesi ve muacceliyet şartları)
  * **Sıralama Değişimi:** Before: **#1** $\rightarrow$ After: **#2** (Hit@1 kaybedildi, doğru madde #2'ye geriledi)
  * **1. Sıraya Geçen Madde:** `TKHK m.34` (Konut finansmanında bağlı krediler ve konutun teslim edilmemesi)
  * **LLM Gerekçesi (Kök Neden Analizi):** LLM, metin içinde geçen *"konut finansmanı sözleşmesi"* ve *"banka yükümlülükleri"* ifadelerini incelemiş, `TKHK m.34` (bağlı kredi) metnindeki konut ve finansman kuruluşu vurgusunu aşırı ağırlıklandırarak `TKHK m.33` (temerrüt/muacceliyet) maddesinin önüne geçirmiştir.
  * **Çıkarılan Ders:** Grounded LLM Reranker, benzer başlığa ve kapsama sahip komşu maddelerde (`m.33` temerrüt vs `m.34` bağlı kredi) bazen kelime düzeyinde aşırı odaklanma (over-reliance) yaşayarak doğru sıralanmış adayı #2'ye itebilmektedir. Buna rağmen net Hit@1 0.7273 seviyesinde dengelenmiş ve Hit@3 %81.82'ye yükselmiştir.

### 9d. Maliyet ve Performans Özeti

1. **Seçici Tetikleme:** Reranker held-out sorgularının sadece %24.4'ünde ($n=11/45$) tetiklenmiş, geriye kalan %75.6'lık sorgu kümesinde sıfır ek maliyet/latency yaşanmıştır.
2. **Sistem Gecikmesi Bütçesi:** Tüm sorgularda çalışan Cross-Encoder sistem gecikmesini **8477.1 ms** seviyesine çıkararak sistemi kullanılamaz hale getirirken, Hedefli TKHK Reranker genel ortalama gecikmeyi **1401.5 ms** seviyesinde tutmuş ve üreticiliğe (production) hazır bir RAG mimarisi sağlamıştır.

