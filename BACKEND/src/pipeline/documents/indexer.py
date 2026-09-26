"""
src/pipeline/documents/indexer.py - Sirket belgelerini company_corpus Qdrant collection-ina indexler
"""

import uuid
import logging
from typing import List

from qdrant_client.http import models as qmodels

log = logging.getLogger("LawAgent.DocumentIndexer")

VECTOR_SIZE_DEFAULT = 768  # Mursit-Base-TR-Retrieval cikis boyutu


def _doc_point_id(document_id: str, chunk_idx: int) -> int:
    """document_id + chunk indexi ile tekrar-uretileBilir uint64 ID olustur."""
    raw = f"{document_id}::chunk::{chunk_idx}"
    return uuid.uuid5(uuid.NAMESPACE_DNS, raw).int >> 64


def ensure_company_collection(qdrant_client, collection_name: str, vector_size: int = VECTOR_SIZE_DEFAULT) -> None:
    """Company corpus collection yoksa olustur."""
    try:
        qdrant_client.get_collection(collection_name)
        log.info(f"[Indexer] Collection '{collection_name}' mevcut.")
    except Exception:
        log.info(f"[Indexer] Collection '{collection_name}' olusturuluyor...")
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(
                size=vector_size,
                distance=qmodels.Distance.COSINE,
            ),
        )
        # document_id uzerinden filtreleme icin payload index
        qdrant_client.create_payload_index(
            collection_name=collection_name,
            field_name="document_id",
            field_schema=qmodels.PayloadSchemaType.KEYWORD,
        )
        log.info(f"[Indexer] Collection '{collection_name}' olusturuldu.")


def delete_document_vectors(document_id: str, qdrant_client, collection_name: str) -> int:
    """
    document_id payload filtresiyle collection'daki tum vektorleri sil.
    Overwrite ve silme islemleri icin kullanilir.
    Silinen nokta sayisini dondurur.
    """
    try:
        result = qdrant_client.delete(
            collection_name=collection_name,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )
        log.info(f"[Indexer] document_id='{document_id}' icin vektorler silindi.")
        return 1  # Qdrant delete sonucu status=completed
    except Exception as e:
        log.warning(f"[Indexer] Vektor silme hatasi (document_id={document_id}): {e}")
        return 0


def index_document(
    document_id: str,
    chunks: List[str],
    embedder,
    qdrant_client,
    collection_name: str,
    batch_size: int = 32,
) -> int:
    """
    Chunk listesini Mursit ile vektorlestirip company_corpus'a yazar.
    Dondurulen deger: indexlenen chunk sayisi.
    """
    if not chunks:
        log.warning(f"[Indexer] document_id='{document_id}': chunk listesi bos, indexleme atlandi.")
        return 0

    # Collection yoksa olustur
    ensure_company_collection(qdrant_client, collection_name, vector_size=embedder.vector_size)

    total_indexed = 0
    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start: batch_start + batch_size]
        # passage: prefix ile encode (Mursit asimetrik arama modeli)
        texts_with_prefix = [f"passage: {c}" for c in batch]
        vectors = embedder.encode(texts_with_prefix)

        points = []
        for i, (chunk_text, vector) in enumerate(zip(batch, vectors)):
            chunk_idx = batch_start + i
            point_id = _doc_point_id(document_id, chunk_idx)
            points.append(
                qmodels.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "document_id": document_id,
                        "chunk_idx": chunk_idx,
                        "text": chunk_text,
                        "source": "company_document",
                    },
                )
            )

        qdrant_client.upsert(collection_name=collection_name, points=points)
        total_indexed += len(points)
        log.info(f"[Indexer] Batch {batch_start//batch_size + 1}: {len(points)} nokta yazildi.")

    log.info(f"[Indexer] document_id='{document_id}': toplam {total_indexed} chunk indexlendi.")
    return total_indexed


def index_single_chunk(
    document_id: str,
    chunk_idx: int,
    chunk_text: str,
    embedder,
    qdrant_client,
    collection_name: str,
    point_id: str = None,
) -> str:
    """
    Tek bir chunk'i embed edip Qdrant'a upsert eder.
    point_id: Qdrant UUID string. None ise uuid.uuid4() ile uretilir.
    Upsert edilen point_id stringi dondurur.
    """
    import uuid as _uuid
    pid = point_id or str(_uuid.uuid4())
    # Qdrant UUID formatina donustur (UUID4)
    pid_uuid = _uuid.UUID(pid) if isinstance(pid, str) else pid
    vector = embedder.encode([f"passage: {chunk_text}"])[0]
    qdrant_client.upsert(
        collection_name=collection_name,
        points=[
            qmodels.PointStruct(
                id=str(pid_uuid),
                vector=vector,
                payload={
                    "document_id": document_id,
                    "chunk_idx": chunk_idx,
                    "text": chunk_text,
                    "source": "company_document",
                },
            )
        ],
    )
    log.info(
        f"[Indexer] Single chunk upsert: document_id={document_id}, "
        f"chunk_idx={chunk_idx}, point_id={str(pid_uuid)}, chars={len(chunk_text)}"
    )
    return str(pid_uuid)


def delete_point(point_id: str, qdrant_client, collection_name: str) -> None:
    """Tek bir Qdrant point'i point_id ile siler."""
    import uuid as _uuid
    pid_uuid = _uuid.UUID(point_id)
    try:
        qdrant_client.delete(
            collection_name=collection_name,
            points_selector=qmodels.PointIdsList(points=[str(pid_uuid)]),
        )
        log.info(f"[Indexer] Point silindi: {str(pid_uuid)}")
    except Exception as e:
        log.warning(f"[Indexer] Point silinemedi ({str(pid_uuid)}): {e}")

