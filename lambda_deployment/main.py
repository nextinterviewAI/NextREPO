from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from routes.interview import router as interview_router
from services.db import create_indexes, get_db, check_collections
import logging
import asyncio
import time
from fastapi.responses import JSONResponse
import os

# Configure logging
logging.basicConfig(
    level=logging.ERROR,  # Only show errors
    format='%(asctime)s - ERROR - %(message)s'
)
logger = logging.getLogger(__name__)

# Check if running in Lambda
IS_LAMBDA = bool(os.getenv('AWS_LAMBDA_FUNCTION_NAME'))

app = FastAPI(title="Mock Interview API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        response = await call_next(request)
        if response.status_code >= 400:
            logger.error(f"Error Response - Status: {response.status_code}, Path: {request.url.path}, Method: {request.method}")
        return response
    except Exception as e:
        logger.error(f"Request Error - Path: {request.url.path}, Method: {request.method}, Error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)}
        )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP Error - Status: {exc.status_code}, Path: {request.url.path}, Detail: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.on_event("startup")
async def startup_event():
    try:
        # Initialize database connection
        db = await get_db()
        
        # Create indexes if not exists
        await create_indexes()
        
        # Check collections
        await check_collections()
        
        # Log startup completion
        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup Error: {str(e)}", exc_info=True)
        if IS_LAMBDA:
            # In Lambda, we want to fail fast if startup fails
            raise

app.include_router(interview_router, prefix="/interview")

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
