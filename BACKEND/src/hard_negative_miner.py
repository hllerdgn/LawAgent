"""
hard_negative_miner.py - LawAgent Hard-Negative Cift Tarayici
================================================================
Corpus'taki mevzuat chunk'larini embedding uzayinda tarar.
Kosinus benzerligi yuksek (varsayilan >0.82 ayni kanun, >0.88 cross)
AMA farkli madde numarasi olan ciftleri hard-negative olarak isaretler.

Oncelik: 1. Ayni kanun ici, 2. Farkli kanunlar arasi.
Ayrica eval_v2 failure_analysis.json'dan bilinen reranking hatalarini dahil eder.

CIKTI: eval/hard_negatives.json

KULLANIM:
    cd BACKEND
    python src/hard_negative_miner.py
    python src/hard_negative_miner.py --same-law-threshold 0.80
    python src/hard_negative_miner.py --no-cross-law
"""

import json
import os
import sys
import time
import argparse
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_SRC_DIR)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from dotenv import load_dotenv
for _p in [Path(_BACKEND_DIR) / ".env", Path(_BACKEND_DIR).parent / ".env"]:
    if _p.exists():
        load_dotenv(dotenv_path=_p)
        break

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("LawAgent.HardNegativeMiner")
logging.getLogger("LawAgent.Embedder").setLevel(logging.WARNING)
logging.getLogger("LawAgent.Retriever").setLevel(logging.WARNING)

CORPUS_PATH = os.path.join(_SRC_DIR, "data", "chunk_corpus_enriched.json")
FAILURE_ANALYSIS = os.path.join(_BACKEND_DIR, "eval", "results_v2", "failure_analysis.json")
OUTPUT_PATH = os.path.join(_BACKEND_DIR, "eval", "hard_negatives.json")
BATCH_SIZE = 64
MAX_PAIRS_TOTAL = 3000

# eval_v2 sonuclarindan bilinen kotu ciftler (dogrulama seti)
KNOWN_PAIRS = [
    {"kanun": "TKHK", "madde_a": "48",  "madde_b": "50",  "aciklama": "cayma hakki suresi vs devre tatil"},
    {"kanun": "TKHK", "madde_a": "24",  "madde_b": "48",  "aciklama": "kredi cayma vs mesafeli cayma"},
    {"kanun": "TBK",  "madde_a": "472", "madde_b": "474", "aciklama": "eser teslimi vs ayip bildirimi"},
    {"kanun": "TBK",  "madde_a": "506", "madde_b": "513", "aciklama": "vekilin ozen borcu ilgili maddeler"},
    {"kanun": "TBK",  "madde_a": "112", "madde_b": "117", "aciklama": "borcun ifasizligi vs temerrut"},
]


def load_corpus():
    log.info(f"Corpus yukleniyor: {CORPUS_PATH}")
    with open(CORPUS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    mevzuat = [c for c in data if c.get("source") == "mevzuat" and c.get("article_no")]
    log.info(f"Toplam chunk: {len(data)} | Mevzuat: {len(mevzuat)}")
    return mevzuat


def get_representative_chunks(corpus):
    """Her (kanun, madde) cifti icin en uzun metni icerenini sec."""
    by_article = defaultdict(list)
    for c in corpus:
        key = (c.get("law", ""), str(c.get("article_no", "")))
        by_article[key].append(c)
    reps = [max(chunks, key=lambda x: len(x.get("text", ""))) for chunks in by_article.values()]
    log.info(f"Benzersiz (kanun, madde): {len(reps)}")
    return reps


def embed_chunks(chunks):
    from embedder import MursitEmbedder
    log.info("Embedder yukleniyor...")
    embedder = MursitEmbedder(quantize=False)
    texts = [c.get("text", "")[:400] for c in chunks]
    log.info(f"{len(texts)} chunk embed ediliyor (batch={BATCH_SIZE})...")
    t0 = time.time()
    all_vecs = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i: i + BATCH_SIZE]
        vecs = embedder.encode(batch, batch_size=BATCH_SIZE, normalize=True)
        all_vecs.extend(vecs)
        pct = min(100, (i + BATCH_SIZE) / len(texts) * 100)
        print(f"\r  Embedding: {pct:.0f}% ({min(i+BATCH_SIZE,len(texts))}/{len(texts)})", end="", flush=True)
    print()
    log.info(f"Embedding tamam: {len(all_vecs)} vektor, {time.time()-t0:.1f}s")
    return np.array(all_vecs, dtype=np.float32)


def cosine_sim_matrix(vecs, chunk_size=200):
    """Normalize edilmis vektorler icin kosinus = dot product. Parcali hesaplama."""
    n = len(vecs)
    log.info(f"Benzerlik matrisi: {n}x{n}")
    sim = np.zeros((n, n), dtype=np.float32)
    for i in range(0, n, chunk_size):
        end_i = min(i + chunk_size, n)
        sim[i:end_i, :] = vecs[i:end_i] @ vecs.T
        pct = i / n * 100
        print(f"\r  Matris: {pct:.0f}%", end="", flush=True)
    print()
    np.fill_diagonal(sim, 0.0)
    return sim


