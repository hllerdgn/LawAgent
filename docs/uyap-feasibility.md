# UYAP Entegrasyonu Kapsamlı Fizibilite Raporu

Bu rapor, LawAgent AI RAG (Retrieval-Augmented Generation) sistemine UYAP (Ulusal Yargı Ağı Bilişim Sistemi) entegrasyonu eklenmesi fikrinin teknik, hukuki, güvenlik, maliyet, operasyonel ve kullanıcı deneyimi (UX) açılarından uygulanabilirliğini değerlendirmektedir.

---

## 1. Yönetici Özeti

- **Projenin Amacı:** LawAgent AI kullanıcılarının kimliklerini güvenli bir şekilde doğrulaması, kendi UYAP dava dosyalarını sisteme aktarması ve yapay zekâ asistanı aracılığıyla bu kişisel veriler üzerinden özelleştirilmiş hukuki analiz/asistanlık hizmeti alması.
- **Temel Bulgular:**
  - **Resmi API Yokluğu:** UYAP ve e-Devlet sistemlerinin genel kullanıma açık, dış geliştiricilerin doğrudan entegre olabileceği bir public API/SSO (Single Sign-On) altyapısı bulunmamaktadır.
  - **Önerilen Entegrasyon Tasarımı (Oturum Üstü Eklenti):** Avukatın tarayıcısına kurulan bir **Chrome Uzantısı (Extension)** aracılığıyla, e-imza/token'ı yerelde tutarak aktif UYAP oturumu üzerinden verilerin salt okunur (read-only) şekilde çekilmesi. Bu yöntem, kullanıcı kimlik bilgilerini okumadan ve backend'de otonom bir "oturum açma" tetiklemesi yapmadan çalışır.
  - **Yüksek Güvenlik ve Hukuki Uyum:** SHA-256 token hashing, cihaz bazlı yetkilendirme ve iptal (revoke) mekanizması, çift filtre doğrulaması ve TCKN/VKN maskelemesi ile KVKK standartlarına tam uyum sağlanır.
- **Fizibilite Kararı:** Doğrudan ve otonom bir **resmi UYAP API entegrasyonu mevcut şartlarda MÜMKÜN DEĞİLDİR.** Ancak, **Senaryo 4 (Oturum Üstü Tarayıcı Eklentisi Köprüsü) teknik ve hukuki açıdan %100 UYGULANABİLİRDİR** ve en iyi kullanıcı deneyimini sunar.
- **Önerilen Strateji (Yol Haritası):**
  1.  **Aşama 1 (MVP):** Kullanıcının UYAP'tan indirdiği belgeleri (UDF, PDF) manuel yüklediği ve Qdrant üzerinde sıkı kullanıcı izolasyonuyla sorguladığı yapı.
  2.  **Aşama 2 (Canlı Sürüm):** Chrome Uzantısı (Manifest V3) tabanlı oturum üstü okuma entegrasyonunun devreye alınması.

---

## 2. Problem Tanımı

Mevcut hukuk asistanı uygulaması (LawAgent AI), yalnızca halka açık kanun metinleri, yönetmelikler ve Yargıtay emsal kararları üzerinden RAG (Retrieval-Augmented Generation) araması yapmaktadır.

### Mevcut Durumdaki Kısıtlar (Acı Noktaları):

1.  **Kişiselleştirme Eksikliği:** Kullanıcılar, asistan ile sohbet ederken kendi dava dosyalarındaki özel detayları (iddianameler, bilirkişi raporları, tensip zaptları vb.) bağlam olarak sunamamaktadır.
2.  **Manuel İşlem Yükü:** Kullanıcının dava belgelerindeki bilgileri kopyalayıp chat ekranına yapıştırması gerekmektedir. Bu durum hem kullanıcı deneyimini bozmakta hem de LLM bağlam sınırlarının aşılmasına yol açmaktadır.
3.  **Güvenlik Endişeleri:** Kullanıcıların hassas belgeleri kontrolsüz şekilde chat arayüzüne yapıştırması, verilerin açık LLM API'lerine kontrolsüz sızması riskini doğurmaktadır.

---

## 3. Mevcut Sistem Analizi

LawAgent AI projesinin güncel mimarisi şu şekildedir:

- **Backend:** Python + FastAPI (İçtihat kazıma, embedding oluşturma, hybrid arama ve Groq LLM API koordinasyonu).
- **Frontend:** React + TypeScript + TailwindCSS (Chat arayüzü ve döküman yönetimi).
- **Vektör Veritabanı:** Qdrant (Lokal / Docker üzerinde çalıştırılan dense ve sparse vektör indeksleme).
- **Metin Vektörleştirme:** `Mursit-Base-TR-Retrieval` (Türkçe hukuk terimlerine duyarlı açık kaynaklı embedding modeli).
- **Veri Akışı:** Statik veri setleri (Borçlar Kanunu, Ticaret Kanunu vb.) önceden kazınmış ve Qdrant üzerinde indekslenmiştir. Çoklu kullanıcı mimarisi veya kullanıcı bazlı veri izolasyonu henüz aktif değildir.

