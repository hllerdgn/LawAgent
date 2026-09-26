"""
src/pipeline/documents/parser.py — Sirket Belgesi Parser & Chunker
"""

import re
import logging
from pathlib import Path
from typing import Literal

log = logging.getLogger("LawAgent.DocumentParser")

FileType = Literal["pdf", "docx", "txt"]

_WORDS_PER_TOKEN = 0.75
_TARGET_TOKENS = 500
_TARGET_WORDS = int(_TARGET_TOKENS / _WORDS_PER_TOKEN)
_OVERLAP_WORDS = int(_TARGET_WORDS * 0.10)


def parse_document(file_path, file_type: str) -> str:
    path = Path(file_path)
    file_type = file_type.lower().strip(".")
    if file_type == "pdf":
        return _parse_pdf(path)
    elif file_type == "docx":
        return _parse_docx(path)
    elif file_type == "txt":
        return _parse_txt(path)
    else:
        raise ValueError(f"Desteklenmeyen dosya formati: {file_type}")


def _parse_pdf(path: Path) -> str:
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    doc = fitz.open(str(path))
    pages = []
    for page in doc:
        blocks = page.get_text("blocks")
        text_blocks = [b[4].strip() for b in blocks if b[6] == 0 and b[4].strip()]
        pages.append("\n".join(text_blocks))
    doc.close()
    return "\n\n".join(pages)


def _parse_docx(path: Path) -> str:
    from docx import Document
    doc = Document(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _parse_txt(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def chunk_generic(
    text: str,
    max_tokens: int = 500,
    overlap_tokens: int = 50,
) -> list:
    """
    Metni chunk'lara boler.

    Donus degeri: List[Tuple[str, int, int]]
        (chunk_text, start_char, end_char) — end_char dahil degil (slice notasyonu)

    Ofset hesabi: re.finditer ile her kelimenin full_text icindeki gercek
    karakter pozisyonu onceden hesaplanir. Boylece PDF'teki cift bosluk veya
    satir sonu nedeniyle normalize edilmis chunk_text'in text.find() ile
    bulunamama sorunu tamamen ortadan kalkar.
    """
    import re as _re

    max_words = int(max_tokens / _WORDS_PER_TOKEN)
    overlap_words = int(overlap_tokens / _WORDS_PER_TOKEN)

    # ── Kelime pozisyon tablosu ───────────────────────────────────────────────
    # Her kelimenin (token) full_text icindeki (start, end) ofsetleri
    word_spans = [(m.start(), m.end()) for m in _re.finditer(r'\S+', text)]
    word_list = [text[s:e] for s, e in word_spans]  # Gercek kelimeler

    if not word_list:
        return []

    # Paragraf ayraclari: iki veya daha fazla bosluk/newline iceren bolumler
    # Hangi kelime indekslerinin yeni paragraf baslattigi bilgisi
    para_breaks: set = set()
    prev_end = 0
    for wi, (ws, we) in enumerate(word_spans):
        gap = text[prev_end:ws]
        if wi > 0 and _re.search(r'\n\s*\n|\n', gap):
            para_breaks.add(wi)
        prev_end = we

    # ── Chunklama — word_spans uzerinden ─────────────────────────────────────
    # current_word_indices: aktif chunk'taki kelime indeksleri
    chunk_word_ranges: list = []  # [(start_wi, end_wi_exclusive), ...]
    current_indices: list = []

    def _flush(indices):
        if len(indices) >= 10:
            chunk_word_ranges.append((indices[0], indices[-1] + 1))

    for wi, word in enumerate(word_list):
        # Paragraf sinirinda: yeni chunk basla
        if wi in para_breaks and len(current_indices) + 1 > max_words:
            _flush(current_indices)
            current_indices = current_indices[-overlap_words:] if overlap_words else []

        current_indices.append(wi)

        if len(current_indices) >= max_words:
            _flush(current_indices)
            current_indices = current_indices[-overlap_words:] if overlap_words else []

    _flush(current_indices)

    # ── Sonuc: (chunk_text, start_char, end_char) ─────────────────────────────
    result: list = []
    for start_wi, end_wi in chunk_word_ranges:
        if end_wi - start_wi < 10:
            continue
        start_char = word_spans[start_wi][0]
        end_char = word_spans[end_wi - 1][1]
        chunk_text = " ".join(word_list[start_wi:end_wi])
        result.append((chunk_text, start_char, end_char))

    log.info(f"[DocumentParser] {len(para_breaks) + 1} paragraf -> {len(result)} chunk")
    return result


