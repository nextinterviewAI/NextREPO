from services.llm.utils import (
    MODEL_NAME, client, retry_with_backoff, safe_strip, parse_json_response, get_fallback_feedback
)
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

@retry_with_backoff
async def get_feedback(conversation: List[Dict[str, Any]], user_name: str) -> dict:
    try:
        formatted = "\n".join([
            f"Interviewer: {turn.get('question', '')}\nCandidate: {turn.get('answer', '')}"
            for turn in conversation
        ])

        prompt = f"""
Based on the following interview conversation with {user_name}, provide comprehensive feedback in JSON format.

Include:
- Summary (2-3 lines)
- Positive Points (3 specific strengths)
- Points to Address (3 unclear parts)
- Areas for Improvement (3 broader areas)

Conversation:
{formatted}

Return only valid JSON with structure:
{{
    "summary": "...",
    "positive_points": [...],
    "points_to_address": [...],
    "areas_for_improvement": [...]
}}
"""

        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": f"You are an expert interviewer providing detailed feedback for {user_name}"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )

        content = safe_strip(getattr(response.choices[0].message, 'content', None))
        return parse_json_response(content, get_fallback_feedback(user_name))

    except Exception as e:
        logger.error(f"Error getting feedback: {str(e)}")
        return get_fallback_feedback(user_name)