---

## 4. UYAP Entegrasyon İncelemesi

UYAP altyapısının harici sistemlerle entegrasyon yetenekleri analiz edilmiştir:

| Entegrasyon Kanalı             | Erişim Durumu                                 | Kimlik Doğrulama Yöntemi                                    | Veri Kapsamı                                                                                          |
| :----------------------------- | :-------------------------------------------- | :---------------------------------------------------------- | :---------------------------------------------------------------------------------------------------- |
| **UYAP Avukat Portal**         | Açık API yok. Sadece web arayüzü.             | e-İmza (Akıllı Kart), Mobil İmza, e-Devlet.                 | Avukatın vekaleti olan veya yetkilendirildiği tüm dava dosyaları, evraklar, safahat, duruşma günleri. |
| **UYAP Vatandaş Portal**       | Açık API yok. Sadece web arayüzü.             | e-Devlet şifresi, Mobil İmza, T.C. Kimlik Kartı.            | Vatandaşın taraf olduğu dava dosyaları ve evrakları.                                                  |
| **UYAP Kurum Portal**          | Protokole bağlı entegrasyon (API/Web Servis). | Kurumsal Sertifika ve IP Kısıtlaması.                       | Kurumu ilgilendiren hukuki süreçler ve sorgulamalar.                                                  |
| **Tarayıcı Eklentisi Köprüsü** | Geliştirilebilir (Chrome Extension).          | Kullanıcının aktif UYAP tarayıcı oturumuna binme (Overlay). | Kullanıcının tarayıcıda görüntülediği / eriştiği dava ve evrak verileri (Read-Only).                  |

### Kritik Soruların Cevapları:

- **Harici bir uygulama UYAP kullanıcı doğrulaması yapabilir mi?**
  - _Cevap:_ Doğrudan yapamaz. Ancak tarayıcı eklentisi kullanıcının yerelde zaten yaptığı e-imza / UYAP oturum açma işleminin üzerine binerek (overlay) oturumu devralabilir.
- **UYAP üzerinden OAuth, SSO veya benzeri kimlik doğrulama yöntemi mevcut mu?**
  - _Cevap:_ Mevcut değildir.
- **Veri erişimi için resmi izin gerekiyor mu?**
  - _Cevap:_ Resmi API kullanımı için Adalet Bakanlığı protokolü gerekir. Ancak eklenti mimarisinde, avukatın kendi yetkisiyle eriştiği verileri kendi rızasıyla uygulamaya aktarması (veri taşınabilirliği hakkı) söz konusudur.
- **Hangi kullanıcı tipleri sisteme entegre olabilir?**
  - _Cevap:_ Avukatlar (Avukat Portal), Vatandaşlar (Vatandaş Portal).

---

## 5. Hukuki ve KVKK Analizi

Eklenti tabanlı entegrasyon çözümünde hukuki riskler ve alınan bilinçli tasarım kararları şunlardır:

### 1. Hukuki Tasarım Kararı ve UYAP Sözleşme Uyumu:

- **Otonom Giriş Yoktur:** Backend üzerinde "avukat adına UYAP'a otomatik giriş yap" gibi bir akış kesinlikle bulunmaz.
- **Aktif Oturum Bağımlılığı:** Eklenti yalnızca avukat kendi bilgisayarında UYAP'a e-imza ile manuel giriş yapmışken çalışır. Sunucu tarafından arka planda otomatik tetiklenen hiçbir UYAP işlemi yoktur. Bu tasarım, Avukat Portal sözleşmesi ve KVKK kapsamında en güvenli ve yasal olarak en savunulabilir yaklaşımdır.
- **Salt Okunur (Read-Only) Sınırı:** Eklenti UYAP üzerinde hiçbir yazma işlemi (takip açma, evrak gönderme, ödeme yapma vb.) gerçekleştirmez. Sadece kullanıcının izin verdiği dava detaylarını okur ve kopyalar.

### 2. KVKK ve Veri Koruma Standartları:

- **Kişisel Verilerin Maskelenmesi:** TCKN ve VKN gibi kritik kimlik bilgileri loglara basılmaz, hata mesajlarında geri gönderilmez ve doğrudan RAG veritabanına ham halde kaydedilmez.
- **Cloudflare Korumalı Altyapı:** Çekilen veriler Cloudflare güvenli altyapısında uçtan uca şifreli (E2E Encrypted) olarak saklanır.
- **Kullanıcı Kontrolü ve Çift Filtre:** Kullanıcı sadece belirli davaların çekilmesi için filtre uygulayabilir. Backend, bu filtre dışındaki hiçbir veriyi kabul etmez ve veri minimizasyonu sağlanır.

