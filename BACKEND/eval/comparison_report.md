# LawAgent AI — Baseline vs Cross-Encoder Karşılaştırma Raporu

> **Oluşturma Tarihi:** 2026-07-26 14:07:43
> **Metodoloji:** eval_comparison.py  
> **Cross-Encoder Modeli:** BAAI/bge-reranker-base (Fallback: ms-marco-MiniLM-L-6-v2)  
> **Kandidat Penceresi:** Top-30 (Asla tüm corpus değil)

## 1. Sistem Mimarisi Karşılaştırması

| Katman | BASELINE | YENİ SYSTEM |
|--------|----------|-------------|
| Dense Retrieval | ✅ Mürşit-Base-TR | ✅ Mürşit-Base-TR |
| BM25+ | ✅ Custom BM25+ | ✅ Custom BM25+ |
| Hybrid Fusion | ✅ Dinamik alpha | ✅ Dinamik alpha |
| Boosting | ✅ Prob. kanun ağırlıklaması | ✅ Prob. kanun ağırlıklaması |
| Diversity Penalty | ✅ Aktif (0.05/aday) | ❌ Kapalı (Cross-Encoder varken gereksiz) |
| Cross-Encoder | ❌ Kapalı | ✅ BAAI/bge-reranker-base, Top-30 |

## 2. Metrik Tablosu

> Not: Held-Out set overfitting'e karşı dayanıklı gerçek genelleme metriğidir.

| Metrik | Gold-Baseline | Gold-Cross | Gold Δ | Held-Baseline | Held-Cross | Held Δ |
|--------|---------------|------------|--------|---------------|------------|--------|
| **Hit@1** | 0.9474 | 0.5000 | -0.4474 ▼ | 0.7111 | 0.1778 | -0.5333 ▼ |
| **Hit@3** | 1.0000 | 0.6316 | -0.3684 ▼ | 0.8222 | 0.3333 | -0.4889 ▼ |
| **Hit@5** | 1.0000 | 0.7632 | -0.2368 ▼ | 0.8667 | 0.4444 | -0.4223 ▼ |
| **Hit@10** | 1.0000 | 0.9211 | -0.0789 ▼ | 0.9111 | 0.6000 | -0.3111 ▼ |
| **MRR** | 0.9737 | 0.6121 | -0.3616 ▼ | 0.7800 | 0.2905 | -0.4895 ▼ |
| **nDCG@10** | 0.9806 | 0.6844 | -0.2962 ▼ | 0.8118 | 0.3632 | -0.4486 ▼ |
| avg_latency_ms | 1002.3 ms | 9414.6 ms | — | 923.6 ms | 8477.1 ms | — |
| p50_latency_ms | 927.7 ms | 9016.9 ms | — | 931.8 ms | 8317.1 ms | — |
| p95_latency_ms | 1117.3 ms | 16729.0 ms | — | 1080.8 ms | 9610.5 ms | — |

### Overfitting Gap (Gold − Held-Out)

| Metrik | Baseline Gap | Cross-Encoder Gap | Gap Değişimi |
|--------|-------------|-------------------|--------------|
| Hit@1 | +0.2363 | +0.3222 ⚠️ | +0.0859 ▲ |
| Hit@3 | +0.1778 | +0.2983 ⚠️ | +0.1205 ▲ |
| Hit@5 | +0.1333 | +0.3188 ⚠️ | +0.1855 ▲ |
| Hit@10 | +0.0889 | +0.3211 ⚠️ | +0.2322 ▲ |
| MRR | +0.1937 | +0.3216 ⚠️ | +0.1279 ▲ |
| nDCG@10 | +0.1688 | +0.3212 ⚠️ | +0.1524 ▲ |

## 3. Kazanç / Kayıp Analizi (Held-Out)

