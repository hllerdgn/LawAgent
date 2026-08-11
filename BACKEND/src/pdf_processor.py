import uuid
import fitz
import json
import os
import re
from datetime import datetime
from typing import List
from qdrant_client.http import models as qmodels

SITE_COLLECTION_NAME = "site_corpus"
DOCS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "site_documents.json")

def get_uploaded_documents() -> List[dict]:
    if not os.path.exists(DOCS_FILE):
        return []
    try:
        with open(DOCS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_document_metadata(filename: str, chunk_count: int):
    docs = get_uploaded_documents()
    # Check if already exists, if so update it
    exists = False
    for d in docs:
        if d["filename"] == filename:
            d["chunk_count"] = chunk_count
            d["upload_date"] = datetime.now().isoformat()
            exists = True
            break
    if not exists:
        docs.append({
            "filename": filename,
            "chunk_count": chunk_count,
            "upload_date": datetime.now().isoformat()
        })
    
    os.makedirs(os.path.dirname(DOCS_FILE), exist_ok=True)
    with open(DOCS_FILE, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=4)

def delete_document(filename: str, qdrant) -> bool:
    try:
        # Create index if it doesn't exist (required for filtering)
        try:
            qdrant.create_payload_index(
                collection_name=SITE_COLLECTION_NAME,
                field_name="filename",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )
        except Exception as idx_err:
            pass
            
        # Delete from Qdrant
        qdrant.delete(
            collection_name=SITE_COLLECTION_NAME,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="filename",
                            match=qmodels.MatchValue(value=filename)
                        )
                    ]
                )
            )
        )
        
        # Delete from JSON
        docs = get_uploaded_documents()
        docs = [d for d in docs if d["filename"] != filename]
        with open(DOCS_FILE, "w", encoding="utf-8") as f:
            json.dump(docs, f, ensure_ascii=False, indent=4)
            
        return True
    except Exception as e:
        print(f"Delete document error: {e}")
        return False

SITE_COLLECTION_NAME = "site_corpus"

# ── Heading / section boundary patterns ───────────────────────────────────────
# Bir satır şu kalıplardan birine uyuyorsa yeni bir bölüm başladığı kabul edilir:
#   • MADDE 12  /  Madde 12  /  m. 12
#   • BÖLÜM III  /  Bölüm 3
#   • § 5
#   • 1. Genel Hükümler  (numara + büyük başlangıç)
#   • I. / II. / III. … (Romen rakamı)
_HEADING_RE = re.compile(
    r"""^
    (?:
        (?:MADDE|Madde|m\.)\s*\d+          # Madde numarası
        | (?:BÖLÜM|Bölüm|KISIM|Kısım)\s*[\dIVXivx]+  # Bölüm / Kısım
        | §\s*\d+                           # § işareti
        | \d+\.\s+[A-ZÇĞİÖŞÜa-zçğışöüü]  # 1. Başlık
        | [IVX]+\.\s+[A-ZÇĞİÖŞÜ]          # Romen rakamı başlık
    )
    """,
    re.VERBOSE,
)


def _is_heading(line: str) -> bool:
    return bool(_HEADING_RE.match(line.strip()))


def _split_oversized(text: str, max_words: int, overlap_words: int) -> List[str]:
    """Doğal sınır bulunamayan büyük blokları kelime bazlı böler (fallback)."""
    words = text.split()
    chunks: List[str] = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i : i + max_words]))
        i += max_words - overlap_words
    return chunks


