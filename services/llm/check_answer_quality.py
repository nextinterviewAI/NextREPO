from services.llm.utils import MODEL_NAME, client, retry_with_backoff, safe_strip
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

@retry_with_backoff
async def check_answer_quality(questions: List[Dict[str, Any]], topic: str) -> str:
    try:
        answers_text = "\n".join([
            f"Q{i+1}: {q['question']}\nA{i+1}: {q['answer']}"
            for i, q in enumerate(questions)
        ])

        prompt = f"""
Review these answers to {topic} interview questions.
Respond with only 'good' or 'bad'.

Answers:
{answers_text}

Quality:"""

        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10
        )

        content = safe_strip(getattr(response.choices[0].message, 'content', None))
        return "good" if content and "good" in content.lower() else "bad"

    except Exception as e:
        logger.error(f"Error checking answer quality: {str(e)}")
        return "bad"

@retry_with_backoff
async def check_single_answer_quality(question: str, answer: str, topic: str, rag_context: Optional[str] = None) -> str:
    try:
        prompt = f"""
Review the following answer to the {topic} interview question.
Evaluate based on:
- Clarity of communication and reasoning
- Correctness of logic and approach
- Ability to reason under pressure
- Awareness of trade-offs and edge cases
- Domain-specific technical knowledge

Respond with only 'good' if the answer demonstrates clear reasoning, relevant technical knowledge, and addresses the question appropriately, or 'bad' if it is gibberish, empty, irrelevant, or lacks coherent reasoning.

Question: {question}
Answer: {answer}
"""
        if rag_context:
            prompt += f"\nReference Context:\n{rag_context}\n"
        prompt += "\nQuality:"
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10
        )
        content = safe_strip(getattr(response.choices[0].message, 'content', None))
        return "good" if content and "good" in content.lower() else "bad"
    except Exception as e:
        logger.error(f"Error checking single answer quality: {str(e)}")
        return "bad"