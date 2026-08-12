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

    def rewrite_query(self, question: str) -> str:

        prompt = f"""
You are a search-query optimizer for the McCain Foods
Code of Conduct knowledge base document
.
Your job is to transform a user's question into a
clear, specific search query that will retrieve the
most relevant policy information.

Rules:

1. Preserve the user's original intent.
2. Do not answer the question.
3. Do not invent facts.
4. Do not add policy information that is not present
   in the user's question.
5. Expand vague references when possible.
6. Remove conversational filler.
7. Return ONLY the rewritten search query.
8. If the question is already clear and specific,
   return it unchanged.

Examples:

User:
"What about gifts?"

Rewrite:
"McCain Foods policy regarding gifts"

User:
"Can I accept one from a supplier?"

Rewrite:
"McCain Foods policy on accepting gifts from suppliers"

User:
"What happens if I report something?"

Rewrite:
"McCain Foods Code of Conduct process for reporting
ethical concerns"

User:
"What is the policy on conflicts of interest?"

Rewrite:
"What is McCain Foods policy on conflicts of interest?"

User question:
{question}

Rewritten search query:
"""
        chain = self.llm | self.output_parser
        rewritten = chain.invoke(prompt)
        return rewritten.strip()


llm_service = LLMService()