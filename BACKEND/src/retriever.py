import json
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
from retrieval.reranker import CrossEncoderReranker, RerankerConfig

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
    MAX_SAME_ARTICLE: int = 1          # v2.1: 2→1, aynı maddeden tek chunk yeter
    ALPHA_DEFAULT: float = 0.68
    ALPHA_EXACT: float = 0.45
    ALPHA_SEMANTIC: float = 0.72
    BOOST_MADDE: float = 35.0
    BOOST_ICTIHAT: float = 6.0
    BOOST_KANUN: float = 6.0
    HYDE_WEIGHT: float = 0.80
    CACHE_PATH: str = os.path.join(_SRC_DIR, "data", "retriever_cache.pkl")
    ENRICHED_PATH: str = os.path.join(_SRC_DIR, "data", "chunk_corpus_enriched.json")
    # v2.1 — Kanun-İçi Density-Aware Fusion
    ALPHA_SAME_LAW_BOOST: float = 0.10   # Dominant kanundan çok aday gelince dense ek artışı
    SAME_LAW_DENSE_THRESHOLD: int = 40   # Bu sayının üzerinde aday → alpha boost aktif
    # v2.1 — Diversity Penalty (Cross-Encoder kapalıyken aktif)
    DIVERSITY_PENALTY: float = 0.05      # Her ek aynı-kanun adayı için %5 düşüş (max %30)
    # v2.2 — Cross-Encoder Reranker
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"              # Öncelikli model (çok dilli)
    RERANKER_FALLBACK: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # Yedek model
    RERANKER_TOP_K: int = 30            # Rerank edilecek aday sayısı (asla tüm corpus değil)
    RERANKER_MAX_DOC_CHARS: int = 512   # Doküman metninin kesileceği maksimum karakter
    RERANKER_DEVICE: str = "cpu"        # Çalışma cihazı
    # v2.3 — Minimum Relevance Score Filter
    # Hybrid (normalize) skoru bu eşiğin altındaki chunk'lar final listeye girmez.
    # Env var MIN_RELEVANCE_SCORE ile override edilebilir.
    MIN_RELEVANCE_SCORE: float = float(os.environ.get("MIN_RELEVANCE_SCORE", "0.15"))


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