def chunk_text(
    text: str,
    max_words: int = 300,
    overlap_words: int = 50,
) -> List[str]:
    """
    Paragraf ve başlık sınırlarına saygı gösteren yapısal chunking.

    Strateji
    --------
    1. Metni çift-yeni-satır (\\n\\n) ile paragraflara böl.
    2. Her paragrafı "başlık mı?" diye kontrol et.
    3. Paragrafları biriktir; toplam kelime sayısı max_words'ü geçince
       birikmiş bloğu bir chunk olarak kaydet ve son overlap_words kelimeyi
       bir sonraki bloğa taşı (bağlam sürekliliği).
    4. Yeni bir BAŞLIK gördüğümüzde mevcut bloğu sıfırla (konu sınırı).
    5. Eğer tek bir paragraf max_words'ü aşarsa _split_oversized ile böl.
    """
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]

    chunks: List[str] = []
    current_block: List[str] = []
    current_words = 0

    def flush(block: List[str]) -> List[str]:
        joined = "\n\n".join(block)
        return _split_oversized(joined, max_words, overlap_words) if len(joined.split()) > max_words else [joined]

    for para in paragraphs:
        para_words = len(para.split())
        is_heading = _is_heading(para)

        # Başlık geldiğinde mevcut bloğu kapat
        if is_heading and current_block:
            chunks.extend(flush(current_block))
            # overlap: son bloğun son overlap_words kelimesini taşı
            last_text = current_block[-1]
            tail_words = last_text.split()[-overlap_words:]
            current_block = [" ".join(tail_words)] if tail_words else []
            current_words = len(current_block[0].split()) if current_block else 0

        # Mevcut blok + yeni paragraf sınırı aşıyorsa flush
        if current_words + para_words > max_words and current_block:
            chunks.extend(flush(current_block))
            last_text = current_block[-1]
            tail_words = last_text.split()[-overlap_words:]
            current_block = [" ".join(tail_words)] if tail_words else []
            current_words = len(current_block[0].split()) if current_block else 0

        current_block.append(para)
        current_words += para_words

    if current_block:
        chunks.extend(flush(current_block))

    return [c for c in chunks if c.strip()]


def _extract_pages(doc: fitz.Document) -> List[dict]:
    """Her sayfadan metni çeker; sayfa numarası metadata olarak döndürülür."""
    pages = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:
            pages.append({"page": page_num, "text": text})
    return pages


def process_and_index_pdf(pdf_bytes: bytes, filename: str, embedder, qdrant) -> int:
    # 1. Sayfa bazlı metin çıkarımı
    doc = fitz.open("pdf", pdf_bytes)
    pages = _extract_pages(doc)

    # 2. Yapısal chunking (paragraf/başlık sınırı)
    all_chunks: List[dict] = []  # {"text": ..., "page": ...}
    for page_info in pages:
        page_chunks = chunk_text(page_info["text"], max_words=300, overlap_words=50)
        for ch in page_chunks:
            all_chunks.append({"text": ch, "page": page_info["page"]})

    if not all_chunks:
        return 0

    # 3. Collection oluştur (yoksa)
    existing = [c.name for c in qdrant.get_collections().collections]
    if SITE_COLLECTION_NAME not in existing:
        qdrant.create_collection(
            SITE_COLLECTION_NAME,
            vectors_config=qmodels.VectorParams(
                size=embedder.vector_size, distance=qmodels.Distance.COSINE
            ),
        )
        
    # 4. Embed + Upload (batch)
    BATCH_SIZE = 32
    total_added = 0
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i : i + BATCH_SIZE]
        texts = [c["text"] for c in batch]
        vecs = embedder.encode(texts)
        
        points = []
        for idx, chunk_info in enumerate(batch):
            chunk_id = uuid.uuid4()
            points.append(
                qmodels.PointStruct(
                    id=chunk_id.int >> 64,
                    vector=vecs[idx],
                    payload={
                        "chunk_id": str(chunk_id),
                        "text": chunk_info["text"],
                        "source": "site_document",
                        "filename": filename,
                        "page": chunk_info["page"],
                    },
                )
            )
        qdrant.upsert(collection_name=SITE_COLLECTION_NAME, points=points)
        total_added += len(points)
        
    save_document_metadata(filename, total_added)
        
    return total_added
