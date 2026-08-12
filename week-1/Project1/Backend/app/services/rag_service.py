import time
from collections.abc import AsyncIterator

from langchain_core.prompts import PromptTemplate

from app.services.retrieval_service import retrieval_service
from app.services.llm_service import llm_service


class RAGService:

    async def astream(
        self,
        question: str,
    ) -> AsyncIterator[str]:

        # =====================================================
        # TOTAL REQUEST TIMER
        # =====================================================

        total_start = time.perf_counter()

        # =====================================================
        # 0. QUERY REWRITING
        # =====================================================

        rewrite_start = time.perf_counter()

        search_query = llm_service.rewrite_query(
            question
        )

        rewrite_time = (
            time.perf_counter()
            - rewrite_start
        )

        print(
            f"[RAG] Query rewrite time: "
            f"{rewrite_time:.3f}s"
        )

        print(
            f"[RAG] Original query: "
            f"{question}"
        )

        print(
            f"[RAG] Search query: "
            f"{search_query}"
        )

        # =====================================================
        # 1. RETRIEVAL
        # =====================================================

        retrieval_start = time.perf_counter()

        results = retrieval_service.search(
            search_query,
            limit=3,
        )

        retrieval_time = (
            time.perf_counter()
            - retrieval_start
        )

        print(
            f"[RAG] Retrieval time: "
            f"{retrieval_time:.3f}s"
        )

        # =====================================================
        # 2. COMBINE RETRIEVED CONTEXT
        # =====================================================

        context_start = time.perf_counter()

        context = "\n\n".join(
            result["text"]
            for result in results
        )

        context_time = (
            time.perf_counter()
            - context_start
        )

        print(
            f"[RAG] Context preparation: "
            f"{context_time:.3f}s"
        )

        print(
            f"[RAG] Retrieved chunks: "
            f"{len(results)}"
        )

        # =====================================================
        # 3. BUILD ANSWER PROMPT
        # =====================================================

        prompt_start = time.perf_counter()

        prompt_template = PromptTemplate.from_template(
            """
Role and Persona
You are the McCain Foods Compliance Success Manager, an innovative, AI-driven mentor designed to help our team understand and navigate the McCain Code of Conduct. Your tone is "friendly formal"—you are approachable, supportive, and conversational, much like a trusted manager guiding an employee over a coffee chat, yet you maintain the professionalism and authority required of corporate compliance. You blend a casual, modern office communication style with strict adherence to company policy.

Primary Objective
Your task is to answer employee inquiries, clarify policies, and resolve ethical dilemmas using only the provided Retrieval-Augmented Generation (RAG) context extracted from the "McCain Foods Code of Conduct" document. You must ensure that every team member feels heard and respected while receiving accurate, policy-backed guidance.

Core Directives & Behavioral Guidelines

The "Friendly Formal" Manager Tone:

Empathy First: Acknowledge the user's situation positively and helpfully.

Professionalism: Maintain a respectful, office-appropriate demeanor.

Collaborative Language: Use pronouns like "we", "our team", and "our company" where appropriate.

Innovative & Digestible Communication:

Do not simply copy and paste large blocks of text.

Synthesize the information into clear and readable formats.

Use bullet points to break down complex procedures.

Use bold text to highlight important concepts.

Where helpful, explain rules in the context of an employee's day-to-day work.

Action-Oriented Escalation:

For sensitive issues such as harassment, fraud, or suspected legal violations, provide the policy answer from the context and encourage the employee to escalate using the appropriate channels mentioned in the context.

Handling Edge Cases & Ambiguity:

If the user's scenario borders on a policy violation, explain the relevant principle from the context and advise the safest course of action supported by the context.

Accuracy Rules:

- Use ONLY information contained in the provided context.
- Do not guess or invent policy information.
- Do not use general knowledge.
- If the answer is not present in the context, say:
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

        prompt_time = (
            time.perf_counter()
            - prompt_start
        )

        print(
            f"[RAG] Prompt preparation: "
            f"{prompt_time:.3f}s"
        )

        # =====================================================
        # 4. LLM STREAMING
        # =====================================================

        llm_start = time.perf_counter()

        first_token = True

        async for chunk in llm_service.astream(
            prompt
        ):

            # -------------------------------------------------
            # FIRST TOKEN / TTFT
            # -------------------------------------------------

            if first_token:

                first_token = False

                llm_ttft = (
                    time.perf_counter()
                    - llm_start
                )

                total_ttft = (
                    time.perf_counter()
                    - total_start
                )

                print(
                    f"[RAG] LLM TTFT: "
                    f"{llm_ttft:.3f}s"
                )

                print(
                    f"[RAG] TOTAL TTFT: "
                    f"{total_ttft:.3f}s"
                )

                print(
                    "[RAG] First token received."
                )

            yield chunk

        # =====================================================
        # 5. TOTAL GENERATION TIME
        # =====================================================

        total_time = (
            time.perf_counter()
            - total_start
        )

        print(
            f"[RAG] Total request time: "
            f"{total_time:.3f}s"
        )


rag_service = RAGService()