| Durum | Sorgu Sayısı | Oran |
|-------|-------------|------|
| ✅ Cross-Encoder iyileştirdi (Hit@1 kazanıldı) | 0 | 0.0% |
| ❌ Cross-Encoder bozdu (Hit@1 kaybedildi) | 24 | 53.3% |
| 🔄 Her iki sistemde başarılı | 8 | 17.8% |
| 🔄 Her iki sistemde başarısız | 13 | 28.9% |

### ❌ Cross-Encoder'ın Bozduğu Sorgular (Held-Out)

> Bu sorgular için neden gerileme yaşandığı Bölüm 5'te analiz edilmektedir.

| Sorgu | Beklenen | Baseline Rank | CE Rank | Baseline Top-1 | CE Top-1 |
|-------|---------|---------------|---------|----------------|----------|
| Kusurlu çıkan bir ürünü geri verip paramı geri alma hak | TKHK m.11 | #1 | — | TKHK m.11 | TBK m.229 |
| Ev kredisi taksitleri ödenmediğinde bankanın borcun tam | TKHK m.33 | #1 | — | TKHK m.33 | TBK m.593 |
| Satın alınan bir cihazın en az kaç yıl boyunca arızalar | TKHK m.56 | #1 | #4 | TKHK m.56 | TBK m.270 |
| Sözleşmeye tüketici aleyhine tek taraflı konulan adalet | TKHK m.5 | #1 | #3 | TKHK m.5 | TBK m.176 |
| Bana sorulmadan adresime gönderilen bir eşyayı geri gön | TKHK m.7 | #1 | — | TKHK m.7 | TTK m.1203 |
| Rakiplerimin müşterilerimi yanıltıcı beyanlarla çekmesi | TTK m.['56', '60'] | #1 | #8 | TTK m.56 | TTK m.38 |
| Yönetim kurulu üyelerinden biri toplantı yapılmasını na | TTK m.392 | #1 | #6 | TTK m.392 | TTK m.414 |
| Şirket ortaklarının katıldığı yıllık genel toplantı ne  | TTK m.409 | #1 | #4 | TTK m.409 | TTK m.617 |
| Yönetim kurulu üyeleri şirkete verdikleri zararlardan ö | TTK m.553 | #1 | #9 | TTK m.553 | TTK m.632 |
| Limited ortaklıkta hissenin başka birine aktarılması iç | TTK m.595 | #1 | #3 | TTK m.595 | TTK m.493 |
| Limited şirketi yöneten kişilerin ortaklara karşı tazmi | TTK m.632 | #1 | #2 | TTK m.632 | TTK m.234 |
| Türkiye sınırları içinde düzenlenen bir ödeme emrinin b | TTK m.796 | #1 | — | TTK m.796 | TBK m.270 |
| İki taraf anlaşmaya vardığında sözleşme ne zaman kurulm | TBK m.1 | #1 | — | TBK m.1 | TBK m.640 |
| Ahlaka veya kamu düzenine aykırı yapılan bir anlaşmanın | TBK m.27 | #1 | — | TBK m.27 | TBK m.173 |
| Karşı tarafın yalan söyleyerek kandırması sonucu imzala | TBK m.['36', '39'] | #1 | #3 | TBK m.36 | TBK m.228 |
| Borcunu hiç yerine getirmeyen kişi karşı tarafın zararı | TBK m.112 | #1 | #7 | TBK m.112 | TBK m.483 |
| Borcunu zamanında yerine getirmeyen tarafa karşı sözleş | TBK m.125 | #1 | — | TBK m.125 | TBK m.271 |
| Kanunda özel bir süre belirtilmemişse borçlar için hak  | TBK m.146 | #1 | #5 | TBK m.146 | TBK m.73 |
| Ev kirası alacakları veya otel konaklama bedelleri için | TBK m.147 | #1 | #2 | TBK m.147 | TBK m.351 |
| Belirli süreli konut kiralama kontratı bittiğinde ev sa | TBK m.347 | #1 | — | TBK m.347 | TBK m.352 |
| İnşaat işini teslim alan kişi işteki eksiklik ve kusurl | TBK m.474 | #1 | #9 | TBK m.474 | TBK m.465 |
| Bir kimse borca ortak olurken eşinin de buna onay verme | TBK m.584 | #1 | — | TBK m.584 | TBK m.349 |
| Kira tespit davalarında Yargıtay'ın güncel içtihatları  | None m.None | #1 | #7 | TBK m.None | TBK m.372 |
| Kat karşılığı inşaat sözleşmelerinin feshinde Yargıtay  | None m.None | #1 | #5 | TBK m.None | TBK m.316 |

