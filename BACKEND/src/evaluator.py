import argparse
import json
import math
import os
import time
import logging
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple, Any

# Kendi modüllerimizden import
from retriever import LegalRetriever, detect_kanun, extract_madde

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("LawAgent.Evaluator")

# ═══════════════════════════════════════════════════════════════════════════════
# HİBRİT BENCHMARK SETİ (Mevzuat + İçtihat)
# Sorgu, Beklenen Kanun, Beklenen Madde Listesi, Beklenen Karar ID (Opsiyonel)
# ═══════════════════════════════════════════════════════════════════════════════
BENCHMARK = [
    # ─────────────────────────────────────────────
    # TBK — Türk Borçlar Kanunu (6098)
    # ─────────────────────────────────────────────
    # Sözleşmenin Kurulması & İrade Sakatlıkları
    (
        "Sözleşmenin esaslı noktalarında irade uyuşması olmadan sözleşme kurulmuş sayılır mı?",
        "TBK",
        ["1", "2"],
        None,
    ),
    (
        "Aldatma (hile) durumunda karşı tarafın sözleşmeyi iptal etme hakkının kullanım süresi nedir?",
        "TBK",
        ["36", "39"],
        None,
    ),
    (
        "Aşırı yararlanma (gabin) şartları nelerdir ve hâkimin sözleşmeyi değiştirme yetkisi var mıdır?",
        "TBK",
        ["28"],
        None,
    ),
    # Haksız Fiil Sorumluluğu
    (
        "Haksız fiil sorumluluğunun dört temel unsuru nedir ve ispat yükü kime aittir?",
        "TBK",
        ["49", "50"],
        None,
    ),
    (
        "Haksız fiilden doğan tazminat davasında zamanaşımı süreleri nelerdir?",
        "TBK",
        ["72"],
        None,
    ),
    (
        "Tehlike sorumluluğunda zarar görenin tazminat talep edebilmesinin koşulları nelerdir?",
        "TBK",
        ["71"],
        None,
    ),
    (
        "Adam çalıştıranın sorumluluğunda kurtuluş beyyinesi nasıl işler?",
        "TBK",
        ["66"],
        None,
    ),
    (
        "Kişilik hakkı ihlalinde manevi tazminatın takdirinde hâkim hangi ölçütleri gözetir?",
        "TBK",
        ["58"],
        None,
    ),
    # Borçların İfası & Temerrüt
    (
        "Muaccel bir borcun borçlusu hangi şartla temerrüde düşer ve ihtar gerekmediği haller nelerdir?",
        "TBK",
        ["117"],
        None,
    ),
    (
        "Temerrüde düşen borçlunun beklenmedik halden (mücbir sebepten) doğan sorumluluğu nedir?",
        "TBK",
        ["119"],
        None,
    ),
    (
        "Alacaklı temerrüdünün şartları ve borçlunun ifa etmeksizin serbest kalma hakkı nedir?",
        "TBK",
        ["106", "107"],
        None,
    ),
    (
        "Karşılıklı borç yükleyen sözleşmelerde süre verilmeksizin sözleşmeden dönülebilecek haller nelerdir?",
        "TBK",
        ["124"],
        None,
    ),
    # Sözleşmenin Sona Ermesi & Zamanaşımı
    (
        "Borçlunun ikrarının zamanaşımını keseceği ve yeni sürenin nasıl başlayacağı hükmü nedir?",
        "TBK",
        ["154"],
        None,
    ),
    (
        "Zamanaşımının durmasına yol açan haller nelerdir?",
        "TBK",
        ["153"],
        None,
    ),
    # Çeşitli Sözleşme Türleri
    (
        "Satım sözleşmesinde ayıbın gizlenmesi (hile ile saklama) durumunda satıcının sorumluluğu sınırlanabilir mi?",
        "TBK",
        ["221"],
        None,
    ),
    (
        "Kira sözleşmesinde kiraya verenin ayıba karşı tekeffül borcu ve kiracının seçimlik hakları nelerdir?",
        "TBK",
        ["305", "306"],
        None,
    ),
    (
        "Kiracının kira bedelini ödememesi hâlinde kiraya verenin yazılı bildirim yaparak tahliye isteme süreci nasıl işler?",
        "TBK",
        ["315"],
        None,
    ),
    (
        "Konut ve çatılı işyeri kiralarında kiracı aleyhine düzenleme yasağının kapsamı nedir?",
        "TBK",
        ["346"],
        None,
    ),
    (
        "Eser sözleşmesinde yaklaşık bedelin aşılması hâlinde iş sahibinin dönme hakkı ne zaman doğar?",
        "TBK",
        ["482"],
        None,
    ),
    (
        "Vekâletin sona ermesinde vekâlet verenin ölümü hâlinde vekilin yükümlülükleri nelerdir?",
        "TBK",
        ["513"],
        None,
    ),
    (
        "Kefalet sözleşmesinin geçerliliği için aranan yazılı şekil ve eşin rızasına ilişkin kurallar nelerdir?",
        "TBK",
        ["583", "584"],
        None,
    ),
    # Borç İlişkilerinin Çeşitli Konuları
    (
        "Alacağın devri (temlik) sözleşmesinin geçerlilik şartları ve borçlunun bilgilendirilmesinin sonuçları nelerdir?",
        "TBK",
        ["184", "186"],
        None,
    ),
    (
        "Müteselsil borçlulukta borçlulardan birinin ödeme yapması diğer borçluların borcunu nasıl etkiler?",
        "TBK",
        ["166", "167"],
        None,
    ),
    (
        "Sebepsiz zenginleşen kişinin iyiniyetli olması hâlinde geri verme yükümlülüğünün kapsamı nasıl daralır?",
        "TBK",
        ["79", "80"],
        None,
    ),
    (
        "Borcun bizzat borçlu tarafından ifa edilmesinde alacaklının menfaatinin varlığı hangi ölçütle belirlenir?",
        "TBK",
        ["83"],
        None,
    ),
    # ─────────────────────────────────────────────
    # TKHK — Tüketicinin Korunması Hakkında Kanun (6502)
    # ─────────────────────────────────────────────
    # Ayıplı Mal & Hizmet
    (
        "Ayıplı malın tespitinde 'teslim tarihinden itibaren altı ay' içinde ortaya çıkan ayıplara ilişkin ispat karinesi nasıl işler?",
        "TKHK",
        ["10"],
        None,
    ),
    (
        "Ayıplı mal durumunda tüketicinin dört seçimlik hakkı nelerdir ve satıcı, üretici, ithalatçının müteselsil sorumluluğu nasıl düzenlenir?",
        "TKHK",
        ["11"],
        None,
    ),
    (
        "Ayıplı hizmet hâlinde tüketicinin seçimlik hakları ve sağlayıcının ücretsiz yeniden ifa yükümlülüğünün azami süresi nedir?",
        "TKHK",
        ["15"],
        None,
    ),
    (
        "Tüketici sözleşmelerinde haksız şartların kesin hükümsüzlüğü ve sözleşmenin geri kalanının geçerliliği nasıl korunur?",
        "TKHK",
        ["5"],
        None,
    ),
    # Mesafeli & İşyeri Dışı Sözleşmeler
    (
        "Mesafeli sözleşmelerde tüketicinin 14 günlük cayma hakkına getirilen istisnalar nelerdir?",
        "TKHK",
        ["48"],
        None,
    ),
    (
        "İşyeri dışında kurulan sözleşmelerde satıcının tüketiciyi bilgilendirme yükümlülüğü ve cayma süresi nedir?",
        "TKHK",
        ["47"],
        None,
    ),
    # Tüketici Kredisi & Finansman
    (
        "Tüketici kredisi sözleşmesinin geçerlilik şartları ve kredi verenin geçersizliği tüketici aleyhine ileri süremeyeceği kuralı nedir?",
        "TKHK",
        ["23"],
        None,
    ),
    (
        "Tüketici kredisinde belirsiz süreli sözleşmelerde faiz artışının tüketiciye bildirim yükümlülüğü ve tüketicinin sözleşmeden çıkma hakkı nasıl işler?",
        "TKHK",
        ["26"],
        None,
    ),
    (
        "Tüketici kredisinin erken kapatılması hâlinde tüketicinin faiz ve masraf indiriminden yararlanma hakkı nedir?",
        "TKHK",
        ["27"],
        None,
    ),
    (
        "Konut finansmanı sözleşmelerinde tüketicinin temerrüdü hâlinde kalan borcun tamamının muaccel kılınabilmesinin şartları nelerdir?",
        "TKHK",
        ["33"],
        None,
    ),
    # Tüketici Hakem Heyeti & Uyuşmazlık Çözümü
    (
        "Tüketici hakem heyetine başvuru parasal sınırları nelerdir ve verilen kararların bağlayıcılık rejimi nasıl işler?",
        "TKHK",
        ["68", "70"],
        None,
    ),
    (
        "Tüketicinin konut alımından kaynaklanan uyuşmazlıklarda yetkili mahkeme hangisidir?",
        "TKHK",
        ["73"],
        None,
    ),
    # Özel Sözleşme Türleri (TKHK)
    (
        "Devre tatil sözleşmelerinde tüketicinin cayma hakkı süresi ve sözleşmeden dönme bedeline ilişkin yasak nedir?",
        "TKHK",
        ["50"],
        None,
    ),
    (
        "Paket tur sözleşmesinde düzenleyicinin seyahat öncesi esaslı değişiklik yapması hâlinde tüketicinin hakları nelerdir?",
        "TKHK",
        ["51"],
        None,
    ),
    (
        "Abonelik sözleşmelerinin tüketici tarafından feshedilmesi hâlinde sağlayıcının depozito iade yükümlülüğü ve süresi nedir?",
        "TKHK",
        ["52"],
        None,
    ),
    (
        "Garanti belgesi düzenleme yükümlülüğüne aykırılık hâlinde tüketiciye tanınan ek haklar nelerdir?",
        "TKHK",
        ["56"],
        None,
    ),
    (
        "Sipariş edilmeyen mal veya hizmet gönderilmesi durumunda satıcı tüketiciden herhangi bir bedel talep edebilir mi?",
        "TKHK",
        ["7"],
        None,
    ),
    # ─────────────────────────────────────────────
    # TTK — Türk Ticaret Kanunu (6102)
    # ─────────────────────────────────────────────
    # Ticari İşletme & Tacir
    (
        "Tacir sıfatının kazanılması ve tacire özgü yükümlülükler (basiretli işletme, ticaret unvanı, tescil) nelerdir?",
        "TTK",
        ["11", "18"],
        None,
    ),
    (
        "Ticaret siciline tescil ve ilanın olumlu (müspet) ve olumsuz (menfi) aleniyet etkisi nedir?",
        "TTK",
        ["36", "37"],
        None,
    ),
    (
        "Ticari işlemlerde fatura ve teyit mektubuna itiraz edilmemesinin hukuki sonuçları nelerdir?",
        "TTK",
        ["21"],
        None,
    ),
    # Haksız Rekabet
    (
        "Haksız rekabet sayılan dürüstlük kuralına aykırı davranışlara karşı açılabilecek hukuk davalarının türleri nelerdir?",
        "TTK",
        ["56"],
        None,
    ),
    (
        "Haksız rekabet nedeniyle açılacak hukuk davalarında zamanaşımı süresi ve başlangıç anı nedir?",
        "TTK",
        ["60"],
        None,
    ),
    # Anonim Şirket
    (
        "Anonim şirket yönetim kurulunun devredilemez ve vazgeçilemez görev ve yetkileri nelerdir?",
        "TTK",
        ["375"],
        None,
    ),
    (
        "2024 TTK değişikliğiyle anonim şirket yönetim kurulunu toplantıya çağırma yetkisi kime tanınmıştır?",
        "TTK",
        ["392"],
        "18-1",  # PwC bülteni referansı
    ),
    (
        "Anonim şirket genel kurul kararlarının butlanı ile iptalinin farkları nelerdir ve iptal davası açma süresi nedir?",
        "TTK",
        ["445", "447"],
        None,
    ),
    (
        "Anonim şirkette nama yazılı pay devrinin pay defterine kaydından şirketin hangi gerekçelerle kaçınabileceği durumlar nelerdir?",
        "TTK",
        ["490", "493"],
        None,
    ),
    (
        "Hamiline yazılı pay senetlerinin devri ve MKK'ya bildirim yükümlülüğü nasıl düzenlenmiştir?",
        "TTK",
        ["489", "486"],
        None,
    ),
    (
        "Anonim şirkette yönetim kurulu üyesinin azlinde gündeme bağlılık ilkesi ve istisnaları nelerdir?",
        "TTK",
        ["413"],
        None,
    ),
    (
        "Anonim şirket yönetim kurulu üyelerinin şirkete, pay sahiplerine ve alacaklılara karşı tazminat sorumluluğunun şartları nelerdir?",
        "TTK",
        ["553"],
        None,
    ),
    # Limited Şirket
    (
        "Limited şirkette esas sermaye payının devri için gereken noter onaylı yazılı şekil şartı ve genel kurul onayı zorunluluğu nedir?",
        "TTK",
        ["595"],
        None,
    ),
    (
        "Limited şirkette müdürün devredilemez ve vazgeçilemez görev ve yetkileri nelerdir?",
        "TTK",
        ["625"],
        None,
    ),
    (
        "Limited şirkette ortaklar genel kurulunun devredilemez yetkileri nelerdir?",
        "TTK",
        ["616"],
        None,
    ),
    (
        "Limited şirkette ortağın haklı sebeple şirketten çıkma ve şirket tarafından çıkarılma halleri nasıl düzenlenmiştir?",
        "TTK",
        ["638", "640"],
        None,
    ),
    # Kıymetli Evrak
    (
        "Poliçede kabul etmeme veya ödememe protestosunun çekilme süresi ve müracaat haklarına etkisi nedir?",
        "TTK",
        ["713", "714"],
        None,
    ),
    (
        "Çekin ibraz süreleri nelerdir ve ibraz edilmeksizin süresi geçen çekte hamilin keşideciye ve ciranta karşı haklarının durumu ne olur?",
        "TTK",
        ["796", "808"],
        None,
    ),
    (
        "Karşılıksız çeken hakkında hamilin talep edebileceği tazminat oranı ve cezai yaptırımlar nelerdir?",
        "TTK",
        ["814"],
        None,
    ),
    (
        "Bonoyu (emre yazılı senedi) poliçeden ayıran temel özellikler ve ciranta sorumluluğu nasıl düzenlenir?",
        "TTK",
        ["776", "777"],
        None,
    ),
    # Ticari İşlemler
    (
        "Ticari işlerde gecikme faizinin belirlenmesinde tarafların serbestisi ve Merkez Bankası referans faizinin rolü nedir?",
        "TTK",
        ["1530"],
        None,
    ),
    (
        "Ticari defterlerin ispat aracı olarak kullanılmasının şartları ve aleyhine delil teşkil etmesi hâlleri nelerdir?",
        "TTK",
        ["64", "222"],
        None,
    ),
]

