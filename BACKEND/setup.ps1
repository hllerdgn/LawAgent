# ════════════════════════════════════════════════════════
# LawAgent AI — İlk Kurulum Scripti (PowerShell / Windows)
# ════════════════════════════════════════════════════════
# Projeyi klonladıktan sonra bu scripti bir kez çalıştırın:
#   cd BACKEND
#   .\setup.ps1
# ════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host @"

  ██╗      █████╗ ██╗    ██╗ █████╗  ██████╗ ███████╗███╗   ██╗████████╗
  ██║     ██╔══██╗██║    ██║██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
  ██║     ███████║██║ █╗ ██║███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   
  ██║     ██╔══██║██║███╗██║██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   
  ███████╗██║  ██║╚███╔███╔╝██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   
  ╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   
  
  LawAgent AI — Kurulum Sihirbazı
"@ -ForegroundColor Cyan

# ── 1. Python sürüm kontrolü ──────────────────────────────
Write-Host "`n[1/5] Python sürümü kontrol ediliyor..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python bulunamadı! https://python.org adresinden kurun." -ForegroundColor Red
    exit 1
}

# ── 2. Sanal ortam ────────────────────────────────────────
Write-Host "`n[2/5] Sanal ortam (venv) hazırlanıyor..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "✅ .venv oluşturuldu" -ForegroundColor Green
} else {
    Write-Host "✅ .venv zaten mevcut" -ForegroundColor Green
}

# Aktivasyon
& ".venv\Scripts\Activate.ps1"
Write-Host "✅ Sanal ortam aktif" -ForegroundColor Green

# ── 3. Bağımlılıkları yükle ───────────────────────────────
Write-Host "`n[3/5] Python bağımlılıkları yükleniyor..." -ForegroundColor Yellow
pip install --upgrade pip --quiet
pip install -r requirements.txt
Write-Host "✅ Bağımlılıklar yüklendi" -ForegroundColor Green

# ── 4. .env dosyası ───────────────────────────────────────
Write-Host "`n[4/5] Ortam değişkenleri (.env) hazırlanıyor..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    if (Test-Path "..\.env.example") {
        Copy-Item "..\.env.example" ".env"
        Write-Host "✅ .env oluşturuldu (.env.example'dan kopyalandı)" -ForegroundColor Green
        Write-Host ""
        Write-Host "⚠️  ÖNEMLİ: .env dosyasını açın ve şu değerleri doldurun:" -ForegroundColor Yellow
        Write-Host "   • GROQ_API_KEY  → https://console.groq.com" -ForegroundColor White
        Write-Host "   • QDRANT_URL    → Docker: http://localhost:6333" -ForegroundColor White
    } else {
        Write-Host "⚠️  .env.example bulunamadı. .env dosyasını manuel oluşturun." -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ .env zaten mevcut" -ForegroundColor Green
}

# ── 5. Klasör yapısı ──────────────────────────────────────
Write-Host "`n[5/5] Proje klasörleri oluşturuluyor..." -ForegroundColor Yellow
$dirs = @(
    "src\data",
    "src\data\qdrant_storage",
    "logs"
)
foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Write-Host "  📁 $dir" -ForegroundColor Gray
}
Write-Host "✅ Klasörler hazır" -ForegroundColor Green

# ── Tamamlandı ────────────────────────────────────────────
Write-Host @"

════════════════════════════════════════════════
✅ Kurulum tamamlandı!
════════════════════════════════════════════════

Sonraki adımlar:
  1. .env dosyasını düzenleyin (API anahtarlarını girin)
  2. Pipeline'ı çalıştırın:
       .\run_pipeline.ps1
  3. API'yi başlatın:
       python src\generator.py --api

  Scraping'i atlayıp mevcut verilerle başlamak için:
       .\run_pipeline.ps1 -SkipScrape

Docker ile çalıştırmak için:
  docker-compose run --rm pipeline
  docker-compose up api

"@ -ForegroundColor Cyan
