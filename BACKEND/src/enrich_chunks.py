"""
enrich_chunks.py — LawAgent Corpus Zenginleştirici

Görev:
1. Mevcut chunk_corpus.json'daki chunk'lara hukuki sinonim/terim prefix ekle
2. Encoding sorunu olan chunk'ları tespit et, Groq ile açıklayıcı bağlam üret
3. chunk_corpus_enriched.json olarak kaydet (orijinali koruyarak)

Kullanım:
    python src/enrich_chunks.py [--mode sinonim|contextual|both] [--limit N]
"""

import json
import re
import os
import sys
import argparse
import time
from typing import Dict, List, Optional

# --- Hukuki Sinonim/Terim Eşleştirme ---
# Format: (kanun, madde_no) -> ek terimler prefix olarak eklenir
ARTICLE_ENRICHMENTS = {
    # TBK — İrade sakatlıkları
    ("TBK", "37"): "ikrah korkutma irade sakatlığı tehdit zorlama sözleşme geçersizlik",
    ("TBK", "38"): "ikrah korkutma koşulları yakın zarar tehlikesi irade sakatlığı",
    ("TBK", "39"): "ikrah korkutma iptal hakkı süre bir yıl hak düşürücü onay onam",
    ("TBK", "28"): "gabin aşırı yararlanma sömürme orantısızlık sarsılma dengesizlik",
    ("TBK", "30"): "yanılma hata irade sakatlığı esaslı yanılma",
    ("TBK", "36"): "hile aldatma irade sakatlığı kandırma",
    # TBK — Temerrüt
    ("TBK", "117"): "borçlu temerrüdü gecikme ihtar ihbarlı temerrüt alacaklının hakları",
    ("TBK", "118"): "temerrüt faizi gecikme faizi ihtar",
    ("TBK", "119"): "munzam zarar temerrüt ispat tazminat",
    # TBK — Zamanaşımı
    ("TBK", "146"): "genel zamanaşımı on yıl süre hak düşürücü",
    ("TBK", "147"): "beş yıllık zamanaşımı kira alacak",
    ("TBK", "153"): "zamanaşımı durması kesilmesi ihtar dava",
    ("TBK", "154"): "zamanaşımı kesilmesi borç ikrarı",
    # TBK — Kira
    ("TBK", "347"): "kira sözleşmesi fesih bildirim süre uzama",
    ("TBK", "350"): "kira tahliye ihtiyaç sebebi ev sahibi",
    ("TBK", "352"): "kira tahliye kiracı temerrüt fesih iki haklı ihtar",
    # TBK — Kefalet
    ("TBK", "583"): "kefalet sözleşmesi şekil koşulu eş rızası yazılı",
    ("TBK", "584"): "eş rızası kefalet geçerlilik şartı",
    # TBK — Vekalet
    ("TBK", "506"): "vekalet sözleşmesi tanımı vekil özen borcu",
    ("TBK", "513"): "vekil özen borcu sadakat yükümlülüğü hesap verme",
    # TBK — Eser sözleşmesi
    ("TBK", "472"): "eser sözleşmesi müteahhit teslim ayıp",
    ("TBK", "474"): "eser sözleşmesi ayıplı iş müteahhit sorumluluk",
    ("TBK", "475"): "eser ayıplı seçimlik haklar bedel indirimi yeniden yapma",
    ("TBK", "482"): "eser ayıp ihbar süresi muayene küçük ayıp",
    # TKHK — Temerrüt / Konut finansmanı
    ("TKHK", "33"): "konut finansmanı temerrüt muacceliyet tüketici kredisi taksit ödenmemesi",
    # TTK — YK azil
    ("TTK", "413"): "yönetim kurulu üyesi azil gündem gündeme bağlılık oy çokluğu",
    ("TTK", "375"): "yönetim kurulu devredilemez görevler vazgeçilemez yetki",
    # TTK — Limited müdür
    ("TTK", "625"): "limited şirket müdürlük yetkisi devir devredilemez temsil",
}

# Düşük kaliteli / encoding bozuk chunk tespiti
def is_corrupt(text: str) -> bool:
    """Encoding bozukluğu olan chunk'ları tespit eder."""
    # Windows-1252 → UTF-8 bozulmasında tipik işaretler
    corrupt_chars = ['?', '?', '?', '?', '?', '?', '?', '?']
    corrupt_count = sum(text.count(c) for c in corrupt_chars)
    return corrupt_count > len(text) * 0.05  # %5'ten fazla bozuk karakter