---

## 6. Teknik Fizibilite Analizi

### Önerilen Güvenlik ve Yetkilendirme Akışı

```
Kullanıcı (Tarayıcı) --> UYAP Manuel Giriş (e-imza local token)
    |
    ↓ (Oturum Açıldıktan Sonra)
Chrome Eklentisi (Oturum Üzerine Biner)
    |
    ↓ (Cihaz Bazlı API Key üretimi)
Cihaz Yetkilendirme (SHA-256 Token Hash Doğrulaması)
    |
    ↓ (Kullanıcı Filtreleri & İstek Doğrulama)
FastAPI Backend (Filtre dışı veriyi reddeder)
    |
    ↓ (Multi-Tenancy Qdrant Indexleme)
Qdrant Vector Database
```

#### Güvenlik Katmanları:

1.  **Cihaz Başına Token:** Kullanıcı her makinesi için ayrı bir API token üretir. Token çalınırsa veya cihaz kaybolursa, sadece o cihaza ait token backend'den pasif (revoke) edilir; diğer makineler etkilenmez.
2.  **Token Hashing (SHA-256):** Veritabanında API token'ın kendisi değil, SHA-256 hash'i saklanır. Veritabanı sızdırılsa dahi saldırganlar geçerli bir token elde edemezler.
3.  **Çift Filtre Doğrulaması:** Veri çekme sınırları hem eklenti tarafında hem de backend API doğrulaması tarafında kontrol edilir.

---

## 7. Entegrasyon Alternatifleri ve Karşılaştırma

### Senaryoların Karşılaştırma Matrisi:

| Kriter                 | Senaryo 1: Doğrudan API | Senaryo 2: Manuel Yükleme (MVP) | Senaryo 3: Gateway Entegrasyonu | Senaryo 4: Tarayıcı Eklentisi (Önerilen Canlı Model) |
| :--------------------- | :---------------------- | :------------------------------ | :------------------------------ | :--------------------------------------------------- |
| **Teknik Zorluk**      | Çok Yüksek              | Düşük                           | Orta                            | Orta (Eklenti ve FastAPI köprüsü)                    |
| **Maliyet**            | Yüksek                  | Düşük                           | Orta-Yüksek                     | Düşük (Kendi geliştirdiğimiz eklenti)                |
| **Güvenlik**           | Çok Yüksek              | Yüksek (Lokal veri)             | Orta-Yüksek (3. parti risk)     | **Çok Yüksek** (E-imza localde, SHA-256 Hash)        |
| **Hukuki Uygunluk**    | Tam Uyumlu              | Tam Uyumlu                      | Kısmen Uyumlu                   | **Tam Uyumlu** (Read-only, otonom giriş yok)         |
| **Kullanıcı Deneyimi** | Mükemmel                | Orta (Manuel işlem)             | İyi                             | **Çok İyi** (Tek tıkla senkronize)                   |
| **Gerçekleşme Süresi** | 12+ Ay                  | 2 - 4 Hafta                     | 2 - 3 Ay                        | **4 - 6 Hafta**                                      |

---

## 8. Sistem Mimari Tasarımı

Senaryo 4 (Chrome Extension + FastAPI + Qdrant) mimarisi aşağıdaki veri akışını kullanır:

```
[ UYAP Avukat Portalı ] (Kullanıcı e-imza ile giriş yapar)
       |
       v (Oturum Üstü DOM Okuma)
[ Chrome Extension (Manifest V3) ]
       | (Sadece Yetkili Davaları Filtreler)
       | (İstek: Headers["X-Device-Token"] ile HTTPS POST)
       v
[ Backend API: FastAPI ]
       | (Token Hash Kontrolü: SHA-256 Hash Match)
       | (Filter Validation: Filtre dışı verileri reddetme)
       v
[ Document Processing Pipeline ]
       |--> HTML/XML to Text Parser
       |--> TCKN/VKN Maskeleme (Anonymization Layer)
       |--> Embedding (Mursit-Base-TR)
       v
[ Qdrant Vector DB ] (Payload: {"tenant_id": "usr_123", "text": "..."})
```

---

## 9. Güvenlik Analizi

### Risk ve Önlem Tablosu:

