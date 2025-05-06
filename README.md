# AI Mock Interview API

FastAPI backend for AI-powered mock interviews.

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Create `.env` file with:
   - MONGODB_URI
   - OPENAI_API_KEY
3. Run: `uvicorn main:app --reload`

## API Endpoints
- POST /interview/init
- POST /interview/answer
- POST /interview/voice-answer
- GET /interview/feedback/{session_id}
- GET /interview/topics
- GET /interview/logs 