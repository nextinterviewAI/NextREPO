# NextInterview AI - API Documentation

<!-- 
This document provides comprehensive API documentation for the NextInterview AI system.
It covers all endpoints for interview management, code optimization, approach analysis, and RAG functionality.
-->

## Base URL
```
http://localhost:8000/  # Local development
https://nextinterview.ai/fastapi/  # Live
```

## API Overview

The NextInterview AI API provides a comprehensive platform for AI-powered mock interviews with the following key features:

- **Mock Interviews**: Dynamic interview sessions with intelligent follow-up questions
- **Code Optimization**: AI-powered code review and optimization suggestions  
- **Approach Analysis**: Detailed analysis of problem-solving approaches
- **RAG System**: Enhanced responses using document knowledge base
- **User Session Management**: Persistent interview sessions and user history

## Available Endpoints

### Interview Management Endpoints

#### 1. Initialize Interview
Creates a new interview session with initial question and setup.

```http
POST /mock/init
```

**Request Body:**
```json
{
    "user_id": "string",
    "module_code": "string"
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
    "first_follow_up": "string",
    "interview_type": "string"
}
```

#### 2. Submit Answer
Processes user answers and provides follow-up questions or transitions to coding phase.

```http
POST /mock/answer
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
- If clarification needed:
```json
{
    "question": "string",
    "clarification": true,
    "ready_to_code": false,
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

- If normal flow:
```json
{
    "question": "string",
    "ready_to_code": boolean,
    "language": "string"
}
```

#### 3. Request Clarification
Requests clarification on interview questions.

```http
POST /mock/clarification
```

**Request Body:**
```json
{
    "session_id": "string",
    "question": "string"
}
```

**Response:**
```json
{
    "clarification": "string",
    "ready_to_code": boolean
}
```

### Code Optimization Endpoints

#### 4. Optimize Code
Analyzes and optimizes user's code with detailed explanations.

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
    "optimization_summary": "string",
    "improvements": ["string"],
    "complexity_analysis": "string"
}
```

#### 5. Code Review
Provides comprehensive code review and suggestions.

```http
POST /code/review
```

**Request Body:**
```json
{
    "code": "string",
    "language": "string",
    "context": "string"
}
```

**Response:**
```json
{
    "review": "string",
    "suggestions": ["string"],
    "best_practices": ["string"],
    "performance_notes": "string"
}
```

### Approach Analysis Endpoints

#### 6. Analyze Approach
Analyzes user's approach to a question and provides detailed feedback.

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
    "score": number,
    "approach_quality": "string"
}
```

#### 7. Get User Patterns
Retrieves user's approach patterns for analysis and personalization.

```http
GET /approach/patterns/{user_id}
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

### RAG System Endpoints

#### 8. Retrieve Context
Retrieves relevant context from knowledge base for interview questions.

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

#### 9. Get RAG Status
Checks the status of the RAG system and initialization.

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

### System Health Endpoints

#### 10. Health Check
Provides system health status including database and RAG system status.

```http
GET /health
```

**Response:**
```json
{
    "status": "healthy",
    "database": "connected",
    "rag_system": {
        "initialized": boolean,
        "message": "string"
    },
    "timestamp": number
}
```

## Data Models

### InterviewInit
```json
{
    "user_id": "string",
    "module_code": "string"
}
```

### AnswerRequest
```json
{
    "session_id": "string",
    "answer": "string",
    "clarification": boolean
}
```

### ClarificationRequest
```json
{
    "session_id": "string",
    "question": "string"
}
```

## Error Handling

The API uses standard HTTP status codes and returns error responses in the following format:

```json
{
    "message": "Error description",
    "detail": "Additional error details"
}
```

**Common Status Codes:**
- `200` - Success
- `400` - Bad Request
- `404` - Not Found
- `500` - Internal Server Error

## Authentication

Currently, the API uses user_id-based authentication. All endpoints require a valid user_id in the request body or path parameters.

## Rate Limiting

The API implements intelligent rate limiting and retry logic for external service calls (OpenAI API) with exponential backoff.

## Development Notes

- The system uses MongoDB for data persistence
- Qdrant vector database for RAG functionality
- OpenAI GPT-4 for AI-powered responses
- spaCy for natural language processing
- Async/await pattern throughout the codebase

## Testing

Use the provided verification scripts to test the system:
- `precompute_rag.py` - Initialize RAG system
- `verify_rag.py` - Verify RAG functionality

## Support

For API support and questions, refer to the Swagger UI documentation available at `/docs` when running the application locally. 