"""
prepare_triplets.py — Contrastive Fine-Tuning Veri Hazırlığı
=============================================================

hard_negatives.json + chunk_corpus_enriched.json kullanarak
(anchor, positive, negative) tripletleri oluşturur.

Strateji:
  - Anchor  : chunk_a'nın metni ("query: " prefix ile)
  - Positive: chunk_a'nın tam corpus metni ("passage: " prefix ile)
  - Negative: chunk_b'nin tam corpus metni ("passage: " prefix ile)

85% Train / 15% Validation split ayrımı yapar ve Held-Out / Gold setlerle
herhangi bir veri sızıntısı (leakage) olmadığını doğrular.

ÇIKTILAR:
    eval/contrastive_triplets.jsonl        (tüm set)
    eval/contrastive_triplets_train.jsonl  (train %85)
    eval/contrastive_triplets_val.jsonl    (val %15)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

# ─── Path ayarı ───────────────────────────────────────────────────────────────
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_SRC_DIR)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("LawAgent.PrepTriplets")

# ─── Dosya Yolları ────────────────────────────────────────────────────────────
HARD_NEG_PATH = os.path.join(_BACKEND_DIR, "eval", "hard_negatives.json")
CORPUS_PATH   = os.path.join(_SRC_DIR, "data", "chunk_corpus_enriched.json")
GOLD_SET_PATH = os.path.join(_BACKEND_DIR, "eval", "gold_set.json")
HELDOUT_PATH  = os.path.join(_BACKEND_DIR, "eval", "gold_set_v2_heldout.json")

OUTPUT_PATH       = os.path.join(_BACKEND_DIR, "eval", "contrastive_triplets.jsonl")
OUTPUT_TRAIN_PATH = os.path.join(_BACKEND_DIR, "eval", "contrastive_triplets_train.jsonl")
OUTPUT_VAL_PATH   = os.path.join(_BACKEND_DIR, "eval", "contrastive_triplets_val.jsonl")

# Embedding prefix
PASSAGE_PREFIX = "passage: "
QUERY_PREFIX   = "query: "
SEED = 42


def load_corpus() -> dict[tuple[str, str], str]:
    log.info(f"Corpus yükleniyor: {CORPUS_PATH}")
    with open(CORPUS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    mevzuat = [
        c for c in data
        if c.get("source") == "mevzuat" and c.get("article_no") and c.get("law")
    ]
    log.info(f"Toplam chunk: {len(data)} | Mevzuat: {len(mevzuat)}")

    rep: dict[tuple[str, str], str] = {}
    for c in mevzuat:
        key = (str(c["law"]).upper(), str(c["article_no"]))
        text = c.get("text", "")
        if key not in rep or len(text) > len(rep[key]):
            rep[key] = text

    log.info(f"Temsilci (kanun, madde) çifti: {len(rep)}")
    return rep


def load_hard_negatives() -> list[dict]:
    log.info(f"Hard-negatives yükleniyor: {HARD_NEG_PATH}")
    with open(HARD_NEG_PATH, encoding="utf-8") as f:
        data = json.load(f)
    pairs = data.get("hard_negatives", [])
    log.info(f"Toplam hard-negative çifti: {len(pairs)}")
    return pairs


def load_gold_set() -> list[dict]:
    log.info(f"Gold set yükleniyor: {GOLD_SET_PATH}")
    with open(GOLD_SET_PATH, encoding="utf-8") as f:
        data = json.load(f)
    mevzuat_queries = [
        q for q in data
        if q.get("expected_law") and q.get("expected_article")
        and q.get("category") != "yargitay_intent"
    ]
    log.info(f"Gold set mevzuat sorguları: {len(mevzuat_queries)}")
    return mevzuat_queries


def load_heldout_articles() -> set[tuple[str, str]]:
    """
    Held-out setindeki (kanun, madde) çiftlerini döner (Leakage kontrolü için).
    """
    if not os.path.exists(HELDOUT_PATH):
        return set()
    with open(HELDOUT_PATH, encoding="utf-8") as f:
        data = json.load(f)
    articles = set()
    for q in data:
        law = str(q.get("expected_law", "")).upper()
        arts = q.get("expected_article")
        if isinstance(arts, str):
            arts = [arts]
        elif isinstance(arts, list):
            arts = [str(a) for a in arts]
        else:
            arts = []
        for a in arts:
            if law and a:
                articles.add((law, a))
    return articles


def make_chunk_triplets(
    pairs: list[dict],
    corpus_map: dict[tuple[str, str], str],
    max_pairs: int | None = None,
    max_per_law: int = 350,
) -> tuple[list[dict], dict[str, int]]:
    triplets = []
    skipped = 0
    kanun_dist: dict[str, int] = defaultdict(int)

    check_pairs = pairs if max_pairs is None else pairs[:max_pairs]

    for pair in check_pairs:
        kanun_a = str(pair.get("kanun_a", "")).upper()
        madde_a = str(pair.get("madde_a", ""))
        kanun_b = str(pair.get("kanun_b", "")).upper()
        madde_b = str(pair.get("madde_b", ""))

        if kanun_dist[kanun_a] >= max_per_law:
            continue

        key_a = (kanun_a, madde_a)
        key_b = (kanun_b, madde_b)

        text_a = corpus_map.get(key_a)
        text_b = corpus_map.get(key_b)

        if not text_a or not text_b:
            skipped += 1
            continue

        anchor_text = QUERY_PREFIX + text_a[:400].strip()
        positive_text = PASSAGE_PREFIX + text_a[:512].strip()
        negative_text = PASSAGE_PREFIX + text_b[:512].strip()

        triplets.append({
            "anchor":   anchor_text,
            "positive": positive_text,
            "negative": negative_text,
            "meta": {
                "type":    "chunk_chunk",
                "kanun_a": kanun_a,
                "madde_a": madde_a,
                "kanun_b": kanun_b,
                "madde_b": madde_b,
                "similarity": pair.get("similarity"),
                "priority":   pair.get("priority", ""),
            }
        })
        kanun_dist[kanun_a] += 1

    log.info(f"Chunk-chunk triplet: {len(triplets)} üretildi (kanun limiti {max_per_law})")
    return triplets, kanun_dist


def make_gold_query_triplets(
    gold_queries: list[dict],
    pairs: list[dict],
    corpus_map: dict[tuple[str, str], str],
) -> tuple[list[dict], dict[str, int]]:
    hn_lookup: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for pair in pairs:
        ka = str(pair.get("kanun_a", "")).upper()
        ma = str(pair.get("madde_a", ""))
        kb = str(pair.get("kanun_b", "")).upper()
        mb = str(pair.get("madde_b", ""))
        if ka and ma and kb and mb:
            hn_lookup[(ka, ma)].append((kb, mb))
            hn_lookup[(kb, mb)].append((ka, ma))

    triplets = []
    kanun_dist: dict[str, int] = defaultdict(int)

    for item in gold_queries:
        law = str(item.get("expected_law", "")).upper()
        articles = item.get("expected_article")
        if isinstance(articles, str):
            articles = [articles]
        query_text = item.get("query", "")

        for article in articles:
            pos_key = (law, article)
            pos_text = corpus_map.get(pos_key)
            if not pos_text:
                continue

            neg_candidates = hn_lookup.get(pos_key, [])
            if not neg_candidates:
                continue

            for neg_key in neg_candidates[:3]:
                neg_text = corpus_map.get(neg_key)
                if not neg_text:
                    continue

                triplets.append({
                    "anchor":   QUERY_PREFIX + query_text.strip(),
                    "positive": PASSAGE_PREFIX + pos_text[:512].strip(),
                    "negative": PASSAGE_PREFIX + neg_text[:512].strip(),
                    "meta": {
                        "type":      "gold_query",
                        "query_id":  item.get("id"),
                        "kanun_pos": law,
                        "madde_pos": article,
                        "kanun_neg": neg_key[0],
                        "madde_neg": neg_key[1],
                    }
                })
                kanun_dist[law] += 1
                break

    log.info(f"Gold-query triplet: {len(triplets)} üretildi")
    return triplets, kanun_dist


def verify_leakage(all_triplets: list[dict], heldout_articles: set[tuple[str, str]]) -> int:
    """
    Held-out setindeki maddelerin kaç tanesinin tripletlerde anchor/pos olarak yer aldığını denetler.
    Bu fonksiyon tüm triplet seti üzerinde çalışır (train + val).
    """
    leakage_count = 0
    for t in all_triplets:
        meta = t.get("meta", {})
        ka = meta.get("kanun_a") or meta.get("kanun_pos")
        ma = meta.get("madde_a") or meta.get("madde_pos")
        if ka and ma and (ka, ma) in heldout_articles:
            leakage_count += 1
    return leakage_count


def assert_no_critical_leakage(
    val_triplets: list[dict],
    heldout_articles: set[tuple[str, str]],
) -> int:
    """
    KONTROL 1 — MADDE NUMARASI SEVIYESI (Uyarı, durdurmaz):
    Val tripletlerindeki pozitif maddelerin held-out seti ile örtüşümünü ölçer.

    Bu tür örtüşme, query metni sızmadığı sürece kabul edilebilir olabilir:
    model eğitimde (TBK, 147) gibi bir chunk gördü, ama held-out’ta
    bu maddeye ait farklı bir doğal dil sorgusu test ediliyor.
    Bununla birlikte bu sayı raporlanır ve kullanıcı karar verir.

    Döner: Val-Held-Out madde örtüşmesi sayısı
    """
    val_pos_keys: set[tuple[str, str]] = set()
    for t in val_triplets:
        meta = t.get("meta", {})
        ka = meta.get("kanun_a") or meta.get("kanun_pos")
        ma = meta.get("madde_a") or meta.get("madde_pos")
        if ka and ma:
            val_pos_keys.add((ka, ma))

    overlap = val_pos_keys & heldout_articles
    if overlap:
        log.warning(
            f"[VAL-HELDOUT MADDE SEVIYESI] Val seti ile held-out arasında "
            f"{len(overlap)} madde örtüşmesi var: "
            f"{sorted(overlap)[:10]}{'...' if len(overlap) > 10 else ''}"
        )
        log.warning(
            "  -> YORUM: Sadece madde numarası örtüşmesi (query metni sızmadığı sürece kabul edilebilir)."
            " Rapora '\u26a0\ufe0f N madde örtüşüyor' olarak yazılacak."
        )
    else:
        log.info("[VAL-HELDOUT-OK] Val seti ile held-out arasında madde örtüşmesi sapıtanamadı.")

    return len(overlap)


def assert_no_query_text_leakage(
    all_triplets: list[dict],
    heldout_queries: list[dict],
) -> int:
    """
    KONTROL 2 — QUERY METNI SEVIYESI (Sert assertion):
    Held-out setindeki sorgu metinlerinin hiçbirinin triplet anchor’ı olarak
    kullanılmadığını garanti eder. Bu kesinlikle 0 olmalıdır.

    Eğer held-out sorgu metni bir triplet'in anchor alanında geçiyorsa
    bu gerçek bir sızıntıdır ve pipeline DURDURULMALIDIR.

    Döner: Sızıntı sayısı (0 ise temiz, >0 ise kritik hata)
    """
    # Held-out sorgu metinlerini normalize et
    heldout_query_texts: set[str] = set()
    for q in heldout_queries:
        text = q.get("query", "").strip().lower()
        if text:
            heldout_query_texts.add(text)

    QUERY_PREFIX_LOWER = QUERY_PREFIX.strip().lower()  # "query:"

    leakage_found: list[str] = []
    for t in all_triplets:
        anchor_raw = t.get("anchor", "")
        # "query: " prefix’ini çıkar
        if anchor_raw.lower().startswith(QUERY_PREFIX_LOWER):
            anchor_text = anchor_raw[len(QUERY_PREFIX):].strip().lower()
        else:
            anchor_text = anchor_raw.strip().lower()

        if anchor_text in heldout_query_texts:
            leakage_found.append(anchor_raw[:80])

    if leakage_found:
        log.error(
            f"[KRİTİK SIZINTI] Held-out sorgu metni triplet anchor olarak bulundu! "
            f"{len(leakage_found)} örnek:\n  "
            + "\n  ".join(leakage_found[:5])
        )
        # Bu gerçek bir sızıntı — pipeline’ı durdur
        raise AssertionError(
            f"Query-text leakage tespit edildi! {len(leakage_found)} held-out sorgusu "
            f"triplet anchor olarak kullanılmış. Pipeline durduruldu."
        )
    else:
        log.info(
            "[QUERY-TEXT-OK] Hiçbir held-out sorgu metni triplet anchor olarak kullanılmamış. "
            f"({len(heldout_query_texts)} held-out sorgusu, {len(all_triplets)} triplet kontrol edildi)"
        )

    return 0


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="hard_negatives.json -> contrastive_triplets.jsonl (with Train/Val Split & Leakage Check)"
    )
    parser.add_argument("--max-pairs", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    corpus_map       = load_corpus()
    pairs            = load_hard_negatives()
    gold             = load_gold_set()
    heldout_articles = load_heldout_articles()

    # Held-out sorgu metinlerini de yükle (query-text leakage kontrolü için)
    heldout_queries: list[dict] = []
    if os.path.exists(HELDOUT_PATH):
        with open(HELDOUT_PATH, encoding="utf-8") as f:
            heldout_queries = json.load(f)
        log.info(f"Held-out sorgu metinleri yüklendi: {len(heldout_queries)} sorgu")

    chunk_triplets, chunk_dist = make_chunk_triplets(pairs, corpus_map, args.max_pairs)
    gold_triplets, gold_dist   = make_gold_query_triplets(gold, pairs, corpus_map)

    all_triplets = chunk_triplets + gold_triplets

    # KONTROL 2 (Sert) — Query metin seviyesi sızıntısını kontrol et
    # Held-out sorgu metinleri ASLA triplet anchor olamaz. Bu sart.
    query_text_leakage = assert_no_query_text_leakage(all_triplets, heldout_queries)

    # KONTROL 1 (Uyarı) — Genel madde-seviyesi leakage
    leak_count = verify_leakage(all_triplets, heldout_articles)
    log.info(
        f"Madde-Seviyesi Leakage Denetimi: {len(heldout_articles)} held-out maddesinden "
        f"{leak_count} tanesi tripletlerde yer alıyor "
        "(Query metni sızmadığı sürece kabul edilebilir)."
    )

    # Train / Val Split (85% Train, 15% Val)
    random.seed(SEED)
    shuffled = list(all_triplets)
    random.shuffle(shuffled)

    val_size = int(len(shuffled) * 0.15)
    val_triplets = shuffled[:val_size]
    train_triplets = shuffled[val_size:]

    # KONTROL 1b (Uyarı) — Val-HeldOut madde örtüşmesi
    val_overlap = assert_no_critical_leakage(val_triplets, heldout_articles)

    print("\n" + "=" * 60)
    print("CONTRASTIVE TRİPLET VURGULANMIŞ OZET TABLOSU")
    print("=" * 60)
    print(f"Toplam Triplet Sayısı       : {len(all_triplets)}")
    print(f"Train Seti (%85)           : {len(train_triplets)}")
    print(f"Validation Seti (%15)      : {len(val_triplets)}")
    print(f"--- Leakage Kontrolünü ---")
    print(f"Query-Text Sızıntısı         : {query_text_leakage} (ASSERT: 0 olmalı, {'OK' if query_text_leakage == 0 else 'KRITIK HATA'})")
    print(f"Madde-Seviyesi Sızıntısı    : {leak_count}/{len(heldout_articles)} held-out madde (Kabul Edilebilir)")
    print(f"Val-HeldOut Madde Örtüşmesi: {val_overlap} madde ({'OK' if val_overlap == 0 else 'UYARI - raporda belirtilecek'})")
    print("=" * 60 + "\n")

    if args.dry_run:
        print("[dry-run] Dosyalar yazılmadı.")
        return

    # Kaydet
    for path, data in [
        (OUTPUT_PATH, all_triplets),
        (OUTPUT_TRAIN_PATH, train_triplets),
        (OUTPUT_VAL_PATH, val_triplets),
    ]:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for t in data:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")
        print(f"[OK] {len(data)} triplet -> {path}")

if __name__ == "__main__":
    main()
