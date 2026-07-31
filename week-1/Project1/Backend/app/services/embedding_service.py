from google import genai
from google.genai import types

from app.core.config import settings


class EmbeddingService:

    MODEL = "gemini-embedding-2"
    DIMENSIONS = 768

    def __init__(self):
        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

    def embed_text(
        self,
        text: str,
        task_type: str = "RETRIEVAL_QUERY",
    ) -> list[float]:

        response = self.client.models.embed_content(
            model=self.MODEL,
            contents=text,
            config=types.EmbedContentConfig(    
                task_type=task_type,
                output_dimensionality=self.DIMENSIONS,
            ),
        )

        return response.embeddings[0].values

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = []

        for text in texts:
            response = self.client.models.embed_content(
                model=self.MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=self.DIMENSIONS,
                ),
            )

            embeddings.append(
                response.embeddings[0].values
            )

        return embeddings

embedding_service = EmbeddingService()