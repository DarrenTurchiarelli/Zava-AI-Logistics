"""
Azure Speech Services Integration
Provides speech-to-text and text-to-speech using Azure AI Speech
"""

import os
import azure.cognitiveservices.speech as speechsdk
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Azure Speech Configuration
SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "australiaeast")

class AzureSpeechService:
    """Azure Speech Services for voice input/output"""
    
    def __init__(self):
        """Initialize Azure Speech Service"""
        if not SPEECH_KEY:
            print("⚠️ AZURE_SPEECH_KEY not set - speech features will be disabled")
            self.enabled = False
            return
        
        self.enabled = True
        self.speech_config = speechsdk.SpeechConfig(
            subscription=SPEECH_KEY,
            region=SPEECH_REGION
        )
        
        # Configure speech recognition language
        self.speech_config.speech_recognition_language = "en-AU"  # Australian English
        
        # Configure speech synthesis voice
        self.speech_config.speech_synthesis_voice_name = "en-AU-NatashaNeural"  # Natural Australian female voice
        
    def get_speech_token(self) -> Optional[dict]:
        """
        Get Azure Speech token for client-side usage
        
        Returns:
            Dictionary with token and region, or None if not configured
        """
        if not self.enabled:
            return None
        
        try:
            # Generate authorization token for client-side use
            auth_token = speechsdk.AuthorizationToken(SPEECH_KEY, SPEECH_REGION)
            token = auth_token.get_token()
            
            return {
                'token': token,
                'region': SPEECH_REGION,
                'language': 'en-AU',
                'voice': 'en-AU-NatashaNeural'
            }
        except Exception as e:
            print(f"❌ Error getting speech token: {str(e)}")
            return None
    
    def synthesize_speech(self, text: str) -> Optional[bytes]:
        """
        Convert text to speech audio
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Audio bytes in WAV format, or None if failed
        """
        if not self.enabled:
            return None
        
        try:
            # Create speech synthesizer
            speech_synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=None  # None = return audio data instead of playing
            )
            
            # Synthesize speech
            result = speech_synthesizer.speak_text_async(text).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return result.audio_data
            else:
                print(f"❌ Speech synthesis failed: {result.reason}")
                return None
                
        except Exception as e:
            print(f"❌ Error synthesizing speech: {str(e)}")
            return None
    
    def recognize_speech_from_audio(self, audio_data: bytes) -> Optional[str]:
        """
        Convert speech audio to text
        
        Args:
            audio_data: Audio bytes in WAV format
            
        Returns:
            Recognized text, or None if failed
        """
        if not self.enabled:
            return None
        
        try:
            # Create audio stream from bytes
            audio_stream = speechsdk.audio.PushAudioInputStream()
            audio_stream.write(audio_data)
            audio_stream.close()
            
            # Create audio config from stream
            audio_config = speechsdk.audio.AudioConfig(stream=audio_stream)
            
            # Create speech recognizer
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            # Recognize speech
            result = speech_recognizer.recognize_once_async().get()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return result.text
            else:
                print(f"❌ Speech recognition failed: {result.reason}")
                return None
                
        except Exception as e:
            print(f"❌ Error recognizing speech: {str(e)}")
            return None


# Singleton instance
_speech_service = None

def get_speech_service() -> AzureSpeechService:
    """Get singleton Azure Speech Service instance"""
    global _speech_service
    if _speech_service is None:
        _speech_service = AzureSpeechService()
    return _speech_service
