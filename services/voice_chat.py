import speech_recognition as sr
import io
import base64
import logging
from typing import Optional, Dict, Any
import json
from datetime import datetime
import wave
import os
import tempfile

logger = logging.getLogger(__name__)

class VoiceChatService:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.active_sessions: Dict[str, Any] = {}
        # Configure for Lambda environment
        self.temp_dir = tempfile.gettempdir()

    async def process_voice_input(self, audio_data: str, session_id: str) -> str:
        """
        Process voice input from base64 encoded audio data
        """
        try:
            if not audio_data:
                raise ValueError("No audio data provided")
                
            # Validate base64 format
            try:
                audio_bytes = base64.b64decode(audio_data)
            except Exception:
                raise ValueError("Invalid base64 audio data format")
            
            # Validate audio data size (max 10MB)
            if len(audio_bytes) > 10 * 1024 * 1024:
                raise ValueError("Audio file too large (max 10MB)")
            
            # Create a temporary file for processing
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False, dir=self.temp_dir) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name
            
            try:
                # Validate WAV format
                with wave.open(temp_file_path, 'rb') as wav_file:
                    # Check if it's a valid WAV file
                    if wav_file.getnchannels() != 1:
                        raise ValueError("Audio must be mono")
                    if wav_file.getsampwidth() != 2:
                        raise ValueError("Audio must be 16-bit")
                    if wav_file.getframerate() not in [8000, 16000, 32000, 44100, 48000]:
                        raise ValueError("Invalid sample rate")
                
                # Use speech recognition
                with sr.AudioFile(temp_file_path) as source:
                    # Adjust for ambient noise
                    self.recognizer.adjust_for_ambient_noise(source)
                    audio_data = self.recognizer.record(source)
                    try:
                        text = self.recognizer.recognize_google(audio_data)
                    except sr.UnknownValueError:
                        raise ValueError("Could not understand audio")
                    except sr.RequestError as e:
                        raise Exception(f"Could not request results from speech recognition service: {str(e)}")
                
                logger.info(f"Successfully processed voice input for session {session_id}")
                return text
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file {temp_file_path}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error processing voice input: {str(e)}")
            raise Exception(f"Failed to process voice input: {str(e)}")

    async def start_chat_session(self, session_id: str) -> None:
        """
        Initialize a new chat session
        """
        self.active_sessions[session_id] = {
            "messages": [],
            "status": "active",
            "created_at": str(datetime.now())
        }

    async def add_chat_message(self, session_id: str, message: str, is_user: bool = True) -> None:
        """
        Add a message to the chat session
        """
        if session_id not in self.active_sessions:
            raise Exception("Chat session not found")
            
        self.active_sessions[session_id]["messages"].append({
            "message": message,
            "is_user": is_user,
            "timestamp": str(datetime.now())
        })

    async def get_chat_history(self, session_id: str) -> list:
        """
        Get chat history for a session
        """
        if session_id not in self.active_sessions:
            raise Exception("Chat session not found")
            
        return self.active_sessions[session_id]["messages"]

    async def end_chat_session(self, session_id: str) -> None:
        """
        End a chat session
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]