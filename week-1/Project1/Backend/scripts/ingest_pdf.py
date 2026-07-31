from pathlib import Path

from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from app.db.qdrant import qdrant_client
from app.services.embedding_service import embedding_service
from app.services.pdf_service import pdf_service


PDF_PATH = Path("data/knowledge_base.pdf")

COLLECTION_NAME = "customer_support_knowledge"

VECTOR_SIZE = 768


def main():

    if not PDF_PATH.exists():
        raise FileNotFoundError(
            f"PDF not found: {PDF_PATH}"
        )

    # 1. Extract PDF text
    print("Reading PDF...")

    text = pdf_service.extract_text(PDF_PATH)

    if not text.strip():
        raise ValueError(
            "No text could be extracted from PDF."
        )

    # 2. Create chunks
    chunks = pdf_service.chunk_text(text)

    print(f"Chunks created: {len(chunks)}")

    # 3. Generate embeddings
    print("Generating embeddings...")

    embeddings = embedding_service.embed_documents(
        chunks
    )

    print(f"Embeddings generated: {len(embeddings)}")

    # 4. Recreate collection
    if qdrant_client.collection_exists(
        COLLECTION_NAME
    ):
        qdrant_client.delete_collection(
            COLLECTION_NAME
        )

    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE,
        ),
    )

    # 5. Build Qdrant points
    points = []

    for index, (chunk, embedding) in enumerate(
        zip(chunks, embeddings)
    ):
        points.append(
            PointStruct(
                id=index,
                vector=embedding,
                payload={
                    "text": chunk,
                    "source": PDF_PATH.name,
                    "chunk_index": index,
                },
            )
        )

    # 6. Store vectors
    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )

    print(
        f"Successfully stored {len(points)} chunks in Qdrant."
    )


if __name__ == "__main__":
    main()