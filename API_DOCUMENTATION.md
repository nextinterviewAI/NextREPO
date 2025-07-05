# Mock Interview API Documentation

<!-- 
This document provides comprehensive API documentation for the Mock Interview system.
It covers all endpoints for interview management, user interactions, and RAG functionality.
-->

## Base URL
```
https://nextinterview.ai/fastapi/
```

## Available Endpoints

<!-- Interview Management Endpoints -->

### 1. Get Available Topics
<!-- Retrieves list of available interview topics for user selection -->
```http
GET /topics
```

**Response:**
```json
{
    "topics": [
        "Deep Learning",
        "Bias-Variance Tradeoff",
        "A/B Testing",
        "Clustering",
        "Linear Regression",
        "Feature Engineering",
        "Data Preprocessing",
        "SQL Modelling",
        "Random Forest",
        "Time Series Analysis"
    ]
}
```

### 2. Initialize Interview
<!-- Creates a new interview session with initial question and setup -->
```http
POST /init
```

**Request Body:**
```json
{
    "topic": "string",
    "user_id": "string"
}
```

**Response:**
```json
{
    "session_id": "string",
    "base_question": "string",
    "difficulty": "string",
    "example": "string",
    "code_stub": "string",
    "tags": ["string"],
    "language": "string",
    "first_follow_up": "string"
}
```

### 3. Submit Text Answer
<!-- Processes user answers and provides follow-up questions or transitions to coding -->
```http
POST /answer
```

**Request Body:**
```json
{
    "session_id": "string",
    "answer": "string",
    "clarification": boolean
}
```

**Response:**
- If clarification: 
```json
{
    "question": "string", // clarification response
    "clarification": true,
    "ready_to_code": true,
    "language": "string"
}
```
- If gibberish/unclear answer:
```json
{
    "question": "string", // original question + error message
    "ready_to_code": false,
    "language": "string"
}
```
- If normal flow:
```json
{
    "question": "string",
    "ready_to_code": boolean,
    "language": "string"
}
```
- If transition to coding phase:
```json
{
    "question": "string",
    "clarification": true,
    "ready_to_code": true,
    "code_stub": "string",
    "language": "string",
    "tags": ["string"]
}
```

### 4. Get Interview Feedback
<!-- Retrieves comprehensive feedback for completed interview sessions -->
```http
GET /feedback/{session_id}
```

**Response:**
```json
{
    "summary": "string",
    "positive_points": ["string"],
    "points_to_address": ["string"],
    "areas_for_improvement": ["string"]
}
```

<!-- User Management Endpoints -->

### 5. Get User Interactions
<!-- Retrieves user's interaction history for analysis and personalization -->
```http
GET /user/interactions/{user_id}?limit=50
```

**Response:**
```json
{
    "interactions": [ ... ] // List of user interaction objects
}
```

### 6. Get User Sessions
<!-- Retrieves list of user's interview sessions with summary information -->
```http
GET /user/sessions/{user_id}?limit=20
```

**Response:**
```json
{
    "sessions": [
        {
            "session_id": "string",
            "topic": "string",
            "user_name": "string",
            "status": "string",
            "current_phase": "string",
            "total_questions": number,
            "created_at": "string",
            "updated_at": "string",
            "has_feedback": boolean
        }
    ]
}
```

### 7. Get User Session Detail
<!-- Retrieves detailed information for a specific interview session -->
```http
GET /user/session/{user_id}/{session_id}
```

**Response:**
```json
{
    "session_id": "string",
    "topic": "string",
    "user_name": "string",
    "status": "string",
    "current_phase": "string",
    "total_questions": number,
    "created_at": "string",
    "updated_at": "string",
    "metadata": { ... },
    "questions": [ ... ],
    "follow_up_questions": [ ... ],
    "clarifications": [ ... ],
    "feedback": { ... }
}
```

### 8. Get User Patterns
<!-- Retrieves enhanced user patterns data for debugging and analysis -->
```http
GET /user/patterns/{user_id}
```

**Response:**
```json
{
    "user_patterns": {
        "recent_topics": ["string"],
        "performance_trend": [number],
        "common_weaknesses": ["string"],
        "strengths": ["string"],
        "completion_rate": number,
        "avg_response_length": number,
        "average_score": number,
        "total_sessions": number
    },
    "personalized_guidance": "string"
}
```

<!-- Analysis and Optimization Endpoints -->

### 9. Analyze Approach
<!-- Analyzes user's approach to a question and provides detailed feedback -->
```http
POST /approach/analyze-approach
```

**Request Body:**
```json
{
    "question": "string",
    "user_answer": "string",
    "user_id": "string"
}
```

**Response:**
```json
{
    "feedback": "string",
    "strengths": ["string"],
    "areas_for_improvement": ["string"],
    "score": number
}
```

### 10. Optimize Code
<!-- Analyzes and optimizes user's code with detailed explanations -->
```http
POST /code/optimize-code
```

**Request Body:**
```json
{
    "question": "string",
    "user_code": "string",
    "sample_input": "string",
    "sample_output": "string",
    "user_id": "string"
}
```

**Response:**
```json
{
    "optimized_code": "string",
    "optimization_summary": "string"
}
```

<!-- RAG System Endpoints -->

### 11. Retrieve RAG Context
<!-- Retrieves relevant context from knowledge base for interview questions -->
```http
POST /rag/retrieve
```

**Request Body:**
```json
{
    "question": "string"
}
```

**Response:**
```json
{
    "question": "string",
    "context": ["string"],
    "context_count": number
}
```

### 12. Get RAG Status
<!-- Checks the status of the RAG system and initialization -->
```http
GET /rag/status
```

**Response:**
```json
{
    "initialized": boolean,
    "message": "string"
}
```

<!-- Example Response -->
<!-- Sample feedback response showing detailed analysis structure -->
{
    "summary": "Test Admin demonstrated a strong understanding of database schema design, normalization principles, and data integrity constraints. Their explanations were detailed and showcased a methodical approach to SQL query construction.",
    "positive_points": [
        "Test Admin effectively identified core entities (Users, Books, Orders, OrderItems) and defined appropriate attributes for each table, showcasing a structured approach to schema design.",
        "Test Admin demonstrated a thorough understanding of data integrity by explaining the use of constraints like NOT NULL, UNIQUE, and primary key constraints to ensure accurate and reliable data.",
        "Test Admin displayed proficiency in enforcing referential integrity through FOREIGN KEY constraints to maintain valid relationships between tables and prevent orphaned records."
    ],
    "points_to_address": [
        "In the schema design explanation, Test Admin could have elaborated more on the rationale behind choosing specific attributes for the Users, Books, Orders, and OrderItems tables.",
        "When discussing data types, Test Admin could have provided additional examples or comparisons to further justify the selection of DECIMAL for Price over FLOAT or INTEGER.",
        "Test Admin's response regarding handling historical price changes could have been enhanced by detailing how the BookPriceHistory table would be queried to retrieve past prices."
    ],
    "areas_for_improvement": [
        "Test Admin could improve by considering potential scenarios where business rules or constraints might impact the schema design, such as user roles or order restrictions, to create a more comprehensive database model.",
        "To enhance schema robustness, Test Admin could explore more advanced techniques like triggers or stored procedures to automate certain data management tasks, such as updating book prices or tracking historical changes.",
        "Test Admin could further develop their understanding of optimizing query performance by discussing indexing strategies or query tuning methods to efficiently retrieve data when dealing with large datasets."
    ]
} 