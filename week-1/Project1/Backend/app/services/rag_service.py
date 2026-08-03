from app.services.retrieval_service import retrieval_service
from app.services.llm_service import llm_service
from langchain_core.prompts import PromptTemplate


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
        prompt_template = PromptTemplate.from_template(
            """
You are a friendly, approachable customer support assistant.

Your job is to answer the user's question using ONLY the information provided in the context.

RESPONSE STYLE:
- Write like a helpful human customer service representative.
- Be warm, conversational, and natural.
- Answer directly.
- Keep responses concise.
- Do not mention the context or knowledge base.

ACCURACY RULES:
- Use ONLY the provided context.
- Never hallucinate.
- If the answer isn't present, reply:
"I could not find this information in the knowledge base."

Context:
{context}

User Question:
{question}

Answer:
"""
        )

        prompt = prompt_template.format(
            context=context,
            question=question,
        )

        # 4. Send context + question to LLM
        return llm_service.generate(prompt)


rag_service = RAGService()