from services.llm.utils import MODEL_NAME, client, retry_with_backoff, safe_strip, get_fallback_optimized_code
from typing import Union, Optional
import logging

logger = logging.getLogger(__name__)

@retry_with_backoff
async def generate_optimized_code(
    question: str,
    user_code: str,
    sample_input: str,
    sample_output: str,
    rag_context: Optional[str] = None
) -> str:
    try:
        prompt = f"""
Question Context: {question}
Sample Input: {sample_input}
Expected Output: {sample_output}
User Code:
{user_code}
"""
        if rag_context:
            prompt += f"\nRelevant Context:\n{rag_context}\n"
        prompt += "\nImprove the code to work correctly and efficiently.\nOnly return the optimized code — no explanation needed.\n"

        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1000
        )

        content = safe_strip(getattr(response.choices[0].message, 'content', None))
        return content or get_fallback_optimized_code()

    except Exception as e:
        logger.error(f"Error optimizing code: {str(e)}")
        return get_fallback_optimized_code()