#!/bin/bash
# ════════════════════════════════════════════════════════
# LawAgent AI — RAG Pipeline (Bash / Linux / Docker)
# ════════════════════════════════════════════════════════
# Çalıştırma:
#   bash run_pipeline.sh
#   bash run_pipeline.sh --skip-scrape   # Scraping'i atla
#   bash run_pipeline.sh --reset-qdrant  # Qdrant'ı sıfırla
# ════════════════════════════════════════════════════════

set -e  # Hata oluşursa dur
set -u  # Tanımsız değişken kullanımını yakala

# ── Argümanlar ────────────────────────────────────────────
SKIP_SCRAPE=false
RESET_QDRANT=false

for arg in "$@"; do
  case $arg in
    --skip-scrape)   SKIP_SCRAPE=true ;;
    --reset-qdrant)  RESET_QDRANT=true ;;
  esac
done

# ── Renkli çıktı ──────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_step() { echo -e "\n${CYAN}━━━ $1 ${NC}"; }
log_ok()   { echo -e "${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_err()  { echo -e "${RED}❌ HATA: $1${NC}"; exit 1; }

# ── 0. Ön Hazırlık ────────────────────────────────────────
log_step "0/6 Ön Hazırlık"

# Gerekli klasörleri oluştur
mkdir -p src/data/qdrant_storage
log_ok "Klasörler hazır: src/data/, src/data/qdrant_storage/"

# .env kontrolü
if [ ! -f ".env" ]; then
  log_warn ".env dosyası bulunamadı! .env.example'dan kopyalanıyor..."
  if [ -f "../.env.example" ]; then
    cp ../.env.example .env
    log_warn ".env oluşturuldu. Lütfen API anahtarlarını doldurun ve tekrar çalıştırın."
    exit 1
  else
    log_err ".env.example de bulunamadı. Lütfen .env dosyasını oluşturun."
  fi
fi

echo -e "${GREEN}🚀 LawAgent RAG Pipeline Başlıyor...${NC}"
START_TIME=$(date +%s)

# ── 1. Veri Kazıma — Mevzuat ─────────────────────────────
if [ "$SKIP_SCRAPE" = false ]; then
  log_step "1/6 Mevzuat Spider (mevzuat.gov.tr)"
  cd src
  scrapy crawl mevzuat -o data/mevzuat_corpus.json --logfile ../logs/mevzuat_spider.log 2>&1 || \
    log_warn "Mevzuat spider hata verdi, devam ediliyor..."
  cd ..
  log_ok "Mevzuat verisi toplandı → src/data/mevzuat_corpus.json"

  # ── 2. Veri Kazıma — Yargıtay ──────────────────────────
  log_step "2/6 Yargıtay Spider (karararama.yargitay.gov.tr)"
  cd src
  scrapy crawl yargitay -o data/yargitay_corpus.json --logfile ../logs/yargitay_spider.log 2>&1 || \
    log_warn "Yargıtay spider hata verdi, devam ediliyor..."
  cd ..
  log_ok "Yargıtay kararları toplandı → src/data/yargitay_corpus.json"
else
  log_warn "Scraping atlandı (--skip-scrape). Mevcut corpus dosyaları kullanılacak."
fi

# ── 3. Ön İşleme (Preprocessing) ─────────────────────────
log_step "3/6 Metin Ön İşleme (preprocessing.py)"
python src/scraper/preprocessing.py || log_err "preprocessing.py başarısız oldu."
log_ok "Metinler temizlendi"

# ── 4. Hukuki Parçalama (Chunking) ───────────────────────
log_step "4/6 Hukuki Parçalama (legal_chunker.py)"
python src/scraper/legal_chunker.py || log_err "legal_chunker.py başarısız oldu."
log_ok "Chunk corpus oluşturuldu → src/data/chunk_corpus.json"

# ── 5. Vektörleştirme (Embedding) ────────────────────────
log_step "5/6 Vektörleştirme (embedder.py)"
if [ "$RESET_QDRANT" = true ]; then
  python src/embedder.py --reset || log_err "embedder.py --reset başarısız oldu."
else
  python src/embedder.py || log_err "embedder.py başarısız oldu."
fi
log_ok "Vektörler Qdrant'a yüklendi"

# ── 6. Retriever Önbelleği ────────────────────────────────
log_step "6/6 Retriever Yapılandırması (retriever.py)"
python src/retriever.py || log_err "retriever.py başarısız oldu."
log_ok "Retriever cache hazır → src/data/retriever_cache.pkl"

# ── Özet ──────────────────────────────────────────────────
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
echo -e "\n${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Pipeline tamamlandı! (${ELAPSED} saniye)${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}🌐 API'yi başlatmak için:${NC}"
echo "   python src/generator.py --api"
echo "   # veya Docker ile:"
echo "   docker-compose up api"