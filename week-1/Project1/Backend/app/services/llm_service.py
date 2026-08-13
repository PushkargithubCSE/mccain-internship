from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings


class LLMService:

    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-3.1-flash-lite",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.3,
        )

        self.output_parser = StrOutputParser()

    def generate(self, prompt: str) -> str:
        chain = self.llm | self.output_parser

        return chain.invoke(prompt)

    async def astream(self, prompt: str):
        chain = self.llm | self.output_parser

        async for chunk in chain.astream(prompt):
            yield chunk

    async def rewrite_query(
        self,
        question: str,
        history: list[dict] | None = None,
    ) -> str:

        history = history or []

        history_text = "\n".join(
            f"{message['role']}: {message['content']}"
            for message in history
        )

        prompt = f"""
You are a search-query optimizer for the McCain Foods
Code of Conduct knowledge base.

Your job is to transform the user's current question
into a clear, specific, self-contained search query
that will retrieve the most relevant policy information.

Conversation history:
{history_text}

Current user question:
{question}

Rules:

1. Preserve the user's original intent.
2. Use conversation history only to resolve references
   such as "it", "that", "this", "one", "they", or "then".
3. Make the rewritten query self-contained.
4. Do not answer the question.
5. Do not invent facts.
6. Do not add policy information that cannot be
   inferred from the conversation.
7. Remove conversational filler.
8. Return ONLY the rewritten search query.
9. If the current question is already clear and
   self-contained, return it unchanged.

Examples:

Conversation:
User: What does the Code say about gifts?
Assistant: The Code provides guidance about gifts...

Current question:
Can I accept one from a supplier?

Rewrite:
McCain Foods policy on accepting gifts from suppliers

Conversation:
User: What does the Code say about conflicts of interest?
Assistant: The Code provides guidance on conflicts...

Current question:
What about financial interests?

Rewrite:
McCain Foods Code of Conduct policy on financial conflicts of interest

Conversation:
User: What happens if I report something?
Assistant: The Code explains reporting ethical concerns...

Current question:
Can it be anonymous?

Rewrite:
McCain Foods Code of Conduct policy on anonymous reporting of ethical concerns

Current question:
{question}

Rewritten search query:
"""

        chain = self.llm | self.output_parser

        rewritten = await chain.ainvoke(prompt)

        return rewritten.strip() or question


llm_service = LLMService()