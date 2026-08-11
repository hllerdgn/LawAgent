import json
import time
import scrapy
from bs4 import BeautifulSoup


class YargitaySpider(scrapy.Spider):
    name = "yargitay"
    allowed_domains = ["karararama.yargitay.gov.tr"]

    start_urls = ["https://karararama.yargitay.gov.tr/"]

    custom_settings = {
        "DOWNLOAD_DELAY": 4.0,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 3.0,
        "AUTOTHROTTLE_MAX_DELAY": 30.0,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "COOKIES_ENABLED": True,
        "RETRY_HTTP_CODES": [429, 500, 502, 503, 504],
        "RETRY_TIMES": 8,
        "RETRY_PRIORITY_ADJUST": -2,
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://karararama.yargitay.gov.tr",
            "Referer": "https://karararama.yargitay.gov.tr/",
            "X-Requested-With": "XMLHttpRequest",
        },
    }

    _TBK_TERMS = [
        "TBK 37",  "TBK 39",  "TBK 28",  "TBK 49",
        "TBK 72",  "TBK 112", "TBK 117", "TBK 146",
        "TBK 161", "TBK 182", "TBK 299", "TBK 344",
        "TBK 347", "TBK 352", "TBK 435", "TBK 481",
        "TBK 506", "TBK 583",
    ]
    _TTK_TERMS = [
        "TTK 18",  "TTK 56",  "TTK 375", "TTK 413",
        "TTK 445", "TTK 553", "TTK 595", "TTK 625",
        "TTK 632", "TTK 644", "TTK 796", "TTK 814",
    ]
    _TKHK_TERMS = [
        "TKHK 8", "TKHK 11", "TKHK 33", "TKHK 48",
        "TKHK 52", "TKHK 68", "TKHK 73",
    ]
    _TMK_TERMS = ["TMK 174", "TMK 185", "TMK 321", "TMK 369"]
    _IIK_TERMS = ["IIK 67", "IIK 89", "IIK 148"]
    _HMK_TERMS = ["HMK 107", "HMK 266", "HMK 353"]

    SEARCH_TERMS = (
        _TBK_TERMS + _TTK_TERMS + _TKHK_TERMS
        + _TMK_TERMS + _IIK_TERMS + _HMK_TERMS
    )

    PAGE_SIZE = 20
    MAX_PAGE = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, "kanun") and self.kanun:
            self.SEARCH_TERMS = [self.kanun]
        self._seen_ids: set = set()

    def parse(self, response):
        for term in self.SEARCH_TERMS:
            yield self._search_request(term, page=1)

    def _search_request(self, term: str, page: int):
        payload = {
            "data": {
                "aranan": term,
                "arananKelime": term,
                "pageSize": self.PAGE_SIZE,
                "pageNumber": page,
            }
        }
        return scrapy.Request(
            url="https://karararama.yargitay.gov.tr/aramalist",
            method="POST",
            body=json.dumps(payload),
            callback=self.parse_search,
            errback=self.handle_error,
            meta={"term": term, "page": page, "handle_httpstatus_list": [429]},
            dont_filter=True,
        )

    def handle_error(self, failure):
        request = failure.request
        self.logger.warning(f"Request error: {failure.value} — {request.url}")

    def parse_search(self, response):
        if response.status == 429:
            term = response.meta["term"]
            page = response.meta["page"]
            retry_after = int(response.headers.get("Retry-After", 60))
            self.logger.warning(f"429 received, sleeping {retry_after}s: {term} p.{page}")
            time.sleep(retry_after + 5)
            yield self._search_request(term, page)
            return

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("JSON decode failed:\n%s", response.text[:500])
            return

        results = data.get("data", {}).get("data", [])
        if not results:
            return

        term = response.meta["term"]
        page = response.meta["page"]

        for karar in results:
            karar_id = karar.get("id")
            if not karar_id or karar_id in self._seen_ids:
                continue
            self._seen_ids.add(karar_id)
            yield scrapy.Request(
                url=f"https://karararama.yargitay.gov.tr/getDokuman?id={karar_id}",
                callback=self.parse_decision,
                errback=self.handle_error,
                meta={"karar_id": karar_id, "term": term},
                dont_filter=True,
            )

        total = data.get("data", {}).get("totalCount", 0)
        fetched_so_far = page * self.PAGE_SIZE
        if page < self.MAX_PAGE and fetched_so_far < total:
            yield self._search_request(term, page + 1)

    def parse_decision(self, response):
        if response.status == 429:
            self.logger.warning(f"429 on decision {response.meta['karar_id']}, sleeping 60s")
            time.sleep(60)
            yield scrapy.Request(
                url=response.url,
                callback=self.parse_decision,
                meta=response.meta,
                dont_filter=True,
            )
            return

        try:
            data = json.loads(response.text)
            html = data.get("data") or ""
        except Exception:
            return

        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n", strip=True)

        if not text or len(text) < 200:
            return

        yield {
            "decision_id": response.meta["karar_id"],
            "query": response.meta["term"],
            "text": text,
            "source": "yargitay",
        }
