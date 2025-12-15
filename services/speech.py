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

# Available high-quality neural voices with different personas
# These are multilingual neural voices from Azure AI Foundry with natural conversational styles
AVAILABLE_VOICES = {
    # Australian English - Natural conversational voices
    "natasha": {
        "name": "en-AU-NatashaNeural",
        "gender": "Female",
        "description": "Warm, friendly Australian female voice - great for customer service",
        "style": "Conversational, professional"
    },
    "william": {
        "name": "en-AU-WilliamNeural", 
        "gender": "Male",
        "description": "Clear, confident Australian male voice - professional and approachable",
        "style": "Professional, reassuring"
    },
    "annette": {
        "name": "en-AU-AnnetteNeural",
        "gender": "Female", 
        "description": "Cheerful, energetic Australian female voice - upbeat and engaging",
        "style": "Friendly, energetic"
    },
    "carly": {
        "name": "en-AU-CarlyNeural",
        "gender": "Female",
        "description": "Natural, conversational Australian female voice - casual and relatable",
        "style": "Casual, conversational"
    },
    "darren": {
        "name": "en-AU-DarrenNeural",
        "gender": "Male",
        "description": "Warm, friendly Australian male voice - trustworthy narrator style",
        "style": "Narrative, warm"
    },
    "duncan": {
        "name": "en-AU-DuncanNeural",
        "gender": "Male",
        "description": "Young, enthusiastic Australian male voice - modern and dynamic",
        "style": "Youthful, energetic"
    },
    "elsie": {
        "name": "en-AU-ElsieNeural",
        "gender": "Female",
        "description": "Gentle, calm Australian female voice - soothing and empathetic",
        "style": "Gentle, caring"
    },
    "freya": {
        "name": "en-AU-FreyaNeural",
        "gender": "Female",
        "description": "Professional, articulate Australian female voice - business focused",
        "style": "Professional, articulate"
    },
    "joanne": {
        "name": "en-AU-JoanneNeural",
        "gender": "Female",
        "description": "Mature, experienced Australian female voice - authoritative yet friendly",
        "style": "Authoritative, experienced"
    },
    "ken": {
        "name": "en-AU-KenNeural",
        "gender": "Male",
        "description": "Deep, resonant Australian male voice - commanding presence",
        "style": "Deep, authoritative"
    },
    "kim": {
        "name": "en-AU-KimNeural",
        "gender": "Female",
        "description": "Bright, clear Australian female voice - excellent clarity",
        "style": "Clear, professional"
    },
    "neil": {
        "name": "en-AU-NeilNeural",
        "gender": "Male",
        "description": "Calm, measured Australian male voice - great for instructions",
        "style": "Calm, instructional"
    },
    "tina": {
        "name": "en-AU-TimNeural",
        "gender": "Male",
        "description": "Versatile Australian male voice - adaptable to various contexts",
        "style": "Versatile, adaptable"
    },
}

class AzureSpeechService:
    """Azure Speech Services for voice input/output"""
    
    def __init__(self, voice_persona: str = "natasha"):
        """Initialize Azure Speech Service
        
        Args:
            voice_persona: Voice persona to use (default: natasha - warm friendly female voice)
                          Options: natasha, william, annette, carly, darren, duncan, elsie, 
                                   freya, joanne, ken, kim, neil, tina
        """
        if not SPEECH_KEY:
            print("⚠️ AZURE_SPEECH_KEY not set - speech features will be disabled")
            self.enabled = False
            return
        
        self.enabled = True
        self.voice_persona = voice_persona
        
        # Get voice configuration
        voice_config = AVAILABLE_VOICES.get(voice_persona.lower(), AVAILABLE_VOICES["william"])
        self.current_voice = voice_config["name"]
        
        self.speech_config = speechsdk.SpeechConfig(
            subscription=SPEECH_KEY,
            region=SPEECH_REGION
        )
        
        # Configure speech recognition language
        self.speech_config.speech_recognition_language = "en-AU"  # Australian English
        
        # Configure speech synthesis voice with selected persona
        self.speech_config.speech_synthesis_voice_name = self.current_voice
        
        print(f"🎙️ Voice persona: {voice_persona.title()} ({voice_config['gender']}) - {voice_config['description']}")
        
    def get_speech_token(self) -> Optional[dict]:
        """
        Get Azure Speech token for client-side usage
        
        Returns:
            Dictionary with token and region, or None if not configured
        """
        if not self.enabled:
            return None
        
        try:
            # Return the subscription key directly for client-side use
            # Azure Speech SDK on client side uses the key to generate tokens
            voice_config = AVAILABLE_VOICES.get(self.voice_persona.lower(), AVAILABLE_VOICES["natasha"])
            
            return {
                'token': SPEECH_KEY,  # Client SDK will handle token generation
                'region': SPEECH_REGION,
                'language': 'en-AU',
                'voice': self.current_voice,
                'voicePersona': self.voice_persona,
                'voiceDescription': voice_config['description']
            }
        except Exception as e:
            print(f"❌ Error getting speech token: {str(e)}")
            return None
    
    def set_voice_persona(self, persona: str) -> bool:
        """
        Change the voice persona dynamically
        
        Args:
            persona: Voice persona name
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        persona_lower = persona.lower()
        if persona_lower not in AVAILABLE_VOICES:
            print(f"⚠️ Unknown voice persona: {persona}")
            return False
        
        voice_config = AVAILABLE_VOICES[persona_lower]
        self.voice_persona = persona_lower
        self.current_voice = voice_config["name"]
        self.speech_config.speech_synthesis_voice_name = self.current_voice
        
        print(f"🎙️ Switched to {persona.title()} voice: {voice_config['description']}")
        return True
    
    @staticmethod
    def list_available_voices() -> dict:
        """Get list of all available voice personas"""
        return AVAILABLE_VOICES
    
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

def get_speech_service(voice_persona: str = None) -> AzureSpeechService:
    """Get singleton Azure Speech Service instance
    
    Args:
        voice_persona: Optional voice persona to use. If not provided, uses environment variable
                      AZURE_SPEECH_VOICE or defaults to 'natasha'
    """
    global _speech_service
    
    # Get voice from parameter, environment, or default
    if voice_persona is None:
        voice_persona = os.getenv("AZURE_SPEECH_VOICE", "natasha")
    
    if _speech_service is None:
        _speech_service = AzureSpeechService(voice_persona=voice_persona)
    elif voice_persona and hasattr(_speech_service, 'voice_persona') and _speech_service.voice_persona != voice_persona.lower():
        # Update voice if different persona requested
        _speech_service.set_voice_persona(voice_persona)
        
    return _speech_service
