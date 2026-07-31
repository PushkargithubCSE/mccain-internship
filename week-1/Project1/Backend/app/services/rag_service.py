from app.services.retrieval_service import retrieval_service
from app.services.llm_service import llm_service


class RAGService:

    def ask(self, question: str) -> str:

        # 1. Retrieve relevant PDF chunks
        results = retrieval_service.search(
            question,
            limit=3,
        )

        # 2. Combine retrieved chunks
        context = "\n\n".join(
            result["text"]
            for result in results
        )

        # 3. Build prompt
        prompt = f"""
You are a customer support assistant.

Answer the user's question using ONLY the context provided below.

If the answer is not present in the context, say:
"I could not find this information in the knowledge base."

Context:
{context}

User question:
{question}

Answer:
"""

        # 4. Send context + question to LLM
        return llm_service.generate(prompt)


rag_service = RAGService()