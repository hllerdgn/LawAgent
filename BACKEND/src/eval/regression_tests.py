"""
regression_tests.py — LawAgent AI Hukuki RAG Regresyon Test Paketi
====================================================================
Kullanım:
    python regression_tests.py --url https://hllerdgn-lawagent-backend.hf.space
    python regression_tests.py --url http://localhost:7860

Her test için:
  - expected_role     : Beklenen hukuki sıfat (alacakli, borclu, belirsiz, ...)
  - expected_concepts : Yanıtta bulunması beklenen kavramlar (substring match)
  - expected_sources  : Yanıtta/kaynakta olması beklenen kanun/madde eşleşmeleri
  - forbidden_sources : Yanıtta KESİNLİKLE bulunmaması gereken maddeler
  - answer_should_ask : Yanıtta netleştirme sorusu olmalı mı?
"""

import argparse
import json
import sys
import time
from typing import List, Dict, Optional, Any
import urllib.request
import urllib.error

# ─────────────────────────────────────────────────────────────────────────────
# Test Tanımları
# ─────────────────────────────────────────────────────────────────────────────

TEST_CASES = [
    # ── GEnel / Belirsiz Sıfatlı Sorular ──────────────────────────────────────
    {
        "id": "GEN-001",
        "category": "genel_belirsiz",
        "query": "Borçlar hukuku kapsamında temel haklarım nelerdir?",
        "expected_role": "belirsiz",
        "expected_concepts": ["hak", "borç", "alacaklı", "borçlu"],
        "expected_sources": [{"kanun": "TBK"}],
        "forbidden_sources": [],
        "answer_should_ask": True,
        "must_not_contain": ["Sunulan yasal kaynaklar çerçevesinde bu soruya dair doğrudan bir hüküm bulunmamaktadır"],
        "description": "Belirsiz sıfatlı TBK genel hak sorusu. Sistem rol varsaymamalı, genel çerçeve vermeli, soru sormalı.",
    },
    {
        "id": "GEN-002",
        "category": "genel_belirsiz",
        "query": "Sözleşmeden doğan haklarım nelerdir?",
        "expected_role": "belirsiz",
        "expected_concepts": ["sözleşme", "hak"],
        "expected_sources": [{"kanun": "TBK"}],
        "forbidden_sources": [],
        "answer_should_ask": True,
        "must_not_contain": [],
        "description": "Sözleşmeden doğan haklar — belirsiz sıfat.",
    },
    {
        "id": "GEN-003",
        "category": "genel_belirsiz",
        "query": "Borç ilişkisinde tarafların hakları nelerdir?",
        "expected_role": "belirsiz",
        "expected_concepts": ["taraf", "hak", "borç"],
        "expected_sources": [{"kanun": "TBK"}],
        "forbidden_sources": [],
        "answer_should_ask": False,  # "taraflar" şeklinde genel sorgu olduğu için iki tarafı açıklayabilir
        "must_not_contain": [],
        "description": "Borç ilişkisinde her iki tarafın haklarının genel açıklanması.",
    },

    # ── Alacaklı Soruları ──────────────────────────────────────────────────────
    {
        "id": "ALC-001",
        "category": "alacakli",
        "query": "Alacaklı olarak hangi haklara sahibim?",
        "expected_role": "alacakli",
        "expected_concepts": ["ifa", "tazminat", "alacaklı"],
        "expected_sources": [{"kanun": "TBK"}],
        "forbidden_sources": [],
        "answer_should_ask": False,
        "must_not_contain": ["Sunulan yasal kaynaklar çerçevesinde bu soruya dair doğrudan bir hüküm bulunmamaktadır"],
        "description": "Açık alacaklı sıfatı. Sistem ifa, temerrüt, seçimlik haklar gibi kavramları sunmalı.",
    },
    {
        "id": "ALC-002",
        "category": "alacakli",
        "query": "Borçlu borcunu ödemezse ne yapabilirim?",
        "expected_role": "alacakli",
        "expected_concepts": ["temerrüt", "ifa", "tazminat"],
        "expected_sources": [{"kanun": "TBK"}],
        "forbidden_sources": [],
        "answer_should_ask": False,
        "must_not_contain": [],
        "description": "Temerrüt hâlinde alacaklının hakları.",
    },

    # ── Borçlu Soruları ───────────────────────────────────────────────────────
    {
        "id": "BOR-001",
        "category": "borclu",
        "query": "Borçlu olarak hangi haklara sahibim?",
        "expected_role": "borclu",
        "expected_concepts": ["borçlu", "hak", "def'i"],
        "expected_sources": [{"kanun": "TBK"}],
        "forbidden_sources": [],
        "answer_should_ask": False,
        "must_not_contain": [],
        "description": "Açık borçlu sıfatı. Sistem ödemezlik def'i, takas vb. kavramları sunmalı.",
    },
    {
        "id": "BOR-002",
        "category": "borclu",
        "query": "Alacağımı borcumla takas edebilir miyim?",
        "expected_role": "borclu",
        "expected_concepts": ["takas"],
        "expected_sources": [{"kanun": "TBK"}],
        "forbidden_sources": [],
        "answer_should_ask": False,
        "must_not_contain": [],
        "description": "Takas hakkı (TBK m.139-143 civarı).",
    },

    # ── İş İlişkisi ───────────────────────────────────────────────────────────
    {
        "id": "IS-001",
        "category": "is_iliskisi",
        "query": "İşverenin talimat verme yetkisi nedir?",
        "expected_role": "isveren",
        "expected_concepts": ["yetki", "talimat", "işveren"],
        "expected_sources": [{"kanun": "TBK"}],
        "forbidden_sources": [],
        "answer_should_ask": False,
        "must_not_contain": [],
        "description": "Yetki kavramı — hak olarak sunulmamalı.",
    },
    {
        "id": "IS-002",
        "category": "is_iliskisi",
        "query": "İşçinin işverene karşı yükümlülükleri nelerdir?",
        "expected_role": "isci",
        "expected_concepts": ["yükümlülük", "işçi", "özen"],
        "expected_sources": [{"kanun": "TBK"}],
        "forbidden_sources": [],
        "answer_should_ask": False,
        "must_not_contain": [],
        "description": "Yükümlülük kavramı — hak olarak sunulmamalı.",
    },

    # ── Teminat Soruları ──────────────────────────────────────────────────────
    {
        "id": "TEM-001",
        "category": "teminat",
        "query": "Kefilin hakları nelerdir?",
        "expected_role": "kefil",
        "expected_concepts": ["kefil", "hak"],
        "expected_sources": [{"kanun": "TBK"}],
        "forbidden_sources": [],
        "answer_should_ask": False,
        "must_not_contain": [],
        "description": "Kefil hakları.",
    },

    # ── Tüketici Soruları ──────────────────────────────────────────────────────
    {
        "id": "TUK-001",
        "category": "tuketici",
        "query": "İnternetten aldığım ürünü iade etmek istiyorum, cayma hakkım var mı?",
        "expected_role": "tuketici",
        "expected_concepts": ["cayma", "mesafeli", "iade"],
        "expected_sources": [{"kanun": "TKHK"}],
        "forbidden_sources": [],
        "answer_should_ask": False,
        "must_not_contain": [],
        "description": "TKHK mesafeli sözleşme cayma hakkı.",
    },

    # ── Haksız Çıkarım / Kavram Karışıklığı ─────────────────────────────────
    {
        "id": "KAV-001",
        "category": "kavram_karmasasi",
        "query": "Sözleşmede işverenin talimat verme yetkisi borçlar hukukunda bir hak mı?",
        "expected_role": "belirsiz",
        "expected_concepts": ["yetki"],
        "expected_sources": [{"kanun": "TBK"}],
        "forbidden_sources": [],
        "answer_should_ask": False,
        "must_not_contain": [],
        "description": "Yetki ile hak ayrımını test eder. Sistem 'yetki'yi 'hak' olarak sunmamalı.",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# HTTP İstemcisi
# ─────────────────────────────────────────────────────────────────────────────

def call_api(base_url: str, query: str, session_id: str, timeout: int = 90) -> Optional[Dict]:
    url = f"{base_url.rstrip('/')}/ask"
    payload = json.dumps({
        "query": query,
        "session_id": session_id,
        "k": 7,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  ❌ HTTP {e.code}: {e.read().decode('utf-8')[:200]}")
        return None
    except Exception as e:
        print(f"  ❌ İstek hatası: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Değerlendirici
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_response(test: Dict, result: Dict) -> Dict[str, Any]:
    answer = (result.get("answer") or "").lower()
    sources = result.get("sources") or []

    checks = {}

    # 1. must_not_contain
    for phrase in test.get("must_not_contain", []):
        checks[f"no_false_negative[{phrase[:30]}]"] = phrase.lower() not in answer

    # 2. expected_concepts (substring match in answer)
    for concept in test.get("expected_concepts", []):
        checks[f"concept[{concept}]"] = concept.lower() in answer

    # 3. expected_sources (kanun match in sources list)
    for exp_src in test.get("expected_sources", []):
        kanun = exp_src.get("kanun", "").upper()
        found = any(kanun in (s.get("kanun") or "").upper() for s in sources)
        madde = exp_src.get("madde")
        if madde:
            found = found and any(
                str(madde) == str(s.get("madde", "")) and kanun in (s.get("kanun") or "").upper()
                for s in sources
            )
        checks[f"source[{kanun}{'.'+str(exp_src.get('madde','')) if exp_src.get('madde') else ''}]"] = found

    # 4. forbidden_sources
    for forb in test.get("forbidden_sources", []):
        kanun = forb.get("kanun", "").upper()
        madde = forb.get("madde")
        found = any(
            kanun in (s.get("kanun") or "").upper() and
            (madde is None or str(madde) == str(s.get("madde", "")))
            for s in sources
        )
        checks[f"not_source[{kanun}{'.'+str(madde) if madde else ''}]"] = not found

    # 5. answer_should_ask (soru işareti kontrolü)
    if test.get("answer_should_ask"):
        checks["has_clarification_question"] = "?" in result.get("answer", "")

    passed = all(checks.values())
    return {"passed": passed, "checks": checks}


# ─────────────────────────────────────────────────────────────────────────────
# Ana Runner
# ─────────────────────────────────────────────────────────────────────────────

def run_tests(base_url: str, categories: Optional[List[str]] = None, verbose: bool = False):
    tests = TEST_CASES
    if categories:
        tests = [t for t in tests if t["category"] in categories]

    print(f"\n{'='*70}")
    print(f"LawAgent AI — Regresyon Test Paketi")
    print(f"Hedef: {base_url}")
    print(f"Test sayısı: {len(tests)}")
    print(f"{'='*70}\n")

    results_summary = []
    passed_total = 0

    for i, test in enumerate(tests, 1):
        test_id = test["id"]
        cat = test["category"]
        query = test["query"]

        print(f"[{i}/{len(tests)}] {test_id} ({cat})")
        print(f"  📋 Sorgu: {query}")

        session_id = f"regtest_{test_id}_{int(time.time())}"
        t_start = time.time()
        result = call_api(base_url, query, session_id)
        elapsed = int((time.time() - t_start) * 1000)

        if result is None:
            print(f"  ❌ API yanıt vermedi ({elapsed}ms)\n")
            results_summary.append({"id": test_id, "passed": False, "error": "no_response"})
            continue

        eval_result = evaluate_response(test, result)
        passed = eval_result["passed"]
        passed_total += int(passed)

        status = "✅ GEÇTI" if passed else "❌ BAŞARISIZ"
        print(f"  {status} ({elapsed}ms)")

        if verbose or not passed:
            answer_preview = (result.get("answer") or "")[:300].replace("\n", " ")
            print(f"  💬 Yanıt: {answer_preview}...")
            sources_str = ", ".join(
                f"{s.get('kanun','')} m.{s.get('madde','')}" for s in (result.get("sources") or [])
            )
            print(f"  📚 Kaynaklar: {sources_str or '(yok)'}")
            for check_name, check_val in eval_result["checks"].items():
                icon = "  ✓" if check_val else "  ✗"
                print(f"    {icon} {check_name}: {check_val}")

        results_summary.append({
            "id": test_id,
            "category": cat,
            "passed": passed,
            "elapsed_ms": elapsed,
            "checks": eval_result["checks"],
        })
        print()

    # Özet
    total = len(tests)
    pct = (passed_total / total * 100) if total else 0
    print(f"{'='*70}")
    print(f"SONUÇ: {passed_total}/{total} test geçti ({pct:.1f}%)")

    by_cat: Dict[str, Dict] = {}
    for r in results_summary:
        cat = r.get("category", "?")
        if cat not in by_cat:
            by_cat[cat] = {"passed": 0, "total": 0}
        by_cat[cat]["total"] += 1
        by_cat[cat]["passed"] += int(r.get("passed", False))

    print("\nKategoriye Göre:")
    for cat, stats in by_cat.items():
        p, t = stats["passed"], stats["total"]
        print(f"  {cat}: {p}/{t}")

    print(f"{'='*70}\n")
    return results_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LawAgent Regresyon Test Paketi")
    parser.add_argument("--url", default="http://localhost:7860", help="API base URL")
    parser.add_argument("--categories", nargs="*", help="Test kategorileri (boşsa hepsi)")
    parser.add_argument("--verbose", action="store_true", help="Tüm test detaylarını göster")
    args = parser.parse_args()

    results = run_tests(args.url, categories=args.categories, verbose=args.verbose)
    # Herhangi bir test başarısız olduysa exit code 1
    all_passed = all(r.get("passed", False) for r in results)
    sys.exit(0 if all_passed else 1)