def find_hard_negatives(chunks, sim_matrix, same_law_thr, cross_law_thr):
    """Yuksek benzerlikli ama farkli madde numarali ciftleri bul."""
    n = len(chunks)
    pairs = []
    seen = set()
    log.info(f"Tarama: {n} madde, same_thr={same_law_thr}, cross_thr={cross_law_thr}")

    for i in range(n):
        law_i = chunks[i].get("law", "")
        art_i = str(chunks[i].get("article_no", ""))
        text_i = chunks[i].get("text", "")[:100].replace("\n", " ")
        row = sim_matrix[i]

        for j in range(n):
            if j == i:
                continue
            law_j = chunks[j].get("law", "")
            art_j = str(chunks[j].get("article_no", ""))
            if law_i == law_j and art_i == art_j:
                continue

            sim = float(row[j])
            same_law = (law_i == law_j)
            thr = same_law_thr if same_law else cross_law_thr
            if sim < thr:
                continue

            key = tuple(sorted([(law_i, art_i), (law_j, art_j)]))
            if key in seen:
                continue
            seen.add(key)

            if same_law and sim >= 0.90:
                priority = "CRITICAL"
            elif same_law and sim >= 0.85:
                priority = "HIGH"
            elif same_law:
                priority = "MED"
            else:
                priority = "LOW"

            pairs.append({
                "kanun_a": law_i,
                "madde_a": art_i,
                "text_a_preview": text_i,
                "kanun_b": law_j,
                "madde_b": art_j,
                "text_b_preview": chunks[j].get("text", "")[:100].replace("\n", " "),
                "similarity": round(sim, 4),
                "same_law": same_law,
                "kaynak": "otomatik_tarama",
                "priority": priority,
            })

    pairs.sort(key=lambda x: (-int(x["same_law"]), -x["similarity"]))
    log.info(f"Toplam bulunan cift: {len(pairs)}")
    return pairs[:MAX_PAIRS_TOTAL]


def extract_from_failure_analysis():
    if not os.path.exists(FAILURE_ANALYSIS):
        log.warning(f"failure_analysis bulunamadi: {FAILURE_ANALYSIS}")
        return []
    with open(FAILURE_ANALYSIS, encoding="utf-8") as f:
        data = json.load(f)

    fa_pairs = []
    for set_key in ["gold_analysis", "heldout_analysis"]:
        for failure in data.get(set_key, {}).get("failure_list", []):
            if failure.get("failure_type") != "reranking_failure":
                continue
            expected = failure.get("expected", "")
            parts = expected.split(" m.")
            if len(parts) != 2:
                continue
            law_exp = parts[0].strip()
            art_exp = parts[1].strip().strip("[]'\"")

            for rank_i, item in enumerate(failure.get("top5_results", [])[:3]):
                law_top = item.get("law", "")
                art_top = str(item.get("article_no", "") or "")
                if not art_top or art_top == "None":
                    continue
                if law_exp == law_top and art_exp == art_top:
                    continue

                fa_pairs.append({
                    "kanun_a": law_exp,
                    "madde_a": art_exp,
                    "text_a_preview": "",
                    "kanun_b": law_top,
                    "madde_b": art_top,
                    "text_b_preview": "",
                    "similarity": round(item.get("skor", 0), 4),
                    "same_law": law_exp == law_top,
                    "kaynak": "eval_v2_failure_analysis",
                    "failure_set": set_key.replace("_analysis", ""),
                    "top_rank": rank_i + 1,
                    "query": failure.get("query", ""),
                    "priority": "CRITICAL",
                })

    # Dedup
    seen = set()
    deduped = []
    for p in fa_pairs:
        key = tuple(sorted([(p["kanun_a"], p["madde_a"]), (p["kanun_b"], p["madde_b"])]))
        if key not in seen:
            seen.add(key)
            deduped.append(p)
    log.info(f"failure_analysis hard-negative: {len(deduped)}")
    return deduped


def verify_known_pairs(chunks, sim_matrix, same_law_thr):
    art_to_idx = {}
    for i, c in enumerate(chunks):
        key = (c.get("law", ""), str(c.get("article_no", "")))
        if key not in art_to_idx:
            art_to_idx[key] = i

    results = []
    print("\n=== BILINEN CIFT DOGRULAMA ===")
    for kp in KNOWN_PAIRS:
        idx_a = art_to_idx.get((kp["kanun"], kp["madde_a"]))
        idx_b = art_to_idx.get((kp["kanun"], kp["madde_b"]))
        if idx_a is None or idx_b is None:
            sim, captured = None, False
            status = "BULUNAMADI (corpus'ta yok)"
        else:
            sim = float(sim_matrix[idx_a, idx_b])
            captured = sim >= same_law_thr
            status = f"YAKALANDI sim={sim:.4f}" if captured else f"KACIRIDI sim={sim:.4f} < {same_law_thr}"
        print(f"  {kp['kanun']} m.{kp['madde_a']} <-> m.{kp['madde_b']}: {status}")
        results.append({**kp, "similarity": round(sim, 4) if sim else None, "captured": captured, "status": status})

    captured_n = sum(1 for r in results if r.get("captured"))
    print(f"Dogrulama: {captured_n}/{len(results)} bilinen cift yakalandi\n")
    return results


