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

llm_service = LLMService()