def enrich_with_synonyms(chunks: List[Dict]) -> tuple[List[Dict], int]:
    """chunk_corpus'a sinonim/terim prefix ekler."""
    enriched = 0
    result = []
    for ch in chunks:
        law = ch.get('law', '')
        art_raw = ch.get('article_no', '')
        art = re.search(r'\d+', str(art_raw))
        art_no = art.group() if art else ''

        key = (law, art_no)
        if key in ARTICLE_ENRICHMENTS:
            prefix = f"[Hukuki Terimler: {ARTICLE_ENRICHMENTS[key]}]\n"
            new_text = prefix + ch.get('text', '')
            ch = {**ch, 'text': new_text, 'enriched': True}
            enriched += 1

        result.append(ch)
    return result, enriched


def enrich_with_context_llm(chunks: List[Dict], limit: int = 50) -> tuple[List[Dict], int]:
    """Groq ile bağlam prefix üretir (Contextual Retrieval)."""
    try:
        from groq import Groq
        client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    except Exception as e:
        print(f"[Contextual] Groq bağlanamadı: {e}")
        return chunks, 0

    # Önce TBK chunk'larını işle (zayıf kategori)
    priority_laws = ["TBK", "TKHK"]
    tbk_chunks = [i for i, ch in enumerate(chunks)
                  if ch.get('law') in priority_laws
                  and not ch.get('context_added')
                  and len(ch.get('text', '')) > 50]

    processed = 0
    result = list(chunks)

    for idx in tbk_chunks[:limit]:
        ch = result[idx]
        law = ch.get('law', '')
        art = re.search(r'\d+', str(ch.get('article_no', '')))
        art_no = art.group() if art else '?'
        text = ch.get('text', '')[:400]

        prompt = (
            f"Türk Hukuku {law} Kanunu Madde {art_no} içeriği:\n{text}\n\n"
            f"Bu maddenin içeriğini 1-2 cümleyle özetle. "
            f"Hangi hukuki kavramı düzenler? Hangi durumda uygulanır? "
            f"Sadece özet, başka açıklama yapma."
        )

        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=100,
            )
            summary = resp.choices[0].message.content.strip()
            context_prefix = f"[Bağlam: {summary}]\n"
            result[idx] = {**ch, 'text': context_prefix + ch['text'], 'context_added': True}
            processed += 1
            print(f"  [{processed}/{limit}] {law} m.{art_no}: {summary[:60]}...")
            time.sleep(0.3)  # Rate limit koruması
        except Exception as e:
            print(f"  HATA {law} m.{art_no}: {e}")
            time.sleep(1.0)

    return result, processed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['sinonim', 'contextual', 'both'], default='sinonim')
    parser.add_argument('--limit', type=int, default=100,
                        help='Contextual mode: max kaç chunk işlensin')
    args = parser.parse_args()

    corpus_path = 'src/data/chunk_corpus.json'
    output_path = 'src/data/chunk_corpus_enriched.json'

    print(f"Corpus yükleniyor: {corpus_path}")
    with open(corpus_path, encoding='utf-8') as f:
        chunks = json.load(f)
    print(f"  {len(chunks)} chunk yüklendi.")

    # Encoding bozuk chunk'ları say
    corrupt = sum(1 for ch in chunks if is_corrupt(ch.get('text', '')))
    print(f"  Encoding bozuk chunk: {corrupt} ({corrupt/len(chunks)*100:.1f}%)")

    total_enriched = 0

    if args.mode in ('sinonim', 'both'):
        print("\n[1/2] Sinonim/terim enrichment...")
        chunks, n = enrich_with_synonyms(chunks)
        total_enriched += n
        print(f"  {n} chunk'a terim prefix eklendi.")

    if args.mode in ('contextual', 'both'):
        print(f"\n[2/2] Contextual prefix (Groq, limit={args.limit})...")
        chunks, n = enrich_with_context_llm(chunks, limit=args.limit)
        total_enriched += n
        print(f"  {n} chunk'a bağlam prefix eklendi.")

    print(f"\nKaydediliyor: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"\nTamamlandi: {total_enriched} chunk zenginlestirildi.")
    print(f"Sonraki adim: embedder.py'yi chunk_corpus_enriched.json ile calistir.")


if __name__ == '__main__':
    main()
