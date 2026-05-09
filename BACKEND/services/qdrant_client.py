import os

from qdrant_client import QdrantClient


DEFAULT_LOCAL_QDRANT_URL = "http://localhost:6333"


def get_qdrant_client() -> QdrantClient:
    """
    Öncelik sırası:
    1. QDRANT_URL varsa → Cloud (QDRANT_API_KEY ile birlikte)
    2. QDRANT_STORAGE varsa → Local path (Docker/local)
    3. Hiçbiri yoksa → localhost:6333
    """
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    if qdrant_url:
        return QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key or None,
            timeout=60,  # Cloud bağlantısı için uzun timeout (WriteTimeout önlenir)
        )

    local_storage = os.getenv("QDRANT_STORAGE")
    if local_storage:
        return QdrantClient(path=local_storage)

    return QdrantClient(url=os.getenv("QDRANT_LOCAL_URL", DEFAULT_LOCAL_QDRANT_URL))
