import logging
import json
import traceback
from mangum import Mangum
from main import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
 
# Create handler for AWS Lambda
handler = Mangum(app, lifespan="off")  # Disable lifespan events in Lambda

def format_response(status_code, body, headers=None, multi_value_headers=None):
    """Format the response for API Gateway proxy integration"""
    response = {
        "isBase64Encoded": False,
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        },
        "body": json.dumps(body) if isinstance(body, (dict, list)) else str(body)
    }
    
    # Add custom headers if provided
    if headers:
        response["headers"].update(headers)
    
    # Add multi-value headers if provided
    if multi_value_headers:
        response["multiValueHeaders"] = multi_value_headers
    
    return response

def lambda_handler(event, context):
    try:
        # Log the full event for debugging
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Check if it's an OPTIONS request (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return format_response(200, {"message": "CORS preflight successful"})
        
        # Process the request
        response = handler(event, context)
        logger.info(f"Handler response: {json.dumps(response)}")
        
        # If response is already in API Gateway format, return it
        if isinstance(response, dict) and 'statusCode' in response:
            return response
            
        # Format the response for API Gateway
        return format_response(200, response)
            
    except Exception as e:
        error_detail = {
            "message": "Internal server error",
            "detail": str(e),
            "traceback": traceback.format_exc()
        }
        logger.error(f"Error in Lambda handler: {json.dumps(error_detail)}")
        return format_response(500, error_detail) 