## 4. Hard Negative Örnekleri (Held-Out Reranking Failures)

> Hard negative: Doğru madde top-10'a giriyor ama üste çıkamıyor.
> Bu bölüm baseline'da reranking failure olan sorguların cross-encoder ile nasıl değiştiğini gösterir.

| # | Sorgu | Beklenen | Baseline Rank | CE Rank | CE Çözüldü? |
|---|-------|---------|---------------|---------|------------|
| 1 | İnternet üzerinden alınan bir ürünü hiçbir gerekçe göst | TKHK m.48 | #4 | #2 | ❌ Hayır |
| 2 | Anonim şirketlerde müdür tayin etme yetkisi başka bir b | TTK m.375 | #2 | — | ❌ Hayır |
| 3 | Ortaklar kurulunda önceden belirlenmemiş bir konunun gö | TTK m.413 | #10 | — | ❌ Hayır |
| 4 | Şirket ortaklar toplantısında kanuna aykırı alınan bir  | TTK m.445 | #2 | #4 | ❌ Hayır |
| 5 | Limited ortaklık müdürünün devredemeyeceği asli görevle | TTK m.625 | #2 | #2 | ❌ Hayır |
| 6 | Kanunun emredici kurallarına aykırı olmayan her türlü s | TBK m.26 | #3 | #8 | ❌ Hayır |
| 7 | Sözleşme yaparken önemli bir konuda hata yapan taraf an | TBK m.30 | #2 | — | ❌ Hayır |
| 8 | Kendi borcunu ödemeyen taraf, diğer taraftan borcunu ye | TBK m.97 | #4 | — | ❌ Hayır |
| 9 | Bir başkası adına iş yürüten avukat veya temsilci işi y | TBK m.506 | #6 | — | ❌ Hayır |

> **Özet:** 9 hard negative sorgudan 0 tanesi (0.0%) Cross-Encoder tarafından çözüldü.

### Detaylı Hard Negative İncelemesi (İlk 3)

**Sorgu:** İnternet üzerinden alınan bir ürünü hiçbir gerekçe göstermeden iade etme süresi nedir?  
**Beklenen:** TKHK m.48 | **Baseline Rank:** #4 | **CE Rank:** #2  

| Sıra | Baseline Top-5 | Skor |  CE Top-5 | Skor | CE Cross-Score |
|------|---------------|------|-----------|------|----------------|
| 1 | TKHK m.50 | 1.0 | TTK m.23 | 0.4172 | 0.7751 |
| 2 | TKHK m.47 | 0.7284 | TKHK m.48 | 0.7579 | 0.471 |
| 3 | TKHK m.45 | 0.6825 | TKHK m.70 | 0.3409 | 0.1903 |
| 4 | TKHK m.48 | 0.6442 | TTK m.1188 | 0.3391 | 0.1456 |
| 5 | TKHK m.43 | 0.577 | TBK m.255 | 0.4733 | 0.1338 |

**Sorgu:** Anonim şirketlerde müdür tayin etme yetkisi başka bir birime devredilebilir mi?  
**Beklenen:** TTK m.375 | **Baseline Rank:** #2 | **CE Rank:** —  

