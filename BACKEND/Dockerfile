# ════════════════════════════════════════════════════════
# LawAgent AI — Dockerfile (HF Spaces + Docker Compose uyumlu)
# ════════════════════════════════════════════════════════
# HF Spaces: port 7860, USER 1000 (zorunlu)
# Local:     PORT env var ile override edilebilir
# ════════════════════════════════════════════════════════

FROM python:3.11-slim

# Sistem bağımlılıkları
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces non-root user zorunluluğu
RUN useradd -m -u 1000 appuser

# Çalışma dizini
WORKDIR /app

# Bağımlılıkları önce kopyala (cache için)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Uygulama kaynak kodunu kopyala
COPY . .

# Gerekli dizinleri oluştur ve kullanıcıya ver
RUN mkdir -p src/data/qdrant_storage && \
    chown -R appuser:appuser /app

# appuser'a geç (HF Spaces zorunluluğu)
USER 1000

# Ortam değişkenleri
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=7860

# Port aç
EXPOSE 7860

# Başlatma komutu (PORT env var'a göre çalışır)
CMD ["sh", "-c", "python src/generator.py --api"]
