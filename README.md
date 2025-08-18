# NextInterview AI 

## Project Structure

```
NextInterview-AI/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── precompute_rag.py      # RAG system initialization script
├── verify_rag.py          # RAG system verification script
├── routes/                # API route handlers
│   ├── mock_interview.py  # Interview endpoints
│   ├── code_optimization.py # Code optimization endpoints
│   ├── approach_analysis.py # Approach analysis endpoints
│   └── rag.py            # RAG endpoints
├── services/              # Business logic services
│   ├── interview.py       # Interview service
│   ├── interview_initialization.py # Interview setup
│   ├── interview_flow.py  # Interview flow management
│   ├── feedback_service.py # Feedback generation
│   ├── code_optimization/ # Code optimization services
│   ├── llm/              # LLM utilities and prompts
│   ├── rag/              # RAG services with Qdrant
│   └── db/               # Database operations (MongoDB)
├── models/                # Pydantic models
│   └── schemas.py        # API request/response schemas
└── data/                 # Document data for RAG system
```

## API Endpoints

### Interview Management
- `POST /mock/init` - Initialize a new interview session
- `POST /mock/answer` - Submit an answer and get feedback
- `POST /mock/clarification` - Request clarification on questions

### Code Optimization
- `POST /code/optimize` - Get code optimization suggestions
- `POST /code/review` - Comprehensive code review

### Approach Analysis
- `POST /approach/analyze` - Analyze problem-solving approach
- `GET /approach/patterns/{user_id}` - Get user's approach patterns

### RAG (Retrieval-Augmented Generation)
- `POST /rag/retrieve` - Query the knowledge base for context
- `GET /rag/status` - Get RAG system status

### System Health
- `GET /health` - Health check endpoint with database and RAG status

## Technology Stack

- **Backend Framework**: FastAPI with async/await support
- **Database**: MongoDB with Motor async driver
- **Vector Database**: Qdrant for RAG system
- **NLP**: spaCy for text processing
- **AI/LLM**: OpenAI API integration
- **Document Processing**: Python-docx for document parsing
- **Text Embeddings**: Advanced embedding system for RAG

## Prerequisites

- Python 3.8+
- MongoDB instance
- OpenAI API key
- Qdrant vector database

## Environment Variables

Create a `.env` file with the following variables:

```bash
MONGODB_URI=your_mongodb_connection_string
DB_NAME=your_database_name
OPENAI_API_KEY=your_openai_api_key
```

## Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd NextInterview-AI
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Install spaCy language model**
```bash
python -m spacy download en_core_web_sm
```

5. **Initialize RAG system**
```bash
python precompute_rag.py
```

## Running the Application

### Local Development
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
python main.py
```

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health