"""
eval_v2.py — LawAgent Retrieval Değerlendirme v2
=================================================

Metodoloji (tam gereksinimler):
  1. İKİ AYRI SET: Gold (38 sorgu) + Held-Out (45 sorgu) her zaman yan yana raporlanır.
     Aralarındaki fark >%15 ise "overfitting_gap" ayrıca işaretlenir.
  2. KATEGORİ BAZLI KIRILIM: Her kategori (direct_madde, semantic_ttk, semantic_tkhk,
     semantic_tbk, yargitay_intent) için n sayısıyla birlikte Hit@1/3/5/10, MRR raporlanır.
  3. HATA ANALİZİ: failure_analysis.json — recall_failure / reranking_failure ayrımı,
     beklenen vs top-5, doğru cevabın rank'i.
  4. DETERMİNİZM TESTİ: LLM adımları (HyDE, LLM reranker) etkinse aynı sorgu 3x çalıştırılır,
     varyans raporlanır.
  5. BOOTSTRAP CI: 1000 iterasyonla %95 güven aralığı hesaplanır.
  6. VERSİYON KARŞILAŞTIRMASI: Historical metrikler tabloya eklenir.

KULLANIM:
    cd BACKEND
    python src/eval_v2.py
    python src/eval_v2.py --mode both                        # gold + held-out (varsayılan)
    python src/eval_v2.py --mode gold                        # sadece gold set
    python src/eval_v2.py --mode heldout                     # sadece held-out
    python src/eval_v2.py --enable-reranker llm              # LLM reranker açık
    python src/eval_v2.py --enable-reranker cross            # Cross-encoder açık
    python src/eval_v2.py --enable-hyde                      # HyDE açık
    python src/eval_v2.py --determinism-runs 3               # 3x determinizm testi
    python src/eval_v2.py --k 10 --bootstrap-n 1000          # tüm parametreler
    python src/eval_v2.py --out-dir eval/results_v2          # çıktı klasörü

ÇIKTILAR:
    eval/results_v2/retrieval_eval_report.md  — özet rapor (markdown)
    eval/results_v2/failure_analysis.json     — hata detayları
    eval/results_v2/raw_results_gold.csv      — ham gold sonuçları
    eval/results_v2/raw_results_heldout.csv   — ham held-out sonuçları
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import os
import random
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

# ─── Proje dizin ayarı ────────────────────────────────────────────────────────
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_SRC_DIR)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from retriever import LegalRetriever, normalize_article  # noqa: E402

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("LawAgent.EvalV2")
logging.getLogger("LawAgent.Retriever").setLevel(logging.WARNING)
logging.getLogger("LawAgent.Embedder").setLevel(logging.WARNING)

# ─── Versiyon Geçmişi (Manuel, önceki eval'lardan) ───────────────────────────
VERSION_HISTORY: List[Dict] = [
    {
        "version": "v1.0 (baseline)",
        "date": "2025-06",
        "set": "gold (38)",
        "Hit@1": 0.605,
        "Hit@3": 0.789,
        "Hit@5": 0.868,
        "Hit@10": 0.921,
        "MRR": 0.697,
        "note": "Dense-only, alpha=0.5",
    },
    {
        "version": "v1.3",
        "date": "2025-07",
        "set": "gold (38)",
        "Hit@1": 0.763,
        "Hit@3": 0.868,
        "Hit@5": 0.921,
        "Hit@10": 0.947,
        "MRR": 0.815,
        "note": "BM25+ Hybrid, BOOST_KANUN=6",
    },
    {
        "version": "v1.4",
        "date": "2025-07",
        "set": "gold (38)",
        "Hit@1": 0.842,
        "Hit@3": 0.921,
        "Hit@5": 0.974,
        "Hit@10": 1.000,
        "MRR": 0.886,
        "note": "_KEYWORD_TO_ARTICLE x25, 60+ kural",
    },
    {
        "version": "v1.6",
        "date": "2025-07",
        "set": "gold (38)",
        "Hit@1": 0.947,
        "Hit@3": 1.000,
        "Hit@5": 1.000,
        "Hit@10": 1.000,
        "MRR": 0.974,
        "note": "Contextual prefix, HyDE, sinonim genişletme",
    },
    {
        "version": "v1.6",
        "date": "2025-07",
        "set": "held-out (45)",
        "Hit@1": 0.400,
        "Hit@3": 0.600,
        "Hit@5": 0.711,
        "Hit@10": 0.867,
        "MRR": 0.542,
        "note": "Baseline held-out — OVERFITTING TESPİTİ",
    },
    {
        "version": "v1.7 (reranker)",
        "date": "2025-07",
        "set": "held-out (45)",
        "Hit@1": 0.489,
        "Hit@3": 0.822,
        "Hit@5": 0.867,
        "Hit@10": 0.911,
        "MRR": 0.652,
        "note": "LLM Reranker (Groq Llama-3.3-70B) aktif",
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# GOLD SET YÜKLEME
# ══════════════════════════════════════════════════════════════════════════════


def load_gold(path: str) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    log.info(f"Yüklendi: {len(data)} sorgu <- {path}")
    return data


# ══════════════════════════════════════════════════════════════════════════════
# HIT TESTİ
# ══════════════════════════════════════════════════════════════════════════════


def _article_matches(expected: Union[str, List[str], None], actual: str) -> bool:
    if expected is None:
        return False
    if isinstance(expected, list):
        return actual in expected
    return actual == expected


def is_hit(item: Dict[str, Any], chunk: Dict[str, Any]) -> bool:
    """Bir chunk, gold item'in beklentisini karsilayor mu?"""
    if item.get("expected_source") == "yargitay":
        if item.get("expected_decision_id"):
            return (
                chunk.get("source") == "yargitay"
                and chunk.get("decision_id") == item["expected_decision_id"]
            )
        return chunk.get("source") == "yargitay"

    law_match = (
        str(chunk.get("law", "")).upper() == str(item.get("expected_law", "")).upper()
    )
    art_match = _article_matches(
        item.get("expected_article"), normalize_article(chunk.get("article_no"))
    )
    return law_match and art_match


