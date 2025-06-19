from services.llm.utils import MODEL_NAME, client, retry_with_backoff, safe_strip
from typing import List, Dict, Any
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