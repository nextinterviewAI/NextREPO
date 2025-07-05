"""
Clarification Service

This module provides AI-powered clarification responses during coding interviews.
Helps candidates understand problems better without giving away solutions.
"""

from services.llm.utils import client, retry_with_backoff, safe_strip, get_fallback_clarification
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
import logging
from typing import Union

logger = logging.getLogger(__name__)

@retry_with_backoff
async def get_clarification(main_question: str, clarification_request: str) -> str:
    """
    Generate clarification response for coding interview questions.
    Provides helpful guidance without revealing the solution.
    """
    try:
        # Build messages for clarification generation
        messages = [
            ChatCompletionSystemMessageParam(
                role="system",
                content="You are a senior technical interviewer providing clarification. Maintain a professional, conversational tone. Provide clear, focused guidance that helps the candidate understand the problem better without giving away the solution. Be encouraging but maintain the interview atmosphere."
            ),
            ChatCompletionUserMessageParam(
                role="user",
                content=f"Main question: {main_question}\nClarification request: {clarification_request}"
            )
        ]

        # Generate clarification using AI
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