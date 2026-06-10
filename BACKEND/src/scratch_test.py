import sys
from retriever import LegalRetriever

def main():
    query = "Aldatma (hile) durumunda karşı tarafın sözleşmeyi iptal etme hakkının kullanım süresi nedir?"
    print(f"Running retriever for query: {query}")
    
    # Initialize retriever in non-quantized/quantized mode as configured
    retriever = LegalRetriever(quantize=True)
    chunks = retriever.retrieve(query, k=7)
    
    print("\n--- RETRIEVED CHUNKS ---")
    for i, c in enumerate(chunks):
        print(f"[{i+1}] Source: {c.get('source')} | Law: {c.get('law')} | Article: {c.get('article_no')}")
        print(f"Text snippet: {c.get('text', '')[:200]}...")
        print("-" * 50)

if __name__ == "__main__":
    main()