# ══════════════════════════════════════════════════════════════════════════════
# TEK SORGU ÇALISTIRMA
# ══════════════════════════════════════════════════════════════════════════════


def run_single_query(
    retriever: LegalRetriever, item: Dict[str, Any], k: int = 10
) -> Dict[str, Any]:
    """Tek bir gold item'i calistirir ve detayli sonuc dondurur."""
    t0 = time.time()
    try:
        chunks = retriever.retrieve(
            item["query"], k=k, query_category=item.get("category")
        )
    except Exception as e:
        print(f"  ERROR '{item['query']}' -> {e}")
        chunks = []
    elapsed_ms = (time.time() - t0) * 1000

    # Rank bul (k icindeki)
    rank: Optional[int] = None
    for i, c in enumerate(chunks, start=1):
        if is_hit(item, c):
            rank = i
            break

    # Top-5 bilgisi (failure analysis icin)
    top5 = []
    for c in chunks[:5]:
        top5.append(
            {
                "law": c.get("law", ""),
                "article_no": c.get("article_no", ""),
                "source": c.get("source", ""),
                "decision_id": c.get("decision_id", ""),
                "skor": round(c.get("skor", 0), 4),
            }
        )

    # Top-10 hit kontrolu (recall vs reranking ayrimi icin)
    hit10 = False
    for c in chunks[:10]:
        if is_hit(item, c):
            hit10 = True
            break

    return {
        "id": item.get("id"),
        "category": item.get("category", "unknown"),
        "query": item.get("query"),
        "expected_law": item.get("expected_law"),
        "expected_article": (
            json.dumps(item.get("expected_article"), ensure_ascii=False)
            if isinstance(item.get("expected_article"), list)
            else item.get("expected_article")
        ),
        "expected_source": item.get("expected_source"),
        "rank": rank,
        "hit10": hit10,
        "elapsed_ms": round(elapsed_ms, 1),
        "top1_law": chunks[0].get("law") if chunks else None,
        "top1_article": chunks[0].get("article_no") if chunks else None,
        "top1_source": chunks[0].get("source") if chunks else None,
        "top1_score": round(chunks[0].get("skor", 0), 4) if chunks else None,
        "top5": top5,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SET DEGERLENDIRME
# ══════════════════════════════════════════════════════════════════════════════


def evaluate_set(
    retriever: LegalRetriever,
    gold: List[Dict[str, Any]],
    k: int = 10,
    set_name: str = "gold",
    show_progress: bool = True,
) -> List[Dict[str, Any]]:
    results = []
    for i, item in enumerate(gold, 1):
        if show_progress:
            query_preview = item["query"][:52]
            print(f"\r  [{set_name}] {i}/{len(gold)} — {query_preview}...", end="", flush=True)
        result = run_single_query(retriever, item, k=k)
        results.append(result)
    if show_progress:
        print()
    return results


# ══════════════════════════════════════════════════════════════════════════════
# METRIK HESAPLAMA
# ══════════════════════════════════════════════════════════════════════════════


def compute_metrics(
    results: List[Dict[str, Any]], k_values: Tuple = (1, 3, 5, 10)
) -> Dict[str, Any]:
    n = len(results)
    if n == 0:
        return {}

    metrics: Dict[str, Any] = {"n": n}
    for k in k_values:
        hits = sum(1 for r in results if r.get("rank") is not None and r["rank"] <= k)
        metrics[f"Hit@{k}"] = round(hits / n, 4)

    mrr_vals = [1.0 / r["rank"] for r in results if r.get("rank")]
    metrics["MRR"] = round(sum(mrr_vals) / n, 4) if mrr_vals else 0.0
    metrics["avg_latency_ms"] = round(
        sum(r["elapsed_ms"] for r in results) / n, 1
    )
    return metrics


def compute_by_category(
    results: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    by_cat: Dict[str, List] = defaultdict(list)
    for r in results:
        by_cat[r.get("category", "other")].append(r)
    return {cat: compute_metrics(items) for cat, items in sorted(by_cat.items())}


# ══════════════════════════════════════════════════════════════════════════════
# BOOTSTRAP GUVEN ARALIGI
# ══════════════════════════════════════════════════════════════════════════════


def bootstrap_ci(
    results: List[Dict[str, Any]],
    metric_fn,
    n_iter: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> Dict[str, Tuple[float, float]]:
    """
    Bootstrap resampling ile %95 guven araliqlari hesaplar.
    Returns: {metric_name: (lower, upper)}
    """
    rng = random.Random(seed)
    n = len(results)
    if n == 0:
        return {}

    bootstrap_metrics: Dict[str, List[float]] = defaultdict(list)

    for _ in range(n_iter):
        sample = [rng.choice(results) for _ in range(n)]
        m = metric_fn(sample)
        for key, val in m.items():
            if isinstance(val, (int, float)) and key not in ("n", "avg_latency_ms"):
                bootstrap_metrics[key].append(val)

    alpha = 1 - ci
    ci_bounds: Dict[str, Tuple[float, float]] = {}
    for key, vals in bootstrap_metrics.items():
        vals_sorted = sorted(vals)
        lo_idx = int(math.floor(alpha / 2 * n_iter))
        hi_idx = int(math.ceil((1 - alpha / 2) * n_iter)) - 1
        ci_bounds[key] = (
            round(vals_sorted[lo_idx], 4),
            round(vals_sorted[hi_idx], 4),
        )

    return ci_bounds


# ══════════════════════════════════════════════════════════════════════════════
# DETERMINIZM TESTI
# ══════════════════════════════════════════════════════════════════════════════


def determinism_test(
    retriever: LegalRetriever,
    gold: List[Dict[str, Any]],
    runs: int = 3,
    k: int = 10,
    sample_size: int = 10,
) -> Dict[str, Any]:
    """
    LLM tabanli adimlarda (HyDE / LLM Reranker etkinse) ayni sorguyu
    `runs` kez calistirir ve rank degiskenligini raporlar.
    """
    hyde_on = os.environ.get("ENABLE_HYDE", "false").lower() == "true"
    llm_rr_on = os.environ.get("ENABLE_LLM_RERANK", "false").lower() == "true"
    cross_rr_on = os.environ.get("ENABLE_CROSS_RERANK", "false").lower() == "true"
    has_llm_step = hyde_on or llm_rr_on

    result = {
        "llm_steps_active": {
            "hyde": hyde_on,
            "llm_reranker": llm_rr_on,
            "cross_encoder": cross_rr_on,
        },
        "determinism_tested": has_llm_step,
        "runs": runs,
        "queries_tested": 0,
        "non_deterministic_count": 0,
        "variance_details": [],
    }

    if not has_llm_step:
        result["note"] = (
            "LLM adimi (HyDE / LLM Reranker) aktif degil. "
            "Embedding+BM25 pipeline'i tamamen deterministiktir — test atlandi."
        )
        return result

    rng = random.Random(42)
    sample = rng.sample(gold, min(sample_size, len(gold)))
    result["queries_tested"] = len(sample)

    for item in sample:
        ranks = []
        for _ in range(runs):
            r = run_single_query(retriever, item, k=k)
            ranks.append(r["rank"])

        non_det = len(set(r if r is not None else -1 for r in ranks)) > 1
        if non_det:
            result["non_deterministic_count"] += 1

        valid_ranks = [r for r in ranks if r is not None]
        if len(valid_ranks) > 1:
            mean_r = sum(valid_ranks) / len(valid_ranks)
            variance = sum((r - mean_r) ** 2 for r in valid_ranks) / (len(valid_ranks) - 1)
        else:
            variance = None

        result["variance_details"].append(
            {
                "query": item["query"],
                "ranks_per_run": ranks,
                "non_deterministic": non_det,
                "rank_variance": round(variance, 4) if variance is not None else None,
            }
        )

    result["determinism_rate"] = round(
        1 - result["non_deterministic_count"] / max(result["queries_tested"], 1), 4
    )
    return result


# ══════════════════════════════════════════════════════════════════════════════
# HATA ANALIZI
# ══════════════════════════════════════════════════════════════════════════════


def build_failure_analysis(
    gold_results: List[Dict[str, Any]],
    heldout_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Basarisiz sorgulari analiz eder:
    - recall_failure: Hit@10=False (dogru madde top-10'a hic girmemis)
    - reranking_failure: Hit@10=True ama Hit@1=False (havuzda var ama uste cikamamis)
    """

    def _analyze(results: List[Dict], set_name: str) -> Dict:
        failures = []
        recall_failures = 0
        reranking_failures = 0

        for r in results:
            hit1 = r.get("rank") is not None and r["rank"] <= 1
            hit10 = r.get("hit10", False)

            if hit1:
                continue  # Basarili — atla

            failure_type = "recall_failure" if not hit10 else "reranking_failure"
            if failure_type == "recall_failure":
                recall_failures += 1
            else:
                reranking_failures += 1

            expected_law = r.get("expected_law", "")
            expected_article = r.get("expected_article", "")
            expected_source = r.get("expected_source", "")

            failures.append(
                {
                    "id": r.get("id"),
                    "set": set_name,
                    "category": r.get("category"),
                    "query": r.get("query"),
                    "expected": (
                        f"{expected_law} m.{expected_article}"
                        if expected_law
                        else f"yargitay"
                    ),
                    "actual_rank": r.get("rank") if r.get("rank") else "not_in_top_10",
                    "failure_type": failure_type,
                    "top5_results": r.get("top5", []),
                    "latency_ms": r.get("elapsed_ms"),
                }
            )

        return {
            "set": set_name,
            "total_queries": len(results),
            "total_failures": len(failures),
            "recall_failures": recall_failures,
            "reranking_failures": reranking_failures,
            "success_rate_hit1": round(
                (len(results) - len(failures)) / max(len(results), 1), 4
            ),
            "failure_list": failures,
        }

    return {
        "generated_at": datetime.now().isoformat(),
        "methodology": {
            "recall_failure": "Hit@10=False — dogru madde top-10 adayina hic girmemis (retrieval problemi)",
            "reranking_failure": "Hit@10=True ama Hit@1=False — madde aday havuzunda var ama uste cikamamis (reranking problemi)",
        },
        "gold_analysis": _analyze(gold_results, "gold"),
        "heldout_analysis": _analyze(heldout_results, "held-out"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# OVERFITTING GAP
# ══════════════════════════════════════════════════════════════════════════════


def compute_overfitting_gap(
    gold_metrics: Dict, heldout_metrics: Dict, threshold: float = 0.15
) -> Dict[str, Any]:
    gaps = {}
    for key in ("Hit@1", "Hit@3", "Hit@5", "Hit@10", "MRR"):
        gv = gold_metrics.get(key, 0)
        hv = heldout_metrics.get(key, 0)
        gap = round(gv - hv, 4)
        gaps[key] = {
            "gold": gv,
            "held_out": hv,
            "gap": gap,
            "overfit_flag": abs(gap) > threshold,
        }
    return gaps


# ══════════════════════════════════════════════════════════════════════════════
# MARKDOWN RAPOR YAZIMI
# ══════════════════════════════════════════════════════════════════════════════


def write_markdown_report(
    gold_results: List[Dict],
    heldout_results: List[Dict],
    gold_metrics: Dict,
    heldout_metrics: Dict,
    gold_ci: Dict,
    heldout_ci: Dict,
    gold_by_cat: Dict,
    heldout_by_cat: Dict,
    overfitting_gaps: Dict,
    determinism: Optional[Dict],
    config: Dict,
    out_path: str,
) -> None:
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def fmt_ci(metrics, ci, key):
        v = metrics.get(key, "-")
        lo_hi = ci.get(key)
        if lo_hi is None or not isinstance(v, float):
            return str(v)
        lo, hi = lo_hi
        return f"{v:.3f} [{lo:.3f}, {hi:.3f}]"

    # Baslik
    lines += [
        "# LawAgent Retrieval Degerlendirme Raporu v2",
        "",
        f"**Olusturma Tarihi:** {now}  ",
        f"**Metodoloji Versiyonu:** eval_v2.py  ",
        f"**k={config['k']} | Bootstrap N={config['bootstrap_n']} | CI=%95**",
        "",
    ]

    # Pipeline Konfigurasyonu
    lines += [
        "## Pipeline Konfigurasyonu",
        "",
        "| Parametre | Deger |",
        "|-----------|-------|",
        f"| HyDE | {'Aktif' if config.get('hyde') else 'Kapali'} |",
        f"| LLM Reranker | {'Aktif' if config.get('llm_reranker') else 'Kapali'} |",
        f"| Cross-Encoder | {'Aktif' if config.get('cross_reranker') else 'Kapali'} |",
        "| Contextual Prefix | Aktif (chunk_corpus_enriched.json) |",
        "| BM25+ Hybrid | Aktif (alpha dinamik) |",
        "",
    ]

    # Genel Metrikler
    lines += [
        "## 1. Genel Metrikler - Gold vs Held-Out",
        "",
        "> NOT: Gold set (38 sorgu), _KEYWORD_TO_ARTICLE boost tablosu ve sinonim enrichment",
        "> ile kalibre edilmistir. Gercek genelleme performansi icin Held-Out seti baz alinmalidir.",
        "",
        "| Metrik | Gold Set (n=38) [95% CI] | Held-Out (n=45) [95% CI] | Overfitting Gap |",
        "|--------|--------------------------|--------------------------|-----------------|",
    ]

    for key in ("Hit@1", "Hit@3", "Hit@5", "Hit@10", "MRR"):
        g_str = fmt_ci(gold_metrics, gold_ci, key)
        h_str = fmt_ci(heldout_metrics, heldout_ci, key)
        gap_info = overfitting_gaps.get(key, {})
        gap = gap_info.get("gap", 0)
        flag = " [OVERFITTING]" if gap_info.get("overfit_flag") else ""
        lines.append(f"| **{key}** | {g_str} | {h_str} | {gap:+.3f}{flag} |")

    gl = gold_metrics.get("avg_latency_ms", "-")
    hl = heldout_metrics.get("avg_latency_ms", "-")
    lines += [f"| avg_latency_ms | {gl} ms | {hl} ms | - |", ""]

    flagged = [k for k, v in overfitting_gaps.items() if v.get("overfit_flag")]
    if flagged:
        lines += [
            f"> **OVERFITTING UYARISI:** Gold vs Held-Out arasindaki fark %15'i asiyor: {', '.join(flagged)}",
            "> Bu, modelin gold set'e ozgu kurallara overfitting yaptigini gosteriyor.",
            "> Gercek performans held-out metrikleri ile degerlendirilmelidir.",
            "",
        ]

    # Kategori Kirilimi
    lines += [
        "## 2. Kategori Bazli Kirilim",
        "",
        "> NOT: Kucuk n'li kategorilerde (n<=5) yuzde yuz gibi sonuclar yaniltici olabilir.",
        "",
        "### 2a. Gold Set Kategorileri",
        "",
        "| Kategori | n | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR | Uyari |",
        "|----------|---|-------|-------|-------|--------|-----|-------|",
    ]
    for cat, m in gold_by_cat.items():
        n = m.get("n", 0)
        warn = "Kucuk n" if n <= 5 else ""
        lines.append(
            f"| {cat} | {n} "
            f"| {m.get('Hit@1', '-')} "
            f"| {m.get('Hit@3', '-')} "
            f"| {m.get('Hit@5', '-')} "
            f"| {m.get('Hit@10', '-')} "
            f"| {m.get('MRR', '-')} "
            f"| {warn} |"
        )
    lines.append("")

    lines += [
        "### 2b. Held-Out Set Kategorileri",
        "",
        "| Kategori | n | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR | Uyari |",
        "|----------|---|-------|-------|-------|--------|-----|-------|",
    ]
    for cat, m in heldout_by_cat.items():
        n = m.get("n", 0)
        warn = "Kucuk n" if n <= 5 else ""
        lines.append(
            f"| {cat} | {n} "
            f"| {m.get('Hit@1', '-')} "
            f"| {m.get('Hit@3', '-')} "
            f"| {m.get('Hit@5', '-')} "
            f"| {m.get('Hit@10', '-')} "
            f"| {m.get('MRR', '-')} "
            f"| {warn} |"
        )
    lines.append("")

    # Hata Ozeti
    lines += [
        "## 3. Hata Analizi Ozeti",
        "",
        "Detayli hata analizi icin failure_analysis.json dosyasina bakin.",
        "",
        "| Set | Toplam | Basarisiz | Recall Hatasi | Reranking Hatasi | Basari Orani |",
        "|-----|--------|-----------|---------------|-----------------|--------------|",
    ]

    def _fail_row(results, set_name):
        total = len(results)
        if total == 0:
            return f"| {set_name} | 0 | - | - | - | - |"
        hit1 = sum(1 for r in results if r.get("rank") is not None and r["rank"] <= 1)
        fails = total - hit1
        recall_f = sum(
            1 for r in results
            if not (r.get("rank") is not None and r["rank"] <= 1)
            and not r.get("hit10", False)
        )
        rerank_f = fails - recall_f
        success = hit1 / total
        return f"| {set_name} | {total} | {fails} | {recall_f} | {rerank_f} | {success:.1%} |"

    if gold_results:
        lines.append(_fail_row(gold_results, "Gold (38)"))
    if heldout_results:
        lines.append(_fail_row(heldout_results, "Held-Out (45)"))
    lines.append("")

    # Determinizm Testi
    if determinism:
        lines += [
            "## 4. Determinizm Testi",
            "",
        ]
        if not determinism.get("determinism_tested"):
            lines += [
                f"> {determinism.get('note', 'LLM adimi aktif degil, test atlandi.')}",
                "",
            ]
        else:
            det_rate = determinism.get("determinism_rate", 1.0)
            non_det = determinism.get("non_deterministic_count", 0)
            total_tested = determinism.get("queries_tested", 0)
            lines += [
                f"- **Calistirma sayisi:** {determinism.get('runs', 3)}x  ",
                f"- **Test edilen sorgu:** {total_tested}  ",
                f"- **Determinizm orani:** {det_rate:.1%} ({total_tested - non_det}/{total_tested} ayni sonuc)  ",
                "",
            ]
            if non_det > 0:
                lines += [
                    f"> {non_det} sorgu non-deterministik — LLM adimlarinin (HyDE/Reranker)",
                    "> farkli calismalarda farkli siralama urettigi gozlemlendi.",
                    "",
                ]

    # Versiyon Karsilastirmasi
    lines += [
        "## 5. Versiyon Karsilastirma Tablosu",
        "",
        "| Versiyon | Tarih | Set | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR | Not |",
        "|----------|-------|-----|-------|-------|-------|--------|-----|-----|",
    ]
    for v in VERSION_HISTORY:
        lines.append(
            f"| {v['version']} | {v['date']} | {v['set']} "
            f"| {v.get('Hit@1', '-')} | {v.get('Hit@3', '-')} | {v.get('Hit@5', '-')} "
            f"| {v.get('Hit@10', '-')} | {v.get('MRR', '-')} | {v.get('note', '')} |"
        )

    gm = gold_metrics
    hm = heldout_metrics
    cfg_note = (
        ("HyDE+" if config.get("hyde") else "")
        + ("LLMRank+" if config.get("llm_reranker") else "")
        + ("CrossRank" if config.get("cross_reranker") else "")
    ) or "vanilla"

    if gm:
        lines.append(
            f"| **v2.0 (eval_v2)** | {datetime.now().strftime('%Y-%m')} | gold (38) "
            f"| {gm.get('Hit@1', '-')} | {gm.get('Hit@3', '-')} | {gm.get('Hit@5', '-')} "
            f"| {gm.get('Hit@10', '-')} | {gm.get('MRR', '-')} | {cfg_note} |"
        )
    if hm:
        lines.append(
            f"| **v2.0 (eval_v2)** | {datetime.now().strftime('%Y-%m')} | held-out (45) "
            f"| {hm.get('Hit@1', '-')} | {hm.get('Hit@3', '-')} | {hm.get('Hit@5', '-')} "
            f"| {hm.get('Hit@10', '-')} | {hm.get('MRR', '-')} | {cfg_note} |"
        )
    lines.append("")

    # Metodoloji Notlari
    lines += [
        "## 6. Metodoloji Notlari",
        "",
        "### Hit@k Tanimi",
        "Dogru hukuki madde (law + article_no eslesme) ilk k sonuc icinde varsa Hit=1.",
        "Yargitay sorgularinda herhangi bir yargitay chunk'i first k'da ise Hit=1.",
        "",
        "### MRR (Mean Reciprocal Rank)",
        "MRR = (1/n) x Sigma (1/rank_i). Dogru sonuc top-k'ya hic girmemisse rank=inf, 1/rank=0.",
        "",
        "### Bootstrap CI",
        f"1000 bootstrap iterasyonu, seed=42, CI=%95. Kucuk setlerde (n<50) CI genis olabilir.",
        "",
        "### Overfitting Gap",
        "Gold - Held-Out farki >%15 ise [OVERFITTING] isaretlenir.",
        "",
        "### Recall vs Reranking Hatasi",
        "- recall_failure: Hit@10=False — dogru madde top-10 adayina hic girmemis.",
        "- reranking_failure: Hit@10=True ama Hit@1=False — madde havuzda var ama siralamasi yanlis.",
        "",
    ]

    content = "\n".join(lines)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  [MD]  Rapor: {out_path}")


# ══════════════════════════════════════════════════════════════════════════════
# CSV KAYIT
# ══════════════════════════════════════════════════════════════════════════════


def save_csv(results: List[Dict[str, Any]], path: str) -> None:
    if not results:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    flat = []
    for r in results:
        row = dict(r)
        row["top5"] = json.dumps(r.get("top5", []), ensure_ascii=False)
        flat.append(row)
    all_keys = list(dict.fromkeys(k for row in flat for k in row))
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(flat)
    print(f"  [CSV] {path}")


# ══════════════════════════════════════════════════════════════════════════════
# KONSOL RAPORU
# ══════════════════════════════════════════════════════════════════════════════


def print_console_summary(
    gold_metrics: Dict,
    heldout_metrics: Dict,
    gold_ci: Dict,
    heldout_ci: Dict,
    gold_by_cat: Dict,
    heldout_by_cat: Dict,
    overfitting_gaps: Dict,
):
    def fmt(metrics, ci, key):
        v = metrics.get(key, 0)
        lo_hi = ci.get(key)
        if lo_hi:
            lo, hi = lo_hi
            return f"{v:.3f} [{lo:.3f},{hi:.3f}]"
        return f"{v:.3f}"

    sep = "=" * 76
    print(f"\n{sep}")
    print("  LAWAGENT RETRIEVAL EVAL v2  |  Dual-Set + Bootstrap 95% CI")
    print(sep)
    print(f"\n  {'Metrik':<12} {'Gold Set (n=38)':>26}   {'Held-Out (n=45)':>26}   {'Gap':>8}")
    print(f"  {'-'*74}")
    for key in ("Hit@1", "Hit@3", "Hit@5", "Hit@10", "MRR"):
        gs = fmt(gold_metrics, gold_ci, key)
        hs = fmt(heldout_metrics, heldout_ci, key)
        gap = overfitting_gaps.get(key, {}).get("gap", 0)
        flag = " [!]" if overfitting_gaps.get(key, {}).get("overfit_flag") else ""
        print(f"  {key:<12} {gs:>26}   {hs:>26}   {gap:>+.3f}{flag}")

    gl = gold_metrics.get("avg_latency_ms", "-")
    hl = heldout_metrics.get("avg_latency_ms", "-")
    print(f"\n  Latency:  Gold={gl}ms  |  Held-Out={hl}ms")

    print(f"\n  {'KATEGORI KIRILIMLARI':}")
    print(f"  {'-'*74}")
    print(f"  {'Kategori':<25} {'SET':<10} {'n':>3}  {'Hit@1':>6} {'Hit@3':>6} {'MRR':>6}")
    print(f"  {'-'*74}")
    all_cats = sorted(set(list(gold_by_cat.keys()) + list(heldout_by_cat.keys())))
    for cat in all_cats:
        for set_label, by_cat in [("gold", gold_by_cat), ("held-out", heldout_by_cat)]:
            m = by_cat.get(cat)
            if m:
                n = m.get("n", 0)
                warn = "*" if n <= 5 else " "
                print(
                    f"  {cat:<25} {set_label:<10} {n:>3}{warn} "
                    f"{m.get('Hit@1', '-'):>6} {m.get('Hit@3', '-'):>6} {m.get('MRR', '-'):>6}"
                )
    flagged = [k for k, v in overfitting_gaps.items() if v.get("overfit_flag")]
    if flagged:
        print(f"\n  [!] OVERFITTING UYARISI: {', '.join(flagged)} metriklerde fark >%15")
    print(f"\n{sep}\n")


# ══════════════════════════════════════════════════════════════════════════════
# ANA FONKSIYON
# ══════════════════════════════════════════════════════════════════════════════


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="LawAgent Retrieval Degerlendirme v2 - Dual-Set + Bootstrap CI"
    )
    parser.add_argument(
        "--gold",
        default=os.path.join(_BACKEND_DIR, "eval", "gold_set.json"),
        help="Gold set JSON yolu",
    )
    parser.add_argument(
        "--heldout",
        default=os.path.join(_BACKEND_DIR, "eval", "gold_set_v2_heldout.json"),
        help="Held-out set JSON yolu",
    )
    parser.add_argument(
        "--mode",
        choices=["both", "gold", "heldout"],
        default="both",
        help="Hangi set(ler) degerlendirilsin",
    )
    parser.add_argument("--k", type=int, default=10, help="Retrieval top-k (varsayilan 10)")
    parser.add_argument(
        "--bootstrap-n",
        type=int,
        default=1000,
        help="Bootstrap iterasyon sayisi (varsayilan 1000)",
    )
    parser.add_argument(
        "--enable-reranker",
        choices=["none", "llm", "cross", "tkhk-only"],
        default="none",
        help="Reranker turu: none|llm|cross|tkhk-only",
    )
    parser.add_argument(
        "--reranker-mode",
        choices=["none", "llm", "cross", "tkhk-only"],
        default=None,
        help="Reranker modu: none|llm|cross|tkhk-only (alternatif flag)",
    )
    parser.add_argument(
        "--enable-hyde",
        action="store_true",
        help="HyDE etkinlestir",
    )
    parser.add_argument(
        "--determinism-runs",
        type=int,
        default=3,
        help="Determinizm testi icin calistirma sayisi (varsayilan 3)",
    )
    parser.add_argument(
        "--out-dir",
        default=os.path.join(_BACKEND_DIR, "eval", "results_v2"),
        help="Cikti klasoru",
    )
    parser.add_argument(
        "--no-determinism",
        action="store_true",
        help="Determinizm testini atla",
    )
    parser.add_argument(
        "--model-path",
        default=None,
        help="Fine-tuned model klasör yolu (varsayılan: newmindai/Mursit-Base-TR-Retrieval)",
    )
    parser.add_argument(
        "--collection-name",
        default=None,
        help="Qdrant koleksiyon adı (varsayılan: lawagent_mursit)",
    )
    parser.add_argument(
        "--model-key",
        default=None,
        help="Model Registry key (örn. production, shadow_mursit_large, shadow_turk4retrieval, shadow_bge_m3)",
    )
    args = parser.parse_args()

    # Reranker modunu birleştir
    effective_reranker = args.reranker_mode if args.reranker_mode else args.enable_reranker

    # Ortam degiskenleri
    if args.enable_hyde:
        os.environ["ENABLE_HYDE"] = "true"
    if effective_reranker == "llm":
        os.environ["ENABLE_LLM_RERANK"] = "true"
    elif effective_reranker == "cross":
        os.environ["ENABLE_CROSS_RERANK"] = "true"
    elif effective_reranker == "tkhk-only":
        os.environ["ENABLE_TKHK_RERANK"] = "true"
        os.environ["ENABLE_LLM_RERANK"] = "tkhk-only"

    config = {
        "k": args.k,
        "bootstrap_n": args.bootstrap_n,
        "hyde": args.enable_hyde,
        "llm_reranker": effective_reranker == "llm",
        "cross_reranker": effective_reranker == "cross",
        "tkhk_reranker": effective_reranker == "tkhk-only",
        "reranker_mode": effective_reranker,
        "mode": args.mode,
        "model_path": args.model_path,
        "collection_name": args.collection_name,
        "model_key": args.model_key,
    }

    # Retriever baslat
    print("\nLawAgent eval_v2.py baslatiliyor...")
    print(f"  k={args.k} | Bootstrap={args.bootstrap_n} | Reranker={args.enable_reranker} | HyDE={args.enable_hyde}")
    if args.model_key:
        print(f"  Model Key (Registry): {args.model_key}")
    if args.model_path:
        print(f"  Model Path: {args.model_path}")
    if args.collection_name:
        print(f"  Collection Name: {args.collection_name}")

    if args.model_key and args.model_key.startswith("shadow_"):
        from shadow_retriever import ShadowRetriever
        print(f"  Shadow Retriever yukleniyor ({args.model_key})...")
        retriever_context = ShadowRetriever(args.model_key)
        retriever = retriever_context.__enter__()
    else:
        print("  Retriever yukleniyor (Qdrant + Embedder)...")
        retriever_context = None
        retriever = LegalRetriever(
            model_path=args.model_path,
            collection_name=args.collection_name,
        )
    print("  Retriever hazir.\n")

    gold_results: List[Dict] = []
    heldout_results: List[Dict] = []

    if args.mode in ("both", "gold"):
        if not os.path.exists(args.gold):
            print(f"HATA: Gold set bulunamadi: {args.gold}")
            sys.exit(1)
        gold_data = load_gold(args.gold)
        print(f"Gold set degerlendiriliyor ({len(gold_data)} sorgu)...")
        gold_results = evaluate_set(retriever, gold_data, k=args.k, set_name="gold")

    if args.mode in ("both", "heldout"):
        if not os.path.exists(args.heldout):
            print(f"HATA: Held-out set bulunamadi: {args.heldout}")
            sys.exit(1)
        heldout_data = load_gold(args.heldout)
        print(f"Held-out set degerlendiriliyor ({len(heldout_data)} sorgu)...")
        heldout_results = evaluate_set(retriever, heldout_data, k=args.k, set_name="held-out")

    # Metrikler
    print("\nMetrikler hesaplaniyor...")
    gold_metrics = compute_metrics(gold_results)
    heldout_metrics = compute_metrics(heldout_results)
    gold_by_cat = compute_by_category(gold_results)
    heldout_by_cat = compute_by_category(heldout_results)

    # Bootstrap CI
    print(f"Bootstrap CI hesaplaniyor ({args.bootstrap_n} iterasyon)...")
    gold_ci = bootstrap_ci(gold_results, compute_metrics, n_iter=args.bootstrap_n) if gold_results else {}
    heldout_ci = bootstrap_ci(heldout_results, compute_metrics, n_iter=args.bootstrap_n) if heldout_results else {}

    # Overfitting Gap
    overfitting_gaps = compute_overfitting_gap(gold_metrics, heldout_metrics)

    # Determinizm Testi
    determinism = None
    if not args.no_determinism:
        det_pool_path = args.gold if args.mode in ("both", "gold") and os.path.exists(args.gold) else args.heldout
        if os.path.exists(det_pool_path):
            det_pool = load_gold(det_pool_path)
            print(f"Determinizm testi ({args.determinism_runs}x run)...")
            determinism = determinism_test(
                retriever, det_pool, runs=args.determinism_runs, k=args.k
            )

    # Konsol ozeti
    print_console_summary(
        gold_metrics, heldout_metrics,
        gold_ci, heldout_ci,
        gold_by_cat, heldout_by_cat,
        overfitting_gaps,
    )

    # Dosya ciktilari
    os.makedirs(args.out_dir, exist_ok=True)
    print(f"Dosyalar kaydediliyor -> {args.out_dir}/")

    report_path = os.path.join(args.out_dir, "retrieval_eval_report.md")
    write_markdown_report(
        gold_results, heldout_results,
        gold_metrics, heldout_metrics,
        gold_ci, heldout_ci,
        gold_by_cat, heldout_by_cat,
        overfitting_gaps,
        determinism,
        config,
        out_path=report_path,
    )

    failure_path = os.path.join(args.out_dir, "failure_analysis.json")
    failure_data = build_failure_analysis(gold_results, heldout_results)
    with open(failure_path, "w", encoding="utf-8") as f:
        json.dump(failure_data, f, ensure_ascii=False, indent=2)
    print(f"  [JSON] Hata analizi: {failure_path}")

    if gold_results:
        save_csv(gold_results, os.path.join(args.out_dir, "raw_results_gold.csv"))
    if heldout_results:
        save_csv(heldout_results, os.path.join(args.out_dir, "raw_results_heldout.csv"))

    if determinism:
        det_path = os.path.join(args.out_dir, "determinism_test.json")
        with open(det_path, "w", encoding="utf-8") as f:
            json.dump(determinism, f, ensure_ascii=False, indent=2)
        print(f"  [JSON] Determinizm: {det_path}")

    if retriever_context is not None:
        retriever_context.__exit__(None, None, None)

    print(f"\neval_v2.py tamamlandi. Ciktilar: {args.out_dir}/\n")


if __name__ == "__main__":
    main()
