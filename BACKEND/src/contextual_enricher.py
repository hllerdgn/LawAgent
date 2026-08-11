"""
contextual_enricher.py — LawAgent Contextual Retrieval Ön İşleme Scripti

Görev:
1. chunk_corpus_enriched.json dosyasını yükler.
2. Tüm chunk'lara programatik bağlam (Kanun adı + Madde no) ekler.
3. Kritik / hata eğilimli maddeler (TBK 161, 163, 39, TTK 375, 625, 632, TKHK 23, 33, 68 vb.) için 
   Groq/Llama-3.3 aracılığıyla detaylı hukuki bağlam üretip ekler (Contextual Retrieval).
4. chunk_corpus_enriched.json dosyasını günceller.
"""

import json
import re
import os
import sys
import time
from typing import Dict, List

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_SRC_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# .env dosyasını yükle
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(_BACKEND_DIR, ".env"))

# Zenginleştirilecek kritik kanun-madde çiftleri
CRITICAL_ARTICLES = {
    ("TBK", "1"): "Sözleşmenin kurulması, irade beyanı ve karşılıklı anlaşma şartları.",
    ("TBK", "19"): "Sözleşmelerin yorumlanması, muvazaa (danışıklı işlem) ve gizli irade.",
    ("TBK", "26"): "Sözleşme özgürlüğü ve sınırları.",
    ("TBK", "27"): "Sözleşmenin ahlaka, kamu düzenine aykırılığı ve butlan (geçersizlik) hükümleri.",
    ("TBK", "28"): "Gabin (aşırı yararlanma), sömürme ve edimler arası aşırı orantısızlık.",
    ("TBK", "30"): "Hata, yanılma ve irade sakatlığı halleri.",
    ("TBK", "36"): "Hile, aldatma, kandırma ve irade sakatlığı.",
    ("TBK", "37"): "İkrah, korkutma, tehdit, zorlama ve irade sakatlığı.",
    ("TBK", "38"): "İkrah (korkutma) koşulları ve yakın zarar tehlikesi.",
    ("TBK", "39"): "İrade sakatlıklarında (hata, hile, ikrah) iptal hakkı ve 1 yıllık hak düşürücü süre.",
    ("TBK", "97"): "Karşılıklı borç yükleyen sözleşmelerde ifa sırası ve kendi borcunu ödeme şartı.",
    ("TBK", "112"): "Borcun ifa edilmemesi, borçlunun genel sorumluluğu ve tazminat.",
    ("TBK", "117"): "Temerrüt, borçlunun temerrüde düşmesi, ihtar ve gecikme süreci.",
    ("TBK", "125"): "Karşılıklı sözleşmelerde temerrüt durumunda alacaklının dönme ve tazminat hakları.",
    ("TBK", "146"): "Alacak haklarında genel zamanaşımı süresi (10 yıllık genel süre).",
    ("TBK", "147"): "Beş yıllık zamanaşımına tabi olan alacaklar (kira alacakları, otel, serbest meslek vb.).",
    ("TBK", "161"): "Müteselsil borçluluk, ortaklaşa borca girme ve borçluların sorumluluğu.",
    ("TBK", "163"): "Müteselsil borçlulardan her birinin alacaklıya karşı sorumluluğu ve borcun tamamının talep edilebilmesi.",
    ("TBK", "347"): "Konut ve çatılı işyeri kiralarında sözleşmenin süresi, uzaması ve tahliye bildirim süreleri.",
    ("TBK", "352"): "Kira sözleşmesinde kiracının tahliye taahhüdü, iki haklı ihtar ve tahliye nedenleri.",
    ("TBK", "474"): "Eser sözleşmesinde (inşaat vb.) ayıplı teslim, muayene ve ihbar süreleri.",
    ("TBK", "506"): "Vekalet sözleşmesinde vekilin özen borcu, sadakat yükümlülüğü ve dikkat derecesi.",
    ("TBK", "584"): "Kefalet sözleşmesinde eşin rızası ve geçerlilik şartları.",
    ("TTK", "18"): "Tacir olmanın hükümleri, basiretli iş adamı gibi davranma yükümlülüğü.",
    ("TTK", "56"): "Haksız rekabet davaları, haksız rekabetin tespiti, önlenmesi ve tazminat.",
    ("TTK", "375"): "Anonim şirket yönetim kurulunun devredilemez ve vazgeçilemez asli yetkileri.",
    ("TTK", "392"): "Anonim şirket yönetim kurulunun toplantıya çağrılması ve bilgi alma hakkı.",
    ("TTK", "409"): "Anonim şirket genel kurul toplantı zamanı ve olağan toplantı esasları.",
    ("TTK", "413"): "Genel kurul toplantılarında gündeme bağlılık ilkesi ve dışı konular.",
    ("TTK", "445"): "Genel kurul kararlarının iptali, butlanı ve iptal davası açma süreleri.",
    ("TTK", "553"): "Yöneticilerin, kurucuların ve yönetim kurulu üyelerinin hukuki sorumluluğu ve tazminat.",
    ("TTK", "595"): "Limited şirket esas sermaye payının devri, noter şartı ve genel kurul onayı.",
    ("TTK", "625"): "Limited şirket müdürlerinin devredilemez ve vazgeçilemez asli görevleri.",
    ("TTK", "632"): "Limited şirket müdürlerinin şirkete ve ortaklara karşı tazminat ve hukuki sorumluluğu.",
    ("TTK", "796"): "Çekin muhatap bankaya ibraz süreleri (10 gün, 1 ay vb. ibraz süreleri).",
    ("TTK", "814"): "Karşılıksız çek düzenlenmesi durumunda hamilin tazminat ve ciro hakları.",
    ("TKHK", "5"): "Tüketici sözleşmelerindeki haksız şartlar ve geçersizlikleri.",
    ("TKHK", "7"): "Sipariş edilmeyen mal veya hizmetlerin gönderilmesi durumunda tüketicinin hakları.",
    ("TKHK", "11"): "Ayıplı (kusurlu) mal durumunda tüketicinin seçimlik hakları (iade, indirim, onarım, değişim).",
    ("TKHK", "23"): "Tüketici kredisi sözleşmesinin geçerlilik şartları ve yazılı yapılma zorunluluğu.",
    ("TKHK", "24"): "Tüketici kredisinde tüketicinin 14 günlük cayma hakkı ve kullanılması.",
    ("TKHK", "27"): "Tüketici kredisinin erken kapatılması durumunda faiz ve komisyon indirimi hakları.",
    ("TKHK", "33"): "Konut finansmanı (ev kredisi) sözleşmelerinde temerrüt ve muacceliyet şartları.",
    ("TKHK", "48"): "Mesafeli sözleşmeler (internet alışverişi vb.) ve tüketicinin 14 günlük cayma hakkı.",
    ("TKHK", "52"): "Abonelik sözleşmelerinin feshedilmesi şartları ve cayma bedeli kuralları.",
    ("TKHK", "56"): "Garanti belgesi düzenleme zorunluluğu ve asgari garanti süreleri.",
    ("TKHK", "68"): "Tüketici hakem heyetine başvuru zorunluluğu ve parasal sınırları."
}