def main():
    parser = argparse.ArgumentParser(description="LawAgent Hard-Negative Miner")
    parser.add_argument("--same-law-threshold", type=float, default=0.82)
    parser.add_argument("--cross-law-threshold", type=float, default=0.88)
    parser.add_argument("--out", default=OUTPUT_PATH)
    parser.add_argument("--no-cross-law", action="store_true")
    args = parser.parse_args()

    print("\n" + "="*65)
    print("  LawAgent Hard-Negative Miner")
    print("="*65)
    print(f"  same_law_threshold : {args.same_law_threshold}")
    print(f"  cross_law_threshold: {args.cross_law_threshold}")
    print(f"  Cikti: {args.out}\n")

    corpus = load_corpus()
    reps = get_representative_chunks(corpus)
    vecs = embed_chunks(reps)
    sim = cosine_sim_matrix(vecs)

    verification = verify_known_pairs(reps, sim, args.same_law_threshold)

    cross_thr = 2.0 if args.no_cross_law else args.cross_law_threshold
    hn_pairs = find_hard_negatives(reps, sim, args.same_law_threshold, cross_thr)

    fa_pairs = extract_from_failure_analysis()

    # Birlestir + dedup
    key_map = {}
    for p in hn_pairs:
        key = tuple(sorted([(p["kanun_a"], p["madde_a"]), (p["kanun_b"], p["madde_b"])]))
        key_map[key] = p

    fa_new = []
    for fp in fa_pairs:
        key = tuple(sorted([(fp["kanun_a"], fp["madde_a"]), (fp["kanun_b"], fp["madde_b"])]))
        if key in key_map:
            key_map[key]["kaynak"] = "otomatik_tarama+eval_v2"
            key_map[key]["priority"] = "CRITICAL"
            if fp.get("query"):
                key_map[key].setdefault("example_queries", []).append(fp["query"])
        else:
            fa_new.append(fp)

    all_pairs = list(key_map.values()) + fa_new

    # Istatistikler
    same_law_cnt = sum(1 for p in all_pairs if p.get("same_law"))
    crit_cnt = sum(1 for p in all_pairs if p.get("priority") == "CRITICAL")
    high_cnt = sum(1 for p in all_pairs if p.get("priority") == "HIGH")
    law_stats = defaultdict(int)
    for p in all_pairs:
        if p.get("same_law"):
            law_stats[p["kanun_a"]] += 1

    print("="*65)
    print("  SONUCLAR")
    print("="*65)
    print(f"  Toplam cift        : {len(all_pairs)}")
    print(f"  Ayni kanun ici     : {same_law_cnt}")
    print(f"  Farkli kanun arasi : {len(all_pairs) - same_law_cnt}")
    print(f"  CRITICAL (eval_v2) : {crit_cnt}")
    print(f"  HIGH (oto sim>0.85): {high_cnt}")
    print(f"\n  Kanun bazinda:")
    for law, cnt in sorted(law_stats.items(), key=lambda x: -x[1]):
        print(f"    {law}: {cnt}")

    output = {
        "generated_at": datetime.now().isoformat(),
        "methodology": {
            "same_law_threshold": args.same_law_threshold,
            "cross_law_threshold": args.cross_law_threshold,
            "model": "newmindai/Mursit-Base-TR-Retrieval",
            "corpus_file": "chunk_corpus_enriched.json",
            "representative_chunks": len(reps),
            "embedding_text_chars": 400,
            "note": "1 representative chunk per (law, article_no) pair — longest text selected",
        },
        "verification_known_pairs": verification,
        "statistics": {
            "total_pairs": len(all_pairs),
            "same_law_pairs": same_law_cnt,
            "cross_law_pairs": len(all_pairs) - same_law_cnt,
            "critical_from_eval_v2": crit_cnt,
            "high_priority_auto": high_cnt,
            "by_law": dict(law_stats),
        },
        "hard_negatives": all_pairs,
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  Kaydedildi: {args.out}")

    same_pairs = [p for p in all_pairs if p.get("same_law")]
    print(f"\n=== ILK 25 AYNI-KANUN HARD-NEGATIVE ===")
    for i, p in enumerate(same_pairs[:25], 1):
        src = p.get("kaynak", "?").replace("otomatik_tarama+eval_v2", "auto+eval").replace("otomatik_tarama", "auto").replace("eval_v2_failure_analysis", "eval")
        print(f"  {i:2}. [{p['kanun_a']}] m.{p['madde_a']:>4} <-> m.{p['madde_b']:<4} | sim={p['similarity']:.4f} | {p['priority']:<8} | {src}")

    print("\n  Hard-negative mining tamamlandi.\n")


if __name__ == "__main__":
    main()