# ═══════════════════════════════════════════════════════════════════════════════
# METRİK FONKSİYONLARI (İçtihat Destekli)
# ═══════════════════════════════════════════════════════════════════════════════


def is_hit(
    result: Dict, expected_maddeler: List[str], expected_decision: str = None
) -> bool:
    """
    Bir sonucun 'doğru' kabul edilmesi için:
    Ya beklenen maddelerden biri olmalı YA DA beklenen karar ID'si olmalı.
    """
    res_art = str(result.get("article_no", ""))
    res_dec = str(result.get("decision_id", ""))

    if res_art in expected_maddeler:
        return True
    if expected_decision and res_dec == expected_decision:
        return True
    return False


def recall_at_k(
    results: List[Dict], expected_m: List[str], expected_d: str, k: int
) -> float:
    if not expected_m and not expected_d:
        return 0.0
    found_count = 0
    seen_targets = set()

    for r in results[:k]:
        if is_hit(r, expected_m, expected_d):
            # Aynı madde/kararın farklı chunklarını mükerrer saymamak için
            target_key = r.get("article_no") or r.get("decision_id")
            if target_key not in seen_targets:
                found_count += 1
                seen_targets.add(target_key)

    total_expected = len(expected_m) + (1 if expected_d else 0)
    return found_count / total_expected


