import uuid
import fitz
import json
import os
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
        
    save_document_metadata(filename, total_added)
        
    return total_added
