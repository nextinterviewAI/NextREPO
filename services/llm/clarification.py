from services.llm.utils import client, retry_with_backoff, safe_strip, get_fallback_clarification
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
import logging
from typing import Union

logger = logging.getLogger(__name__)

@retry_with_backoff
async def get_clarification(main_question: str, clarification_request: str) -> str:
    try:
        messages = [
            ChatCompletionSystemMessageParam(
                role="system",
                content="Provide business-level guidance without technical jargon."
            ),
            ChatCompletionUserMessageParam(
                role="user",
                content=f"Main question: {main_question}\nClarification request: {clarification_request}"
            )
        ]

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )

        content = safe_strip(getattr(response.choices[0].message, 'content', None))
        return content or get_fallback_clarification()

    except Exception as e:
        logger.error(f"Error generating clarification: {str(e)}")
        return get_fallback_clarification()