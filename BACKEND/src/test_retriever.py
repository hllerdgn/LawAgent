from embedder import MursitEmbedder, _chunk_id_to_uint64, COLLECTION_NAME
from services.qdrant_client import get_qdrant_client


def legal_search(query_text: str, top_k: int = 20):
    # 1. Embedder'ı yükle
    embedder = MursitEmbedder(quantize=False)
    client = get_qdrant_client()

    # 2. Sorguyu vektörize et
    query_vector = embedder.encode_single(query_text)

    # 3. Qdrant'ta ara (Yeni API formatı)
    try:
        # En güncel Qdrant API kullanımı
        response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,  # query_batch yerine doğrudan query
            limit=top_k,
            with_payload=True,
        )
        results = response.points
    except Exception as e:
        # Eğer yukarıdaki de başarısız olursa (versiyon çok eskiyse)
        print(f"[Sistem] Yeni API hatası ({e}), fallback deneniyor...")
        # Alternatif: LocalClient'larda bazen 'search' doğrudan çalışır
        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
        )

    # 4. Sonuçları Raporla
    print(f"\n🔍 Sorgu: '{query_text}'")
    print("=" * 60)

    for i, res in enumerate(results):
        p = res.payload
        score = getattr(res, "score", 0)  # query_points'te skor her zaman mevcuttur

        print(
            f"[{i+1}] Skor: {score:.4f} | Kaynak: {p.get('source', 'Bilinmiyor').upper()}"
        )

        if p.get("source") == "mevzuat":
            print(f"📍 {p.get('law')} Madde {p.get('article_no')}")
        else:
            print(f"🏛️ Yargıtay Kararı ID: {p.get('decision_id')}")

        text_snippet = p.get("text", "").replace("\n", " ")[:150]
        print(f"📝 Metin: {text_snippet}...")
        print("-" * 40)


if __name__ == "__main__":
    # Test Sorgusu
    # Örn: "Temerrüt ihtar şartı" veya "Kırkambar sözleşmesi sorumluluk"
    user_query = input("Hukuki sorunuzu girin: ")
    legal_search(user_query)
