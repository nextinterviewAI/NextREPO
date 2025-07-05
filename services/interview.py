"""
Interview Service

This module handles interview question generation and conversation management.
Provides AI-powered follow-up questions based on candidate responses.
"""

from services.llm.utils import client, retry_with_backoff, safe_strip, get_fallback_interview_question
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam
)
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Senior Technical Interviewer with over 15 years of experience conducting technical interviews for data-focused roles. You are simulating a real-world interview environment to help candidates prepare for roles such as Data Analyst, Data Scientist, Data Engineer, and ML Engineer.

Your role is to evaluate the candidate's problem-solving ability, reasoning clarity, and technical communication, while offering only minimal, realistic interviewer-level prompts. Avoid guiding the candidate or offering technical tips.

Guidelines:
1. Never provide solutions or technical hints
2. Ask follow-up questions that probe deeper into the candidate's approach
3. Challenge assumptions and ask for justification
4. Evaluate based on clarity of communication, correctness of logic, ability to reason under pressure, and awareness of trade-offs
5. After 4 good answers, transition to coding phase
6. Maintain a conversational and professional tone throughout
7. Use natural affirmations like "Sounds good", "Alright, go ahead", "Interesting direction", "Thanks for clarifying that"

Domain-Specific Evaluation:
- Python Data Analysis: Evaluate Pandas/Numpy pipelines, data transformations, handling of missing/outlier data
- Data Structures & Algorithms: Evaluate data structure selection, time-space complexity, edge case handling
- SQL: Evaluate correctness of joins, filters, groupings, subqueries, window functions, and edge cases

Problem-Solving Framework:
If candidate struggles:
- "What led you to that choice?"
- "What assumption are you making here?"
- "Could there be an edge case that challenges this approach?"
- "Would this logic hold for all types of inputs?"

If candidate performs well:
- "Sounds like you've structured this well. Continue with your reasoning."
- "How does your solution scale with larger datasets?"

Depth-Probing Follow-ups:
- "Why this method over another?"
- "How would you optimize this?"
- "How would your solution behave if duplicate values were involved?"
- "Does your approach rely on any hidden assumptions?"
"""

@retry_with_backoff
async def get_next_question(
    questions: List[Dict[str, Any]],
    is_base_question: bool = False,
    topic: str = "",
    rag_context: Optional[str] = None
) -> str:
    """
    Generate next interview question based on conversation history.
    Uses AI to create contextually relevant follow-up questions.
    """
    try:
        # Return standard first question for base questions
        if is_base_question:
            return "Can you walk me through your thought process on how you would approach this problem?"

        # Build conversation with system prompt and context
        messages: List[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=SYSTEM_PROMPT)
        ]

        # Add RAG context if available
        if rag_context:
            messages.append(ChatCompletionUserMessageParam(
                role="user",
                content=f"Reference Context for this topic/question:\n{rag_context}"
            ))
        
        # Add conversation history
        for q in questions:
            messages.append(q)

        # Add instruction for follow-up question generation
        messages.append(ChatCompletionUserMessageParam(
            role="user",
            content="""Based on the candidate's response, ask a follow-up question that:
1. Probes deeper into their understanding
2. Asks about specific aspects of their solution
3. Tests their technical knowledge
4. Is relevant to their previous answer"""
        ))

        # Generate next question using AI
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )

        content = safe_strip(getattr(response.choices[0].message, 'content', None))
        return content or get_fallback_interview_question()

    except Exception as e:
        logger.error(f"Error generating next question: {str(e)}", exc_info=True)
        return get_fallback_interview_question() 