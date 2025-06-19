from services.llm.utils import MODEL_NAME, client, retry_with_backoff, safe_strip, parse_json_response, get_fallback_analysis
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class ApproachAnalysisService:
    def __init__(self):
        self.client = client
        logger.info("ApproachAnalysisService using shared OpenAI client")

    @retry_with_backoff
    async def analyze_approach(self, question: str, user_answer: str) -> Dict[str, Any]:
        try:
            prompt = f"""
Question: {question}
User's Answer: {user_answer}

Analyze the approach and return:
1. Detailed feedback
2. Key strengths
3. Areas for improvement
4. Score out of 10

Return ONLY JSON with:
{{
    "feedback": "...",
    "strengths": [...],
    "areas_for_improvement": [...],
    "score": score
}}
"""

            response = await self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )

            content = safe_strip(getattr(response.choices[0].message, 'content', None))
            return parse_json_response(content, get_fallback_analysis())

        except Exception as e:
            logger.error(f"Error analyzing approach: {str(e)}")
            return get_fallback_analysis()