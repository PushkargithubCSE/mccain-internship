from app.services.retrieval_service import retrieval_service


question = input("Ask a question about the PDF: ")

results = retrieval_service.search(
    question,
    limit=3,
)

print("\nTop relevant chunks:\n")

for index, result in enumerate(results, start=1):

    print(f"RESULT {index}")
    print(f"Score: {result['score']}")
    print(f"Chunk: {result['chunk_index']}")
    print(result["text"])
    print("-" * 70)