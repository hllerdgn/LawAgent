"""
eval_comparison.py — LawAgent Baseline vs Cross-Encoder Karşılaştırması
=========================================================================

Karşılaştırılan Sistemler:
  BASELINE: Dense + BM25 + Fusion + Boosting + Diversity Penalty
  NEW:      Dense + BM25 + Fusion + Boosting + Cross Encoder (BAAI/bge-reranker-base)

Metrikler:
  Hit@1, Hit@3, Hit@5, Hit@10, MRR, nDCG@10
  Latency: avg_ms, p50_ms, p95_ms

Dataset:
  Gold Set     : eval/gold_set.json          (38 sorgu)
  Held-Out Set : eval/gold_set_v2_heldout.json (45 sorgu)

Çıktı:
  eval/comparison_report.md

Kullanım:
  cd BACKEND
  python src/eval_comparison.py
  python src/eval_comparison.py --skip-cross   # Sadece baseline (hızlı)
  python src/eval_comparison.py --no-cache     # Önceki sonuçları kullanma
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# ─── Proje dizin ayarı ────────────────────────────────────────────────────────
_SRC_DIR     = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_SRC_DIR)
for _p in (_SRC_DIR, _BACKEND_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from retriever import LegalRetriever, normalize_article  # noqa: E402

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("LawAgent.Comparison")
for _lg in ("LawAgent.Retriever", "LawAgent.Embedder", "LawAgent.Reranker"):
    logging.getLogger(_lg).setLevel(logging.INFO)   # Reranker latency logları görünsün

# ─── Sabitler ─────────────────────────────────────────────────────────────────
GOLD_PATH    = os.path.join(_BACKEND_DIR, "eval", "gold_set.json")
HELDOUT_PATH = os.path.join(_BACKEND_DIR, "eval", "gold_set_v2_heldout.json")
CACHE_DIR    = os.path.join(_BACKEND_DIR, "eval", "comparison_cache")
OUT_PATH     = os.path.join(_BACKEND_DIR, "eval", "comparison_report.md")
TOP_K        = 10


# ══════════════════════════════════════════════════════════════════════════════
# VERİ YÜKLEME
# ══════════════════════════════════════════════════════════════════════════════


def load_dataset(path: str) -> List[Dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data


# ══════════════════════════════════════════════════════════════════════════════
# HIT & RANK YARDIMCILARI
# ══════════════════════════════════════════════════════════════════════════════


def _article_matches(expected, actual: str) -> bool:
    if expected is None:
        return False
    if isinstance(expected, list):
        return actual in expected
    return actual == expected


def is_hit(item: Dict, chunk: Dict) -> bool:
    if item.get("expected_source") == "yargitay":
        if item.get("expected_decision_id"):
            return chunk.get("source") == "yargitay" and chunk.get("decision_id") == item["expected_decision_id"]
        return chunk.get("source") == "yargitay"
    law_match = str(chunk.get("law", "")).upper() == str(item.get("expected_law", "")).upper()
    art_match = _article_matches(item.get("expected_article"), normalize_article(chunk.get("article_no")))
    return law_match and art_match


# ══════════════════════════════════════════════════════════════════════════════
# TEK SORGU ÇALIŞTIRMA
# ══════════════════════════════════════════════════════════════════════════════


def run_query(retriever: LegalRetriever, item: Dict, k: int = 10) -> Dict:
    t0 = time.perf_counter()
    try:
        chunks = retriever.retrieve(item["query"], k=k)
    except Exception as e:
        log.warning(f"Retrieve hatası '{item['query']}': {e}")
        chunks = []
    elapsed_ms = (time.perf_counter() - t0) * 1000

    rank: Optional[int] = None
    for i, c in enumerate(chunks, 1):
        if is_hit(item, c):
            rank = i
            break

    hit10 = any(is_hit(item, c) for c in chunks[:10])

    top5 = [
        {
            "law":        c.get("law", ""),
            "article_no": c.get("article_no", ""),
            "source":     c.get("source", ""),
            "skor":       round(c.get("skor", 0), 4),
            "cross_score": round(c.get("cross_score", 0), 4) if "cross_score" in c else None,
        }
        for c in chunks[:5]
    ]

    return {
        "id":               item.get("id"),
        "category":         item.get("category", "unknown"),
        "query":            item["query"],
        "expected_law":     item.get("expected_law"),
        "expected_article": item.get("expected_article"),
        "expected_source":  item.get("expected_source"),
        "rank":             rank,
        "hit10":            hit10,
        "elapsed_ms":       round(elapsed_ms, 1),
        "top5":             top5,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SET DEĞERLENDİRME
# ══════════════════════════════════════════════════════════════════════════════


def evaluate_set(
    retriever: LegalRetriever,
    dataset: List[Dict],
    label: str,
    k: int = 10,
) -> List[Dict]:
    results = []
    for i, item in enumerate(dataset, 1):
        preview = item["query"][:55]
        print(f"\r  [{label}] {i}/{len(dataset)} — {preview}...", end="", flush=True)
        results.append(run_query(retriever, item, k=k))
    print()
    return results


# ══════════════════════════════════════════════════════════════════════════════
# METRİK HESAPLAMA
# ══════════════════════════════════════════════════════════════════════════════


def compute_ndcg(results: List[Dict], k: int = 10) -> float:
    """
    nDCG@k hesaplaması.
    Binary relevance: doğru madde rank içindeyse rel=1, yoksa rel=0.
    İdeal DCG = 1 (her zaman top-1'de olsa), bu yüzden nDCG = DCG / IDCG.
    """
    total = 0.0
    n = len(results)
    if n == 0:
        return 0.0
    for r in results:
        rank = r.get("rank")
        if rank is not None and rank <= k:
            total += 1.0 / math.log2(rank + 1)
    idcg = 1.0  # Binary relevance: ideal = madde top-1'de → 1/log2(2) = 1.0
    return round(total / (n * idcg), 4)


def compute_p95_latency(results: List[Dict]) -> float:
    latencies = sorted(r["elapsed_ms"] for r in results)
    if not latencies:
        return 0.0
    idx = min(int(math.ceil(0.95 * len(latencies))), len(latencies)) - 1
    return round(latencies[max(0, idx)], 1)


def compute_metrics(results: List[Dict], k_values: Tuple = (1, 3, 5, 10)) -> Dict:
    n = len(results)
    if n == 0:
        return {"n": 0}

    metrics: Dict[str, Any] = {"n": n}
    for k in k_values:
        hits = sum(1 for r in results if r.get("rank") is not None and r["rank"] <= k)
        metrics[f"Hit@{k}"] = round(hits / n, 4)

    mrr_vals = [1.0 / r["rank"] for r in results if r.get("rank")]
    metrics["MRR"] = round(sum(mrr_vals) / n, 4) if mrr_vals else 0.0

    metrics["nDCG@10"] = compute_ndcg(results, k=10)

    latencies = [r["elapsed_ms"] for r in results]
    metrics["avg_latency_ms"] = round(sum(latencies) / n, 1) if latencies else 0.0
    metrics["p50_latency_ms"] = round(sorted(latencies)[n // 2], 1) if latencies else 0.0
    metrics["p95_latency_ms"] = compute_p95_latency(results)

    return metrics


def compute_by_category(results: List[Dict]) -> Dict[str, Dict]:
    by_cat: Dict[str, List] = defaultdict(list)
    for r in results:
        by_cat[r.get("category", "other")].append(r)
    return {cat: compute_metrics(items) for cat, items in sorted(by_cat.items())}


# ══════════════════════════════════════════════════════════════════════════════
# KAYIP / KAZANÇ ANALİZİ
# ══════════════════════════════════════════════════════════════════════════════


def compare_queries(
    baseline_results: List[Dict],
    new_results: List[Dict],
) -> Dict[str, List[Dict]]:
    """
    Her sorgu için baseline vs yeni sistem sonuçlarını karşılaştırır.
    Returns:
        improved: Cross-encoder Hit@1 kazandı
        regressed: Cross-encoder Hit@1 kaybetti
        unchanged_success: Her iki sistemde de başarılı
        unchanged_failure: Her iki sistemde de başarısız
    """
    b_by_id = {r["id"]: r for r in baseline_results}
    n_by_id = {r["id"]: r for r in new_results}

    improved: List[Dict] = []
    regressed: List[Dict] = []
    unchanged_success: List[Dict] = []
    unchanged_failure: List[Dict] = []

    for qid, b in b_by_id.items():
        n = n_by_id.get(qid)
        if not n:
            continue

        b_hit1 = b.get("rank") is not None and b["rank"] <= 1
        n_hit1 = n.get("rank") is not None and n["rank"] <= 1

        entry = {
            "id":               qid,
            "query":            b["query"],
            "category":         b.get("category"),
            "expected":         f"{b.get('expected_law', '')} m.{b.get('expected_article', '')}",
            "baseline_rank":    b.get("rank"),
            "new_rank":         n.get("rank"),
            "baseline_top1":    f"{b['top5'][0]['law']} m.{b['top5'][0]['article_no']}" if b.get("top5") else "?",
            "new_top1":         f"{n['top5'][0]['law']} m.{n['top5'][0]['article_no']}" if n.get("top5") else "?",
            "baseline_latency": b.get("elapsed_ms"),
            "new_latency":      n.get("elapsed_ms"),
        }

        if not b_hit1 and n_hit1:
            improved.append(entry)
        elif b_hit1 and not n_hit1:
            regressed.append(entry)
        elif b_hit1 and n_hit1:
            unchanged_success.append(entry)
        else:
            unchanged_failure.append(entry)

    return {
        "improved":           improved,
        "regressed":          regressed,
        "unchanged_success":  unchanged_success,
        "unchanged_failure":  unchanged_failure,
    }


def build_failure_detail(baseline_results: List[Dict], new_results: List[Dict]) -> List[Dict]:
    """
    Yalnızca baseline'da başarısız ama cross-encoder ile değişen sorguları detaylı inceler.
    Hard negative analizi için: top-10'a girmiş ama Hit@1 olamamış sorgular.
    """
    b_by_id = {r["id"]: r for r in baseline_results}
    n_by_id = {r["id"]: r for r in new_results}

    hard_negatives = []
    for qid, b in b_by_id.items():
        b_hit1  = b.get("rank") is not None and b["rank"] <= 1
        b_hit10 = b.get("hit10", False)
        if b_hit1:
            continue
        # Sadece reranking failure (top-10'da ama üste çıkamamış)
        if not b_hit10:
            continue

        n = n_by_id.get(qid, {})
        hard_negatives.append({
            "id":            qid,
            "query":         b["query"],
            "category":      b.get("category"),
            "expected":      f"{b.get('expected_law', '')} m.{b.get('expected_article', '')}",
            "baseline_rank": b.get("rank", "not_in_10"),
            "new_rank":      n.get("rank", "not_in_10"),
            "resolved":      n.get("rank") is not None and n["rank"] <= 1,
            "baseline_top5": b.get("top5", []),
            "new_top5":      n.get("top5", []),
        })
    return hard_negatives


# ══════════════════════════════════════════════════════════════════════════════
# CACHE YÖNETME
# ══════════════════════════════════════════════════════════════════════════════


def save_cache(results: List[Dict], name: str) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def load_cache(name: str) -> Optional[List[Dict]]:
    path = os.path.join(CACHE_DIR, f"{name}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


# ══════════════════════════════════════════════════════════════════════════════
# MARKDOWN RAPOR
# ══════════════════════════════════════════════════════════════════════════════


def _delta(new_val: float, base_val: float) -> str:
    """Fark: +yeşil / -kırmızı gibi işaret. Markdown'da renk yok, sembol kullan."""
    d = new_val - base_val
    if d > 0:
        return f"+{d:.4f} ▲"
    elif d < 0:
        return f"{d:.4f} ▼"
    return "±0.0000 ="


def _rank_display(rank) -> str:
    if rank is None or rank == "not_in_10":
        return "—"
    return f"#{rank}"


def write_report(
    gold_base:     Dict,
    gold_new:      Dict,
    held_base:     Dict,
    held_new:      Dict,
    gold_compare:  Dict,
    held_compare:  Dict,
    gold_hn:       List[Dict],
    held_hn:       List[Dict],
    gold_base_cat: Dict,
    gold_new_cat:  Dict,
    held_base_cat: Dict,
    held_new_cat:  Dict,
    out_path:      str,
) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []

    # ── Başlık ─────────────────────────────────────────────────────────────────
    lines += [
        "# LawAgent AI — Baseline vs Cross-Encoder Karşılaştırma Raporu",
        "",
        f"> **Oluşturma Tarihi:** {now}",
        f"> **Metodoloji:** eval_comparison.py  ",
        f"> **Cross-Encoder Modeli:** BAAI/bge-reranker-base (Fallback: ms-marco-MiniLM-L-6-v2)  ",
        f"> **Kandidat Penceresi:** Top-30 (Asla tüm corpus değil)",
        "",
    ]

    # ── 1. Sistem Karşılaştırması ───────────────────────────────────────────────
    lines += [
        "## 1. Sistem Mimarisi Karşılaştırması",
        "",
        "| Katman | BASELINE | YENİ SYSTEM |",
        "|--------|----------|-------------|",
        "| Dense Retrieval | ✅ Mürşit-Base-TR | ✅ Mürşit-Base-TR |",
        "| BM25+ | ✅ Custom BM25+ | ✅ Custom BM25+ |",
        "| Hybrid Fusion | ✅ Dinamik alpha | ✅ Dinamik alpha |",
        "| Boosting | ✅ Prob. kanun ağırlıklaması | ✅ Prob. kanun ağırlıklaması |",
        "| Diversity Penalty | ✅ Aktif (0.05/aday) | ❌ Kapalı (Cross-Encoder varken gereksiz) |",
        "| Cross-Encoder | ❌ Kapalı | ✅ BAAI/bge-reranker-base, Top-30 |",
        "",
    ]

    # ── 2. Metrik Tablosu ───────────────────────────────────────────────────────
    METRICS = ["Hit@1", "Hit@3", "Hit@5", "Hit@10", "MRR", "nDCG@10"]
    LAT_METRICS = ["avg_latency_ms", "p50_latency_ms", "p95_latency_ms"]

    def metric_row(m_key, gold_b, gold_n, held_b, held_n, is_latency=False):
        gb = gold_b.get(m_key, 0.0)
        gn = gold_n.get(m_key, 0.0)
        hb = held_b.get(m_key, 0.0)
        hn = held_n.get(m_key, 0.0)
        if is_latency:
            return (
                f"| {m_key} | {gb} ms | {gn} ms | — | "
                f"{hb} ms | {hn} ms | — |"
            )
        return (
            f"| **{m_key}** | {gb:.4f} | {gn:.4f} | {_delta(gn, gb)} | "
            f"{hb:.4f} | {hn:.4f} | {_delta(hn, hb)} |"
        )

    lines += [
        "## 2. Metrik Tablosu",
        "",
        "> Not: Held-Out set overfitting'e karşı dayanıklı gerçek genelleme metriğidir.",
        "",
        "| Metrik | Gold-Baseline | Gold-Cross | Gold Δ | Held-Baseline | Held-Cross | Held Δ |",
        "|--------|---------------|------------|--------|---------------|------------|--------|",
    ]
    for m in METRICS:
        lines.append(metric_row(m, gold_base, gold_new, held_base, held_new))
    for m in LAT_METRICS:
        lines.append(metric_row(m, gold_base, gold_new, held_base, held_new, is_latency=True))
    lines.append("")

    # ── Overfitting gap ─────────────────────────────────────────────────────────
    lines += ["### Overfitting Gap (Gold − Held-Out)", ""]
    lines += [
        "| Metrik | Baseline Gap | Cross-Encoder Gap | Gap Değişimi |",
        "|--------|-------------|-------------------|--------------|",
    ]
    for m in METRICS:
        b_gap = round((gold_base.get(m, 0) - held_base.get(m, 0)), 4)
        n_gap = round((gold_new.get(m, 0)  - held_new.get(m, 0)),  4)
        flag = " ⚠️" if abs(n_gap) > 0.15 else ""
        lines.append(f"| {m} | {b_gap:+.4f} | {n_gap:+.4f}{flag} | {_delta(n_gap, b_gap)} |")
    lines.append("")

    # ── 3. Kazanç/Kayıp Analizi ────────────────────────────────────────────────
    lines += ["## 3. Kazanç / Kayıp Analizi (Held-Out)", ""]

    hc = held_compare
    n_total   = len(hc["improved"]) + len(hc["regressed"]) + len(hc["unchanged_success"]) + len(hc["unchanged_failure"])
    n_imp     = len(hc["improved"])
    n_reg     = len(hc["regressed"])
    n_unch_ok = len(hc["unchanged_success"])
    n_unch_fa = len(hc["unchanged_failure"])

    lines += [
        f"| Durum | Sorgu Sayısı | Oran |",
        f"|-------|-------------|------|",
        f"| ✅ Cross-Encoder iyileştirdi (Hit@1 kazanıldı) | {n_imp} | {n_imp/max(n_total,1)*100:.1f}% |",
        f"| ❌ Cross-Encoder bozdu (Hit@1 kaybedildi) | {n_reg} | {n_reg/max(n_total,1)*100:.1f}% |",
        f"| 🔄 Her iki sistemde başarılı | {n_unch_ok} | {n_unch_ok/max(n_total,1)*100:.1f}% |",
        f"| 🔄 Her iki sistemde başarısız | {n_unch_fa} | {n_unch_fa/max(n_total,1)*100:.1f}% |",
        "",
    ]

    # İyileştirme örnekleri
    if hc["improved"]:
        lines += ["### ✅ Cross-Encoder'ın İyileştirdiği Sorgular (Held-Out)", ""]
        lines += [
            "| Sorgu | Beklenen | Baseline Rank | CE Rank |",
            "|-------|---------|---------------|---------|",
        ]
        for e in hc["improved"][:10]:
            q = e["query"][:60]
            lines.append(
                f"| {q} | {e['expected']} | "
                f"{_rank_display(e['baseline_rank'])} | {_rank_display(e['new_rank'])} |"
            )
        lines.append("")

    # Gerileme örnekleri
    if hc["regressed"]:
        lines += [
            "### ❌ Cross-Encoder'ın Bozduğu Sorgular (Held-Out)",
            "",
            "> Bu sorgular için neden gerileme yaşandığı Bölüm 5'te analiz edilmektedir.",
            "",
            "| Sorgu | Beklenen | Baseline Rank | CE Rank | Baseline Top-1 | CE Top-1 |",
            "|-------|---------|---------------|---------|----------------|----------|",
        ]
        for e in hc["regressed"]:
            q = e["query"][:55]
            lines.append(
                f"| {q} | {e['expected']} | "
                f"{_rank_display(e['baseline_rank'])} | {_rank_display(e['new_rank'])} | "
                f"{e['baseline_top1']} | {e['new_top1']} |"
            )
        lines.append("")

    # ── 4. Hard Negative Örnekleri ────────────────────────────────────────────
    lines += [
        "## 4. Hard Negative Örnekleri (Held-Out Reranking Failures)",
        "",
        "> Hard negative: Doğru madde top-10'a giriyor ama üste çıkamıyor.",
        "> Bu bölüm baseline'da reranking failure olan sorguların cross-encoder ile nasıl değiştiğini gösterir.",
        "",
    ]

    if held_hn:
        lines += [
            "| # | Sorgu | Beklenen | Baseline Rank | CE Rank | CE Çözüldü? |",
            "|---|-------|---------|---------------|---------|------------|",
        ]
        for i, hn in enumerate(held_hn, 1):
            q = hn["query"][:55]
            resolved = "✅ Evet" if hn["resolved"] else "❌ Hayır"
            lines.append(
                f"| {i} | {q} | {hn['expected']} | "
                f"{_rank_display(hn['baseline_rank'])} | "
                f"{_rank_display(hn['new_rank'])} | {resolved} |"
            )
        lines.append("")

        resolved_count = sum(1 for h in held_hn if h["resolved"])
        lines += [
            f"> **Özet:** {len(held_hn)} hard negative sorgudan {resolved_count} tanesi "
            f"({resolved_count/max(len(held_hn),1)*100:.1f}%) Cross-Encoder tarafından çözüldü.",
            "",
        ]

        # Detaylı örnek (ilk 3 hard negative)
        lines += ["### Detaylı Hard Negative İncelemesi (İlk 3)", ""]
        for hn in held_hn[:3]:
            lines += [
                f"**Sorgu:** {hn['query']}  ",
                f"**Beklenen:** {hn['expected']} | **Baseline Rank:** {_rank_display(hn['baseline_rank'])} | **CE Rank:** {_rank_display(hn['new_rank'])}  ",
                "",
                "| Sıra | Baseline Top-5 | Skor |  CE Top-5 | Skor | CE Cross-Score |",
                "|------|---------------|------|-----------|------|----------------|",
            ]
            bt5 = hn.get("baseline_top5", [])
            nt5 = hn.get("new_top5", [])
            for j in range(max(len(bt5), len(nt5))):
                b_entry = bt5[j] if j < len(bt5) else {}
                n_entry = nt5[j] if j < len(nt5) else {}
                b_label = f"{b_entry.get('law','')} m.{b_entry.get('article_no','')}" if b_entry else "—"
                n_label = f"{n_entry.get('law','')} m.{n_entry.get('article_no','')}" if n_entry else "—"
                b_skor  = b_entry.get("skor", "—")
                n_skor  = n_entry.get("skor", "—")
                cs      = n_entry.get("cross_score", "—")
                lines.append(f"| {j+1} | {b_label} | {b_skor} | {n_label} | {n_skor} | {cs} |")
            lines.append("")
    else:
        lines += ["> Baseline'da reranking failure bulunamadı (tüm sorgular Hit@1 başarılı).", ""]

    # ── 5. Performans Düşüşü Analizi ─────────────────────────────────────────
    lines += ["## 5. Performans Analizi", ""]

    held_hit1_delta = held_new.get("Hit@1", 0) - held_base.get("Hit@1", 0)
    held_mrr_delta  = held_new.get("MRR", 0)   - held_base.get("MRR", 0)
    lat_delta       = held_new.get("avg_latency_ms", 0) - held_base.get("avg_latency_ms", 0)

    if held_hit1_delta > 0:
        lines += [
            "### ✅ Cross-Encoder Performansı Artırdı",
            "",
            f"- Held-Out Hit@1: **{_delta(held_new.get('Hit@1',0), held_base.get('Hit@1',0))}**",
            f"- Held-Out MRR: **{_delta(held_new.get('MRR',0), held_base.get('MRR',0))}**",
            f"- Latency artışı (avg): **+{lat_delta:.0f}ms** (model ilk çağrıda yükleniyor, sonraki çağrılarda daha hızlı)",
            "",
        ]
    elif held_hit1_delta < 0:
        lines += [
            "### ⚠️ Cross-Encoder Performansı Düşürdü — Kök Neden Analizi",
            "",
            f"- Held-Out Hit@1: **{_delta(held_new.get('Hit@1',0), held_base.get('Hit@1',0))}**",
            "",
            "**Olası nedenler:**",
            "",
            "1. **Dil Uyumsuzluğu:** `BAAI/bge-reranker-base` ağırlıklı olarak İngilizce/Çince verilerle eğitilmiştir.",
            "   Türkçe hukuki terminoloji (cayma hakkı, temerrüt, borç ilişkisi) için suboptimal scoring yapabilir.",
            "   **Çözüm:** Türkçe-bilinçli cross-encoder modeli fine-tune etmek veya query'i İngilizceye çevirip sormak.",
            "",
            "2. **Madde Numarası Yanıltıcılığı:** Cross-encoder document metnini değil başlığı puanlıyor olabilir.",
            "   Örnek: 'TBK m.472 eser teslimi' vs 'TBK m.474 ayıp bildirimi' — ikisi de semantik olarak yakın.",
            "   **Çözüm:** Document format'a madde numarasını daha belirgin şekilde yerleştirmek.",
            "",
            "3. **Aday Havuzu Sorunu:** Fusion+Boosting zaten doğru maddeyi #1-3 arası getiriyorsa,",
            "   Cross-encoder'ın bu sırayı bozması mümkün. Diversity Penalty'nin kaldırılması da etken olabilir.",
            "   **Çözüm:** Cross-encoder'ı sadece #3-10 arası için uygulamak (ilk 2'yi koru).",
            "",
            "4. **Gerileme Örnekleri:**",
            "",
        ]
        for e in hc["regressed"]:
            lines += [
                f"   - `{e['query'][:70]}`",
                f"     Beklenen: {e['expected']} | Baseline: {_rank_display(e['baseline_rank'])} → CE: {_rank_display(e['new_rank'])}",
                f"     Baseline Top-1: `{e['baseline_top1']}` | CE Top-1: `{e['new_top1']}`",
                "",
            ]
    else:
        lines += [
            "### 🔄 Cross-Encoder Performansı Değiştirmedi",
            "",
            "Hit@1 metriği değişmedi. Cross-encoder mevcut ranking'i korumaktadır.",
            "",
        ]

    # Latency analizi
    lines += [
        "### ⏱️ Latency Analizi",
        "",
        "| Metrik | Baseline | Cross-Encoder | Artış |",
        "|--------|----------|---------------|-------|",
    ]
    for lm in ["avg_latency_ms", "p50_latency_ms", "p95_latency_ms"]:
        bv = held_base.get(lm, 0)
        nv = held_new.get(lm, 0)
        lines.append(f"| {lm} | {bv} ms | {nv} ms | {_delta(nv, bv).replace('▲','').replace('▼','').strip()} ms |")
    lines += [
        "",
        "> **Not:** İlk sorgu model yüklemesini içerdiğinden yüksek görünebilir.",
        "> Warm-start sonrası p50 ve p95 daha güvenilir latency metriğidir.",
        "> BAAI/bge-reranker-base: ~270MB, CPU'da top-30 için yaklaşık 800-2000ms.",
        "",
    ]

    # ── Kategori Bazlı Kırılım ───────────────────────────────────────────────
    lines += ["## 6. Kategori Bazlı Kırılım (Held-Out)", ""]
    all_cats = sorted(set(list(held_base_cat.keys()) + list(held_new_cat.keys())))
    lines += [
        "| Kategori | n | Base-Hit@1 | CE-Hit@1 | Δ | Base-MRR | CE-MRR | Δ |",
        "|----------|---|-----------|---------|---|---------|--------|---|",
    ]
    for cat in all_cats:
        bm = held_base_cat.get(cat, {})
        nm = held_new_cat.get(cat, {})
        n  = bm.get("n", nm.get("n", 0))
        bh = bm.get("Hit@1", 0.0)
        nh = nm.get("Hit@1", 0.0)
        bm_ = bm.get("MRR", 0.0)
        nm_ = nm.get("MRR", 0.0)
        warn = " ⚠️" if n <= 5 else ""
        lines.append(
            f"| {cat}{warn} | {n} | {bh:.3f} | {nh:.3f} | {_delta(nh, bh)} | "
            f"{bm_:.3f} | {nm_:.3f} | {_delta(nm_, bm_)} |"
        )
    lines += [
        "",
        "> ⚠️ = n≤5 kategorilerinde yüzde değerleri yanıltıcı olabilir.",
        "",
    ]

    # ── Sonuç ────────────────────────────────────────────────────────────────
    lines += [
        "## 7. Sonuç ve Öneriler",
        "",
    ]

    if held_hit1_delta > 0.05:
        lines += [
            "**✅ Cross-Encoder Önerilir:** Held-Out Hit@1 metriğinde anlamlı iyileşme sağlandı.",
            "",
            "Önerilen next steps:",
            "- [ ] Cross-encoder'ı production'da etkinleştir (`ENABLE_CROSS_RERANK=true`)",
            "- [ ] Gerileme örneklerini incele ve document format'ı optimize et",
            "- [ ] Türkçe hukuk verisiyle fine-tune için `hard_negatives.json` kullan",
        ]
    elif held_hit1_delta < -0.03:
        lines += [
            "**❌ Cross-Encoder Şu An Önerilmez:** Held-Out metriklerinde gerileme gözlemlendi.",
            "",
            "Öncelikli aksiyonlar:",
            "- [ ] Türkçe hukuk verisine uygun cross-encoder modeli araştır (STS-TR, multilingual modeller)",
            "- [ ] Document format'ı zenginleştir (madde başlığı, kanun tam adı)",
            "- [ ] Cross-encoder'ı sadece top 5-10 arası için uygula (ilk sonuçları koru)",
            "- [ ] Diversity Penalty'yi cross-encoder ile birlikte değil ardından kullan",
        ]
    else:
        lines += [
            "**🔄 Cross-Encoder Nötr Etkili:** Anlamlı bir değişim gözlemlenmedi (+/-3%).",
            "",
            "Öneriler:",
            "- [ ] Türkçe fine-tuned cross-encoder dene",
            "- [ ] Sadece reranking failure olan sorgulara cross-encoder uygula (seçici)",
            "- [ ] `hard_negatives.json` ile contrastive fine-tuning pipeline'ı kur",
        ]
    lines += [""]

    # Yaz
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n  [✓] Rapor yazıldı: {out_path}")


# ══════════════════════════════════════════════════════════════════════════════
# KONSOL ÖZETİ
# ══════════════════════════════════════════════════════════════════════════════


def print_summary(gold_base, gold_new, held_base, held_new):
    SEP = "=" * 78
    METRICS = ["Hit@1", "Hit@3", "Hit@5", "Hit@10", "MRR", "nDCG@10"]

    print(f"\n{SEP}")
    print("  BASELINE vs CROSS-ENCODER KARSILASTIRMASı")
    print(SEP)
    print(f"\n  {'Metrik':<12} {'Gold-BASE':>10} {'Gold-CE':>10} {'Gold-Δ':>10}  "
          f"{'Held-BASE':>10} {'Held-CE':>10} {'Held-Δ':>10}")
    print(f"  {'-'*76}")
    for m in METRICS:
        gb = gold_base.get(m, 0.0)
        gn = gold_new.get(m,  0.0)
        hb = held_base.get(m, 0.0)
        hn = held_new.get(m,  0.0)
        gd = gn - gb
        hd = hn - hb
        g_mark = "▲" if gd > 0 else ("▼" if gd < 0 else "=")
        h_mark = "▲" if hd > 0 else ("▼" if hd < 0 else "=")
        print(
            f"  {m:<12} {gb:>10.4f} {gn:>10.4f} {gd:>+9.4f}{g_mark}  "
            f"{hb:>10.4f} {hn:>10.4f} {hd:>+9.4f}{h_mark}"
        )

    print(f"\n  {'Latency':<20} {'Baseline':>10} {'CE':>10} {'Δ':>10}")
    print(f"  {'-'*50}")
    for lm in ["avg_latency_ms", "p95_latency_ms"]:
        bv = held_base.get(lm, 0)
        nv = held_new.get(lm, 0)
        print(f"  {lm:<20} {bv:>10.1f} {nv:>10.1f} {(nv-bv):>+9.1f} ms")

    print(f"\n{SEP}\n")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="LawAgent Baseline vs Cross-Encoder Karşılaştırması"
    )
    parser.add_argument("--skip-cross", action="store_true",
                        help="Cross-encoder'ı çalıştırma, sadece baseline")
    parser.add_argument("--no-cache",   action="store_true",
                        help="Önceki sonuçları kullanma, baştan çalıştır")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--gold",    default=GOLD_PATH)
    parser.add_argument("--heldout", default=HELDOUT_PATH)
    parser.add_argument("--out",     default=OUT_PATH)
    args = parser.parse_args()

    print("\n" + "="*70)
    print("  LawAgent — Baseline vs Cross-Encoder Karşılaştırması")
    print("="*70)

    # ── Veri yükle ────────────────────────────────────────────────────────────
    if not os.path.exists(args.gold) or not os.path.exists(args.heldout):
        print(f"\nHATA: Dataset bulunamadı:\n  {args.gold}\n  {args.heldout}")
        sys.exit(1)

    gold_data    = load_dataset(args.gold)
    heldout_data = load_dataset(args.heldout)
    print(f"\n  Gold Set:     {len(gold_data)} sorgu")
    print(f"  Held-Out Set: {len(heldout_data)} sorgu")

    # ── Retriever başlat ──────────────────────────────────────────────────────
    print("\n  Retriever yükleniyor (Qdrant + Embedder)...")
    t0 = time.perf_counter()
    retriever = LegalRetriever()
    print(f"  Retriever hazır ({(time.perf_counter()-t0)*1000:.0f}ms)\n")

    # ══════════════════════════════════════════════════════════════════════════
    # BASELINE (ENABLE_CROSS_RERANK=false)
    # ══════════════════════════════════════════════════════════════════════════
    os.environ["ENABLE_CROSS_RERANK"] = "false"
    os.environ["ENABLE_LLM_RERANK"]   = "false"

    gold_base_results    = load_cache("gold_baseline")    if not args.no_cache else None
    heldout_base_results = load_cache("heldout_baseline") if not args.no_cache else None

    if gold_base_results is None:
        print("  [BASELINE] Gold Set değerlendiriliyor...")
        gold_base_results = evaluate_set(retriever, gold_data, "BASELINE-GOLD", args.k)
        save_cache(gold_base_results, "gold_baseline")

    if heldout_base_results is None:
        print("  [BASELINE] Held-Out Set değerlendiriliyor...")
        heldout_base_results = evaluate_set(retriever, heldout_data, "BASELINE-HELD", args.k)
        save_cache(heldout_base_results, "heldout_baseline")

    # ══════════════════════════════════════════════════════════════════════════
    # CROSS-ENCODER (ENABLE_CROSS_RERANK=true)
    # ══════════════════════════════════════════════════════════════════════════
    gold_new_results    = None
    heldout_new_results = None

    if not args.skip_cross:
        os.environ["ENABLE_CROSS_RERANK"] = "true"

        gold_new_results    = load_cache("gold_cross")    if not args.no_cache else None
        heldout_new_results = load_cache("heldout_cross") if not args.no_cache else None

        if gold_new_results is None:
            print("\n  [CROSS-ENCODER] Gold Set değerlendiriliyor (model yükleniyor)...")
            gold_new_results = evaluate_set(retriever, gold_data, "CROSS-GOLD", args.k)
            save_cache(gold_new_results, "gold_cross")

        if heldout_new_results is None:
            print("  [CROSS-ENCODER] Held-Out Set değerlendiriliyor...")
            heldout_new_results = evaluate_set(retriever, heldout_data, "CROSS-HELD", args.k)
            save_cache(heldout_new_results, "heldout_cross")

        os.environ["ENABLE_CROSS_RERANK"] = "false"  # reset

    # Fallback: cross sonuç yoksa baseline ile aynı al (raporu yine de yaz)
    if gold_new_results is None:
        gold_new_results    = gold_base_results
    if heldout_new_results is None:
        heldout_new_results = heldout_base_results

    # ── Metrikler ─────────────────────────────────────────────────────────────
    print("\n  Metrikler hesaplanıyor...")
    gold_base_m    = compute_metrics(gold_base_results)
    gold_new_m     = compute_metrics(gold_new_results)
    held_base_m    = compute_metrics(heldout_base_results)
    held_new_m     = compute_metrics(heldout_new_results)

    gold_base_cat  = compute_by_category(gold_base_results)
    gold_new_cat   = compute_by_category(gold_new_results)
    held_base_cat  = compute_by_category(heldout_base_results)
    held_new_cat   = compute_by_category(heldout_new_results)

    # ── Karşılaştırma ─────────────────────────────────────────────────────────
    gold_compare = compare_queries(gold_base_results, gold_new_results)
    held_compare = compare_queries(heldout_base_results, heldout_new_results)

    gold_hn = build_failure_detail(gold_base_results, gold_new_results)
    held_hn = build_failure_detail(heldout_base_results, heldout_new_results)

    # ── Konsol özeti ──────────────────────────────────────────────────────────
    print_summary(gold_base_m, gold_new_m, held_base_m, held_new_m)

    # ── Rapor yaz ─────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    write_report(
        gold_base=gold_base_m,   gold_new=gold_new_m,
        held_base=held_base_m,   held_new=held_new_m,
        gold_compare=gold_compare, held_compare=held_compare,
        gold_hn=gold_hn,         held_hn=held_hn,
        gold_base_cat=gold_base_cat, gold_new_cat=gold_new_cat,
        held_base_cat=held_base_cat, held_new_cat=held_new_cat,
        out_path=args.out,
    )

    print(f"  Tüm işlem tamamlandı.\n")


if __name__ == "__main__":
    main()