def _apply_diversity_penalty(
    fused: List[Dict], penalty: float = 0.05
) -> List[Dict]:
    """
    v2.1 — Kanun-İçi Diversity Penalty
    ====================================
    Fusion sonrası aynı kanundan gelen ardışık maddeler için kademeli ceza.

    Mantık:
      - Her kanunun ilk adayı tam skor alır (ceza yok).
      - Aynı kanundan 2. aday: skor * (1 - 1*penalty)
      - Aynı kanundan 3. aday: skor * (1 - 2*penalty)
      - ... maksimum %30 ceza (penalty*6 üst sınır)

    Hedef:
      - Doğru maddeyi cezalandırmadan yanlış komşu maddeleri aşağı itmek.
      - _KEYWORD_TO_ARTICLE boost SONRASINDA çağrıl — kural tabanlı boost
        doğru maddeyi zaten öne çekmiş olur, penalty sadece ikinci-üçüncü
        adaylara dokunur.

    Parametre:
      penalty: Her ek aynı-kanun adayı için ek indirim oranı (varsayılan 0.05 = %5).
    """
    law_seen_count: Dict[str, int] = defaultdict(int)

    for c in fused:
        law = c.get("law", "")
        if not law or c.get("source") != "mevzuat":
            continue  # Yargıtay ve site_document'a dokunma

        count = law_seen_count[law]
        if count > 0:
            decay = penalty * count
            c["skor"] = c["skor"] * (1.0 - min(decay, 0.30))  # max %30 ceza

        law_seen_count[law] += 1

    fused.sort(key=lambda x: -x.get("skor", 0))
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
    # Genel Hukuk Alanı Eklemeleri
    "borçlar hukuku": "Türk Borçlar Kanunu TBK sözleşme ifa borçlu temerrüdü alacaklı hakları borç ilişkisi fesih dönme tazminat TBK Madde 1 112 117 125",
    "borçlar": "Türk Borçlar Kanunu TBK ifa borçlu alacaklı haklar sözleşme tazminat TBK Madde 1 112 117 125",
    "borç ilişkisi": "Türk Borçlar Kanunu TBK borç ifa talep alacaklı borçlu TBK Madde 1 112",
    "ticaret hukuku": "Türk Ticaret Kanunu TTK tacir şirket anonim limited yönetim kurulu ortak pay senet TTK Madde 1 375 553 595 625",
    "tüketici hukuku": "Tüketicinin Korunması Hakkında Kanun TKHK tüketici hakları ayıplı mal cayma hakkı hakem heyeti TKHK Madde 1 11 48 68",
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
    "anonim şirketlerde müdür": "yönetim kurulu devredilemez görev yetki TTK Madde 375",
    "anonim müdür": "yönetim kurulu devredilemez görev yetki TTK Madde 375",
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
    "hesabında para bulunmayan": "karşılıksız çek hamil tazminat şerh TTK Madde 814",
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
    # Ek kavram genişletmeleri (Genelleşmiş hukuki terimler)
    "azil": "anonim şirket yönetim kurulu üyesi azil gündem TTK Madde 413",
    "yönetim kurulu azil": "anonim şirket yönetim kurulu üyesi azil gündeme bağlılık TTK Madde 413",
    "bana sorulmadan": "sipariş edilmemiş mal hizmet gönderme tüketici bedel talep TKHK Madde 7",
    "adresime gönderilen": "sipariş edilmemiş mal hizmet gönderme tüketici bedel talep TKHK Madde 7",
    "ücretsiz tamir": "garanti belgesi sorumluluk iki yıl düzenleme yükümlülük TKHK Madde 56 57",
    "mahkemeye gitmeden": "tüketici hakem heyeti başvuru parasal sınır bağlayıcı karar TKHK Madde 68 70",
    "evi boşaltacağına": "kiracı tahliye taahhüdü yazılı bildirim TBK Madde 352",
    "tahliye taahhüdü": "kiracı tahliye taahhüdü yazılı bildirim TBK Madde 352",
    "resmi yazılı": "geçerlilik şartı yazılı tüketici kredisi sözleşmesi TKHK Madde 23",
    "ortaklaşa borç": "müteselsil borçluluk alacaklı başvurma dayanışma TBK Madde 161 162",
    "kendi borcunu ödemeyen": "ödemezlik def'i borcun ifası karşılıklı sözleşme TBK Madde 97",
    "emredici kurallara aykırı": "sözleşme özgürlüğü serbestisi emredici hukuk kuralları TBK Madde 26",
    "hata yapan taraf": "yanılma esaslı hata sözleşmenin iptali TBK Madde 30 39",
    "anlaşmaya vardığında": "sözleşmenin kurulması rıza icap kabul irade TBK Madde 1",

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
    # ── TBK — İrade sakatlıkları ─────────────────────────────────────────────
    (("gabin",),                             ("TBK", "28")),
    (("aşırı yararlanma",),                  ("TBK", "28")),
    (("gabın",),                             ("TBK", "28")),
    (("ikrah",),                             ("TBK", "37")),
    (("korkutma", "sözleşme"),               ("TBK", "37")),
    (("irade sakatlığı", "iptal"),           ("TBK", "39")),
    (("iptal", "hak düşürücü"),              ("TBK", "39")),
    # ── TBK — Müteselsil borçluluk ────────────────────────────────────────────
    (("müteselsil", "alacaklı", "başvur"),   ("TBK", "161")),
    (("müteselsil borçlu",),                 ("TBK", "161")),
    (("müteselsil", "iç ilişki"),            ("TBK", "162")),
    (("müteselsil", "rücu"),                 ("TBK", "167")),
    # ── TBK — Borçlu temerrüdü ────────────────────────────────────────────────
    (("borçlu", "temerrüt", "alacaklı", "hak"), ("TBK", "117")),
    (("temerrüde düş", "alacaklı"),          ("TBK", "117")),
    (("temerrüt", "munzam zarar"),           ("TBK", "119")),
    (("temerrüt", "ispat"),                  ("TBK", "119")),
    (("temerrüt", "faiz", "talep"),          ("TBK", "117")),
    # ── TTK — Ek eşleşmeler (eval başarısız sorgular) ─────────────────────────
    (("yönetim kurulu", "devredemez"),        ("TTK", "375")),
    (("yönetim kurulu", "devredile"),         ("TTK", "375")),
    (("yönetim kurulu", "devredebilir"),      ("TTK", "375")),   # morfoloji fix
    (("yönetim kurulu", "devredilebilir"),    ("TTK", "375")),   # morfoloji fix
    (("yönetim kurulu", "gündeme"),           ("TTK", "413")),
    (("üyenin azli",),                       ("TTK", "413")),
    (("azil", "gündem"),                     ("TTK", "413")),
    (("azli", "gündem"),                     ("TTK", "413")),   # morfoloji fix
    (("azli", "gündemde"),                   ("TTK", "413")),   # morfoloji fix
    (("azl", "yönetim kurulu", "üye"),       ("TTK", "413")),   # morfoloji fix
    (("limited", "müdürlük", "devir"),       ("TTK", "625")),
    (("limited", "müdürlük", "devredilebilir"), ("TTK", "625")), # morfoloji fix
    (("limited", "müdürlük", "devredebilir"), ("TTK", "625")),  # morfoloji fix
    (("limited", "müdür", "ortak"),          ("TTK", "632")),
    (("limited", "ortaklar", "sorumluluk"),  ("TTK", "632")),
    (("karşılıksız çek", "hamil", "tazminat"), ("TTK", "814")),
    (("karşılıksız", "hamil", "tazminat"),   ("TTK", "814")),   # morfoloji fix (çıkan çekte)
    (("karşılıksız", "çek", "hamilin"),       ("TTK", "814")),   # morfoloji fix
    (("hamilin", "tazminat", "çek"),         ("TTK", "814")),   # morfoloji fix
    # ── TKHK m.33 — Ek eşleşmeler ────────────────────────────────────────────
    (("konut finansman", "temerrüt"),        ("TKHK", "33")),
    (("konut finansman", "temerrüde"),       ("TKHK", "33")),   # morfoloji fix
    (("konut finansman", "borcun muaccel"),  ("TKHK", "33")),
    (("tüketici kredi", "taksit", "ödemem"), ("TKHK", "33")),
    (("konut finansman", "düşürsem"),        ("TKHK", "33")),   # morfoloji fix (düşers em)
    (("konut finansmanında", "temerrüt"),    ("TKHK", "33")),   # morfoloji fix
    (("konut finansmanında", "temerrüde"),   ("TKHK", "33")),   # morfoloji fix
    # ── TBK m.37–39 — ikrah / irade sakatlığı süresi ────────────────────────────
    (("ikrah", "iptal", "süre"),             ("TBK", "39")),    # sorgu: ikrah iptali süresi
    (("ikrah", "sözleşme", "süre"),          ("TBK", "39")),
    (("korkutma", "iptal", "süre"),          ("TBK", "39")),
    (("irade sakatlığı", "süre"),           ("TBK", "39")),
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


_dynamic_expand_cache: Dict[str, str] = {}


def expand_query_dynamic(query: str) -> str:
    """
    Kavram Odaklı Dinamik Hukuki Sorgu Anlayıcı ve Genişletici (Concept-Based Query Understanding).
    Sorguyu hukuki olarak analiz eder; doktrinsel kurumları, taraf haklarını ve kavramları
    (ifa, temerrüt, tazminat, seçimlik haklar, def'i, fesih vb.) dinamik olarak üretir.
    KESİNLİKLE sabit madde numarası üretmez veya zorlamaz; retrieval motorunun anlamsal uzayda
    doğru maddeleri kendisinin bulmasını sağlar.
    """
    q_clean = query.strip()
    if len(q_clean.split()) < 2:
        return expand_query(query)

    cache_key = q_clean.lower()
    if cache_key in _dynamic_expand_cache:
        return _dynamic_expand_cache[cache_key]

    base_expanded = expand_query(query)

    try:
        from groq import Groq
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            return base_expanded

        g_client = Groq(api_key=groq_key)
        model = os.getenv("GROQ_MODEL", "groq/compound-mini")

        prompt = (
            "Sen bir Türk Hukuku uzmanısın. Kullanıcının sorusundaki hukuki uyuşmazlığı ve doktrinsel kavramları analiz et.\n"
            "GÖREV: Soruyla doğrudan ilgili 5-8 temel hukuki kavramı, kurum adını ve taraf haklarını (ör. ifa talebi, temerrüt, tazminat, dönme, def'i hakları, uyarlama vb.) "
            "boşlukla ayırarak tek satırda yaz.\n"
            "KURALLAR:\n"
            "1. KESİNLİKLE madde numarası (m. 112 vb.) YAZMA.\n"
            "2. Kullanıcının sıfatını (alacaklı/borçlu/tüketici) kesin varsayma; olası tüm hukuki kurum ve hak kavramlarını ekle.\n"
            "3. Yorum veya açıklama ekleme.\n\n"
            f"Soru: {query}\n"
            "Hukuki Kavramlar:"
        )

        resp = g_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=70,
        )
        expanded_terms = resp.choices[0].message.content or ""
        expanded_terms = re.sub(r"<think>.*?</think>", "", expanded_terms, flags=re.DOTALL).strip()
        expanded_terms = re.sub(r"[\n\r\"']", " ", expanded_terms).strip()

        if expanded_terms:
            result = f"{query} {expanded_terms}"
        else:
            result = base_expanded

        if len(_dynamic_expand_cache) >= 256:
            _dynamic_expand_cache.pop(next(iter(_dynamic_expand_cache)))
        _dynamic_expand_cache[cache_key] = result
        return result

    except Exception as e:
        log.warning(f"[Dynamic Query Expansion] Fallback devreye girdi: {e}")
        return base_expanded


