import uuid
import fitz
from typing import List
from qdrant_client.http import models as qmodels

SITE_COLLECTION_NAME = "site_corpus"

def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> List[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks

def process_and_index_pdf(pdf_bytes: bytes, filename: str, embedder, qdrant) -> int:
    # 1. Extract text from PDF
    doc = fitz.open("pdf", pdf_bytes)
    full_text = ""
    for page in doc:
        full_text += page.get_text("text") + "\n"
    
    # 2. Chunk text
    chunks = chunk_text(full_text, chunk_size=300, overlap=50)
    if not chunks:
        return 0

    # 3. Ensure collection exists
    existing = [c.name for c in qdrant.get_collections().collections]
    if SITE_COLLECTION_NAME not in existing:
        qdrant.create_collection(
            SITE_COLLECTION_NAME,
            vectors_config=qmodels.VectorParams(
                size=embedder.vector_size, distance=qmodels.Distance.COSINE
            ),
        )
        
    # 4. Embed and Upload in batches
    BATCH_SIZE = 32
    total_added = 0
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i+BATCH_SIZE]
        vecs = embedder.encode(batch)
        
        points = []
        for idx, chunk in enumerate(batch):
            chunk_id = uuid.uuid4()
            points.append(
                qmodels.PointStruct(
                    id=chunk_id.int >> 64,
                    vector=vecs[idx],
                    payload={
                        "chunk_id": str(chunk_id),
                        "text": chunk,
                        "source": "site_document",
                        "filename": filename
                    }
                )
            )
        qdrant.upsert(collection_name=SITE_COLLECTION_NAME, points=points)
        total_added += len(points)
        
    return total_added
