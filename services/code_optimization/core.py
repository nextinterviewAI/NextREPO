"""
Core Code Optimization Module

Contains the main optimization function and LLM integration logic.
"""

import logging
import json
from typing import Optional

from services.llm.utils import client, retry_with_backoff, safe_strip, MODEL_NAME
from .language_detection import detect_language
from .prompts import get_language_specific_prompt

logger = logging.getLogger(__name__)

# Use the MODEL_NAME from utils.py instead of hardcoding

@retry_with_backoff
async def generate_optimized_code(
    question: str,
    description: str,
    user_code: str,
    sample_input: str,
    sample_output: str,
    rag_context: Optional[str] = None,
    model: str = MODEL_NAME
) -> dict:
    """
    Generate optimized version of user's code (Python/MySQL).
    Uses language-aware prompts and optimized quality checks for faster response.
    """
    try:
        logger.info(f"Starting code optimization for question: {question[:100]}...")
        
        # Detect language
        language = detect_language(user_code)
        logger.info(f"Detected language: {language}")
        logger.info(f"Original code preview: {user_code[:200]}...")
        
        # Validate language detection makes sense
        if "def " in user_code and "for " in user_code and language != "python":
            logger.warning(f"Language detection may be wrong! Code contains Python keywords but detected as {language}")
        elif "SELECT" in user_code.upper() and "FROM" in user_code.upper() and language != "sql":
            logger.warning(f"Language detection may be wrong! Code contains SQL keywords but detected as {language}")
        
        # First attempt with standard prompt
        result = await _attempt_optimization(
            language, question, description, user_code, sample_input, sample_output, rag_context, model, is_retry=False
        )
        
        # If first attempt failed to produce different code, try with more aggressive prompt
        if result.get("optimized_code") == user_code:
            logger.info("First optimization attempt failed, trying with more aggressive prompt...")
            result = await _attempt_optimization(
                language, question, description, user_code, sample_input, sample_output, rag_context, model, is_retry=True
            )
        
        return result

    except Exception as e:
        logger.error(f"Error optimizing code: {str(e)}", exc_info=True)
        return {"optimized_code": user_code}

async def _attempt_optimization(
    language: str, 
    question: str, 
    description: str, 
    user_code: str, 
    sample_input: str, 
    sample_output: str, 
    rag_context: Optional[str], 
    model: str,
    is_retry: bool = False
) -> dict:
    """
    Attempt to optimize code with the given prompt.
    """
    try:
        # Generate language-specific prompt
        prompt = get_language_specific_prompt(
            language, question, description, user_code, sample_input, sample_output
        )
        
        # Add retry-specific instructions if this is a retry
        if is_retry:
            if language == "sql":
                prompt += "\n\n**RETRY INSTRUCTIONS:** The previous attempt failed. You MUST rewrite this query completely. Replace the inefficient subquery approach with a JOIN-based solution. Use CTEs or derived tables. The result MUST be structurally different from the original."
            else:
                prompt += "\n\n**RETRY INSTRUCTIONS:** The previous attempt failed. You MUST change the code structure significantly. The result MUST be different from the original."
        
        logger.info(f"Generated prompt for {language}. Prompt length: {len(prompt)} characters")
        
        if rag_context:
            prompt += f"\nRelevant context:\n{rag_context}\n"
            logger.info("Added RAG context to prompt")

        logger.info(f"Calling LLM with model: {model}")
        from services.llm.utils import safe_openai_call
        
        response = await safe_openai_call(
            client.chat.completions.create,
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=2000,  
            response_format={"type": "json_object"}
        )

        logger.info("LLM response received successfully")
        content = safe_strip(getattr(response.choices[0].message, 'content', None))

        if not content:
            logger.warning("Empty response from LLM, returning original code")
            return {"optimized_code": user_code}

        logger.info(f"LLM content length: {len(content)} characters")
        logger.info(f"LLM content preview: {content[:200]}...")

        try:
            parsed = json.loads(content)
            logger.info(f"Successfully parsed JSON response. Keys: {list(parsed.keys())}")
            
            optimized_code = parsed.get("optimized_code", "")
            logger.info(f"Extracted optimized code. Length: {len(optimized_code)} characters")
            logger.info(f"Original code length: {len(user_code)} characters")
            
            if not optimized_code:
                logger.warning("No optimized_code in LLM response, returning original code")
                return {"optimized_code": user_code}
            
            # Log the actual content for debugging
            logger.info(f"Original code: {repr(user_code)}")
            logger.info(f"Optimized code: {repr(optimized_code)}")
            
            # Validate that the optimized code contains actual code, not just comments
            if _is_valid_optimized_code(optimized_code, user_code, language):
                logger.info("LLM optimization successful, returning optimized code")
                return {"optimized_code": optimized_code}
            else:
                logger.warning("Optimized code appears incomplete or invalid, returning original code")
                logger.warning(f"Validation failed - original: {len(user_code.strip())} chars, optimized: {len(optimized_code.strip())} chars")
                return {"optimized_code": user_code}
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            logger.error(f"Raw content that failed to parse: {content[:500]}...")
            return {"optimized_code": user_code}

    except Exception as e:
        logger.error(f"Error in optimization attempt: {str(e)}", exc_info=True)
        return {"optimized_code": user_code}

def _is_valid_optimized_code(optimized_code: str, original_code: str, language: str) -> bool:
    """
    Validate that the optimized code is complete and contains actual code.
    
    Args:
        optimized_code: The code returned by the LLM
        original_code: The original user code
        
    Returns:
        bool: True if the optimized code appears valid
    """
    if not optimized_code or len(optimized_code.strip()) == 0:
        return False
    
    # Check if the optimized code is just comments
    lines = optimized_code.strip().split('\n')
    code_lines = [line for line in lines if line.strip() and not line.strip().startswith(('--', '#'))]
    
    if len(code_lines) == 0:
        logger.warning("Optimized code contains only comments, no actual code")
        return False
    
    # CRITICAL: Check if the optimized code is actually different from original
    original_clean = original_code.strip().lower().replace(' ', '').replace('\n', '')
    optimized_clean = optimized_code.strip().lower().replace(' ', '').replace('\n', '')
    
    if original_clean == optimized_clean:
        logger.warning("Optimized code is identical to original - no optimization performed")
        return False
    
    # Check if the optimized code is too short compared to original
    if len(optimized_code.strip()) < len(original_code.strip()) * 0.5:
        logger.warning("Optimized code is significantly shorter than original, likely incomplete")
        return False
    
    # Language-specific validation
    if language == "sql":
        # SQL should contain SELECT, FROM, etc.
        sql_keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'GROUP BY', 'ORDER BY', 'HAVING']
        if not any(keyword in optimized_code.upper() for keyword in sql_keywords):
            logger.warning("SQL code missing essential keywords")
            return False
    
    elif language == "python":
        # Python should contain actual code statements
        python_indicators = ['def ', 'class ', 'import ', 'from ', 'if ', 'for ', 'while ', 'return ', 'print(', '=']
        if not any(indicator in optimized_code for indicator in python_indicators):
            logger.warning("Python code missing essential code elements")
            return False
    
    logger.info("Optimized code validation passed")
    return True
