from pathlib import Path
import time

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from app.db.qdrant import qdrant_client
from app.services.embedding_service import embedding_service


# =====================================================
# Configuration
# =====================================================

PDF_PATH = Path("data/support_doc.pdf")

COLLECTION_NAME = "customer_support_knowledge"

VECTOR_SIZE = 768

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

UPLOAD_BATCH_SIZE = 20

MAX_UPLOAD_RETRIES = 3


# =====================================================
# Upload Helper
# =====================================================

def upload_batch(points, batch_number):

    for attempt in range(1, MAX_UPLOAD_RETRIES + 1):

        try:

            qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=points,
            )

            print(
                f"✅ Batch {batch_number} uploaded successfully."
            )

            return

        except Exception as e:

            print(
                f"❌ Batch {batch_number} failed "
                f"(Attempt {attempt}/{MAX_UPLOAD_RETRIES})"
            )

            if attempt == MAX_UPLOAD_RETRIES:
                raise

            time.sleep(2)


# =====================================================
# Main Pipeline
# =====================================================

def main():

    start_time = time.time()

    if not PDF_PATH.exists():
        raise FileNotFoundError(
            f"PDF not found: {PDF_PATH}"
        )

    print("=" * 70)
    print("📄 Reading PDF...")
    print("=" * 70)

    # =====================================================
    # LANGCHAIN CHANGE #1
    # PDF Loading
    # =====================================================

    loader = PyPDFLoader(str(PDF_PATH))

    documents = loader.load()

    print(f"PDF Path      : {PDF_PATH.resolve()}")
    print(f"Pages Loaded  : {len(documents)}")

    print("\n===== FIRST PAGE PREVIEW =====")
    print(documents[0].page_content[:500])
    print("==============================\n")

    # =====================================================
    # LANGCHAIN CHANGE #2
    # Chunking
    # =====================================================

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
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

    print(f"Chunks Created : {len(chunks)}")

    # =====================================================
    # Embeddings
    # =====================================================

    print("\nGenerating embeddings...")

    embeddings = embedding_service.embed_documents(
        chunks
    )

    print(
        f"Embeddings Generated : {len(embeddings)}"
    )

    # =====================================================
    # Create Collection
    # =====================================================

    if qdrant_client.collection_exists(
        COLLECTION_NAME
    ):
        print("\nDeleting existing collection...")

        qdrant_client.delete_collection(
            COLLECTION_NAME
        )

    print("Creating new collection...")

    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE,
        ),
    )

    # =====================================================
    # Build Points
    # =====================================================

    print("\nPreparing vector points...")

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

    print(
        f"Prepared {len(points)} vector points."
    )

    # =====================================================
    # Batch Upload (NEW)
    # =====================================================

    print("\nUploading vectors to Qdrant...")

    total_points = len(points)

    total_batches = (
        total_points + UPLOAD_BATCH_SIZE - 1
    ) // UPLOAD_BATCH_SIZE

    for i in range(
        0,
        total_points,
        UPLOAD_BATCH_SIZE,
    ):

        batch = points[
            i:i + UPLOAD_BATCH_SIZE
        ]

        batch_number = (
            i // UPLOAD_BATCH_SIZE
        ) + 1

        upload_batch(
            batch,
            batch_number,
        )

        uploaded = min(
            i + UPLOAD_BATCH_SIZE,
            total_points,
        )

        print(
            f"Progress : "
            f"{uploaded}/{total_points} vectors "
            f"(Batch {batch_number}/{total_batches})"
        )

    # =====================================================
    # Summary
    # =====================================================

    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print("INGESTION SUMMARY")
    print("=" * 70)

    print(f"PDF              : {PDF_PATH.name}")
    print(f"Pages            : {len(documents)}")
    print(f"Chunks           : {len(chunks)}")
    print(f"Embeddings       : {len(embeddings)}")
    print(f"Vectors Uploaded : {len(points)}")
    print(f"Batch Size       : {UPLOAD_BATCH_SIZE}")
    print(f"Upload Batches   : {total_batches}")
    print(f"Total Time       : {elapsed:.2f} sec")

    print("=" * 70)

    print("\n✅ PDF ingestion completed successfully.")


if __name__ == "__main__":
    main()

    