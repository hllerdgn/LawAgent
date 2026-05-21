import math
import os
import sys
import pickle
import re
import logging
import atexit
import warnings
import copyreg
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
    ALPHA_DEFAULT: float = 0.72
    ALPHA_EXACT: float = 0.45
    ALPHA_SEMANTIC: float = 0.80
    BOOST_MADDE: float = 35.0
    BOOST_ICTIHAT: float = 6.0
    BOOST_KANUN: float = 2.5
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
    # TKHK Eklemeleri
    "aidat": "üyelik ücreti yıllık ücret kart çıkarma bedeli",
    "promosyon": "hediye kültürel ürün süreli yayın 21",
    # TTK (En çok hata burada)
    "unvan": "ticaret unvanı tecavüz koruma marka 52",
    "müdür": "limited şirket müdür sorumluluk temsil 623 630 644",
    "bono": "emre yazılı senet kambiyo senedi zamanaşımı temel ilişki 732",
    "çek": "karşılıksızdır ibraz şerh arkasına vurulan 796 814",
    "rüçhan": "yeni pay alma öncelik sermaye artırımı 461",
    "defter": "ticari defter tasdik delil niteliği 64 222",
}


def expand_query(query: str) -> str:
    q = query.lower()
    ekler = []
    for anahtar, deger in _ESANLAMLILAR.items():
        if anahtar in q:
            ekler.append(deger)
    return query + " " + " ".join(ekler) if ekler else query


def detect_kanun(query: str) -> Optional[str]:
    q = query.lower()
    mapping = {
        "tbk": "TBK",
        "ttk": "TTK",
        "tkhk": "TKHK",
        "borçlar": "TBK",
        "ticaret": "TTK",
        "tüketici": "TKHK",
    }
    for k, v in mapping.items():
        if k in q:
            return v
    return None


def extract_madde(query: str) -> Optional[str]:
    # "TBK 117", "m.117", "madde 117" gibi tüm varyasyonları yakalar
    found = re.search(r"(?:tbk|ttk|tkhk|madde|m\.|md\.)?\s*(\d+)", query.lower())
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

        self.bm25.index([c["text"] for c in self.corpus])
        os.makedirs(os.path.dirname(self.cfg.CACHE_PATH), exist_ok=True)
        with open(self.cfg.CACHE_PATH, "wb") as f:
            pickle.dump({"corpus": self.corpus, "bm25": self.bm25}, f)

    def retrieve(self, query: str, k: int = None) -> List[Dict]:
        k = k or self.cfg.FINAL_K

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
        dense_results = self.qdrant.query_points(
            COLLECTION_NAME, query=vec, limit=self.cfg.TOP_K_DENSE, with_payload=True
        ).points
        dense_hits = [{**p.payload, "dense_score": p.score} for p in dense_results]

        # Site corpus araması (sadece dense)
        site_hits = []
        try:
            site_results = self.qdrant.query_points(
                "site_corpus", query=vec, limit=self.cfg.FINAL_K, with_payload=True
            ).points
            # Site belgelerini yüksek başlangıç skoruyla ekleyelim ki üst sıralara çıksınlar
            site_hits = [{**p.payload, "skor": p.score + 10.0, "source": "site_document"} for p in site_results]
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
