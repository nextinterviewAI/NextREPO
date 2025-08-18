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
1. **INEFFICIENT SUBQUERY**: The IN clause with subquery can be slow and may not use indexes properly
2. **MULTIPLE EXECUTIONS**: Subquery might be executed multiple times
3. **POOR INDEXING**: Complex subqueries often don't leverage indexes effectively

**REQUIRED OPTIMIZATIONS:**
1. **REPLACE IN + SUBQUERY** with JOIN-based approach for better performance
2. **USE CTE (Common Table Expression)** or derived table for the top 3 departments
3. **IMPROVE READABILITY** with proper formatting and table aliases
4. **ADD COMMENTS** explaining the performance improvements
5. **MUST BE DIFFERENT** from the original query structure

**OPTIMIZATION APPROACH:**
- Use WITH clause or derived table to get top 3 departments first
- JOIN this result with employees table
- Ensure proper indexing considerations
- Add clear optimization comments

**OUTPUT FORMAT (JSON only):**
{{
"optimized_code": "complete optimized SQL query with performance improvements and comments"
}}

**CRITICAL:** Return a COMPLETELY DIFFERENT query structure that eliminates the performance issues.
"""

    else:  # Python
        return f"""
You are a **Senior Python Code Optimization Expert**. Optimize this Python code for performance, readability, and best practices.

**ORIGINAL CODE:**
```python
{user_code}
```

**TASK:** {question}
**DESCRIPTION:** {description}
**EXPECTED INPUT:** {sample_input}
**EXPECTED OUTPUT:** {sample_output}

**REQUIREMENTS:**
1. **MUST CHANGE** the code structure, formatting, or organization
2. **PRESERVE** exact functionality and outputs
3. **IMPROVE** readability and performance
4. **ADD COMMENTS** explaining what optimizations were made
5. **RETURN COMPLETE** executable Python code

**OPTIMIZATION FOCUS:**
- Better variable names and structure
- PEP8 compliance
- Performance improvements
- Code organization
- Clear documentation

**OUTPUT FORMAT (JSON only):**
{{
"optimized_code": "complete optimized Python code with optimization comments"
}}

**CRITICAL:** Return the FULL optimized Python code, not just comments.
"""