def detect_kanun_probs(query: str) -> Dict[str, float]:
    """Sorgudan olası kanun dağılımını döndürür.
    Tek kanun yerine ağırlıklı olasılık döndürür — çok kanunlu kavramları
    (temerrüt, zamanaşımı, ayıplı mal) daha iyi ele alır.
    """
    q = query.lower()
    probs: Dict[str, float] = defaultdict(float)

    # ── 1. Doğrudan kanun referansı (kesin) ──────────────────────────────────
    direct = {
        "borçlar hukuku": "TBK", "borclar hukuku": "TBK", "borçlar kanunu": "TBK", "borclar kanunu": "TBK",
        "borçlar": "TBK", "borclar": "TBK", "tbk": "TBK", "6098": "TBK",
        "ticaret hukuku": "TTK", "ticaret kanunu": "TTK", "ttk": "TTK", "6102": "TTK",
        "tüketici hukuku": "TKHK", "tüketici hakları": "TKHK", "tüketici haklari": "TKHK",
        "tüketicinin korunması": "TKHK", "tuketici haklari": "TKHK", "tkhk": "TKHK", "6502": "TKHK",
        "medeni hukuk": "TMK", "medeni kanun": "TMK", "tmk": "TMK", "4721": "TMK",
        "icra iflas": "İİK", "icra iflas kanunu": "İİK", "iik": "İİK", "2004": "İİK",
        "hukuk muhakemeleri": "HMK", "hmk": "HMK", "6100": "HMK",
    }
    # Uzun anahtarlara öncelik vererek kontrol et
    for kw, kanun in sorted(direct.items(), key=lambda x: -len(x[0])):
        if kw in q:
            probs[kanun] += 1.0  # Kesin eşleşme — tam ağırlık
            break  # En spesifik kanun bulundu

    if probs:  # Açık kanun referansı varsa onu kullan
        total = sum(probs.values())
        return {k: v / total for k, v in probs.items()}

    # ── 2. Çok kanunlu kavramlar (olasılıklı dağılım) ─────────────────────────
    # Temerrüt: TBK genel hüküm, TKHK tüketici sözleşmesinde özel
    if any(kw in q for kw in ["temerrüt", "temerrüd", "temerrüde", "temerrütten"]):
        probs["TBK"] += 0.55
        probs["TKHK"] += 0.35
        probs["TTK"] += 0.10

    # Zamanaşımı: TBK genel, ama TTK/HMK özel süreler
    if "zamanaşımı" in q:
        probs["TBK"] += 0.55
        probs["TTK"] += 0.25
        probs["HMK"] += 0.10
        probs["İİK"] += 0.10

    # Ayıplı mal: TKHK tüketici, TBK genel
    if "ayıplı" in q:
        if "tüketici" in q:
            probs["TKHK"] += 0.80
            probs["TBK"]  += 0.20
        else:
            probs["TBK"]  += 0.55
            probs["TKHK"] += 0.45

    # Kira: TBK genel, İİK icra yolu
    if any(kw in q for kw in ["kira", "kiracı", "tahliye"]):
        probs["TBK"] += 0.75
        probs["İİK"] += 0.25

    # Tazminat: TBK haksız fiil, İş K., TKHK
    if "tazminat" in q and not probs:
        probs["TBK"] += 0.60
        probs["TKHK"] += 0.25
        probs["TTK"] += 0.15

    # ── 3. Tek kanunlu kavramlar ──────────────────────────────────────────────
    tkhk_signals = [
        "tüketici", "mesafeli", "cayma hakkı", "garanti belgesi",
        "abonelik", "devre tatil", "paket tur", "hakem heyeti",
        "tüketici kredisi", "konut finansmanı", "sipariş edilmey",
        "işyeri dışı", "haksız şart",
    ]
    for kw in tkhk_signals:
        if kw in q:
            probs["TKHK"] += 0.80
            break

    ttk_signals = [
        "anonim şirket", "limited şirket", "haksız rekabet", "genel kurul",
        "yönetim kurulu", "ticaret sicil", "nama yazılı", "hamiline yazılı",
        "pay devri", "ticari defter", "bono", "poliçe", "kambiyo",
        "ibraz", "tacir", "ticari işletme", "çek",
    ]
    for kw in ttk_signals:
        if kw in q:
            probs["TTK"] += 0.80
            break

    tbk_signals = [
        "haksız fiil", "borçlu", "alacaklı", "vekalet", "vekâlet", "kefalet",
        "eser sözleşme", "satım", "sebepsiz zenginleş", "alacağın devri",
        "temlik", "müteselsil", "sözleşme", "borç", "işçi",
        "gabin", "aşırı yararlanma", "ikrah", "korkutma",
        "irade sakatlığı", "munzam zarar",
    ]
    for kw in tbk_signals:
        if kw in q:
            probs["TBK"] += 0.80
            break

    if not probs:
        return {}  # Kanun belirlenemedi — filtresiz arama

    total = sum(probs.values())
    return {k: v / total for k, v in probs.items()}


def detect_kanun(query: str) -> Optional[str]:
    """Geriye dönük uyumluluk için — en yüksek olasılıklı kanunu döndürür."""
    probs = detect_kanun_probs(query)
    if not probs:
        return None
    return max(probs, key=probs.get)


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
# LLM RERANKER
# ═══════════════════════════════════════════════════════════════════════════════


