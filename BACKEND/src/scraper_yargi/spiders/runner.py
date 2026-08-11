import sys
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

try:
    from .yargitay_spider import YargitaySpider
except ImportError:
    from yargitay_spider import YargitaySpider


def run_scraper():
    print("\n" + "=" * 50)
    print("      YARGITAY İÇTİHAT TARAMA SİSTEMİ")
    print("=" * 50 + "\n")

    # 1. Kullanıcıdan input alıyoruz
    print("Hangi kanun veya kavram (örneğin: TBK, İş Kazası, TCK) için")
    target_law = input("içtihatları taramak istersiniz?: ").strip()

    if not target_law:
        print("\n[!] Herhangi bir kelime girmediniz. İşlem iptal edildi.")
        return

    # 2. Scrapy ayarlarını yapılandırıyoruz
    # Sonuçları otomatik olarak kanun_adi.json şeklinde kaydeder
    settings = get_project_settings()
    settings.update(
        {
            "FEEDS": {
                f"{target_law.lower()}_sonuclar.json": {
                    "format": "json",
                    "encoding": "utf8",
                    "indent": 4,
                    "overwrite": True,  # Her yeni aramada üzerine yazar
                },
            },
            "LOG_LEVEL": "INFO",  # Terminalde çok fazla teknik detay görmemek için
        }
    )

    # 3. CrawlerProcess ile mevcut spider'ı tetikliyoruz
    process = CrawlerProcess(settings)

    print(f"\n[+] '{target_law}' için tarama başlatılıyor. Lütfen bekleyin...\n")

    # Spider'ınızın __init__ metoduna 'kanun' parametresini gönderiyoruz
    process.crawl(YargitaySpider, kanun=target_law)
    process.start()

    print("\n" + "=" * 50)
    print(
        f"[TAMAMLANDI] Veriler '{target_law.lower()}_sonuclar.json' dosyasına kaydedildi."
    )
    print("=" * 50)


if __name__ == "__main__":
    try:
        run_scraper()
    except KeyboardInterrupt:
        print("\n\n[!] İşlem kullanıcı tarafından durduruldu.")
        sys.exit(0)
