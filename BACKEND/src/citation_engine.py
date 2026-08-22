"""
citation_engine.py — LawAgent AI Deterministik Atıf & Kaynak Eşleme Motoru
=============================================================================
Bu modül:
  1. Retrieved chunk'ları [K1], [K2] formatında yapılandırılmış XML bağlamına çevirir.
  2. LLM çıktısındaki atıfları ([K1], [K2]) deterministik olarak doğrular.
  3. Yalnızca metinde fiilen kullanılan veya doğrudan dayanak olan kaynakları
     API 'sources' listesine ekler (kaynak uydurma ve mükerrerliği önler).
"""

import re
from typing import Dict, List, Tuple, Any, Optional
from legal_normalizer import CANONICAL_LAW_NAMES


def get_canonical_law_title(law_code: str) -> str:
    """Kısa kanun kodundan (TKHK) resmi tam başlığı üretir."""
    code_clean = (law_code or "").strip().upper()
    return CANONICAL_LAW_NAMES.get(code_clean, law_code or "Mevzuat")


def build_grounded_context(chunks: List[Dict], source_filter: Optional[str] = None) -> Tuple[str, Dict[str, Dict]]:
    """
    Retrieved chunk listesini yapılandırılmış XML formatına dönüştürür ve
    her kaynağa benzersiz bir etiket ([K1], [K2]...) atar.
    
    Returns:
        context_str: Prompt'a enjekte edilecek metin.
        source_map: {"K1": chunk_dict, "K2": chunk_dict, ...}
    """
    lines = ["<HUKUKI_KAYNAKLAR>"]
    source_map: Dict[str, Dict] = {}
    
    k_index = 1
    for c in chunks:
        source_type = str(c.get("source", "Mevzuat")).upper()
        if source_filter and source_type != source_filter.upper():
            continue
            
        key = f"K{k_index}"
        source_map[key] = c
        
        if source_type == "SITE_DOCUMENT":
            doc_name = c.get("filename", "Bilinmeyen Belge")
            page_info = f" (Sayfa {c.get('page')})" if c.get("page") else ""
            lines.append(
                f"[KAYNAK {key}]\n"
                f"Tür: Özel Belge\n"
                f"Belge: {doc_name}{page_info}\n"
                f"Metin: {c.get('text', '').strip()}"
            )
        elif source_type == "YARGITAY":
            decision_id = c.get("decision_id", "Emsal Karar")
            lines.append(
                f"[KAYNAK {key}]\n"
                f"Tür: Yargıtay Emsal Kararı\n"
                f"Karar Künyesi: {decision_id}\n"
                f"Hukuki İlke: {c.get('text', '').strip()}"
            )
        else:
            law_raw = c.get("law", "Mevzuat")
            law_full = get_canonical_law_title(law_raw)
            art_no = str(c.get("article_no", "")).strip()
            lines.append(
                f"[KAYNAK {key}]\n"
                f"Tür: Kanun Maddesi\n"
                f"Kanun: {law_full} ({law_raw})\n"
                f"Madde: {art_no if art_no else 'Genel Hüküm'}\n"
                f"Metin: {c.get('text', '').strip()}"
            )
            
        lines.append("")  # Boşluk
        k_index += 1
        
    lines.append("</HUKUKI_KAYNAKLAR>")
    return "\n".join(lines), source_map


def validate_and_extract_citations(
    answer: str,
    source_map: Dict[str, Dict],
    fallback_chunks: Optional[List[Dict]] = None,
) -> Tuple[str, List[Dict], bool]:
    """
    Yanıttaki [K1], [K2] gibi etiketleri tarar, source_map ile doğrular
    ve sadece atıf alan gerçek kaynakları listeler.
    
    Returns:
        sanitized_answer: Doğrulanmış yanıt metni.
        validated_sources: API'ye döndürülecek kaynak listesi.
        is_fully_grounded: Tüm atıflar doğru mu?
    """
    if not answer:
        return "", [], False
        
    # Yanıtta geçen tüm [K\d+] etiketlerini bul
    found_tags = set(re.findall(r"\[(K\d+)\]", answer))
    
    validated_sources: List[Dict] = []
    seen_source_keys = set()
    invalid_tags = set()
    
    for tag in sorted(found_tags, key=lambda x: int(x[1:])):
        if tag in source_map:
            chunk = source_map[tag]
            law_name = chunk.get("law") or chunk.get("filename") or "Mevzuat"
            art_no = str(chunk.get("article_no", "")).strip()
            
            # Mükerrerlik engelleme
            source_key = f"{law_name}_{art_no}"
            if source_key not in seen_source_keys:
                seen_source_keys.add(source_key)
                validated_sources.append({
                    "kanun": get_canonical_law_title(law_name) if chunk.get("source") != "site_document" else law_name,
                    "madde": art_no,
                    "ozet": chunk.get("text", "")[:300],
                    "citation_key": tag,
                })
        else:
            invalid_tags.add(tag)
            
    # Geçersiz / uydurma etiketleri metinden temizle
    sanitized_answer = answer
    for inv_tag in invalid_tags:
        sanitized_answer = re.sub(rf"\[{inv_tag}\]", "", sanitized_answer)
        
    # Eğer model [K_i] etiketi kullanmadıysa ama madde numarası eşleşiyorsa fallback
    if not validated_sources and fallback_chunks:
        mentioned_articles = set(re.findall(r"m(?:adde)?\.?\s*(\d+)", sanitized_answer, re.IGNORECASE))
        for c in fallback_chunks:
            c_art = str(c.get("article_no", "")).strip()
            if c_art and c_art in mentioned_articles:
                law_name = c.get("law") or c.get("filename") or "Mevzuat"
                source_key = f"{law_name}_{c_art}"
                if source_key not in seen_source_keys:
                    seen_source_keys.add(source_key)
                    validated_sources.append({
                        "kanun": get_canonical_law_title(law_name) if c.get("source") != "site_document" else law_name,
                        "madde": c_art,
                        "ozet": c.get("text", "")[:300],
                        "citation_key": "auto_matched",
                    })
                    
    # Eğer hala kaynak listesi boşsa ve metin olumlu bir analiz ise, en yüksek skorlu 2 chunk'ı koy
    if not validated_sources and fallback_chunks and len(fallback_chunks) > 0:
        for c in fallback_chunks[:2]:
            law_name = c.get("law") or c.get("filename") or "Mevzuat"
            art_no = str(c.get("article_no", "")).strip()
            validated_sources.append({
                "kanun": get_canonical_law_title(law_name) if c.get("source") != "site_document" else law_name,
                "madde": art_no,
                "ozet": c.get("text", "")[:300],
                "citation_key": "top_retrieved",
            })
            
    is_fully_grounded = len(invalid_tags) == 0
    return sanitized_answer.strip(), validated_sources, is_fully_grounded
