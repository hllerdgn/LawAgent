"""
Retrieval Diagnostic Script
Hangi sorgu tipleri ve maddelerin sistematik olarak başarısız olduğunu tespit eder.
"""
import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from retriever import LegalRetriever, detect_kanun, extract_madde
from evaluator import BENCHMARK
import math
import re
from collections import defaultdict

def normalize_article(x):
    found = re.search(r"(\d+)", str(x))
    return found.group(1) if found else ""

def is_hit(result, expected_maddeler, expected_decision=None):
    res_art = str(result.get("article_no", ""))
    res_dec = str(result.get("decision_id", ""))
    text = result.get("text", "").lower()
    if res_art in expected_maddeler:
        return True
    if expected_decision and res_dec == expected_decision:
        return True
    for madde in expected_maddeler:
        pattern = rf"\b(?:madde|m\.|m)\s*[:\-\.]?\s*{madde}\b"
        if re.search(pattern, text):
            return True
    return False

def run_diagnosis():
    print("LegalRetriever başlatılıyor...")
    r = LegalRetriever()
    K = 10

    failures = []  # (query, law, expected_articles, rank_found)
    article_stats = defaultdict(lambda: {"total": 0, "hit": 0, "rank_sum": 0, "mrr_sum": 0.0})

    print(f"\n🔬 {len(BENCHMARK)} sorgu analiz ediliyor...\n")

    for idx, (query, kanun, maddeler, karar_id) in enumerate(BENCHMARK, 1):
        try:
            results = r.retrieve(query, k=K)
        except Exception as e:
            print(f"  ⚠️ [{idx}] HATA: {e}")
            continue

        # MRR hesapla
        rank_found = None
        for rank, res in enumerate(results, 1):
            if is_hit(res, maddeler, karar_id):
                rank_found = rank
                break

        key = f"{kanun}|{','.join(maddeler)}"
        article_stats[key]["total"] += 1
        if rank_found:
            article_stats[key]["hit"] += 1
            article_stats[key]["rank_sum"] += rank_found
            article_stats[key]["mrr_sum"] += 1.0 / rank_found
        else:
            failures.append({
                "query": query,
                "kanun": kanun,
                "maddeler": maddeler,
                "top3": [
                    f"{res.get('law','')} m.{res.get('article_no','')} [{res.get('source','')}]"
                    for res in results[:3]
                ]
            })

    # --- Sonuç Raporu ---
    print("\n" + "="*70)
    print("📊 ARTICLE-LEVEL BAŞARISIZLIK ANALİZİ")
    print("="*70)
    print(f"{'Kanun|Madde':<30} {'Toplam':>7} {'Hit':>5} {'Hit%':>6} {'Ort.Rank':>9} {'MRR':>6}")
    print("-"*70)

    # Başarısız olanları bul, MRR'a göre sırala
    sorted_stats = sorted(article_stats.items(), key=lambda x: x[1]["mrr_sum"] / max(x[1]["total"],1))
    for key, s in sorted_stats[:20]:  # En kötü 20
        hit_pct = 100 * s["hit"] / s["total"]
        avg_rank = s["rank_sum"] / s["hit"] if s["hit"] else 99
        avg_mrr  = s["mrr_sum"] / s["total"]
        marker = "❌" if hit_pct < 50 else ("⚠️" if avg_mrr < 0.5 else "✅")
        print(f"{marker} {key:<28} {s['total']:>7} {s['hit']:>5} {hit_pct:>5.0f}% {avg_rank:>9.1f} {avg_mrr:>6.3f}")

    print("\n" + "="*70)
    print("🔍 TOP-10'DA BULUNAMAYAN SORGULAR (MRR=0)")
    print("="*70)
    seen = set()
    for f in failures:
        key = f"{f['kanun']}|{','.join(f['maddeler'])}"
        if key in seen:
            continue
        seen.add(key)
        print(f"\n❌ [{f['kanun']}] Madde: {f['maddeler']}")
        print(f"   Sorgu: {f['query'][:80]}")
        print(f"   Sistem ne döndürdü (Top-3): {' | '.join(f['top3'])}")

    print(f"\n\nToplam {len(failures)} başarısız sorgu, {len(seen)} unique madde tipi")

if __name__ == "__main__":
    run_diagnosis()