def _llm_rerank(query: str, chunks: List[Dict], top_k: int = 10) -> List[Dict]:
    """Groq API ile top-N chunk'ı içerik bazlı yeniden sıralar.
    
    Çalışma: Sorgu + chunk metni çiftleri LLM'e verilir, LLM 0–10 arası
    alaka puanı üretir, puana göre yeniden sıralanır.
    
    Etkinleştirme: ENABLE_LLM_RERANK=true (env. var.)
    """
    if not chunks:
        return chunks

    try:
        from groq import Groq
        groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    except Exception as e:
        log.warning(f"[LLM Rerank] Groq bağlantısı başarısız: {e}. Orijinal sıralama korunuyor.")
        return chunks

    candidates = chunks[:20]  # max 20 chunk re-rank edilir
    chunk_lines = []
    for i, c in enumerate(candidates):
        law = c.get("law", "")
        art = c.get("article_no", "")
        src = c.get("source", "")
        label = f"{law} m.{art}" if art else src
        snippet = c.get("text", "")[:250].replace("\n", " ")
        chunk_lines.append(f"[{i+1}] {label}: {snippet}")

    chunk_text = "\n".join(chunk_lines)

    prompt = f"""Sen Türk hukuku uzmanı bir yargıçsın.
Aşağıdaki hukuki sorguya hangi metin parçalarının en doğrudan cevap verdiğini belirle.
Her parçaya 0-10 arası alaka puanı ver (10=en ilgili, 0=hiç ilgili değil).

Sorgu: {query}

Metin parçaları:
{chunk_text}

Sadece JSON döndür, başka açıklama yapma:
{{"1": puan, "2": puan, ...}}"""

    try:
        model = os.getenv("GROQ_MODEL", "groq/compound-mini")
        resp = groq_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=200,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        # JSON için temizle (bazen kod bloğu içinde gelebilir)
        raw = re.sub(r"```[\w]*\n?", "", raw).strip()
        scores = json.loads(raw)
        scores = {str(k): float(v) for k, v in scores.items()}
    except Exception as e:
        log.warning(f"[LLM Rerank] Puan parse hatasi: {e}. Orijinal siralama korunuyor.")
        return chunks

    # Puana göre sırala
    def _get_score(item):
        idx = candidates.index(item) + 1
        return scores.get(str(idx), 5.0)

    reranked = sorted(candidates, key=_get_score, reverse=True)
    # Re-rank edilmemiş chunk'ları arkaya ekle
    remaining = [c for c in chunks[20:]]
    log.info(f"[LLM Rerank] {len(candidates)} chunk yeniden sıralandı, top-{top_k} seçildi.")
    return reranked[:top_k] + remaining


# ═══════════════════════════════════════════════════════════════════════════════
# TKHK HEDEFLİ GROUNDED LLM RERANKER
# ═══════════════════════════════════════════════════════════════════════════════

TKHK_SYSTEM_PROMPT = """Sen bir Türk Tüketici Hukuku (TKHK) uzmanı asistansın. Görevin, kullanıcının sorusuna en uygun kanun maddesini, SANA VERİLEN ADAY MADDE METİNLERİ ARASINDAN seçip sıralamaktır.

KESİN KURALLAR:
1. SADECE aşağıda verilen aday madde metinlerini kullan. Listede olmayan madde numarası UYDURMA.
2. Kararını verirken genel hukuk bilgini kullanabilirsin ANCAK son kararın mutlaka önündeki madde METNİNE dayanmalı.
3. TKHK'da en sık karışan madde grupları: mesafeli satış (m.48) vs devre tatil (m.50), cayma hakkı vs garanti hükümleri — bu maddeler arasındaki İNCE farkı açıkça belirt.
4. Her aday için gerekçeni madde metninden dayanarak, max 2 cümlede yaz.

ÇIKTI FORMATI (sadece geçerli JSON):
{"ranking": [{"candidate_id": "...", "rank": 1, "gerekce": "..."}]}"""


def should_apply_reranker(query_category: Optional[str], top_candidates: List[Dict]) -> bool:
    """
    Sadece TKHK sorgularında reranker'ı tetikler. Diğer kategorilerde 
    (TBK, TTK, yargitay_intent) mevcut fusion sıralaması korunur — 
    bu kategorilerde fine-tuning zaten yeterli discrimination sağlıyor.

    Güvenlik & Maliyet Notu:
    ------------------------
    Reranker sadece TKHK sorgularında tetiklendiği için toplam sorgu hacminin
    küçük bir yüzdesinde (~%24 held-out'ta, prod'da muhtemelen ~%20-25) ek LLM
    çağrısı olacak. Groq maliyeti/latency'si bu oranla çarpılınca ortalama
    sistem gecikmesine sadece ~250-300ms ekler. Bu durum, genel-amaçlı cross-encoder'ın
    8.4s'lik gecikme felaketine kıyasla üretime son derece uygundur.
    """
    if query_category == "semantic_tkhk":
        return True

    if top_candidates and len(top_candidates) > 0:
        tkhk_count = sum(
            1 for c in top_candidates 
            if str(c.get("law", "")).upper() == "TKHK"
        )
        tkhk_ratio = tkhk_count / len(top_candidates)
        if tkhk_ratio >= 0.5:
            return True

    return False


