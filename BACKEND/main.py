"""
main.py — LawAgent AI Ana Başlatıcı (CLI & API)
==============================================
Kullanım:
    python main.py --api           # FastAPI sunucusunu başlatır
    python main.py --interactive   # Terminalden interaktif soru-cevap
"""

import sys
import os
import argparse
from pathlib import Path

# Backend kök dizinini sys.path'e ekle
_BACKEND_DIR = str(Path(__file__).resolve().parent)
_SRC_DIR = str(Path(__file__).resolve().parent / "src")
for _p in [_BACKEND_DIR, _SRC_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from config.settings import settings
from core.logging import log
from api.app import create_application


def main():
    parser = argparse.ArgumentParser(description="LawAgent AI — Türk Hukuku Asistanı")
    parser.add_argument("--api", action="store_true", help="FastAPI sunucusunu başlat")
    parser.add_argument("--interactive", action="store_true", help="İnteraktif CLI modunda çalıştır")
    parser.add_argument("--port", type=int, default=None, help=f"Port (varsayılan: {settings.PORT})")
    args = parser.parse_args()

    if args.api:
        port = args.port or settings.PORT
        log.info(f"FastAPI sunucusu başlatılıyor... (port={port})")
        import uvicorn
        app = create_application()
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

    elif args.interactive:
        from src.generator import LegalGenerator
        gen = LegalGenerator(k=settings.DEFAULT_ASK_K)
        session = "cli_session"
        print("\n" + "=" * 70)
        print("⚖️  LawAgent AI — Türk Hukuku Asistanı (CLI Modu)")
        print("=" * 70)
        print("Soru sorabilirsiniz. Çıkmak için 'quit' veya 'q' yazın.\n")
        
        while True:
            try:
                sorgu = input("\n⚖️  Soru: ").strip()
                if sorgu.lower() in {"quit", "q", "çık", "exit"}:
                    print("Görüşmek üzere!")
                    break
                if not sorgu:
                    continue
                result = gen.generate(sorgu, session_id=session)
                print("\n" + "-" * 70)
                print(f"📋 Niyet: {result.get('intent', 'UNKNOWN')}")
                print(f"💬 Yanıt:\n{result['answer']}")
                if result.get("sources"):
                    print(f"\n📚 Kaynaklar ({len(result['sources'])} adet):")
                    for i, src in enumerate(result["sources"], 1):
                        print(f"  {i}. {src.get('kanun', '')} {src.get('madde', '')}")
                print(f"\n⏱️ Süre: {result.get('sure_ms', 0)}ms")
                print("-" * 70)
            except (KeyboardInterrupt, EOFError):
                print("\nÇıkış yapıldı.")
                break
    else:
        # Varsayılan olarak API'yi başlat
        port = args.port or settings.PORT
        log.info(f"Parametre belirtilmedi, API başlatılıyor... (port={port})")
        import uvicorn
        app = create_application()
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
