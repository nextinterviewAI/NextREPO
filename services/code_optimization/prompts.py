"""
Optimization Prompts Module

Contains language-specific prompts for code optimization.
"""


def get_language_specific_prompt(language: str, question: str, description: str, user_code: str, sample_input: str, sample_output: str) -> str:
    """
    Generate detailed, comprehensive optimization prompts for better results.
    """
    if language == "sql":
        return f"""
You are a **senior MySQL performance engineer**. This SQL query has performance issues and needs significant optimization.

**ORIGINAL QUERY (WITH PERFORMANCE ISSUES):**
```sql
{user_code}
```

**TASK:** {question}
**DESCRIPTION:** {description}
**EXPECTED OUTPUT:** {sample_output}
**TABLE STRUCTURE:** {sample_input}

**PERFORMANCE ISSUES TO FIX:**
1. **INEFFICIENT SUBQUERIES**: IN clauses with subqueries can be slow and may not use indexes properly
2. **MULTIPLE EXECUTIONS**: Subquery might be executed multiple times
3. **POOR INDEXING**: Complex subqueries often don't leverage indexes effectively
4. **OFFSET PERFORMANCE**: LIMIT/OFFSET can be slow on large datasets
5. **NESTED QUERIES**: Deeply nested queries can cause performance bottlenecks

**REQUIRED OPTIMIZATIONS:**
1. **REPLACE INEFFICIENT PATTERNS** with JOIN-based approaches where applicable
2. **USE CTEs (Common Table Expressions)** or derived tables for complex logic
3. **IMPROVE READABILITY** with proper formatting, indentation, and table aliases
4. **ADD CONCISE COMMENTS** at the end explaining key improvements
5. **MUST BE DIFFERENT** from the original query structure
6. **OPTIMIZE FOR INDEXES** by restructuring WHERE clauses and JOINs

**OPTIMIZATION APPROACH:**
- Analyze the query structure and identify performance bottlenecks
- Replace subqueries with JOINs where beneficial
- Use CTEs for complex aggregations or ranking operations
- Ensure proper indexing considerations
- Add brief optimization comments at the end
- Maintain exact same results while improving performance

**OUTPUT FORMAT (JSON only):**
{{
"optimized_code": "complete optimized SQL query with brief optimization comments at the end"
}}

**CRITICAL:** Return a COMPLETELY DIFFERENT query structure that eliminates the performance issues while maintaining the same results. Keep comments concise and place them at the end.
"""

    else:  # Python
        return f"""
You are a **Senior Python Code Optimization Expert**. You MUST return Python code only.

**IMPORTANT: This is PYTHON code optimization. Return ONLY Python code, NOT SQL.**

**ORIGINAL PYTHON CODE:**
```python
{user_code}
```

**TASK:** {question}
**DESCRIPTION:** {description}
**EXPECTED INPUT:** {sample_input}
**EXPECTED OUTPUT:** {sample_output}

**PYTHON OPTIMIZATION REQUIREMENTS:**
1. **MUST CHANGE** the Python code structure, formatting, or organization
2. **PRESERVE** exact functionality and outputs
3. **IMPROVE** readability and performance
4. **ADD CONCISE COMMENTS** at the end explaining key optimizations
5. **RETURN COMPLETE** executable Python code
6. **MUST BE PYTHON** - no SQL, no other languages

**PYTHON OPTIMIZATION FOCUS:**
- Better variable names and structure
- PEP8 compliance and Python best practices
- Performance improvements (use sets, dict.fromkeys, list comprehensions)
- Code organization and readability
- Clear documentation and docstrings
- Python-specific optimizations (avoid O(n²) operations)

**OUTPUT FORMAT (JSON only):**
{{
"optimized_code": "complete optimized Python code with brief optimization comments at the end"
}}

**CRITICAL:** 
- Return ONLY Python code, NOT SQL
- The result MUST be executable Python code
- Include proper Python syntax, indentation, and structure
- Add concise Python-style comments (#) at the end, not throughout the code
- Keep comments brief but informative
"""