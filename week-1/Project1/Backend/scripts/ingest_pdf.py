from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from app.db.qdrant import qdrant_client
from app.services.embedding_service import embedding_service


PDF_PATH = Path("data/knowledge_base.pdf")

COLLECTION_NAME = "customer_support_knowledge"

VECTOR_SIZE = 768


def main():

    if not PDF_PATH.exists():
        raise FileNotFoundError(
            f"PDF not found: {PDF_PATH}"
        )

    # =====================================================
    # LANGCHAIN CHANGE #1
    # Instead of pdf_service.extract_text(),
    # use LangChain's PyPDFLoader.
    # =====================================================

    print("Reading PDF...")

    loader = PyPDFLoader(str(PDF_PATH))

    documents = loader.load()

    # =====================================================
    # LANGCHAIN CHANGE #2
    # Instead of pdf_service.chunk_text(),
    # use RecursiveCharacterTextSplitter.
    # =====================================================

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
            "",
        ],
    )

    split_documents = splitter.split_documents(
        documents
    )

    chunks = [
        document.page_content
        for document in split_documents
    ]

    print(f"Chunks created: {len(chunks)}")

    # =====================================================
    # Existing code (UNCHANGED)
    # Your own embedding service is still used.
    # =====================================================

    print("Generating embeddings...")

    embeddings = embedding_service.embed_documents(
        chunks
    )

    print(f"Embeddings generated: {len(embeddings)}")

    # =====================================================
    # Existing Qdrant logic (UNCHANGED)
    # =====================================================

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

    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )

    print(
        f"Successfully stored {len(points)} chunks in Qdrant."
    )


if __name__ == "__main__":
    main()