| Sıra | Baseline Top-5 | Skor |  CE Top-5 | Skor | CE Cross-Score |
|------|---------------|------|-----------|------|----------------|
| 1 | TTK m.625 | 5.746 | TTK m.571 | 2.3465 | 0.8681 |
| 2 | TTK m.375 | 3.9536 | TTK m.367 | 2.681 | 0.8393 |
| 3 | TTK m.624 | 3.1407 | TTK m.315 | 1.737 | 0.5398 |
| 4 | TTK m.623 | 2.8653 | TTK m.395 | 2.2266 | 0.3479 |
| 5 | TTK m.630 | 1.9757 | TTK m.574 | 1.5742 | 0.3409 |

**Sorgu:** Ortaklar kurulunda önceden belirlenmemiş bir konunun görüşülüp karara bağlanması mümkün müdür?  
**Beklenen:** TTK m.413 | **Baseline Rank:** #10 | **CE Rank:** —  

| Sıra | Baseline Top-5 | Skor |  CE Top-5 | Skor | CE Cross-Score |
|------|---------------|------|-----------|------|----------------|
| 1 | TMK m.None | 0.9761 | TBK m.625 | 0.4046 | 0.9896 |
| 2 | TBK m. | 0.8039 | TTK m.418 | 0.5196 | 0.806 |
| 3 | TTK m.617 | 0.7425 | TTK m.416 | 0.5538 | 0.6667 |
| 4 | TTK m.392 | 0.6816 | TTK m.225 | 0.3545 | 0.5994 |
| 5 | TTK m.415 | 0.6209 | TTK m.221 | 0.3438 | 0.4998 |

## 5. Performans Analizi

### ⚠️ Cross-Encoder Performansı Düşürdü — Kök Neden Analizi

- Held-Out Hit@1: **-0.5333 ▼**

**Olası nedenler:**

1. **Dil Uyumsuzluğu:** `BAAI/bge-reranker-base` ağırlıklı olarak İngilizce/Çince verilerle eğitilmiştir.
   Türkçe hukuki terminoloji (cayma hakkı, temerrüt, borç ilişkisi) için suboptimal scoring yapabilir.
   **Çözüm:** Türkçe-bilinçli cross-encoder modeli fine-tune etmek veya query'i İngilizceye çevirip sormak.

2. **Madde Numarası Yanıltıcılığı:** Cross-encoder document metnini değil başlığı puanlıyor olabilir.
   Örnek: 'TBK m.472 eser teslimi' vs 'TBK m.474 ayıp bildirimi' — ikisi de semantik olarak yakın.
   **Çözüm:** Document format'a madde numarasını daha belirgin şekilde yerleştirmek.

3. **Aday Havuzu Sorunu:** Fusion+Boosting zaten doğru maddeyi #1-3 arası getiriyorsa,
   Cross-encoder'ın bu sırayı bozması mümkün. Diversity Penalty'nin kaldırılması da etken olabilir.
   **Çözüm:** Cross-encoder'ı sadece #3-10 arası için uygulamak (ilk 2'yi koru).

