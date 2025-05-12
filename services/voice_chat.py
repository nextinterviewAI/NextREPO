import speech_recognition as sr
import io
import base64
import logging
from typing import Optional, Dict, Any
import json
from datetime import datetime
import wave

logger = logging.getLogger(__name__)

class VoiceChatService:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.active_sessions: Dict[str, Any] = {}

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
            
            # Create a BytesIO object with the WAV data
            wav_io = io.BytesIO(audio_bytes)
            
            # Validate WAV format
            try:
                with wave.open(wav_io, 'rb') as wav_file:
                    # Check if it's a valid WAV file
                    if wav_file.getnchannels() != 1:
                        raise ValueError("Audio must be mono")
                    if wav_file.getsampwidth() != 2:
                        raise ValueError("Audio must be 16-bit")
                    if wav_file.getframerate() not in [8000, 16000, 32000, 44100, 48000]:
                        raise ValueError("Invalid sample rate")
            except Exception as e:
                raise ValueError(f"Invalid WAV format: {str(e)}")
            
            # Reset the BytesIO position
            wav_io.seek(0)
            
            # Use speech recognition
            with sr.AudioFile(wav_io) as source:
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
            
        except Exception as e:
            logger.error(f"Error processing voice input: {str(e)}")
            raise Exception(f"Failed to process voice input: {str(e)}")

    async def start_chat_session(self, session_id: str) -> None:
        """
        Initialize a new chat session
        """
        self.active_sessions[session_id] = {
            "messages": [],
            "status": "active"
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