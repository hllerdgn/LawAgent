"""
update_qdrant_enriched.py — LawAgent Akıllı Qdrant Güncelleyici

Görev:
1. chunk_corpus_enriched.json dosyasını yükler.
2. Qdrant'taki mevcut noktaların (points) payload metinlerini (text) yeni zenginleştirilmiş metinlerle günceller (Model yüklemeden, sıfır bellek kullanımı!).
3. Sadece kritik / LLM ile zenginleştirilmiş (~39) maddeler için Mürşit modelini yükleyip yeni vektörlerini hesaplar ve upsert eder.
"""

import json
import re
import os
import sys
import time
import uuid
import logging
from typing import Dict, List, Set

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_SRC_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(_BACKEND_DIR, ".env"))

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from services.qdrant_client import get_qdrant_client
from src.embedder import MursitEmbedder, COLLECTION_NAME, _chunk_id_to_uint64, qdrant_retry
from src.contextual_enricher import CRITICAL_ARTICLES, get_law_full_name

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("LawAgent.QdrantUpdater")

def main():
    enriched_path = os.path.join(_SRC_DIR, "data", "chunk_corpus_enriched.json")
    if not os.path.exists(enriched_path):
        log.error(f"Enriched corpus not found at {enriched_path}. Run contextual_enricher.py first.")
        return

    with open(enriched_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    client = get_qdrant_client()

    # Kritik kanun-madde kümesini hazırlayalım
    critical_keys = { (law, art_no) for law, art_no in CRITICAL_ARTICLES.keys() }

    to_payload_update = []
    to_vector_update = []

    for c in chunks:
        if c.get("source") != "mevzuat":
            continue
        
        law = str(c.get("law", ""))
        art_raw = c.get("article_no", "")
        art = re.search(r'\d+', str(art_raw))
        art_no = art.group() if art else ''
        key = (law, art_no)

        if key in critical_keys:
            to_vector_update.append(c)
        else:
            to_payload_update.append(c)

    log.info(f"Payload only updates: {len(to_payload_update)}")
    log.info(f"Vector + Payload updates: {len(to_vector_update)}")

    # 1. Aşama: Payload Güncellemeleri (Toplu/Batch halinde yapalım)
    log.info("Updating payloads in Qdrant...")
    batch_size = 100
    for i in range(0, len(to_payload_update), batch_size):
        batch = to_payload_update[i : i + batch_size]
        
        # Qdrant payload güncellemeleri için set_payload veya overwrite_payload kullanabiliriz.
        # overwrite_payload tüm payload'u değiştireceği için en güvenlisidir.
        for c in batch:
            point_id = _chunk_id_to_uint64(c["chunk_id"])
            payload = {
                "chunk_id": c.get("chunk_id", ""),
                "text": c.get("text", ""),
                "law": c.get("law", ""),
                "article_no": c.get("article_no", ""),
                "source": c.get("source", ""),
                "decision_id": c.get("decision_id", ""),
                "token_len": c.get("token_len", 0),
                "atiflar": c.get("atiflar", [])
            }
            try:
                qdrant_retry(
                    client.set_payload,
                    collection_name=COLLECTION_NAME,
                    payload=payload,
                    points=[point_id]
                )
            except Exception as e:
                log.warning(f"Failed to update payload for {c.get('chunk_id')}: {e}")
        
        if (i // batch_size) % 5 == 0:
            log.info(f"Progress: {i}/{len(to_payload_update)} updated.")

    log.info("Payload updates finished successfully.")

    # 2. Aşama: Kritik Maddelerin Yeniden Vektörleştirilmesi & Yüklenmesi
    if to_vector_update:
        log.info("Loading Mursit model for critical chunks vectorization...")
        try:
            # Bellek kazanmak için quantize=True ile yükleyelim
            embedder = MursitEmbedder(quantize=True)
            
            log.info("Encoding critical chunks...")
            enriched_texts = []
            for c in to_vector_update:
                enriched_texts.append(f"{c.get('law', '')} Madde {c.get('article_no', '')}: {c.get('text', '')}")
            
            vecs = embedder.encode(enriched_texts, batch_size=16)

            log.info("Upserting critical chunks with new vectors into Qdrant...")
            points = [
                qmodels.PointStruct(
                    id=_chunk_id_to_uint64(c["chunk_id"]),
                    vector=vecs[idx],
                    payload={
                        "chunk_id": c.get("chunk_id", ""),
                        "text": c.get("text", ""),
                        "law": c.get("law", ""),
                        "article_no": c.get("article_no", ""),
                        "source": c.get("source", ""),
                        "decision_id": c.get("decision_id", ""),
                        "token_len": c.get("token_len", 0),
                        "atiflar": c.get("atiflar", [])
                    },
                )
                for idx, c in enumerate(to_vector_update)
            ]
            qdrant_retry(client.upsert, collection_name=COLLECTION_NAME, points=points)
            log.info(f"Successfully re-embedded and updated {len(to_vector_update)} critical points.")
        except Exception as e:
            log.error(f"Error during critical vector update: {e}")
            raise e

    log.info("All Qdrant updates completed successfully!")

if __name__ == "__main__":
    main()
