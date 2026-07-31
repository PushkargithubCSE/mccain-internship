from app.db.qdrant import qdrant_client
from app.services.embedding_service import embedding_service


COLLECTION_NAME = "customer_support_knowledge"


class RetrievalService:

    def search(
        self,
        query: str,
        limit: int = 3,
    ) -> list[dict]:

        # Convert user's question into an embedding
        query_vector = embedding_service.embed_text(
            query,
            task_type="RETRIEVAL_QUERY",
        )

        # Search Qdrant for similar PDF chunks
        response = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=limit,
            with_payload=True,
        )

        results = []

        for point in response.points:
            results.append(
                {
                    "text": point.payload["text"],
                    "score": point.score,
                    "chunk_index": point.payload["chunk_index"],
                }
            )

        return results


retrieval_service = RetrievalService()