4. **Gerileme Örnekleri:**

   - `Kusurlu çıkan bir ürünü geri verip paramı geri alma hakkım var mıdır?`
     Beklenen: TKHK m.11 | Baseline: #1 → CE: —
     Baseline Top-1: `TKHK m.11` | CE Top-1: `TBK m.229`

   - `Ev kredisi taksitleri ödenmediğinde bankanın borcun tamamını isteme şa`
     Beklenen: TKHK m.33 | Baseline: #1 → CE: —
     Baseline Top-1: `TKHK m.33` | CE Top-1: `TBK m.593`

   - `Satın alınan bir cihazın en az kaç yıl boyunca arızalara karşı ücretsi`
     Beklenen: TKHK m.56 | Baseline: #1 → CE: #4
     Baseline Top-1: `TKHK m.56` | CE Top-1: `TBK m.270`

   - `Sözleşmeye tüketici aleyhine tek taraflı konulan adaletsiz maddelerin `
     Beklenen: TKHK m.5 | Baseline: #1 → CE: #3
     Baseline Top-1: `TKHK m.5` | CE Top-1: `TBK m.176`

   - `Bana sorulmadan adresime gönderilen bir eşyayı geri göndermek veya par`
     Beklenen: TKHK m.7 | Baseline: #1 → CE: —
     Baseline Top-1: `TKHK m.7` | CE Top-1: `TTK m.1203`

   - `Rakiplerimin müşterilerimi yanıltıcı beyanlarla çekmesine karşı hangi `
     Beklenen: TTK m.['56', '60'] | Baseline: #1 → CE: #8
     Baseline Top-1: `TTK m.56` | CE Top-1: `TTK m.38`

   - `Yönetim kurulu üyelerinden biri toplantı yapılmasını nasıl talep eder?`
     Beklenen: TTK m.392 | Baseline: #1 → CE: #6
     Baseline Top-1: `TTK m.392` | CE Top-1: `TTK m.414`

   - `Şirket ortaklarının katıldığı yıllık genel toplantı ne zaman yapılmalı`
     Beklenen: TTK m.409 | Baseline: #1 → CE: #4
     Baseline Top-1: `TTK m.409` | CE Top-1: `TTK m.617`

   - `Yönetim kurulu üyeleri şirkete verdikleri zararlardan ötürü ne zaman s`
     Beklenen: TTK m.553 | Baseline: #1 → CE: #9
     Baseline Top-1: `TTK m.553` | CE Top-1: `TTK m.632`

   - `Limited ortaklıkta hissenin başka birine aktarılması için noter onayı `
     Beklenen: TTK m.595 | Baseline: #1 → CE: #3
     Baseline Top-1: `TTK m.595` | CE Top-1: `TTK m.493`

   - `Limited şirketi yöneten kişilerin ortaklara karşı tazminat yükümlülüğü`
     Beklenen: TTK m.632 | Baseline: #1 → CE: #2
     Baseline Top-1: `TTK m.632` | CE Top-1: `TTK m.234`

   - `Türkiye sınırları içinde düzenlenen bir ödeme emrinin bankadan tahsil `
     Beklenen: TTK m.796 | Baseline: #1 → CE: —
     Baseline Top-1: `TTK m.796` | CE Top-1: `TBK m.270`

   - `İki taraf anlaşmaya vardığında sözleşme ne zaman kurulmuş sayılır?`
     Beklenen: TBK m.1 | Baseline: #1 → CE: —
     Baseline Top-1: `TBK m.1` | CE Top-1: `TBK m.640`

   - `Ahlaka veya kamu düzenine aykırı yapılan bir anlaşmanın akıbeti nedir?`
     Beklenen: TBK m.27 | Baseline: #1 → CE: —
     Baseline Top-1: `TBK m.27` | CE Top-1: `TBK m.173`

   - `Karşı tarafın yalan söyleyerek kandırması sonucu imzaladığım sözleşmed`
     Beklenen: TBK m.['36', '39'] | Baseline: #1 → CE: #3
     Baseline Top-1: `TBK m.36` | CE Top-1: `TBK m.228`

   - `Borcunu hiç yerine getirmeyen kişi karşı tarafın zararını ödemek zorun`
     Beklenen: TBK m.112 | Baseline: #1 → CE: #7
     Baseline Top-1: `TBK m.112` | CE Top-1: `TBK m.483`

   - `Borcunu zamanında yerine getirmeyen tarafa karşı sözleşmeden dönme hak`
     Beklenen: TBK m.125 | Baseline: #1 → CE: —
     Baseline Top-1: `TBK m.125` | CE Top-1: `TBK m.271`

   - `Kanunda özel bir süre belirtilmemişse borçlar için hak arama süresi ka`
     Beklenen: TBK m.146 | Baseline: #1 → CE: #5
     Baseline Top-1: `TBK m.146` | CE Top-1: `TBK m.73`

   - `Ev kirası alacakları veya otel konaklama bedelleri için dava açma süre`
     Beklenen: TBK m.147 | Baseline: #1 → CE: #2
     Baseline Top-1: `TBK m.147` | CE Top-1: `TBK m.351`

   - `Belirli süreli konut kiralama kontratı bittiğinde ev sahibi kiracıyı h`
     Beklenen: TBK m.347 | Baseline: #1 → CE: —
     Baseline Top-1: `TBK m.347` | CE Top-1: `TBK m.352`

   - `İnşaat işini teslim alan kişi işteki eksiklik ve kusurları ne kadar sü`
     Beklenen: TBK m.474 | Baseline: #1 → CE: #9
     Baseline Top-1: `TBK m.474` | CE Top-1: `TBK m.465`

   - `Bir kimse borca ortak olurken eşinin de buna onay vermesi gerekir mi?`
     Beklenen: TBK m.584 | Baseline: #1 → CE: —
     Baseline Top-1: `TBK m.584` | CE Top-1: `TBK m.349`

   - `Kira tespit davalarında Yargıtay'ın güncel içtihatları ne yöndedir?`
     Beklenen: None m.None | Baseline: #1 → CE: #7
     Baseline Top-1: `TBK m.None` | CE Top-1: `TBK m.372`

   - `Kat karşılığı inşaat sözleşmelerinin feshinde Yargıtay kararları neler`
     Beklenen: None m.None | Baseline: #1 → CE: #5
     Baseline Top-1: `TBK m.None` | CE Top-1: `TBK m.316`

