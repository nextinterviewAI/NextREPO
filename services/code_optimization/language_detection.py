"""
Language Detection Module

This module provides a fast, token-based approach for language detection
optimized for performance in a code optimization endpoint.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Define high-priority keywords for quick detection
# These keywords are highly indicative of a specific language and are
# used to make an immediate decision without a full file scan.

# Python keywords: prioritize file-level or block-level keywords
HIGH_PROBABILITY_PYTHON_KEYWORDS = {
    'def', 'class', 'import', 'from', 'try', 'except', 'async', 'await',
    'return', 'yield', 'lambda'
}

# SQL keywords: prioritize command-based keywords
HIGH_PROBABILITY_SQL_KEYWORDS = {
    'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP',
    'TABLE', 'PROCEDURE', 'DATABASE', 'JOIN', 'WHERE', 'SET', 'VALUES'
}

# Define maximum number of characters to analyze for speed
MAX_CHARS_TO_ANALYZE = 2000


def detect_language(code: str) -> str:
    """
    Detects the language of the provided code using a fast, token-based approach.
    Returns 'python' or 'sql'.
    """
    if not code or code.isspace():
        logger.info("Empty code provided, defaulting to python")
        return "python"

    # Analyze only the first part of the code for performance
    # This avoids scanning large files and is sufficient for most cases.
    sample_code = code[:MAX_CHARS_TO_ANALYZE]

    # Simple, fast check for definitive Python keywords
    for keyword in HIGH_PROBABILITY_PYTHON_KEYWORDS:
        if re.search(r'\b' + re.escape(keyword) + r'\b', sample_code):
            logger.info(f"Fast detection: Python keyword '{keyword}' found.")
            return "python"

    # Simple, fast check for definitive SQL keywords
    for keyword in HIGH_PROBABILITY_SQL_KEYWORDS:
        if re.search(r'\b' + re.escape(keyword) + r'\b', sample_code, re.IGNORECASE):
            logger.info(f"Fast detection: SQL keyword '{keyword}' found.")
            return "sql"

    # If no definitive keywords are found, perform a quick, weighted check.
    # This handles ambiguous cases like simple variable assignments.
    logger.info("No definitive keywords found, performing quick weighted analysis.")
    return _quick_weighted_analysis(sample_code)


def _quick_weighted_analysis(code_sample: str) -> str:
    """
    Performs a simple weighted analysis on a code sample.
    """
    sql_score = 0
    python_score = 0
    
    # Check for MySQL-specific syntax (highest confidence)
    if re.search(r'`[^`]+`|\bENGINE\s*=|@\w+', code_sample, re.IGNORECASE):
        sql_score += 5
        
    # Check for Python-specific syntax
    if re.search(r'__\w+__|\.append|\.join|\(self,', code_sample):
        python_score += 5

    # Check for assignment operators and semicolons
    if re.search(r'=', code_sample):
        python_score += 1
    if re.search(r';', code_sample):
        sql_score += 1

    if sql_score > python_score:
        return 'sql'
    else:
        # Default to Python if scores are equal or Python has a higher score.
        return 'python'