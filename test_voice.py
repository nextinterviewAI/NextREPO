import sounddevice as sd
import numpy as np
import wave
import requests
import json
import base64
import io
import time

def record_audio(sample_rate=16000):
    """
    Record audio until the user presses Enter.
    Returns the recorded audio data and sample rate.
    """
    print("\nRecording... Press Enter to stop recording.")
    
    # Initialize recording
    recording = []
    stop_recording = False
    
    def audio_callback(indata, frames, time, status):
        if status:
            print(f"Status: {status}")
        if not stop_recording:
            recording.append(indata.copy())
    
    # Start recording in a non-blocking way
    with sd.InputStream(samplerate=sample_rate, channels=1, callback=audio_callback):
        print("Recording started. Press Enter when you're done speaking...")
        input()  # Wait for Enter key
        stop_recording = True
        time.sleep(0.5)  # Small delay to ensure last chunk is recorded
    
    # Convert recording to numpy array
    audio_data = np.concatenate(recording, axis=0)
    return audio_data, sample_rate

def save_to_wav(audio_data, sample_rate):
    """Convert numpy array to WAV format"""
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 2 bytes for 16-bit audio
        wf.setframerate(sample_rate)
        wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())
    return buffer.getvalue()

def encode_audio(audio_data):
    """Encode audio data to base64"""
    return base64.b64encode(audio_data).decode('utf-8')

def submit_voice_answer(session_id, audio_data):
    """Submit voice answer to the API"""
    url = "http://localhost:8000/mock-interview-api/voice-answer"
    headers = {"Content-Type": "application/json"}
    data = {
        "session_id": session_id,
        "audio_data": audio_data
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error submitting voice answer: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return None

def init_interview(topic, user_name):
    """Initialize interview session"""
    url = "http://localhost:8000/mock-interview-api/init"
    headers = {"Content-Type": "application/json"}
    data = {
        "topic": topic,
        "user_name": user_name
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error initializing interview: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return None

def main():
    # Initialize interview
    topic = input("Enter interview topic (e.g., Python, JavaScript): ")
    user_name = input("Enter your name: ")
    
    init_response = init_interview(topic, user_name)
    if not init_response:
        print("Failed to initialize interview")
        return
    
    session_id = init_response.get("session_id")
    print(f"\nInterview initialized with session ID: {session_id}")
    print(f"Base question: {init_response.get('base_question')}")
    print(f"First follow-up: {init_response.get('first_followup')}")
    
    try:
        while True:
            input("\nPress Enter to start recording your answer...")
            
            # Record audio
            audio_data, sample_rate = record_audio()
            
            # Convert to WAV and encode
            wav_data = save_to_wav(audio_data, sample_rate)
            encoded_audio = encode_audio(wav_data)
            
            # Submit answer
            print("\nSubmitting your answer...")
            response = submit_voice_answer(session_id, encoded_audio)
            
            if response:
                print("\nNext question:", response.get("next_question", "No more questions"))
                print("Current status:", response.get("status", "Unknown"))
                print("Good answers count:", response.get("good_answers_count", 0))
            
            if input("\nContinue? (y/n): ").lower() != 'y':
                break
                
    except KeyboardInterrupt:
        print("\nInterview ended by user")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()