### ⏱️ Latency Analizi

| Metrik | Baseline | Cross-Encoder | Artış |
|--------|----------|---------------|-------|
| avg_latency_ms | 923.6 ms | 8477.1 ms | +7553.5000 ms |
| p50_latency_ms | 931.8 ms | 8317.1 ms | +7385.3000 ms |
| p95_latency_ms | 1080.8 ms | 9610.5 ms | +8529.7000 ms |

> **Not:** İlk sorgu model yüklemesini içerdiğinden yüksek görünebilir.
> Warm-start sonrası p50 ve p95 daha güvenilir latency metriğidir.
> BAAI/bge-reranker-base: ~270MB, CPU'da top-30 için yaklaşık 800-2000ms.

## 6. Kategori Bazlı Kırılım (Held-Out)

| Kategori | n | Base-Hit@1 | CE-Hit@1 | Δ | Base-MRR | CE-MRR | Δ |
|----------|---|-----------|---------|---|---------|--------|---|
| semantic_tbk | 19 | 0.737 | 0.210 | -0.5263 ▼ | 0.803 | 0.285 | -0.5177 ▼ |
| semantic_tkhk | 11 | 0.727 | 0.273 | -0.4546 ▼ | 0.750 | 0.371 | -0.3788 ▼ |
| semantic_ttk | 13 | 0.615 | 0.077 | -0.5385 ▼ | 0.739 | 0.249 | -0.4896 ▼ |
| yargitay_intent ⚠️ | 2 | 1.000 | 0.000 | -1.0000 ▼ | 1.000 | 0.171 | -0.8286 ▼ |

> ⚠️ = n≤5 kategorilerinde yüzde değerleri yanıltıcı olabilir.

## 7. Sonuç ve Öneriler

**❌ Cross-Encoder Şu An Önerilmez:** Held-Out metriklerinde gerileme gözlemlendi.

Öncelikli aksiyonlar:
- [ ] Türkçe hukuk verisine uygun cross-encoder modeli araştır (STS-TR, multilingual modeller)
- [ ] Document format'ı zenginleştir (madde başlığı, kanun tam adı)
- [ ] Cross-encoder'ı sadece top 5-10 arası için uygula (ilk sonuçları koru)
- [ ] Diversity Penalty'yi cross-encoder ile birlikte değil ardından kullan
