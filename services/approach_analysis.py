from services.llm.utils import MODEL_NAME, client, retry_with_backoff, safe_strip, parse_json_response, get_fallback_analysis
from typing import Dict, Any
import logging
from services.rag.retriever_factory import get_rag_retriever
import asyncio

logger = logging.getLogger(__name__)

class ApproachAnalysisService:
    def __init__(self):
        self.client = client
        logger.info("ApproachAnalysisService using shared OpenAI client")

    async def _get_context(self, question: str, top_k: int = 2) -> str:
        """Retrieve and format relevant context from RAG system"""
        try:
            retriever = await get_rag_retriever()
            if retriever is None:
                logger.warning("RAGRetriever not initialized")
                return ""
            context_chunks = await retriever.retrieve_context(question, top_k=top_k)
            return "\n\n".join(context_chunks)
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return ""

    @retry_with_backoff
    async def analyze_approach(self, question: str, user_answer: str) -> Dict[str, Any]:
        try:
            # Get relevant context from RAG
            context = await self._get_context(question)

            # Build final prompt with or without context
            prompt = f"""
Question: {question}
User's Answer: {user_answer}

Analyze the approach and provide feedback based on the following guidelines:
1. Use any provided context to validate the answer
2. Highlight strengths in reasoning and structure
3. Identify gaps or misunderstandings
4. Score out of 10 based on accuracy and completeness

Return ONLY JSON with:
{{
    "feedback": "...",
    "strengths": [...],
    "areas_for_improvement": [...],
    "score": score
}}

Context:
{context}
"""

            response = await self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )

            content = safe_strip(getattr(response.choices[0].message, 'content', None))
            result = parse_json_response(content, get_fallback_analysis())

            # Log success
            logger.info(f"Successfully analyzed approach for question: {question[:50]}...")
            return result

        except Exception as e:
            logger.error(f"Error analyzing approach: {str(e)}")
            return get_fallback_analysis()