def rerank_tkhk_candidates(query: str, candidates: List[Dict], timeout: float = 3.0) -> List[Dict]:
    """
    Top-5 TKHK aday maddesini Groq / Llama 3.3 üzerinden grounded ranking kullanarak yeniden sıralar.

    Sorumluluklar:
      - Sadece verilen top-5 adayı tam madde metniyle LLM'e gönderir.
      - 3.0 saniyelik sert zaman aşımı (TimeoutError koruması).
      - candidate_id doğrulaması (ValidationError): Dönen ID'ler gönderilen listede yoksa
        reranker sonucunu reddeder ve fusion sıralamasına geri döner (fallback).
    """
    import concurrent.futures

    if not candidates:
        return candidates

    top5 = candidates[:5]
    valid_ids = {str(c.get("chunk_id", i)) for i, c in enumerate(top5)}
    candidate_map = {str(c.get("chunk_id", i)): c for i, c in enumerate(top5)}

    candidate_blocks = []
    for i, c in enumerate(top5):
        cid = str(c.get("chunk_id", i))
        law = c.get("law", "TKHK")
        art = c.get("article_no", "")
        text = c.get("text", "")[:600].replace("\n", " ")
        candidate_blocks.append(
            f"Candidate ID: {cid}\nKanun & Madde: {law} m.{art}\nMetin: {text}"
        )

    user_msg = (
        f"Kullanıcı Sorgusu: {query}\n\n"
        "Aday Maddeler:\n"
        + "\n---\n".join(candidate_blocks)
        + "\n\nLütfen yukarıdaki KESİN KURALLARA ve JSON ÇIKTI FORMATINA uygun yanıt ver."
    )

    def _call_llm() -> List[Dict]:
        from groq import Groq
        model = os.getenv("GROQ_MODEL", "groq/compound-mini")
        resp = groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": TKHK_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.0,
            max_tokens=400,
        )
        content = resp.choices[0].message.content.strip()
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        content = re.sub(r"```[\w]*\n?", "", content).strip()
        data = json.loads(content)
        ranking = data.get("ranking", [])
        if not ranking:
            raise ValueError("LLM boş veya geçersiz ranking yapısı döndürdü")

        returned_ids = {str(r.get("candidate_id")) for r in ranking if "candidate_id" in r}
        if not returned_ids.issubset(valid_ids):
            unrecognized = returned_ids - valid_ids
            raise ValueError(f"ValidationError: Tanımsız candidate_id tespit edildi: {unrecognized}")

        ordered = []
        seen = set()
        for r in sorted(ranking, key=lambda x: x.get("rank", 99)):
            cid = str(r.get("candidate_id"))
            if cid in candidate_map and cid not in seen:
                cand = candidate_map[cid].copy()
                cand["tkhk_gerekce"] = r.get("gerekce", "")
                ordered.append(cand)
                seen.add(cid)

        for c in top5:
            cid = str(c.get("chunk_id", ""))
            if cid not in seen:
                ordered.append(c)

        return ordered

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_call_llm)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Reranker 3.0s zaman aşımına uğradı (timeout={timeout}s)")



_cross_encoder_model = None
_cross_encoder_model_name = None

# v2.1: Fallback zinciri — daha küçük model önce denenir
_CROSS_ENCODER_MODELS = [
    "cross-encoder/ms-marco-MiniLM-L-6-v2",   # ~90MB, hızlı, İngilizce ağırlıklı
    "BAAI/bge-reranker-base",                  # ~270MB, daha iyi ama daha fazla RAM
]


def _cross_encoder_rerank(query: str, chunks: List[Dict], top_k: int = 10) -> List[Dict]:
    """
    v2.1 — Cross-Encoder Reranker (Fallback Zincirli)
    ===================================================
    Daha hafif modelden başlayarak RAM kısıtına göre fallback yapar.

    Pair formatı: query + "Kanun {law} Madde {art}: {text[:350]}"
    Law/article bilgisi cross-encoder'ın kanun ayrımını daha iyi yapmasını sağlar.

    Model önceliği:
      1. cross-encoder/ms-marco-MiniLM-L-6-v2  (~90MB, hızlı)
      2. BAAI/bge-reranker-base                 (~270MB, yedek)

    RAM kısıtı / OS Error 1455 durumunda orijinal sıralama korunur.
    """
    global _cross_encoder_model, _cross_encoder_model_name
    if not chunks:
        return chunks

    # Model yükle (yoksa fallback zinciriyle dene)
    if _cross_encoder_model is None:
        from sentence_transformers import CrossEncoder
        for model_name in _CROSS_ENCODER_MODELS:
            try:
                log.info(f"[Cross Rerank] Model yukleniyor: {model_name}...")
                _cross_encoder_model = CrossEncoder(model_name, device="cpu")
                _cross_encoder_model_name = model_name
                log.info(f"[Cross Rerank] Yuklendi: {model_name}")
                break
            except MemoryError:
                log.warning(f"[Cross Rerank] {model_name} → MemoryError, sonraki deneniyor...")
            except Exception as e:
                log.warning(f"[Cross Rerank] {model_name} yuklenemedi: {e}, sonraki deneniyor...")

        if _cross_encoder_model is None:
            log.warning("[Cross Rerank] Hicbir model yuklenemedi. Orijinal siralama korunuyor.")
            return chunks

    try:
        candidates = chunks[:20]

        # v2.1: Law + article bilgisini pair'e ekle
        def _make_doc(c: Dict) -> str:
            law = c.get("law", "")
            art = c.get("article_no", "")
            text = c.get("text", "")[:350]
            if law and art:
                return f"Kanun {law} Madde {art}: {text}"
            elif law:
                return f"Kanun {law}: {text}"
            return text

        pairs = [(query, _make_doc(c)) for c in candidates]
        scores = _cross_encoder_model.predict(pairs)

        for c, score in zip(candidates, scores):
            c["cross_score"] = float(score)

        reranked = sorted(candidates, key=lambda x: -x.get("cross_score", 0.0))
        remaining = chunks[20:]
        log.info(
            f"[Cross Rerank] {len(candidates)} chunk yeniden siralandi "
            f"({_cross_encoder_model_name}), top-{top_k} secildi."
        )
        return reranked[:top_k] + remaining

    except Exception as e:
        log.warning(f"[Cross Rerank] Rerank sirasinda hata: {e}. Orijinal siralama korunuyor.")
        # Model bozuksa bir sonraki çağrıda yeniden yükleme denesin
        if "1455" in str(e) or "memory" in str(e).lower():
            _cross_encoder_model = None
            _cross_encoder_model_name = None
        return chunks



# ═══════════════════════════════════════════════════════════════════════════════
# HyDE — HYPOTHETICAL DOCUMENT EMBEDDING
# ═══════════════════════════════════════════════════════════════════════════════