| Risk                                    | Etki Derecesi | Alınacak Önlem / Tasarım Kararı                                                                                                |
| :-------------------------------------- | :------------ | :----------------------------------------------------------------------------------------------------------------------------- |
| **E-imza / Şifre Çalınması**            | Kritik        | **USB token ve PIN yerelde kalır.** Eklenti kimlik bilgilerine dokunmaz, sadece aktif web session'ı üzerindeki verileri okur.  |
| **Veritabanı Sızıntısı**                | Yüksek        | DB üzerinde API token'ların sadece SHA-256 hash'leri tutulur. Veriler Cloudflare altyapısında E2E şifrelenir.                  |
| **Cihazın Çalınması / Sızıntı**         | Yüksek        | **Cihaz Bazlı Token:** Her cihaz için ayrı token üretilir. Çalınan makinenin yetkisi tek tıkla panelden iptal (revoke) edilir. |
| **Yetkisiz Yazma / İşlem Tetikleme**    | Yüksek        | **Read-Only Yapı:** API ve eklenti üzerinde UYAP'a veri yazacak (evrak gönderme vb.) hiçbir kod bloku bulunmaz.                |
| **KVKK İhlali (Hassas Veri Sızıntısı)** | Yüksek        | TCKN/VKN maskelemesi. Loglarda kişisel veri tutulmaması.                                                                       |

---

## 10. Yapay Zekâ ve RAG Entegrasyonu

Eklentiden FastAPI'ye gelen UYAP verilerinin RAG pipeline entegrasyonu:

1.  **Metin Parçalama (Chunking):** Karar ve dilekçe metinleri 512 karakterlik, anlam bütünlüğü korunmuş parçalara ayrılır.
2.  **Embedding:** `Mursit-Base-TR-Retrieval` modeli ile metinler vektörleştirilir.
3.  **Tenant İzolasyonu:** Vektörler Qdrant'a yazılırken `tenant_id` etiketi alır. RAG sorgusu yapılırken FastAPI otomatik olarak kullanıcının `tenant_id` değerini filtreye ekler. Bu sayede hiçbir kullanıcı başka bir avukatın/kullanıcının UYAP verilerine erişemez.

---

## 11. Maliyet Analizi

### 1. Geliştirme Maliyeti (Tek Seferlik):

- **Chrome Extension (Manifest V3) Geliştirme:** 2.500 USD
- **FastAPI Backend (SHA-256 Auth, Device Revocation Panel, Ingestion API):** 3.500 USD
- **RAG ve Multi-Tenancy Güvenlik Katmanı:** 2.000 USD
- _Toplam Geliştirme:_ **8.000 USD**

### 2. Altyapı Maliyeti (Aylık):

- **AWS / Cloudflare Güvenli Sunucu + PostgreSQL:** 100 USD / Ay
- **Qdrant Cloud:** 50 USD / Ay
- **LLM API:** Kullanım bazlı (~100 USD / Ay)
- _Toplam Altyapı:_ **~250 USD / Ay**

---

## 12. Risk ve SWOT Analizi

### SWOT Analizi:

- **Güçlü Yönler (S):** Çok yüksek güvenlik düzeyi (e-imza yerelde), KVKK uyumlu tasarım kararları, cihaz bazlı kolay yetki yönetimi (revocation).
- **Zayıf Yönler (W):** Kullanıcının Chrome Uzantısı yüklemesini gerektirmesi (mobil tarayıcılarda eklenti desteği kısıtlıdır, masaüstü odaklıdır).
- **Fırsatlar (O):** Sektörde güvenliğe önem veren kurumsal hukuk bürolarının güvenini kazanarak rakiplerin önüne geçilmesi.
- **Tehditler (T):** UYAP Avukat Portalı arayüz yapısının (DOM) kökten değişmesi durumunda eklentinin scraper kodlarının güncellenmesi ihtiyacı.

---

## 13. Sonuç ve Yol Haritası

### Uygulanabilirlik Kararı:

Önerilen **Senaryo 4 (Oturum Üstü Eklenti Köprüsü)**, hukuk asistanı projesine UYAP entegrasyonu eklemek için **EN UYGUN, EN GÜVENLİ VE HUKUKİ AÇIDAN EN AZ RİSKLİ** yöntemdir. Bu çözümün sisteme eklenmesi kesinlikle mümkündür ve tavsiye edilir.

### Yol Haritası (Geliştirme Planı):

- **Hafta 1 - 2 (Altyapı):** FastAPI backend üzerinde cihaz bazlı API Key üretimi, SHA-256 hash saklama tabloları ve iptal (revoke) mekanizmasının kodlanması.
- **Hafta 3 - 4 (Eklenti):** Chrome Extension (Manifest V3) tabanlı DOM parser'ın yazılması, UYAP dava detay ekranından veri okuma testleri.
- **Hafta 5 (Entegrasyon & RAG):** Eklenti verilerinin FastAPI ingestion endpoint'ine aktarılması, TCKN maskeleme filtresi ve Qdrant multi-tenancy entegrasyonu.
- **Hafta 6 (Test ve Sürüm):** Güvenlik sızma testleri ve pilot avukat grubuyla canlı testlerin yapılması.
