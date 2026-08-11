# ⚡ LawAgent AI — Uptime Monitoring Rehberi

Bu dokümanda **Hugging Face ücretsiz CPU Space**'ini mümkün olduğunca aktif tutmak için kullanılan strateji ve araçlar açıklanmaktadır.

---

## ⚠️ Önemli Not

**UptimeRobot**, Hugging Face'in resmi bir özelliği veya ortağı **değildir**.

Hugging Face ücretsiz Space'lerin sleep politikası şu şekildedir:
- Ücretsiz CPU Space, **belirli bir süre HTTP isteği almadığında** uykuya geçer (genellikle 48 saat).
- Uykudaki Space'e gelen ilk istek, **10–30 saniyelik cold start gecikmesine** neden olabilir.
- Bu araç, Space'in resmi sleep politikasını **bypass etmez**, yalnızca Space'in düzenli istek almasını sağlar.

Bu çözüm:
- ✅ Ücretsiz
- ✅ Production-safe
- ✅ Policy-compliant (Hugging Face kullanım şartlarını ihlal etmez)

---

## 🔗 Health Endpoint

Backend, uptime monitoring için optimize edilmiş minimal bir endpoint sunar:

```
GET https://hllerdgn-lawagent-backend.hf.space/health
```

**Beklenen Response:**
```json
{ "status": "ok" }
```

**HTTP Status:** `200 OK`

Bu endpoint:
- ❌ Groq API çağrısı yapmaz
- ❌ Qdrant'a istek göndermez
- ❌ Embedding model yüklemez
- ✅ Yalnızca FastAPI process'inin çalıştığını doğrular

---

## 🚀 Yöntem 1: UptimeRobot (Önerilen)

UptimeRobot, gerçek uptime monitoring + **e-posta/SMS alert** özelliği sunar.

### Kurulum Adımları

#### 1. Hesap Oluştur
[uptimerobot.com](https://uptimerobot.com) adresine gidin ve ücretsiz hesap oluşturun.
> Ücretsiz plan: 50 monitör, **5 dakika** monitoring interval.

#### 2. Yeni Monitor Ekle
Dashboard'da **"Add New Monitor"** butonuna tıklayın.

#### 3. Monitor Ayarları

| Alan | Değer |
|---|---|
| Monitor Type | **HTTP(s)** |
| Friendly Name | `LawAgent AI Backend` |
| URL (or IP) | `https://hllerdgn-lawagent-backend.hf.space/health` |
| Monitoring Interval | `5 minutes` |
| HTTP Method | `GET` |
| Expected HTTP Status | `200` |

#### 4. Alert Contact Ekle
"Alert Contacts" bölümünden e-posta adresinizi ekleyin. Space down olduğunda bildirim alırsınız.

#### 5. Monitörü Aktif Et
**"Create Monitor"** butonuna tıklayın. Monitoring hemen başlar.

### Kontrol
"Monitors" sayfasında yeşil renk → Space aktif ve sağlıklı.

---

## 🤖 Yöntem 2: GitHub Actions Keep-Alive (Yedek)

`.github/workflows/keep-alive.yml` dosyası, GitHub Actions aracılığıyla düzenli ping gönderir.

- **Interval:** Her 25 dakikada bir (günde ~58 istek)
- **Aylık maliyet:** ~58 × 30 × 1 dakika ≈ 1740 dakika (GitHub Free: 2000 dakika/ay — limit içinde)
- **Amaç:** UptimeRobot ile birlikte ikincil güvence katmanı

---

## 🔄 Cold Start Davranışı

Space uykudan uyanırken ilk istek **30 saniyeye kadar** gecikebilir. LawAgent AI frontend bu durumu ele alır:

- İlk istek timeout olursa: `⏳ Sunucu başlatılıyor, lütfen birkaç saniye bekleyin...` mesajı gösterilir.
- Kullanıcı birkaç saniye bekleyip soruyu tekrar deneyebilir.

---

## 📋 Vercel Frontend Yapılandırması

Frontend `VITE_API_URL` env var'ı ile backend URL'sini otomatik okur.

`FRONTEND/.env.production` dosyasında:
```env
VITE_API_URL=https://hllerdgn-lawagent-backend.hf.space
```

Vercel dashboard'unda da aynı değişkeni set etmeyi unutmayın:
- **Setting:** `VITE_API_URL`
- **Value:** `https://hllerdgn-lawagent-backend.hf.space`

---

## ✅ Kontrol Listesi (Deployment Sonrası)

```
[ ] GET https://hllerdgn-lawagent-backend.hf.space/health → 200 {"status":"ok"}
[ ] UptimeRobot monitörü aktif ve yeşil
[ ] GitHub Actions keep-alive workflow çalışıyor (Actions sekmesinden kontrol et)
[ ] Vercel frontend'i backend'e bağlanabiliyor
[ ] Admin paneli (Vercel) backend API'ye ulaşabiliyor
[ ] ChatbotWidget cold start mesajı görüntüleniyor
```
