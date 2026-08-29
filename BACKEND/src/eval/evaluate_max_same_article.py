"""
evaluate_max_same_article.py — MAX_SAME_ARTICLE Parametrik Değerlendirme Betiği
================================================================================
Bu betik, LawAgent AI Retriever motorunu farklı MAX_SAME_ARTICLE (1, 2, 3, 5, Limitsiz)
parametre değerleri altında test eder ve aşağıdaki metrikleri karşılaştırmalı olarak hesaplar:

1. Recall@10: Ground truth maddelerden kaçının top-10'da yakalandığı oranı
2. MRR@10: İlk ilgili maddenin sıralamadaki ters sıra ortalaması (1/rank)
3. Hit Rate (Hit@10 / Hit@1): En az bir ilgili maddenin top-10 ve top-1'de bulunma oranı
4. Article Diversity@10: Top-10 içerisindeki benzersiz madde sayısı (çeşitlilik)
5. Citation / Retrieval Precision@10: Top-10'da dönen chunk'lardan kaçının ground-truth ile eşleştiği
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Set
from collections import defaultdict

# Path ayarları
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_SRC_DIR = Path(__file__).resolve().parent.parent
for p in [str(_BACKEND_DIR), str(_SRC_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from src.retriever import LegalRetriever, CFG

# ── Ground Truth Hukuki Test Kümesi (30 Kapsamlı Soru) ─────────────────────────

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
    # ── TKHK (Tüketici Hukuku) ──────────────────────────────────────────────
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


def evaluate_retriever_for_setting(retriever: LegalRetriever, max_same_art: int, top_k: int = 10) -> Dict[str, float]:
    """Belirli bir MAX_SAME_ARTICLE ayarında tüm benchmark sorgularını koşturup metrikleri hesaplar."""
    retriever.cfg.MAX_SAME_ARTICLE = max_same_art

    recalls = []
    mrrs = []
    hits_at_1 = []
    hits_at_10 = []
    precisions = []
    distinct_articles_counts = []

    for test in BENCHMARK_DATASET:
        query = test["query"]
        relevant_set: Set[Tuple[str, str]] = {(law.upper(), str(art)) for law, art in test["relevant"]}

        # Retrieval yap (top-10)
        chunks = retriever.retrieve(query, k=top_k)

        # Çekilen (law, article_no) listesi
        retrieved_articles = []
        distinct_seen = set()

        for c in chunks:
            law = (c.get("law") or "").upper().strip()
            art = str(c.get("article_no") or "").strip()
            if law and art:
                retrieved_articles.append((law, art))
                distinct_seen.add((law, art))

        distinct_articles_counts.append(len(distinct_seen))

        # 1. Hit@1
        if retrieved_articles and retrieved_articles[0] in relevant_set:
            hits_at_1.append(1.0)
        else:
            hits_at_1.append(0.0)

        # 2. Hit@10
        found_relevant_at_all = any(art_tuple in relevant_set for art_tuple in retrieved_articles)
        hits_at_10.append(1.0 if found_relevant_at_all else 0.0)

        # 3. MRR@10 (Mean Reciprocal Rank)
        rr = 0.0
        for rank, art_tuple in enumerate(retrieved_articles, start=1):
            if art_tuple in relevant_set:
                rr = 1.0 / rank
                break
        mrrs.append(rr)

        # 4. Recall@10 (Yakalanan ilgili madde sayısı / Toplam ilgili madde sayısı)
        retrieved_relevant_distinct = set(retrieved_articles).intersection(relevant_set)
        rec = len(retrieved_relevant_distinct) / max(len(relevant_set), 1)
        recalls.append(rec)

        # 5. Precision@10 (Top-10 içindeki ilgili chunk veya madde oranı)
        prec = len(retrieved_relevant_distinct) / max(len(retrieved_articles), 1)
        precisions.append(prec)

    n = len(BENCHMARK_DATASET)
    return {
        "max_same_article": max_same_art,
        "recall_at_10": sum(recalls) / n,
        "mrr_at_10": sum(mrrs) / n,
        "hit_rate_at_10": sum(hits_at_10) / n,
        "hit_rate_at_1": sum(hits_at_1) / n,
        "precision_at_10": sum(precisions) / n,
        "avg_distinct_articles": sum(distinct_articles_counts) / n,
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    
    print("=" * 80)
    print("LawAgent AI - MAX_SAME_ARTICLE Karsilastirmali Performans Degerlendirmesi")
    print(f"Toplam Test Sorgusu: {len(BENCHMARK_DATASET)}")
    print("=" * 80)

    print("\nRetriever baslatiliyor (Quantized Mursit + BM25+)...")
    t0 = time.time()
    retriever = LegalRetriever(quantize=True)
    print(f"Retriever hazir ({time.time()-t0:.2f}s)\n")

    settings_to_test = [1, 2, 3, 5, 10]
    results = []

    for val in settings_to_test:
        label = f"MAX_SAME_ARTICLE = {val}" if val < 10 else "MAX_SAME_ARTICLE = 10 (Filtresiz)"
        print(f"[*] Test ediliyor: {label}...")
        res = evaluate_retriever_for_setting(retriever, max_same_art=val, top_k=10)
        results.append(res)

    print("\n" + "=" * 92)
    print(f"{'Ayar':<28} | {'Recall@10':<10} | {'MRR@10':<9} | {'Hit@10':<9} | {'Hit@1':<8} | {'Precision@10':<13} | {'Çeşitlilik':<10}")
    print("-" * 92)

    for r in results:
        val = r['max_same_article']
        label = f"MAX_SAME_ARTICLE = {val} (Mevcut)" if val == 1 else (f"MAX_SAME_ARTICLE = {val}" if val < 10 else "MAX_SAME_ARTICLE = Limitsiz")
        print(
            f"{label:<28} | "
            f"{r['recall_at_10']*100:6.2f}%    | "
            f"{r['mrr_at_10']:6.4f}   | "
            f"{r['hit_rate_at_10']*100:6.2f}%   | "
            f"{r['hit_rate_at_1']*100:5.2f}%  | "
            f"{r['precision_at_10']*100:6.2f}%       | "
            f"{r['avg_distinct_articles']:4.1f} / 10"
        )
    print("=" * 92)

    # Sonuçları JSON olarak da kaydet
    out_file = _SRC_DIR / "eval" / "max_same_article_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] Sonuclar '{out_file}' dosyasina kaydedildi.\n")


if __name__ == "__main__":
    main()
