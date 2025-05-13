from typing import Dict, Any
import openai
import os
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ApproachAnalysisService:
    def __init__(self):
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.error("OPENAI_API_KEY not found in environment variables")
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = openai.AsyncOpenAI(api_key=openai_api_key)
        logger.info("OpenAI API client initialized successfully")

    async def analyze_approach(self, question: str, user_answer: str) -> Dict[str, Any]:
        """
        Analyze the user's approach to the question and provide feedback.
        
        Args:
            question (str): The interview question
            user_answer (str): User's response to the question
            
        Returns:
            Dict containing:
            - feedback (str): Detailed feedback on the approach
            - strengths (list): List of identified strengths
            - areas_for_improvement (list): List of areas to improve
            - score (int): Score out of 10
        """
        try:
            prompt = f"""
            Question: {question}
            User's Answer: {user_answer}

            Please analyze the user's approach and provide:
            1. Detailed feedback on their approach
            2. Key strengths in their response
            3. Areas for improvement
            4. A score out of 10

            Return ONLY a JSON object with the following structure, no markdown formatting or additional text:
            {{
                "feedback": "detailed feedback here",
                "strengths": ["strength1", "strength2", ...],
                "areas_for_improvement": ["area1", "area2", ...],
                "score": score
            }}
            """

            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert interviewer analyzing candidate responses. Return only valid JSON without any markdown formatting or additional text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            # Parse the response
            analysis_text = response.choices[0].message.content.strip()
            
            # Remove any markdown formatting if present
            if analysis_text.startswith("```json"):
                analysis_text = analysis_text[7:]
            if analysis_text.endswith("```"):
                analysis_text = analysis_text[:-3]
            
            # Parse JSON
            try:
                analysis = json.loads(analysis_text)
                return analysis
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {analysis_text}")
                raise Exception(f"Invalid JSON response from analysis: {str(e)}")

        except Exception as e:
            logger.error(f"Error in approach analysis: {str(e)}", exc_info=True)
            raise Exception(f"Error in approach analysis: {str(e)}") 