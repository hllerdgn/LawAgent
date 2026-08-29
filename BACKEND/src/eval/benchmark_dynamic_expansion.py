"""
benchmark_dynamic_expansion.py — Dinamik Step-Back ve Hukuki Kavram Genisletme Benchmark
========================================================================================
Bu betik, LawAgent AI Retriever motorunda:
1. Ham Sorgu (Genisletmesiz Baseline)
2. Dinamik Step-Back & Legal Concept Expansion (Yeni Groq Destekli Model)

yontemlerini 30 kapsamli hukuki soru uzerinde karsilastirir ve Recall@10, MRR@10,
Hit Rate@10, Hit Rate@1, Precision@10 ve gecikme metriklerini raporlar.
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict

# UTF-8 stdout fix for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Path ayarlari
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_SRC_DIR = Path(__file__).resolve().parent.parent
for p in [str(_BACKEND_DIR), str(_SRC_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from src.retriever import LegalRetriever, normalize_article, expand_query_step_back
from config.settings import settings

# ── Ground Truth Hukuki Test Kumesi (30 Kapsamli Soru) ─────────────────────────

BENCHMARK_DATASET = [
    {
        "id": "TBK-01",
        "query": "Borçlu temerrüdünün genel şartları ve ihtarsız temerrüt halleri",
        "relevant": [("TBK", "117")]
    },
    {
        "id": "TBK-02",
        "query": "Temerrüde düşen borçlunun gecikme tazminatı ve gecikme faizi sorumluluğu",
        "relevant": [("TBK", "118"), ("TBK", "120")]
    },
    {
        "id": "TBK-03",
        "query": "Karşılıklı borç yükleyen sözleşmelerde temerrüt ek süre ve seçimlik haklar",
        "relevant": [("TBK", "123"), ("TBK", "124"), ("TBK", "125")]
    },
    {
        "id": "TBK-04",
        "query": "Kira sözleşmesinde kiracının temerrüdü ve tahliye ihtarı süresi",
        "relevant": [("TBK", "315")]
    },
    {
        "id": "TBK-05",
        "query": "Kira bedelinin belirlenmesi ve kira tespit davası beş yıllık sınır",
        "relevant": [("TBK", "344"), ("TBK", "345")]
    },
    {
        "id": "TBK-06",
        "query": "Konut kiralarında sözleşmenin bildirim yoluyla feshi ve 10 yıllık uzama",
        "relevant": [("TBK", "347")]
    },
    {
        "id": "TBK-07",
        "query": "Kiralananın gereksinim ihtiyaç sebebiyle tahliyesi ve yeniden kiralama yasağı",
        "relevant": [("TBK", "350"), ("TBK", "355")]
    },
    {
        "id": "TBK-08",
        "query": "Taşınır satışında ayıplı mal karşısında alıcının seçimlik hakları",
        "relevant": [("TBK", "227")]
    },
    {
        "id": "TBK-09",
        "query": "Haksız fiil sorumluluğunun unsurları hukuka aykırılık zarar ve kusur",
        "relevant": [("TBK", "49")]
    },
    {
        "id": "TBK-10",
        "query": "Sebepsiz zenginleşmeden doğan iade istemi ve zamanaşımı süreleri",
        "relevant": [("TBK", "77"), ("TBK", "82")]
    },
    {
        "id": "TBK-11",
        "query": "Borcun hiç veya gereği gibi ifa edilmemesi borçlunun sorumluluğu",
        "relevant": [("TBK", "112")]
    },
    {
        "id": "TBK-12",
        "query": "Aşırı ifa güçlüğü sözleşmenin yeni koşullara uyarlanması ve fesih",
        "relevant": [("TBK", "138")]
    },
    {
        "id": "TBK-13",
        "query": "Borçlar hukukunda takasın şartları ve takas beyanı",
        "relevant": [("TBK", "139"), ("TBK", "143")]
    },
    {
        "id": "TBK-14",
        "query": "Müteselsil borçlulukta alacaklının hakları ve borçlular arası rücu",
        "relevant": [("TBK", "162"), ("TBK", "167")]
    },
    {
        "id": "TBK-15",
        "query": "Alacağın devri temliki geçerlilik şekli ve borçluya bildirim",
        "relevant": [("TBK", "183"), ("TBK", "184"), ("TBK", "186")]
    },
    # ── TKHK (Tuketici Hukuku) ──────────────────────────────────────────────
    {
        "id": "TKHK-01",
        "query": "Tüketici işlemlerinde ayıplı mal ve tüketicinin dört seçimlik hakkı",
        "relevant": [("TKHK", "11")]
    },
    {
        "id": "TKHK-02",
        "query": "İnternetten mesafeli sözleşmelerde tüketicinin 14 günlük cayma hakkı",
        "relevant": [("TKHK", "48"), ("TKHK", "15")]
    },
    {
        "id": "TKHK-03",
        "query": "Tüketici kredisi sözleşmelerinde cayma hakkı ve erken ödeme indirimi",
        "relevant": [("TKHK", "24"), ("TKHK", "27")]
    },
    {
        "id": "TKHK-04",
        "query": "Tüketici hakem heyetine başvuru parasal sınırlar ve bağlayıcılık",
        "relevant": [("TKHK", "68"), ("TKHK", "70")]
    },
    {
        "id": "TKHK-05",
        "query": "Tüketici hukukunda garanti belgesi zorunluluğu ve azami tamir süresi",
        "relevant": [("TKHK", "56"), ("TKHK", "58")]
    },
    # ── TTK (Ticaret Hukuku) ────────────────────────────────────────────────
    {
        "id": "TTK-01",
        "query": "Ticari iş karinesi ve tacir olmanın genel hükümleri",
        "relevant": [("TTK", "18"), ("TTK", "19")]
    },
    {
        "id": "TTK-02",
        "query": "Tacirler arası ihbar ve ihtarlar noter telgraf ve iadeli mektup",
        "relevant": [("TTK", "18")]
    },
    {
        "id": "TTK-03",
        "query": "Anonim şirketlerde yönetim kurulunun devredilemez ve vazgeçilemez görevleri",
        "relevant": [("TTK", "375")]
    },
    {
        "id": "TTK-04",
        "query": "Anonim şirket genel kurul kararlarının iptali ve butlan davaları",
        "relevant": [("TTK", "445"), ("TTK", "446"), ("TTK", "447")]
    },
    {
        "id": "TTK-05",
        "query": "Limited şirkette esas sermaye payının devri ve genel kurul onayı",
        "relevant": [("TTK", "595")]
    },
    {
        "id": "TTK-06",
        "query": "Ticari defterlerin ibrazı açılış kapanış onayları ve delil olma niteliği",
        "relevant": [("TTK", "64"), ("TTK", "83"), ("TTK", "84")]
    },
    {
        "id": "TTK-07",
        "query": "Türk Ticaret Kanunu haksız rekabet halleri ve açılabilecek davalar",
        "relevant": [("TTK", "54"), ("TTK", "55"), ("TTK", "56")]
    },
    {
        "id": "TTK-08",
        "query": "Bono ve poliçede bulunması zorunlu yasal unsurlar",
        "relevant": [("TTK", "776"), ("TTK", "671")]
    },
    {
        "id": "TTK-09",
        "query": "Kambiyo senetlerinde aval verenin sorumluluğu ve zamanaşımı",
        "relevant": [("TTK", "700"), ("TTK", "701"), ("TTK", "749")]
    },
    {
        "id": "TTK-10",
        "query": "Ticari satışta ayıbı ihbar süreleri iki ve sekiz günlük muayene külfeti",
        "relevant": [("TTK", "23")]
    },
]


def evaluate_retriever_mode(retriever: LegalRetriever, enable_dynamic: bool, top_k: int = 10) -> Dict[str, Any]:
    """Retriever modunu test eder."""
    settings.ENABLE_DYNAMIC_EXPANSION = enable_dynamic

    recalls = []
    mrrs = []
    hits_at_1 = []
    hits_at_10 = []
    precisions = []
    latencies = []
    distinct_articles_counts = []

    for test in BENCHMARK_DATASET:
        query = test["query"]
        relevant_set: Set[Tuple[str, str]] = {(law.upper(), str(art)) for law, art in test["relevant"]}

        t0 = time.perf_counter()
        chunks = retriever.retrieve(query, k=top_k)
        t_elapsed = (time.perf_counter() - t0) * 1000
        latencies.append(t_elapsed)

        retrieved_articles = []
        distinct_seen = set()

        for chunk in chunks:
            law = str(chunk.get("law", "")).upper()
            art = normalize_article(chunk.get("article_no", ""))
            if law and art:
                retrieved_articles.append((law, art))
                distinct_seen.add((law, art))

        distinct_articles_counts.append(len(distinct_seen))

        # 1. Recall@10
        found_relevant = set(retrieved_articles) & relevant_set
        recall = len(found_relevant) / len(relevant_set) if relevant_set else 0.0
        recalls.append(recall)

        # 2. Precision@10
        total_retrieved = len(retrieved_articles)
        precision = len(found_relevant) / total_retrieved if total_retrieved > 0 else 0.0
        precisions.append(precision)

        # 3. Hit Rate@10
        hit_10 = 1.0 if len(found_relevant) > 0 else 0.0
        hits_at_10.append(hit_10)

        # 4. Hit Rate@1
        if retrieved_articles:
            first_doc = retrieved_articles[0]
            hit_1 = 1.0 if first_doc in relevant_set else 0.0
        else:
            hit_1 = 0.0
        hits_at_1.append(hit_1)

        # 5. MRR@10
        mrr = 0.0
        for rank, doc in enumerate(retrieved_articles, start=1):
            if doc in relevant_set:
                mrr = 1.0 / rank
                break
        mrrs.append(mrr)

    return {
        "enable_dynamic": enable_dynamic,
        "recall_at_10": sum(recalls) / len(recalls),
        "mrr_at_10": sum(mrrs) / len(mrrs),
        "hit_rate_at_10": sum(hits_at_10) / len(hits_at_10),
        "hit_rate_at_1": sum(hits_at_1) / len(hits_at_1),
        "precision_at_10": sum(precisions) / len(precisions),
        "avg_distinct_articles": sum(distinct_articles_counts) / len(distinct_articles_counts),
        "avg_latency_ms": sum(latencies) / len(latencies),
    }


def main():
    print("=" * 90)
    print("LawAgent AI — Dinamik Step-Back & Hukuki Kavram Genisletme Benchmark")
    print("=" * 90)

    print("\n[INFO] Retriever motoru baslatiliyor (quantize=False)...")
    retriever = LegalRetriever(quantize=False)

    results = []

    # 1. Mod A: Dinamik Genisletme Kapali (Ham Sorgu Baseline)
    print("\n>>> [1/2] Test ediliyor: Ham Sorgu (No Expansion Baseline)...")
    res_base = evaluate_retriever_mode(retriever, enable_dynamic=False, top_k=10)
    res_base["mode_label"] = "Ham Sorgu (Baseline - Genisletmesiz)"
    results.append(res_base)

    # 2. Mod B: Dinamik Step-Back & Hukuki Kavram Genisletme (Yeni Groq Pipeline)
    print("\n>>> [2/2] Test ediliyor: Dinamik Step-Back & Legal Concept Expansion (Groq)...")
    res_dynamic = evaluate_retriever_mode(retriever, enable_dynamic=True, top_k=10)
    res_dynamic["mode_label"] = "Dinamik Step-Back & Legal Concept Expansion (Yeni)"
    results.append(res_dynamic)

    # Tabloyu ekrana yazdir
    print("\n" + "=" * 105)
    print(f"{'Strateji':<50} | {'Recall@10':<10} | {'MRR@10':<8} | {'Hit@10':<8} | {'Hit@1':<8} | {'Precision@10':<12} | {'Ort. Gecikme':<12}")
    print("-" * 105)

    for r in results:
        label = r["mode_label"]
        rec = f"{r['recall_at_10']*100:.2f}%"
        mrr = f"{r['mrr_at_10']:.4f}"
        hit10 = f"{r['hit_rate_at_10']*100:.2f}%"
        hit1 = f"{r['hit_rate_at_1']*100:.2f}%"
        prec = f"{r['precision_at_10']*100:.2f}%"
        lat = f"{r['avg_latency_ms']:.1f} ms"
        print(f"{label:<50} | {rec:<10} | {mrr:<8} | {hit10:<8} | {hit1:<8} | {prec:<12} | {lat:<12}")

    print("=" * 105)

    out_path = Path(_SRC_DIR) / "eval" / "dynamic_expansion_benchmark_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Sonuclar '{out_path}' dosyasina kaydedildi.")


if __name__ == "__main__":
    main()
