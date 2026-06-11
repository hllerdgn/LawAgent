import math
import os
import sys
import pickle
import re
import logging
import atexit
import warnings
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

# Bu dosyanın bulunduğu dizin (src/) — CWD'den bağımsız
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))

# services/ klasörü BACKEND/ kökünde — hangi dizinden çalıştırılırsa çalıştırılsın bulsun
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from qdrant_client.http import models as qm
from embedder import MursitEmbedder, COLLECTION_NAME
from services.qdrant_client import get_qdrant_client

warnings.filterwarnings("ignore", category=UserWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("LawAgent.Retriever")

# ═══════════════════════════════════════════════════════════════════════════════
# AYARLAR
# ═══════════════════════════════════════════════════════════════════════════════


class CFG:
    TOP_K_DENSE: int = 200
    TOP_K_BM25: int = 200
    FINAL_K: int = 15
    MAX_SAME_ARTICLE: int = 2
    ALPHA_DEFAULT: float = 0.68
    ALPHA_EXACT: float = 0.45
    ALPHA_SEMANTIC: float = 0.72
    BOOST_MADDE: float = 35.0
    BOOST_ICTIHAT: float = 6.0
    BOOST_KANUN: float = 6.0
    CACHE_PATH: str = os.path.join(_SRC_DIR, "data", "retriever_cache.pkl")


BOLUM_ANAHTARLARI = ("GEREKÇE", "HÜKÜM", "KARAR", "UYUŞMAZLIK", "SONUÇ")

# ═══════════════════════════════════════════════════════════════════════════════
# BM25PLUS SINIFI
# ═══════════════════════════════════════════════════════════════════════════════


class BM25Plus:
    def __init__(self, k1: float = 1.6, b: float = 0.68, delta: float = 1.0):
        self.k1 = k1
        self.b = b
        self.delta = delta
        self.n = 0
        self.avgdl = 0.0
        self.idf: Dict[str, float] = {}
        self.tf: List[Dict[str, int]] = []
        self.dl: List[int] = []

    def _tokenize(self, text: str) -> List[str]:
        text = text.replace("\u0307", "")
        text = re.sub(r"[^\w\s]", " ", text.lower())
        return [t for t in text.split() if len(t) > 1]

    def index(self, docs: List[str]) -> None:
        self.n = len(docs)
        toks = [self._tokenize(d) for d in docs]
        self.dl = [len(t) for t in toks]
        self.avgdl = sum(self.dl) / max(self.n, 1)
        df = defaultdict(int)
        for t in toks:
            for term in set(t):
                df[term] += 1
        self.idf = {
            term: math.log((self.n - f + 0.5) / (f + 0.5) + 1) for term, f in df.items()
        }
        self.tf = [
            dict(defaultdict(int, {term: t.count(term) for term in t})) for t in toks
        ]
        log.info(f"[BM25+] {self.n} doküman indexlendi.")

    def score(self, query: str, n: int = 300) -> List[Tuple[int, float]]:
        q_toks = self._tokenize(query)
        if not q_toks:
            return []
        scores = []
        for i in range(self.n):
            dl, tf, skor = self.dl[i], self.tf[i], 0.0
            for t in q_toks:
                if t not in self.idf or tf.get(t, 0) == 0:
                    continue
                f = tf[t]
                num = f * (self.k1 + 1)
                den = f + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                skor += self.idf[t] * ((num / den) + self.delta)
            if skor > 0:
                scores.append((i, skor))
        scores.sort(key=lambda x: -x[1])
        return scores[:n]


# ═══════════════════════════════════════════════════════════════════════════════
# FUSION VE YARDIMCILAR
# ═══════════════════════════════════════════════════════════════════════════════


def _minmax_normalize(vals: List[float]) -> List[float]:
    if not vals:
        return vals
    mn, mx = min(vals), max(vals)
    rng = mx - mn
    return [(v - mn) / rng if rng > 0 else 1.0 for v in vals]


def hybrid_fuse(
    dense_hits: List[Dict], bm25_hits: List[Dict], alpha: float
) -> List[Dict]:
    d_norms = _minmax_normalize([h["dense_score"] for h in dense_hits])
    dense_map = {
        h["chunk_id"]: {**h, "dense_norm": dn} for h, dn in zip(dense_hits, d_norms)
    }

    b_norms = _minmax_normalize([h["bm25_score"] for h in bm25_hits])
    bm25_map = {
        h["chunk_id"]: {**h, "bm25_norm": bn} for h, bn in zip(bm25_hits, b_norms)
    }

    all_cids = set(dense_map) | set(bm25_map)
    fused = []
    for cid in all_cids:
        d, b = dense_map.get(cid), bm25_map.get(cid)
        base = d if d else b
        d_n, b_n = (d["dense_norm"] if d else 0.0), (b["bm25_norm"] if b else 0.0)
        fused.append(
            {
                **base,
                "skor": round(alpha * d_n + (1 - alpha) * b_n, 6),
                "dense_score": round(d["dense_score"] if d else 0.0, 4),
                "bm25_score": round(b["bm25_score"] if b else 0.0, 4),
            }
        )
    fused.sort(key=lambda x: -x["skor"])
    return fused


def detect_source_intent(query: str) -> str:
    q = query.lower()
    ictihat_keywords = ["karar", "içtihat", "yargıtay", "emsal", "görüş", "daire"]
    return "yargitay" if any(kw in q for kw in ictihat_keywords) else "hybrid"


def normalize_article(x: Any) -> str:
    if x is None:
        return ""
    found = re.search(r"(\d+)", str(x))
    return found.group(1) if found else ""


_ESANLAMLILAR = {
    # TBK Eklemeleri
    "gabin": "aşırı oransızlık sömürme sarsılma orantısız 28",
    "ikrah": "korkutma tehdit zorlama 37 38 39",
    "müteselsil": "zincirleme ortaklaşa dayanışma 161 162",
    "kira": "kira sözleşmesi bildirim feshi uzama tahliye TBK Madde 347 350 352",
    "tahliye": "kira kiracı tahliye bildirim süre fesih TBK Madde 347",
    "işçi": "işçi alacakları zamanaşımı on yıl TBK Madde 146 147",
    "haksız fiil": "haksız fiil tazminat zamanaşımı süre rücu TBK Madde 72 49 50",
    "temerrüt": "temerrüd borçlu gecikme ihtar TBK Madde 117 119",
    "vekalet": "vekâlet vekil özen borcu TBK Madde 506 513",
    "kefalet": "kefil kefalet eş rıza TBK Madde 583 584",
    "eser": "eser sözleşmesi müteahhit ayıp bedel TBK Madde 474 475 482",
    "zamanaşımı": "süre hak düşürücü on yıl iki yıl TBK Madde 146 147 72 153 154",
    # TKHK Eklemeleri
    "aidat": "üyelik ücreti yıllık ücret kart çıkarma bedeli",
    "promosyon": "hediye kültürel ürün süreli yayın 21",
    "ayıplı": "ayıplı mal satıcı sorumluluk seçimlik haklar üretici TKHK Madde 10 11",
    "ayıplı mal": "ayıplı mal satıcı üretici ithalatçı müteselsil sorumluluk seçimlik hak TKHK Madde 11 10",
    "ayıplı hizmet": "ayıplı hizmet sağlayıcı seçimlik hak ücretsiz yeniden görme TKHK Madde 15 16",
    "mesafeli": "mesafeli satış teslim süresi otuz gün cayma TKHK Madde 48",
    "mesafeli sözleşme cayma": "mesafeli sözleşme cayma hakkı 14 gün istisnalar TKHK Madde 48",
    "abonelik": "abonelik sözleşmesi haksız şart tüketici denetim TKHK Madde 5 52",
    "abonelik fesih": "abonelik sözleşmesi fesih bildirim sağlayıcı tazminat depozito iade TKHK Madde 52",
    "cayma": "cayma hakkı tüketici mesafeli sözleşme iade TKHK Madde 24 48",
    "kredi": "tüketici kredisi cayma erken ödeme TKHK Madde 23 24 27",
    "tüketici kredisi cayma": "cayma hakkı ondört gün tüketici kredisi TKHK Madde 24",
    "tüketici kredisi geçerlilik": "geçerlilik şartı yazılı kredi sözleşmesi TKHK Madde 23",
    "tüketici kredisi erken": "erken kapatma faiz masraf indirim TKHK Madde 27",
    "tüketici kredisi temerrüt": "konut finansmanı temerrüt muacceliyet TKHK Madde 33",
    "tüketici kredisi faiz": "faiz artışı bildirim belirsiz süreli TKHK Madde 26",
    "haksız şart": "haksız şart tüketici sözleşmesi kesin hükümsüzlük geçersizlik TKHK Madde 5",
    "devre tatil": "devre tatil sözleşmesi cayma hakkı bedel iade TKHK Madde 50",
    "paket tur": "paket tur sözleşmesi esaslı değişiklik cayma düzenleyici TKHK Madde 51",
    "garanti belgesi": "garanti belgesi sorumluluk iki yıl düzenleme yükümlülük TKHK Madde 56 57",
    "sipariş edilmey": "sipariş edilmemiş mal hizmet gönderme tüketici bedel talep TKHK Madde 7",
    "hakem heyeti": "tüketici hakem heyeti başvuru parasal sınır bağlayıcı karar TKHK Madde 68 70",
    "tüketici mahkeme": "tüketici mahkemesi yetkili mahkeme uyuşmazlık konut TKHK Madde 73",
    "işyeri dışı": "işyeri dışında sözleşme satıcı bilgilendirme yükümlülük cayma TKHK Madde 47",
    "tüketici": "tüketici hakkı TKHK Madde 5 7 10 11 15 23 24 47 48 50 51 52 56 68 70 73",
    # TTK
    "unvan": "ticaret unvanı tecavüz koruma marka TTK Madde 50 52",
    "müdür": "limited şirket müdür sorumluluk temsil TTK Madde 623 625 630 632 644",
    "limited müdür sorumluluk": "limited şirket müdür ortaklara alacaklılara sorumluluk TTK Madde 632 644",
    "limited müdür devredilemez": "limited şirket müdür devredilemez yetki vazgeçilemez TTK Madde 625",
    "limited sermaye payı devri": "limited şirket sermaye payı devir noter onay TTK Madde 595",
    "limited genel kurul devredilemez": "limited şirket ortaklar kurulu devredilemez yetki TTK Madde 616",
    "limited ortak çıkma": "limited şirket ortak çıkma çıkarılma haklı sebep TTK Madde 638 640",
    "bono": "emre yazılı senet kambiyo senedi zamanaşımı temel ilişki TTK Madde 776 777",
    "bono poliçe fark": "bono emre yazılı senet poliçe ayırt edici özellik ciro TTK Madde 776 777",
    "çek": "karşılıksızdır ibraz şerh hamilin hakları TTK Madde 796 808 814",
    "çek ibraz": "çek ibraz süresi muhatap banka hamilin hakları başvuru TTK Madde 796 797 808",
    "karşılıksız çek": "karşılıksız çek hamil tazminat cezai yaptırım TTK Madde 814",
    "ibraz": "çek ibraz süresi muhatap banka hamilin hakları TTK Madde 796 797 808",
    "poliçe protesto": "poliçe protesto kabul etmeme ödememe süre müracaat TTK Madde 713 714",
    "rüçhan": "yeni pay alma öncelik sermaye artırımı 461",
    "defter": "ticari defter tasdik delil niteliği 64 222",
    "genel kurul": "anonim şirket genel kurul olağan toplantı zaman TTK Madde 409 410",
    "genel kurul olağan": "anonim şirket genel kurul olağan toplantı yıllık TTK Madde 409 410",
    "genel kurul butlan": "genel kurul kararı butlan iptal fark dava TTK Madde 445 447",
    "anonim": "anonim şirket yönetim kurulu genel kurul TTK Madde 375 409 445 553",
    "yönetim kurulu devredilemez": "yönetim kurulu devredilemez görev yetki vazgeçilemez TTK Madde 375",
    "yönetim kurulu çağrı": "yönetim kurulu toplantı çağırma yetki TTK Madde 392",
    "yönetim kurulu sorumluluk alacaklı": "yönetim kurulu üye sorumluluk şirket alacaklı TTK Madde 553",
    "nama yazılı pay devri": "nama yazılı pay defteri kayıt şirket itiraz TTK Madde 490 493",
    "hamiline yazılı pay": "hamiline yazılı pay devir MKK bildirim TTK Madde 489 486",
    "gecikme faizi ticari": "ticari faiz gecikme TCMB Merkez Bankası oranı TTK Madde 1530",
    "limited": "limited şirket müdür ortak pay devri TTK Madde 595 616 625 632 638",
    "haksız rekabet": "dürüstlük kuralı rekabet davası TTK Madde 56 60",
    # Ek kısaltmalar
    "azil": "anonim şirket yönetim kurulu üyesi azil gündem TTK Madde 413",
    "yönetim kurulu azil": "anonim şirket yönetim kurulu üyesi azil gündeme bağlılık TTK Madde 413",
}


# ═══════════════════════════════════════════════════════════════════════════════
# HEDEFLI MADDE BOOST — Belirli konu ifadeleri tespit edildiğinde spesifik maddeye
# güçlü boost uygular. Format: (zorunlu_kelimeler_tuple) -> (kanun, madde_no)
# ═══════════════════════════════════════════════════════════════════════════════
_KEYWORD_TO_ARTICLE = [
    # TKHK — semantik olarak TBK ile karışan maddeler
    # Ayıplı mal / hizmet
    (("ayıplı mal", "seçimlik"),             ("TKHK", "11")),
    (("ayıplı mal", "satıcı", "sorumluluk"), ("TKHK", "11")),
    (("ayıplı mal", "tüketici"),             ("TKHK", "11")),
    (("ayıplı", "ispat karinesi"),           ("TKHK", "10")),
    (("ayıplı hizmet",),                     ("TKHK", "15")),
    # Haksız şart
    (("haksız şart", "tüketici"),            ("TKHK", "5")),
    (("haksız şart", "kesin hükümsüz"),      ("TKHK", "5")),
    (("haksız şart", "abonelik"),            ("TKHK", "5")),
    # Mesafeli / işyeri dışı sözleşme
    (("mesafeli", "cayma"),                  ("TKHK", "48")),
    (("mesafeli", "teslim"),                 ("TKHK", "48")),
    (("mesafeli", "istisna"),                ("TKHK", "48")),
    (("işyeri dışı", "bilgilendirme"),       ("TKHK", "47")),
    (("işyeri dışı", "satıcı"),              ("TKHK", "47")),
    # Tüketici kredisi
    (("tüketici kredi", "cayma"),            ("TKHK", "24")),
    (("tüketici kredi", "geçerlilik"),       ("TKHK", "23")),
    (("tüketici kredi", "erken kapatma"),    ("TKHK", "27")),
    (("tüketici kredi", "temerrüt"),         ("TKHK", "33")),
    (("tüketici kredi", "faiz artış"),       ("TKHK", "26")),
    (("konut finansman", "temerrüt"),        ("TKHK", "33")),
    (("konut finansman", "muaccel"),         ("TKHK", "33")),
    # Özel sözleşme türleri
    (("devre tatil",),                       ("TKHK", "50")),
    (("paket tur",),                         ("TKHK", "51")),
    (("abonelik", "fesh"),                   ("TKHK", "52")),
    (("abonelik", "depozito"),               ("TKHK", "52")),
    (("abonelik", "tüketici", "fesih"),      ("TKHK", "52")),
    (("sipariş edil",),                      ("TKHK", "7")),
    (("sipariş edilmem",),                   ("TKHK", "7")),
    (("garanti belgesi",),                   ("TKHK", "56")),
    # Uyuşmazlık çözümü
    (("hakem heyeti", "tüketici"),           ("TKHK", "68")),
    (("hakem heyeti", "parasal sınır"),      ("TKHK", "68")),
    (("tüketici", "mahkeme"),                ("TKHK", "73")),
    (("tüketici", "yetkili mahkeme"),        ("TKHK", "73")),
    # TTK — anonim şirket
    (("yönetim kurulu", "devredilemez"),     ("TTK", "375")),
    (("yönetim kurulu", "vazgeçilemez"),     ("TTK", "375")),
    (("yönetim kurulu", "toplantı", "çağır"), ("TTK", "392")),
    (("yönetim kurulu", "toplantıya çağır"), ("TTK", "392")),
    (("genel kurul", "butlan", "iptal"),     ("TTK", "445")),
    (("genel kurul", "kararı", "butlan"),    ("TTK", "445")),
    (("genel kurul", "iptal", "dava"),       ("TTK", "445")),
    (("yönetim kurulu", "alacaklı", "sorumlul"), ("TTK", "553")),
    (("yönetim kurulu", "pay sahibi", "sorumlul"), ("TTK", "553")),
    (("yönetim kurulu", "tazminat sorumlul"), ("TTK", "553")),
    (("yönetim kurulu", "üye", "azil"),      ("TTK", "413")),
    (("gündeme bağlılık",),                  ("TTK", "413")),
    (("genel kurul", "olağan toplantı"),     ("TTK", "409")),
    (("genel kurul", "olağan", "ne zaman"),  ("TTK", "409")),
    (("genel kurul", "yılda"),               ("TTK", "409")),
    # TTK — limited şirket
    (("limited", "müdür", "sorumluluk"),     ("TTK", "632")),
    (("limited", "müdür", "devredilemez"),   ("TTK", "625")),
    (("limited", "müdür", "vazgeçilemez"),   ("TTK", "625")),
    (("limited", "sermaye payı", "devri"),   ("TTK", "595")),
    (("limited", "sermaye payı", "noter"),   ("TTK", "595")),
    (("limited", "ortak", "devredilemez"),   ("TTK", "616")),
    (("limited", "ortaklar kurulu", "yetki"), ("TTK", "616")),
    (("limited", "ortak", "çıkma"),          ("TTK", "638")),
    (("limited", "haklı sebep", "çıkma"),    ("TTK", "638")),
    # TTK — pay senetleri
    (("nama yazılı pay", "devri"),           ("TTK", "490")),
    (("nama yazılı pay", "pay defteri"),     ("TTK", "490")),
    (("hamiline yazılı", "mkk"),             ("TTK", "489")),
    (("hamiline yazılı pay", "devir"),       ("TTK", "489")),
    # TTK — kıymetli evrak
    (("çek", "ibraz süresi"),               ("TTK", "796")),
    (("çekin ibraz",),                       ("TTK", "796")),
    (("çek", "ibraz", "hamilin"),            ("TTK", "796")),
    (("karşılıksız çek", "tazminat"),        ("TTK", "814")),
    (("karşılıksız çek", "hamil"),           ("TTK", "814")),
    (("bono", "poliçe"),                     ("TTK", "776")),
    (("emre yazılı senet",),                 ("TTK", "776")),
    (("poliçe", "protesto"),                 ("TTK", "713")),
    (("poliçe", "kabul etmeme"),             ("TTK", "713")),
    (("gecikme faizi", "ticari"),            ("TTK", "1530")),
    (("ticari", "gecikme faizi", "merkez"),  ("TTK", "1530")),
]

# ═══════════════════════════════════════════════════════════════════════════════
# SORGU TEMİZLEME
# ═══════════════════════════════════════════════════════════════════════════════

_NOISE_PREFIXES = [
    "yargıtay uygulamalarına göre ",
    "geçerli kanunda ",
    "kanuna göre ",
    "mevzuatta ",
    "hukuken ",
]


def _clean_query(query: str) -> str:
    """Sorgudaki gürültü prefix ve suffix'lerini temizler."""
    q_lower = query.lower()
    for prefix in _NOISE_PREFIXES:
        if q_lower.startswith(prefix):
            query = query[len(prefix):]
            break
    # Senaryo suffix'ini kaldır: "(Senaryo 42)" gibi
    query = re.sub(r'\s*\(Senaryo\s+\d+\)\s*$', '', query, flags=re.IGNORECASE)
    return query.strip()


def expand_query(query: str) -> str:
    q = query.lower()
    ekler = []
    for anahtar, deger in _ESANLAMLILAR.items():
        if anahtar in q:
            ekler.append(deger)
    return query + " " + " ".join(ekler) if ekler else query


def detect_kanun(query: str) -> Optional[str]:
    q = query.lower()
    # 1. Doğrudan kanun adı eşleşmesi (en yüksek öncelik)
    direct_mapping = {
        "tbk": "TBK", "ttk": "TTK", "tkhk": "TKHK",
        "borçlar kanunu": "TBK", "ticaret kanunu": "TTK",
        "6098": "TBK", "6102": "TTK", "6502": "TKHK",
        "tüketicinin korunması": "TKHK",
    }
    for k, v in direct_mapping.items():
        if k in q:
            return v

    # 2. Konu bazlı çıkarım (uzun ifadeler önce kontrol edilir)
    # TKHK konuları — ÖNCE kontrol edilir (TBK ile karışan alanlara özeldir)
    tkhk_kw = [
        "tüketici", "ayıplı mal", "ayıplı hizmet", "mesafeli", "cayma hakkı",
        "garanti belgesi", "abonelik", "devre tatil", "paket tur", "hakem heyeti",
        "tüketici kredisi", "konut finansmanı", "sipariş edilmeyen",
        "işyeri dışında", "işyeri dışı", "haksız şart", "satışın finansmanı",
        "tüketici hakem", "seyahat acentesi",
    ]
    for kw in tkhk_kw:
        if kw in q:
            return "TKHK"

    # TTK konuları (uzun ifadeler önce)
    ttk_kw = ["anonim şirket", "limited şirket", "haksız rekabet", "genel kurul",
              "yönetim kurulu", "ticaret sicil", "ticaret unvan", "nama yazılı",
              "hamiline yazılı", "pay devri", "ticari defter",
              "çek", "bono", "poliçe", "kambiyo", "ibraz", "tacir", "ticari işletme"]
    for kw in ttk_kw:
        if kw in q:
            return "TTK"

    # TBK konuları
    tbk_kw = ["haksız fiil", "borçlu", "alacaklı", "temerrüt", "temerrüd",
              "kira", "kiracı", "tahliye", "vekalet", "vekâlet", "kefalet",
              "eser sözleşme", "satım", "sebepsiz zenginleş", "alacağın devri",
              "temlik", "müteselsil", "zamanaşımı", "sözleşme",
              "borç", "işçi", "ticaret"]
    for kw in tbk_kw:
        if kw in q:
            return "TBK"

    return None


def extract_madde(query: str) -> Optional[str]:
    # Eğer sorgunun tamamı sadece bir sayı ise direkt onu döndür
    q_stripped = query.strip()
    if q_stripped.isdigit():
        return q_stripped
    
    # Değilse, önünde mutlaka kanun veya madde belirteci (m., madde, md., tbk vb.) olmalı
    found = re.search(r"\b(?:tbk|ttk|tkhk|madde|m\.|md\.|md|m)\s*[:\-\.]?\s*(\d+)\b", query.lower())
    if found:
        return found.group(1)
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# LEGAL RETRIEVER SINIFI
# ═══════════════════════════════════════════════════════════════════════════════


class LegalRetriever:
    def __init__(self, quantize: bool = False, reindex: bool = False):
        self.cfg = CFG()
        self.embedder = MursitEmbedder(quantize=quantize)
        self.qdrant = get_qdrant_client()
        self.bm25 = BM25Plus()
        self.corpus: List[Dict] = []
        atexit.register(self._kapat)
        self._load(reindex)

    def _kapat(self):
        try:
            self.qdrant.close()
        except:
            pass

    def _query_qdrant_with_retry(self, collection_name: str, query: Any, limit: int, with_payload: bool, retries: int = 5, delay: float = 1.0) -> Any:
        for i in range(retries):
            try:
                return self.qdrant.query_points(
                    collection_name, query=query, limit=limit, with_payload=with_payload
                )
            except Exception as e:
                if i == retries - 1:
                    raise e
                import time
                wait_time = delay * (2 ** i)
                log.warning(f"Qdrant sorgu hatası (Deneme {i+1}/{retries}): {e}. {wait_time}s bekleniyor...")
                time.sleep(wait_time)

    def _load(self, reindex: bool) -> None:
        if not reindex and os.path.exists(self.cfg.CACHE_PATH):
            # Pickle __main__.BM25Plus → retriever.BM25Plus yönlendirmesi
            # (retriever.py doğrudan çalıştırılıp cache kaydedilmişse gerekli)
            import sys as _sys
            _this_module = _sys.modules.get(__name__) or _sys.modules.get("retriever")
            if _this_module and not hasattr(_sys.modules.get("__main__"), "BM25Plus"):
                import types
                _fake = types.ModuleType("__main__")
                _fake.BM25Plus = BM25Plus
                _sys.modules.setdefault("__main__", _fake)
                _sys.modules["__main__"].BM25Plus = BM25Plus
            try:
                with open(self.cfg.CACHE_PATH, "rb") as f:
                    data = pickle.load(f)
                self.corpus, self.bm25 = data["corpus"], data["bm25"]
                log.info(f"Cache yuklendi: {len(self.corpus)} chunk.")
                return
            except (AttributeError, ModuleNotFoundError) as e:
                log.warning(f"Cache yuklenemedi ({e}), Qdrant'tan yeniden olusturuluyor...")
                # Bozuk cache'i sil, aşağıda yeniden oluşturulacak
                try:
                    os.remove(self.cfg.CACHE_PATH)
                except OSError:
                    pass

        log.info("Corpus Qdrant'tan çekiliyor (Scroll)...")
        offset = None
        while True:
            res, offset = self.qdrant.scroll(
                COLLECTION_NAME, limit=500, offset=offset, with_payload=True
            )
            for p in res:
                pay = p.payload
                self.corpus.append(
                    {
                        "chunk_id": str(p.id),
                        "text": pay.get("text", ""),
                        "law": pay.get("law", ""),
                        "article_no": normalize_article(pay.get("article_no")),
                        "source": pay.get("source", ""),
                        "decision_id": pay.get("decision_id", ""),
                    }
                )
            if offset is None:
                break

        self.bm25.index([f"{c.get('law', '')} Madde {c.get('article_no', '')} {c['text']}" for c in self.corpus])
        os.makedirs(os.path.dirname(self.cfg.CACHE_PATH), exist_ok=True)
        with open(self.cfg.CACHE_PATH, "wb") as f:
            pickle.dump({"corpus": self.corpus, "bm25": self.bm25}, f)

    def retrieve(self, query: str, k: int = None) -> List[Dict]:
        k = k or self.cfg.FINAL_K
        query = query.replace("\u0307", "")
        query = _clean_query(query)  # Gürültü prefix/suffix temizleme

        # Sorgu Genişletme (Sadece BM25 için değil, tüm süreci besler)
        expanded_q = expand_query(query)

        kanun, madde, source_intent = (
            detect_kanun(query),
            extract_madde(query),
            detect_source_intent(query),
        )

        # --- DİNAMİK ALPHA (GÜNCELLENDİ) ---
        query_len = len(query.split())
        if madde:
            alpha = self.cfg.ALPHA_EXACT
        elif query_len > 10:  # Uzun cümlelerde Mürşit'e daha çok güven
            alpha = self.cfg.ALPHA_SEMANTIC
        else:
            alpha = self.cfg.ALPHA_DEFAULT

        # 1. Dense Search (Orijinal query ile anlamsal arama)
        vec = self.embedder.encode_single(query)
        dense_results = self._query_qdrant_with_retry(
            COLLECTION_NAME, query=vec, limit=self.cfg.TOP_K_DENSE, with_payload=True
        ).points
        dense_hits = [{**p.payload, "dense_score": p.score} for p in dense_results]

        # Site corpus araması (sadece dense)
        site_hits = []
        try:
            site_results = self._query_qdrant_with_retry(
                "site_corpus", query=vec, limit=1000, with_payload=True
            ).points
            
            # Basit anahtar kelime destekli skorlama (BM25 yedeği)
            import string
            query_words = set(query.lower().translate(str.maketrans('', '', string.punctuation)).split())
            for p in site_results:
                text_lower = p.payload.get("text", "").lower()
                keyword_matches = sum(1 for w in query_words if w in text_lower and len(w) > 2)
                # Eşleşen kelime başına +0.2 puan veriyoruz ki dense score'u düşük İngilizce metinler üste çıksın
                p.score += (keyword_matches * 0.2)
                
            site_results.sort(key=lambda p: -p.score)
            
            # Site belgelerini daha makul bir başlangıç skoruyla ekleyelim ki orijinal kanunları ezmesin
            site_hits = [
                {**p.payload, "skor": p.score + 0.5, "source": "site_document"} 
                for p in site_results[:self.cfg.FINAL_K] if p.score > 0.10
            ]
        except Exception:
            pass

        # 2. BM25 Search (Genişletilmiş query ile anahtar kelime araması)
        bm25_hits_raw = self.bm25.score(expanded_q, n=self.cfg.TOP_K_BM25)
        bm25_hits = [{**self.corpus[idx], "bm25_score": s} for idx, s in bm25_hits_raw]

        # 3. Hybrid Fusion
        fused = hybrid_fuse(dense_hits, bm25_hits, alpha)

        # 4. Boosting
        for c in fused:
            # article_no'yu her ihtimale karşı tekrar temizleyip string yapıyoruz
            res_art = normalize_article(c.get("article_no", ""))

            # Madde numarası tam eşleşiyorsa
            if madde and str(res_art) == str(madde):
                # DEBUG: Gerçekten buraya giriyor mu görmek için terminale yazdırabilirsin
                # print(f"DEBUG: {madde} maddesi yakalandı, boost uygulanıyor.")
                c["skor"] *= self.cfg.BOOST_MADDE

            # Diğer boostlar...
            if source_intent == "yargitay" and c.get("source") == "yargitay":
                c["skor"] *= self.cfg.BOOST_ICTIHAT

            if kanun and str(c.get("law", "")).upper() == str(kanun).upper():
                c["skor"] *= self.cfg.BOOST_KANUN

        # Skorlara göre tekrar sırala
        fused.extend(site_hits)
        fused.sort(key=lambda x: -x.get("skor", 0))

        # ── Hedefli Madde Boost ──────────────────────────────────────────────
        # Belirli konu ifadeleri saptanırsa, spesifik hedef maddeye 25x boost
        # uygular. Bu sayede doğru madde top-10'a giremese bile üst sıraya çıkar.
        q_lower_clean = query.lower()
        for keywords, (target_law, target_art) in _KEYWORD_TO_ARTICLE:
            if all(kw in q_lower_clean for kw in keywords):
                boosted = False
                for c in fused:
                    if (normalize_article(c.get("article_no", "")) == target_art and
                            str(c.get("law", "")).upper() == target_law):
                        c["skor"] *= 25.0
                        boosted = True
                if boosted:
                    fused.sort(key=lambda x: -x.get("skor", 0))
                break
        # ─────────────────────────────────────────────────────────────────────

        return self._filter_results(fused, k)

    def _filter_results(self, results: List[Dict], k: int) -> List[Dict]:
        seen_art = defaultdict(int)  # mevzuat maddeleri için
        seen_dec = defaultdict(int)  # içtihat kararları için
        filtered = []

        for r in results:
            if r["source"] == "mevzuat":
                key = f"{r['law']}_{r['article_no']}"
                # Aynı maddeden en fazla 1 kez al (config'te MAX_SAME_ARTICLE=1 olmalı)
                if seen_art[key] >= self.cfg.MAX_SAME_ARTICLE:
                    continue
                seen_art[key] += 1
            elif r["source"] == "yargitay":
                key = r["decision_id"]
                # Aynı karardan sadece 1 kez al (diversity artırıldı)
                if seen_dec[key] >= 1:
                    continue
                seen_dec[key] += 1
            elif r.get("source") == "site_document":
                # Site belgeleri için ekstra kısıtlama koymayabiliriz
                pass
            filtered.append(r)
            if len(filtered) >= k:
                break
        return filtered


if __name__ == "__main__":
    r = LegalRetriever()
    # İçtihat beklediğimiz bir sorgu
    test_sorgu = "Kira bedeli ödenmezse tahliye süreci ve Yargıtay kararları"

    print(f"\n🔍 TEST SORGUSU: {test_sorgu}")
    print("-" * 80)

    sonuclar = r.retrieve(test_sorgu, k=5)

    for i, s in enumerate(sonuclar, 1):
        kaynak = s.get("source", "Bilinmiyor").upper()
        madde = s.get("article_no", "-")
        karar_id = s.get("decision_id", "-")
        skor = s.get("skor", 0)

        print(f"{i}. [{kaynak}] | Skor: {skor:.4f}")
        if kaynak == "YARGITAY":
            print(f"   ⚖️ KARAR ID: {karar_id}")
        else:
            print(f"   📜 MADDE: {s.get('law')} m.{madde}")

        print(f"   📝 METİN: {s.get('text')[:150]}...")
        print("-" * 80)