def _hyde_generate(query: str) -> Optional[str]:
    """HyDE: Groq ile sorguya uygun hipotetik Türk hukuku belgesi üretir.

    Çalışma mantığı:
      - Kullanıcı sorgusunu doğrudan embed etmek yerine, LLM'e
        'Bu soruya cevap veren bir kanun maddesi nasıl olur?' sorusu sorulur.
      - LLM'nin ürettiği hipotetik belge, gerçek kanun metni diliyle yazılır.
      - Bu metnin embedding'i, gerçek kanun chunk'larına çok daha yakındır.
      - Özellikle corpus'ta var olan ama sorgu embedding'i yakalayamayan
        chunk'lar için kritik önem taşır (ikrah, gabin gibi nadir terimler).

    Etkinleştirme: ENABLE_HYDE=true (env. var.)
    """
    try:
        from groq import Groq
        client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
        prompt = (
            "Türk hukuku uzmanı olarak, aşağıdaki hukuki soruya doğrudan cevap veren "
            "bir kanun maddesi metni yaz. Gerçek Türk kanun dilini kullan, madde numarası "
            "ve hukuki terimleri ekle. En fazla 150 kelime, sadece kanun maddesi metni döndür.\n\n"
            f"Soru: {query}\n\nKanun maddesi:"
        )
        model = os.getenv("GROQ_MODEL", "groq/compound-mini")
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=250,
        )
        hyp = resp.choices[0].message.content.strip()
        hyp = re.sub(r"<think>.*?</think>", "", hyp, flags=re.DOTALL).strip()
        log.info(f"[HyDE] Üretilen belge: {hyp[:120]}...")
        return hyp
    except Exception as e:
        log.warning(f"[HyDE] Üretim başarısız: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# LEGAL RETRIEVER SINIFI
# ═══════════════════════════════════════════════════════════════════════════════


class LegalRetriever:
    def __init__(
        self,
        quantize: bool = False,
        reindex: bool = False,
        model_path: str = None,
        collection_name: str = None,
    ):
        """
        Parametreler:
            quantize        : int8 dynamic quantization
            reindex         : Qdrant cache'i yoksay, yeniden oluştur
            model_path      : Fine-tuned model klasör yolu (None → varsayılan Mursit-Base-TR)
            collection_name : Qdrant koleksiyonu (None → 'lawagent_mursit')
                              Fine-tuned eval için 'lawagent_mursit_ft' kullanın.
        """
        self.cfg = CFG()
        # Fine-tuned eval için koleksiyon override
        self._collection_name = collection_name if collection_name else COLLECTION_NAME
        self.embedder = MursitEmbedder(quantize=quantize, model_name_or_path=model_path)
        self.qdrant = get_qdrant_client()
        # Ana mevzuat corpus'u (lawagent_mursit)
        self.bm25 = BM25Plus()
        self.corpus: List[Dict] = []
        # Kullanıcı belgeleri corpus'u (site_corpus)
        self.site_bm25 = BM25Plus()
        self.site_corpus: List[Dict] = []
        # v2.2 — Cross-Encoder Reranker (lazy model yükleme — ilk rerank() çağrısında yüklenir)
        self._reranker = CrossEncoderReranker(
            RerankerConfig(
                model=self.cfg.RERANKER_MODEL,
                fallback_models=[self.cfg.RERANKER_FALLBACK],
                top_k=self.cfg.RERANKER_TOP_K,
                max_doc_chars=self.cfg.RERANKER_MAX_DOC_CHARS,
                device=self.cfg.RERANKER_DEVICE,
            )
        )
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
                self._collection_name, limit=500, offset=offset, with_payload=True
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

        # ── Enriched corpus overlay — BM25 için zenginleştirilmiş metin ──────
        # chunk_corpus_enriched.json varsa, Qdrant chunk_id'leri ile eşleştirip
        # BM25 index'i için metin override eder. Dense vektörler değişmez.
        if os.path.exists(self.cfg.ENRICHED_PATH):
            try:
                with open(self.cfg.ENRICHED_PATH, "r", encoding="utf-8") as f:
                    enriched_chunks = json.load(f)
                # chunk_id → enriched text map'i kur (normalize ile eşleştir)
                enriched_map: Dict[str, str] = {}
                for ec in enriched_chunks:
                    if ec.get("enriched") or ec.get("context_added"):
                        cid = str(ec.get("chunk_id", ""))
                        if cid:
                            enriched_map[cid] = ec["text"]
                # Corpus'a uygula
                applied = 0
                for c in self.corpus:
                    if c["chunk_id"] in enriched_map:
                        c["bm25_text"] = enriched_map[c["chunk_id"]]  # ayrı alan
                        applied += 1
                log.info(f"[Enriched] {applied} chunk'a zenginleştirilmiş metin uygulandı.")
            except Exception as _ee:
                log.warning(f"[Enriched] Yuklenemedi: {_ee}")
        # ────────────────────────────────────────────────────────────────

        # BM25 index: enriched text varsa onu kullan, yoksa orijinal text
        self.bm25.index([
            f"{c.get('law', '')} Madde {c.get('article_no', '')} {c.get('bm25_text', c['text'])}"
            for c in self.corpus
        ])


        # ── site_corpus BM25 indexi ─────────────────────────────────────────
        try:
            collections = [col.name for col in self.qdrant.get_collections().collections]
            if "site_corpus" in collections:
                log.info("site_corpus Qdrant'tan çekiliyor...")
                s_offset = None
                while True:
                    s_res, s_offset = self.qdrant.scroll(
                        "site_corpus", limit=500, offset=s_offset, with_payload=True
                    )
                    for p in s_res:
                        pay = p.payload
                        self.site_corpus.append(
                            {
                                "chunk_id": str(p.id),
                                "text": pay.get("text", ""),
                                "source": "site_document",
                                "filename": pay.get("filename", ""),
                                "page": pay.get("page"),
                            }
                        )
                    if s_offset is None:
                        break
                if self.site_corpus:
                    self.site_bm25.index([c["text"] for c in self.site_corpus])
                    log.info(f"[site_corpus] {len(self.site_corpus)} chunk BM25 indexlendi.")
        except Exception as _se:
            log.warning(f"site_corpus BM25 indexlenemedi: {_se}")
        # ────────────────────────────────────────────────────────────────────

        os.makedirs(os.path.dirname(self.cfg.CACHE_PATH), exist_ok=True)
        with open(self.cfg.CACHE_PATH, "wb") as f:
            pickle.dump({"corpus": self.corpus, "bm25": self.bm25}, f)

    def retrieve(self, query: str, k: int = None, query_category: Optional[str] = None) -> List[Dict]:  # noqa: C901
        import time as _time
        _t_total_start = _time.perf_counter()

        k = k or self.cfg.FINAL_K
        query = query.replace("\u0307", "")
        query = _clean_query(query)  # Gürültü prefix/suffix temizleme

        # Sorgu Genişletme (LLM tabanlı dinamik hukuki kavram sentezi)
        expanded_q = expand_query_dynamic(query)

        kanun, madde, source_intent = (
            detect_kanun(query),
            extract_madde(query),
            detect_source_intent(query),
        )

        # --- DİNAMİK ALPHA v2.1 ---
        query_len = len(query.split())
        if madde:
            alpha = self.cfg.ALPHA_EXACT
        elif query_len > 10:  # Uzun cümlelerde Mürşit'e daha çok güven
            alpha = self.cfg.ALPHA_SEMANTIC
        else:
            alpha = self.cfg.ALPHA_DEFAULT

        # 1. Dense Search (Kavramsal olarak zenginleştirilmiş sorgu ile anlamsal arama)
        _t_retrieval_start = _time.perf_counter()
        dense_query = expanded_q if expanded_q else query
        vec = self.embedder.encode_single(dense_query)
        dense_results = self._query_qdrant_with_retry(
            self._collection_name, query=vec, limit=self.cfg.TOP_K_DENSE, with_payload=True
        ).points
        dense_hits = [{**p.payload, "dense_score": p.score, "chunk_id": str(p.id)}
                      for p in dense_results]

        # 1b. HyDE — Hypothetical Document Embedding (opsiyonel)
        # Sorgu embedding'inin yakalayamadığı chunk'ları bulmak için:
        # LLM → hipotetik kanun maddesi üret → embed → Qdrant ara → dense_hits ile birleştir
        if not madde and os.environ.get("ENABLE_HYDE", "false").lower() == "true":
            hyp_doc = _hyde_generate(query)
            if hyp_doc:
                hyde_vec = self.embedder.encode_single(hyp_doc)
                hyde_results = self._query_qdrant_with_retry(
                    self._collection_name, query=hyde_vec,
                    limit=self.cfg.TOP_K_DENSE // 2, with_payload=True
                ).points
                # Mevcut chunk_id'leri indekse al (hızlı arama)
                existing_ids = {h["chunk_id"]: i for i, h in enumerate(dense_hits)}
                for p in hyde_results:
                    cid = str(p.id)
                    hyde_score = p.score * self.cfg.HYDE_WEIGHT
                    if cid in existing_ids:
                        # Zaten var → skoru güçlendir (max al)
                        idx = existing_ids[cid]
                        dense_hits[idx]["dense_score"] = max(
                            dense_hits[idx]["dense_score"], hyde_score
                        )
                    else:
                        # HyDE'ın bulduğu yeni chunk — dense_hits'e ekle
                        dense_hits.append({
                            **p.payload,
                            "dense_score": hyde_score,
                            "chunk_id": cid,
                        })
                log.info(f"[HyDE] {len(hyde_results)} sonuç dense_hits ile birleştirildi.")

        # Site corpus araması: dense + BM25 hybrid (kelime hack kaldırıldı)
        site_hits: List[Dict] = []
        try:
            site_results = self._query_qdrant_with_retry(
                "site_corpus", query=vec, limit=min(200, max(50, self.cfg.TOP_K_DENSE)), with_payload=True
            ).points
            site_dense_hits = [
                {**p.payload, "chunk_id": str(p.id), "dense_score": p.score}
                for p in site_results
            ]

            # Gerçek BM25 site_corpus üzerinde
            if self.site_corpus:
                site_bm25_raw = self.site_bm25.score(expanded_q, n=self.cfg.TOP_K_BM25)
                site_bm25_hits = [
                    {**self.site_corpus[idx], "bm25_score": s}
                    for idx, s in site_bm25_raw
                ]
                site_fused = hybrid_fuse(site_dense_hits, site_bm25_hits, alpha=self.cfg.ALPHA_DEFAULT)
            else:
                # site_corpus henüz BM25 indexli değilse sadece dense kullan
                d_norms = _minmax_normalize([h["dense_score"] for h in site_dense_hits])
                site_fused = [
                    {**h, "skor": round(dn, 6)}
                    for h, dn in zip(site_dense_hits, d_norms)
                ]

            site_hits = [
                {**c, "source": "site_document"}
                for c in site_fused[:self.cfg.FINAL_K]
                if c.get("skor", 0) > 0.05
            ]
        except Exception:
            pass

        # 2. BM25 Search (Genişletilmiş query ile anahtar kelime araması)
        bm25_hits_raw = self.bm25.score(expanded_q, n=self.cfg.TOP_K_BM25)
        bm25_hits = [{**self.corpus[idx], "bm25_score": s} for idx, s in bm25_hits_raw]

        # v2.1 — Kanun-İçi Density-Aware Alpha Ayarı
        # Dense sonuçlardaki dominant kanunu tespit et.
        # Eğer aynı kanundan çok sayıda (>THRESHOLD) aday geliyorsa,
        # BM25 keyword taşması riski artar → Dense ağırlığını artır.
        from collections import Counter
        law_counts_dense = Counter(
            h.get("law", "") for h in dense_hits[:60] if h.get("law")
        )
        if law_counts_dense and not madde:
            top_law_name, top_law_count = law_counts_dense.most_common(1)[0]
            kanun_probs_pre = detect_kanun_probs(query)
            if (top_law_count >= self.cfg.SAME_LAW_DENSE_THRESHOLD
                    and kanun_probs_pre.get(top_law_name, 0) > 0.5):
                alpha = min(alpha + self.cfg.ALPHA_SAME_LAW_BOOST, 0.85)
                log.debug(
                    f"[Alpha+] {top_law_name}: {top_law_count} dense aday "
                    f"→ alpha={alpha:.2f} (BM25 taşması riski azaltıldı)"
                )

        # 3. Hybrid Fusion
        fused = hybrid_fuse(dense_hits, bm25_hits, alpha)
        _t_retrieval_elapsed = (_time.perf_counter() - _t_retrieval_start) * 1000

        # 4. Boosting — Probabilistik kanun ağırlıklaması
        kanun_probs = detect_kanun_probs(query)  # {"TBK": 0.6, "TKHK": 0.35, ...}

        for c in fused:
            res_art = normalize_article(c.get("article_no", ""))
            chunk_law = str(c.get("law", "")).upper()

            # Madde numarası tam eşleşmesi (en güçlü sinyal)
            if madde and str(res_art) == str(madde):
                c["skor"] *= self.cfg.BOOST_MADDE

            # İçtihat boost (yargitay intent varsa)
            if source_intent == "yargitay" and c.get("source") == "yargitay":
                c["skor"] *= self.cfg.BOOST_ICTIHAT

            # Probabilistik kanun boost — tek kanun yerine ağırlıklı
            if kanun_probs:
                law_weight = kanun_probs.get(chunk_law, 0.0)
                if law_weight > 0:
                    # Ağırlık orantılı boost: en yüksek ağırlıklı kanun tam boost alır
                    boost = 1.0 + (self.cfg.BOOST_KANUN - 1.0) * law_weight
                    c["skor"] *= boost
            elif kanun and chunk_law == str(kanun).upper():
                # Fallback: eski binary boost
                c["skor"] *= self.cfg.BOOST_KANUN

        # Skorlara göre tekrar sırala
        fused.extend(site_hits)
        fused.sort(key=lambda x: -x.get("skor", 0))

        # ── Hedefli Madde Boost ──────────────────────────────────────────────
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

        # ─────────────────────────────────────────────────────────────────────
        # 5. Reranking / Diversity  (v2.2 & v2.3 Conditional TKHK)
        # ─────────────────────────────────────────────────────────────────────
        # Ortam değişkenlerini oku
        _cross_on = os.environ.get("ENABLE_CROSS_RERANK", "true").lower() == "true"
        _llm_mode = os.environ.get("ENABLE_LLM_RERANK", "false").lower()
        _tkhk_on  = (
            os.environ.get("ENABLE_TKHK_RERANK", "false").lower() == "true" or
            _llm_mode in ("tkhk-only", "tkhk") or
            os.environ.get("RERANKER_MODE", "").lower() in ("tkhk-only", "tkhk")
        )
        _llm_full_on = _llm_mode in ("true", "1", "yes", "all")

        import time as _time
        _t_rerank_start = _time.perf_counter()

        if _cross_on:
            # Cross-Encoder RE-RANKING
            pre_rerank = self._filter_results(fused, self.cfg.RERANKER_TOP_K)
            fused = self._reranker.rerank(query, pre_rerank)
            _rerank_label = f"cross_encoder({self._reranker.model_name or 'loading'})"

        elif _tkhk_on:
            # KOŞULLU GROUNDED LLM RERANKER (Sadece TKHK sorgularına özel)
            fused = _apply_diversity_penalty(fused, penalty=self.cfg.DIVERSITY_PENALTY)
            if should_apply_reranker(query_category, fused[:10]):
                log.info(f"[TKHK Reranker] Sorgu '{query[:40]}' için Grounded LLM Reranker tetiklendi.")
                try:
                    reranked_top5 = rerank_tkhk_candidates(query, fused[:5], timeout=3.0)
                    fused = reranked_top5 + fused[5:]
                    _rerank_label = "tkhk_grounded_llm_reranker"
                except (TimeoutError, ValueError, Exception) as e:
                    log.warning(f"[Reranker Fallback] {e}, fusion sırası korundu")
                    _rerank_label = "tkhk_reranker_fallback_fusion"
            else:
                _rerank_label = "diversity_penalty(no_tkhk_trigger)"

        elif _llm_full_on:
            # Genel LLM RERANKING (tüm sorgularda)
            fused = _apply_diversity_penalty(fused, penalty=self.cfg.DIVERSITY_PENALTY)
            pre_rerank = self._filter_results(fused, max(k * 3, 20))
            fused = _llm_rerank(query, pre_rerank, top_k=k)
            _rerank_label = "llm_rerank"

        else:
            # VARSAYILAN: Sadece Diversity Penalty
            fused = _apply_diversity_penalty(fused, penalty=self.cfg.DIVERSITY_PENALTY)
            _rerank_label = "diversity_penalty"

        _t_rerank_elapsed = (_time.perf_counter() - _t_rerank_start) * 1000
        _t_total_elapsed  = (_time.perf_counter() - _t_total_start)  * 1000

        log.info(
            f"[Retrieve] stage={_rerank_label} | "
            f"retrieval={_t_retrieval_elapsed:.0f}ms | "
            f"reranking={_t_rerank_elapsed:.0f}ms | "
            f"total={_t_total_elapsed:.0f}ms"
        )

        # ── v2.3 — Minimum Relevance Score Filter ──────────────────────────────
        # Cross-encoder veya diversity penalty sonrası skorsuz chunk'ları temizle.
        # Not: cross-encoder skor normalize etmez; skor sıfır veya None chunk'ları hariç tut.
        _min_score = self.cfg.MIN_RELEVANCE_SCORE
        _before = len(fused)
        fused_filtered = []
        for _c in fused:
            _s = _c.get("skor", None)
            # Cross-encoder sonrası 'skor' alanı olmayabilir; cross_score kontrol et
            _cs = _c.get("cross_score", None)
            if _s is not None and _s < _min_score and _cs is None:
                log.debug(
                    f"[MinScore] ELENDI: {_c.get('law','')} m.{_c.get('article_no','')} "
                    f"hybrid_score={_s:.4f} < threshold={_min_score}"
                )
                continue
            fused_filtered.append(_c)

        _removed = _before - len(fused_filtered)
        if _removed > 0:
            log.info(f"[MinScore] {_removed} düşük ilgili chunk elendi (threshold={_min_score})")

        return self._filter_results(fused_filtered, k)


    def _filter_results(self, results: List[Dict], k: int) -> List[Dict]:
        seen_art = defaultdict(int)  # mevzuat maddeleri için
        seen_dec = defaultdict(int)  # içtihat kararları için
        filtered = []
        rejected_log = []

        for r in results:
            if r["source"] == "mevzuat":
                key = f"{r['law']}_{r['article_no']}"
                # Aynı maddeden en fazla 1 kez al (config'te MAX_SAME_ARTICLE=1 olmalı)
                if seen_art[key] >= self.cfg.MAX_SAME_ARTICLE:
                    rejected_log.append(
                        f"{r.get('law','')} m.{r.get('article_no','')} "
                        f"[duplicate, score={r.get('skor', r.get('cross_score', 0)):.4f}]"
                    )
                    continue
                seen_art[key] += 1
            elif r["source"] == "yargitay":
                key = r["decision_id"]
                # Aynı karardan sadece 1 kez al (diversity artırıldı)
                if seen_dec[key] >= 1:
                    rejected_log.append(f"Yargıtay:{key} [duplicate]")
                    continue
                seen_dec[key] += 1
            elif r.get("source") == "site_document":
                # Site belgeleri için ekstra kısıtlama koymayabiliriz
                pass

            log.debug(
                f"[Filter] KABUL: {r.get('source','?')} "
                f"{r.get('law','')} m.{r.get('article_no','')} "
                f"score={r.get('skor', r.get('cross_score', 0)):.4f}"
            )
            filtered.append(r)
            if len(filtered) >= k:
                break

        if rejected_log:
            log.debug(f"[Filter] ELENEN ({len(rejected_log)} adet): {rejected_log[:10]}")

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
