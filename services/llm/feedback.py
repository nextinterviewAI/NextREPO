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
Based on the following interview conversation with {user_name}, provide comprehensive and STRICT feedback in JSON format.

Be honest and critical. If any answers are missing, incomplete, or appear to be gibberish, explicitly call this out in the summary, points to address, and areas for improvement. Do NOT give positive feedback for unclear, irrelevant, or missing answers. Penalize low-quality or insufficient responses. Only praise clear, correct, and complete answers.

Include:
- Summary (2-3 lines, must mention if any answers were missing, unclear, or gibberish)
- Positive Points (up to 3 specific strengths, only if present)
- Points to Address (at least 3 unclear, missing, or weak parts)
- Areas for Improvement (at least 3 broader areas, especially if answers were incomplete or low quality)

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