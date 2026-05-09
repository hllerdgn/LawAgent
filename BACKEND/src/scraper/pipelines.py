from scrapy.exceptions import DropItem
from scraper.preprocessing import preprocess_text, anonymize_text


class MevzuatPreprocessPipeline:
    def process_item(self, item, spider):
        if spider.name != "mevzuat":
            return item

        temiz = preprocess_text(item["text"])

        if len(temiz) < 50:
            raise DropItem("Metin çok kısa")

        item["text"] = temiz
        item["char_len"] = len(temiz)
        return item


class YargiCleanPipeline:
    """
    Yargıtay kararları için temizlik ve anonimleştirme pipeline'ı
    """

    MIN_CHAR_LEN = 300  # Yargıtay kararları için daha güvenli alt sınır

    def process_item(self, item, spider):
        if spider.name != "yargitay":
            return item

        text = item.get("text")
        if not text:
            raise DropItem("Metin alanı boş")

        temiz = preprocess_text(text)

        temiz = anonymize_text(temiz)

        if len(temiz) < self.MIN_CHAR_LEN:
            raise DropItem("Karar metni çok kısa")

        item["text"] = temiz
        item["char_len"] = len(temiz)

        item.setdefault("source", "yargitay")

        return item