def mrr_at_k(
    results: List[Dict], expected_m: List[str], expected_d: str, k: int
) -> float:
    for rank, r in enumerate(results[:k], 1):
        if is_hit(r, expected_m, expected_d):
            return 1.0 / rank
    return 0.0


def ndcg_at_k(
    results: List[Dict], expected_m: List[str], expected_d: str, k: int
) -> float:
    dcg = sum(
        1.0 / math.log2(i + 1)
        for i, r in enumerate(results[:k], 1)
        if is_hit(r, expected_m, expected_d)
    )

    total_targets = len(expected_m) + (1 if expected_d else 0)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, min(total_targets, k) + 1))
    return dcg / idcg if idcg > 0 else 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# DEĞERLENDİRME MOTORU
# ═══════════════════════════════════════════════════════════════════════════════


def run_evaluation(retriever: LegalRetriever, k: int = 10):
    stats = {"recall": [], "mrr": [], "ndcg": [], "hit": [], "time": []}
    detailed_results = []

    print(f"\n🚀 {len(BENCHMARK)} benchmark sorgusu test ediliyor...")

    for query, kanun, maddeler, karar_id in BENCHMARK:
        t0 = time.time()
        results = retriever.retrieve(query, k=k)
        duration = (time.time() - t0) * 1000

        rec = recall_at_k(results, maddeler, karar_id, k)
        mrr = mrr_at_k(results, maddeler, karar_id, k)
        ndcg = ndcg_at_k(results, maddeler, karar_id, k)
        hit = 1 if mrr > 0 else 0

        stats["recall"].append(rec)
        stats["mrr"].append(mrr)
        stats["ndcg"].append(ndcg)
        stats["hit"].append(hit)
        stats["time"].append(duration)

        detailed_results.append(
            {
                "query": query,
                "hit": hit,
                "mrr": mrr,
                "top_result": results[0]["text"][:100] if results else "Yok",
            }
        )

        status = "✅" if hit else "❌"
        print(f"  {status} Sorgu: {query[:50]}... (MRR: {mrr:.2f})")

    # Ortalama Hesaplama
    avg_stats = {m: sum(v) / len(v) for m, v in stats.items()}
    _print_report(avg_stats, k)


def _print_report(results: Dict, k: int):
    print(f"\n{'='*60}")
    print(f"📊 LAWAGENT RETRIEVAL PERFORMANS RAPORU (k={k})")
    print(f"{'='*60}")
    print(f"  Recall@{k}   : {results['recall']:.4f}  (Hedef: ≥0.75)")
    print(f"  MRR@{k}      : {results['mrr']:.4f}  (Hedef: ≥0.60)")
    print(f"  nDCG@{k}     : {results['ndcg']:.4f}  (Hedef: ≥0.70)")
    print(f"  Hit Rate@{k} : {results['hit']:.4f}")
    print(f"  Ort. Süre   : {results['time']:.1f} ms")
    print(f"{'='*60}")

    # TÜBİTAK Hedef Kontrolü
    if results["recall"] >= 0.75 and results["mrr"] >= 0.60:
        print("🎉 TEBRİKLER: Proje formu hedeflerine ulaşıldı!")
    else:
        print("⚠️ DİKKAT: Bazı metrikler hedef değerlerin altında.")


if __name__ == "__main__":
    # Önce retriever'ı başlatalım (Cache varsa hızlı yüklenir)
    r = LegalRetriever(quantize=False)
    run_evaluation(r, k=10)
