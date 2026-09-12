"""
src/pipeline/storage.py — Ortak JSON Okuma/Yazma Yardımcıları
==============================================================
Admin ve pipeline modülleri tarafından paylaşılır.
Dosyaya yazma sorumluluğu buradadır; scraper ve cleaner sadece dict döndürür.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

# Proje kök dizinlerine göre sabit klasör yolları
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DIR = _BACKEND_DIR / "src" / "pipeline" / "scraping" / "raw_corpus"
CLEAN_DIR = _BACKEND_DIR / "src" / "pipeline" / "preprocessing" / "clean_corpus"


def versioned_name(law_id: str, suffix: str) -> str:
    """
    Versiyonlu dosya adı üretir.
    Örnek: "6098_raw_v20260912_215500.json"
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_id = law_id.replace("/", "_").replace("\\", "_")
    return f"{safe_id}_{suffix}_v{ts}.json"


def save_json(data: dict, directory: Path, filename: str) -> Path:
    """
    Veriyi JSON olarak belirtilen dizine kaydeder.
    Dizin yoksa otomatik oluşturur. Üzerine yazmaz — her çağrı yeni dosya.
    Returns: kaydedilen dosyanın tam Path'i.
    """
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / filename
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return target


def load_json(path: str | Path) -> dict:
    """
    JSON dosyasını okuyup dict olarak döndürür.
    Raises: FileNotFoundError | json.JSONDecodeError
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_versions(law_id: str, suffix: str, directory: Path) -> list[Path]:
    """
    Belirli bir law_id ve suffix için mevcut versiyonlu dosyaları döndürür.
    En yeniden en eskiye sıralı.
    """
    safe_id = law_id.replace("/", "_").replace("\\", "_")
    pattern = f"{safe_id}_{suffix}_v*.json"
    files = sorted(directory.glob(pattern), reverse=True)
    return files
