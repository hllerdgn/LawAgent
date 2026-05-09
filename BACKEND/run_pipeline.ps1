# ========================================================
# LawAgent AI — RAG Pipeline (PowerShell / Windows Native)
# ========================================================
# Calistirma:
#   .\run_pipeline.ps1
#   .\run_pipeline.ps1 -SkipScrape          # Scraping'i atla
#   .\run_pipeline.ps1 -ResetQdrant         # Qdrant'i sifirla
#   .\run_pipeline.ps1 -SkipScrape -ResetQdrant
# ========================================================

param(
    [switch]$SkipScrape,
    [switch]$ResetQdrant
)

# -- Encoding ----------------------------------------------
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# -- Renk yardimcilari -------------------------------------
function Write-Step  { param($n,$msg) Write-Host "`n--- $n $msg" -ForegroundColor Cyan }
function Write-OK    { param($msg)    Write-Host "OK: $msg"       -ForegroundColor Green }
function Write-Warn  { param($msg)    Write-Host "WARN: $msg"     -ForegroundColor Yellow }
function Write-Err   { param($msg)    Write-Host "ERROR: $msg"    -ForegroundColor Red; exit 1 }

$StartTime = Get-Date

# -- 0. On Hazirlik ----------------------------------------
Write-Step "0/6" "On Hazirlik"

# Gerekli klasorleri olustur
New-Item -ItemType Directory -Force -Path "src\data\qdrant_storage" | Out-Null
New-Item -ItemType Directory -Force -Path "logs" | Out-Null
Write-OK "Klasorler hazir: src\data\, logs\"

# .env kontrolü
if (-not (Test-Path ".env")) {
    Write-Warn ".env dosyasi bulunamadi!"
    if (Test-Path "..\.env.example") {
        Copy-Item "..\.env.example" ".env"
        Write-Warn ".env olusturuldu. Lutfen .env icindeki API anahtarlarini doldurun ve tekrar calistirin."
        exit 1
    } else {
        Write-Err ".env.example de bulunamadi. Lutfen .env dosyasini olusturun."
    }
}

Write-Host "`nLAUNCH: LawAgent RAG Pipeline Basliyor..." -ForegroundColor Cyan

# -- 1. Mevzuat Spider -------------------------------------
if (-not $SkipScrape) {
    Write-Step "1/6" "Mevzuat Spider (mevzuat.gov.tr)"
    try {
        Push-Location "src"
        scrapy crawl mevzuat -o data/mevzuat_corpus.json 2>&1 | Out-File -FilePath "..\logs\mevzuat_spider.log" -Encoding utf8
        Pop-Location
        Write-OK "Mevzuat verisi toplandi -> src\data\mevzuat_corpus.json"
    } catch {
        Pop-Location -ErrorAction SilentlyContinue
        Write-Warn "Mevzuat spider hata verdi: $($_.Exception.Message) — devam ediliyor..."
    }

    # -- 2. Yargitay Spider --------------------------------
    Write-Step "2/6" "Yargitay Spider (karararama.yargitay.gov.tr)"
    try {
        Push-Location "src"
        scrapy crawl yargitay -o data/yargitay_corpus.json 2>&1 | Out-File -FilePath "..\logs\yargitay_spider.log" -Encoding utf8
        Pop-Location
        Write-OK "Yargitay kararlari toplandi -> src\data\yargitay_corpus.json"
    } catch {
        Pop-Location -ErrorAction SilentlyContinue
        Write-Warn "Yargitay spider hata verdi: $($_.Exception.Message) — devam ediliyor..."
    }
} else {
    Write-Warn "Scraping atlandi (-SkipScrape). Mevcut corpus dosyalari kullanilacak."
}

# -- 3. On Isleme (Preprocessing) --------------------------
Write-Step "3/6" "Metin On Isleme (preprocessing.py)"
try {
    python src/scraper/preprocessing.py
    Write-OK "Metinler temizlendi"
} catch {
    Write-Err "preprocessing.py basarisiz: $($_.Exception.Message)"
}

# -- 4. Hukuki Parçalama (Chunking) ------------------------
Write-Step "4/6" "Hukuki Parcalama (legal_chunker.py)"
try {
    python src/scraper/legal_chunker.py
    Write-OK "Chunk corpus olusturuldu -> src\data\chunk_corpus.json"
} catch {
    Write-Err "legal_chunker.py basarisiz: $($_.Exception.Message)"
}

# -- 5. Vektorlestirme (Embedding) -------------------------
Write-Step "5/6" "Vektorlestirme (embedder.py)"
try {
    if ($ResetQdrant) {
        python src/embedder.py --reset
    } else {
        python src/embedder.py
    }
    Write-OK "Vektorler Qdrant'a yuklendi"
} catch {
    Write-Err "embedder.py basarisiz: $($_.Exception.Message)"
}

# ── 6. Retriever Önbelleği ────────────────────────────────
Write-Step "6/6" "Retriever Yapilandirmasi (retriever.py)"
try {
    python src/retriever.py
    Write-OK "Retriever cache hazir -> src\data\retriever_cache.pkl"
} catch {
    Write-Err "retriever.py basarisiz: $($_.Exception.Message)"
}

# ── Özet ──────────────────────────────────────────────────
$Elapsed = [int]((Get-Date) - $StartTime).TotalSeconds
Write-Host "`n════════════════════════════════════════" -ForegroundColor Green
Write-Host "✅ Pipeline tamamlandi! ($Elapsed saniye)" -ForegroundColor Green
Write-Host "════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "API'yi baslatmak icin:" -ForegroundColor Cyan
Write-Host "   python src/generator.py --api"
Write-Host "   # Streamlit arayuzu icin:"
Write-Host "   streamlit run app.py"