def get_law_full_name(code: str) -> str:
    mapping = {
        "TBK": "Türk Borçlar Kanunu",
        "TTK": "Türk Ticaret Kanunu",
        "TKHK": "Tüketicinin Korunması Hakkında Kanun",
        "TMK": "Türk Medeni Kanunu",
        "IIK": "İcra ve İflas Kanunu",
        "HMK": "Hukuk Muhakemeleri Kanunu"
    }
    return mapping.get(code.upper(), code)

def main():
    enriched_path = os.path.join(_SRC_DIR, "data", "chunk_corpus_enriched.json")
    if not os.path.exists(enriched_path):
        import shutil
        shutil.copy(os.path.join(_SRC_DIR, "data", "chunk_corpus.json"), enriched_path)

    print(f"Loading corpus from {enriched_path}...")
    with open(enriched_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    groq_client = None
    try:
        from groq import Groq
        api_key = os.environ.get("GROQ_API_KEY", "")
        if api_key:
            groq_client = Groq(api_key=api_key)
            print("Groq API connected successfully.")
    except Exception as e:
        print(f"Warning: Groq client could not start: {e}. Falling back to rule-based prefix.")

    updated_count = 0
    llm_count = 0

    print("Enriching chunks with Contextual Prefixes...")
    for idx, c in enumerate(chunks):
        if c.get("source") != "mevzuat":
            continue

        law = str(c.get("law", ""))
        art_raw = c.get("article_no", "")
        art = re.search(r'\d+', str(art_raw))
        art_no = art.group() if art else ''
        key = (law, art_no)

        law_name = get_law_full_name(law)
        context_sentence = ""
        
        if key in CRITICAL_ARTICLES and groq_client:
            summary = CRITICAL_ARTICLES[key]
            text_snippet = c.get("text", "")[:400]
            
            prompt = (
                f"Sen bir Türk Hukuku uzmanısın. Aşağıdaki kanun maddesi metnini analiz et:\n"
                f"Kanun: {law_name} ({law})\n"
                f"Madde: {art_no}\n"
                f"Metin: {text_snippet}\n\n"
                f"Bu madde genel olarak '{summary}' konusunu düzenlemektedir.\n"
                f"Bu metnin hangi hukuki durumda, kimler arasında ve ne amaçla uygulanacağını "
                f"açıklayan 1-2 cümlelik net bir bağlam özeti yaz. Yanıtında sadece bu özeti ver, "
                f"başka hiçbir şey yazma (örn. 'Bu madde...' diye başlama, doğrudan konuyu açıkla)."
            )
            
            try:
                resp = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=100
                )
                context_sentence = resp.choices[0].message.content.strip()
                llm_count += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"Error calling Groq for {law} m.{art_no}: {e}")
                context_sentence = f"{law_name} ({law}) kapsamında {summary} konusunu düzenler."
        
        if not context_sentence:
            if key in CRITICAL_ARTICLES:
                context_sentence = f"{law_name} ({law}) kapsamında {CRITICAL_ARTICLES[key]}"
            else:
                context_sentence = f"{law_name} ({law}) Madde {art_no} hükümleri ve hukuki düzenlemeleri kapsamındadır."

        current_text = c.get("text", "")
        prefix = f"[Bağlam: {context_sentence}]\n"
        
        if "[Bağlam:" not in current_text:
            new_text = prefix + current_text
            chunks[idx] = {**c, "text": new_text, "context_added": True}
            updated_count += 1

    print(f"Enrichment completed. Programmatic prefix applied to {updated_count} chunks.")
    print(f"LLM-generated detailed prefix applied to {llm_count} critical chunks.")

    with open(enriched_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"Saved enriched corpus to {enriched_path}.")

if __name__ == "__main__":
    main()
