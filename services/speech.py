"""
Azure Speech Services Integration
Provides speech-to-text and text-to-speech using Azure AI Speech
Uses managed identity (DefaultAzureCredential) - no API keys required.
"""

import os
import time
from typing import Optional

import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

load_dotenv()

# Azure Speech Configuration
SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "australiaeast")
SPEECH_RESOURCE_ID = os.getenv("AZURE_SPEECH_RESOURCE_ID", "")

# Legacy key support (optional fallback)
SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")

# Available high-quality neural voices with different personas
# These are multilingual neural voices from Azure AI Foundry with natural conversational styles
AVAILABLE_VOICES = {
    # Australian English - Natural conversational voices
    "natasha": {
        "name": "en-AU-NatashaNeural",
        "display_name": "Natasha",
        "gender": "Female",
        "description": "Warm, friendly Australian female voice - great for customer service",
        "style": "Conversational, professional",
    },
    "william": {
        "name": "en-AU-WilliamNeural",
        "display_name": "William",
        "gender": "Male",
        "description": "Clear, confident Australian male voice - professional and approachable",
        "style": "Professional, reassuring",
    },
    "annette": {
        "name": "en-AU-AnnetteNeural",
        "display_name": "Annette",
        "gender": "Female",
        "description": "Cheerful, energetic Australian female voice - upbeat and engaging",
        "style": "Friendly, energetic",
    },
    "carly": {
        "name": "en-AU-CarlyNeural",
        "display_name": "Carly",
        "gender": "Female",
        "description": "Natural, conversational Australian female voice - casual and relatable",
        "style": "Casual, conversational",
    },
    "darren": {
        "name": "en-AU-DarrenNeural",
        "display_name": "Darren",
        "gender": "Male",
        "description": "Warm, friendly Australian male voice - trustworthy narrator style",
        "style": "Narrative, warm",
    },
    "duncan": {
        "name": "en-AU-DuncanNeural",
        "display_name": "Duncan",
        "gender": "Male",
        "description": "Young, enthusiastic Australian male voice - modern and dynamic",
        "style": "Youthful, energetic",
    },
    "elsie": {
        "name": "en-AU-ElsieNeural",
        "display_name": "Elsie",
        "gender": "Female",
        "description": "Gentle, calm Australian female voice - soothing and empathetic",
        "style": "Gentle, caring",
    },
    "freya": {
        "name": "en-AU-FreyaNeural",
        "display_name": "Freya",
        "gender": "Female",
        "description": "Professional, articulate Australian female voice - business focused",
        "style": "Professional, articulate",
    },
    "joanne": {
        "name": "en-AU-JoanneNeural",
        "display_name": "Joanne",
        "gender": "Female",
        "description": "Mature, experienced Australian female voice - authoritative yet friendly",
        "style": "Authoritative, experienced",
    },
    "ken": {
        "name": "en-AU-KenNeural",
        "display_name": "Ken",
        "gender": "Male",
        "description": "Deep, resonant Australian male voice - commanding presence",
        "style": "Deep, authoritative",
    },
    "kim": {
        "name": "en-AU-KimNeural",
        "display_name": "Kim",
        "gender": "Female",
        "description": "Bright, clear Australian female voice - excellent clarity",
        "style": "Clear, professional",
    },
    "neil": {
        "name": "en-AU-NeilNeural",
        "display_name": "Neil",
        "gender": "Male",
        "description": "Calm, measured Australian male voice - great for instructions",
        "style": "Calm, instructional",
    },
    "tina": {
        "name": "en-AU-TinaNeural",
        "display_name": "Tina",
        "gender": "Female",
        "description": "Versatile Australian female voice - adaptable to various contexts",
        "style": "Versatile, adaptable",
    },
}


class AzureSpeechService:
    """Azure Speech Services for voice input/output using managed identity"""

    # Token cache to avoid re-fetching on every request
    _cached_aad_token = None
    _token_expiry = 0

    def __init__(self, voice_persona: str = "natasha"):
        """Initialize Azure Speech Service with managed identity or API key fallback

        Args:
            voice_persona: Voice persona to use (default: natasha - warm friendly female voice)
        """
        self.voice_persona = voice_persona
        self.enabled = False
        self._use_aad = False

        # Get voice configuration
        voice_config = AVAILABLE_VOICES.get(voice_persona.lower(), AVAILABLE_VOICES["natasha"])
        self.current_voice = voice_config["name"]

        # Try managed identity first, then fall back to API key
        if self._init_managed_identity():
            self._use_aad = True
            self.enabled = True
            print(
                f"🎙️ Speech (AAD auth) - {voice_persona.title()} ({voice_config['gender']}) - {voice_config['description']}"
            )
        elif SPEECH_KEY:
            # Fallback to API key if available
            self.speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
            self.speech_config.speech_recognition_language = "en-AU"
            self.speech_config.speech_synthesis_voice_name = self.current_voice
            self.enabled = True
            print(
                f"🎙️ Speech (API key) - {voice_persona.title()} ({voice_config['gender']}) - {voice_config['description']}"
            )
        else:
            print("⚠️ Azure Speech not configured - speech features disabled")
            print("   Set AZURE_SPEECH_RESOURCE_ID + use managed identity, or set AZURE_SPEECH_KEY")

    def _init_managed_identity(self) -> bool:
        """Initialize with managed identity / Azure CLI credential"""
        try:
            self._get_credential()
            # Test that we can get a token
            self._refresh_aad_token()
            return True
        except Exception as e:
            print(f"⚠️ Managed identity not available for Speech: {e}")
            return False

    def _get_credential(self):
        """Get the appropriate Azure credential"""
        if os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true":
            from azure.identity import ManagedIdentityCredential

            self._credential = ManagedIdentityCredential()
        else:
            from azure.identity import AzureCliCredential

            self._credential = AzureCliCredential(process_timeout=30)

    def _refresh_aad_token(self) -> str:
        """Get or refresh the AAD token for Speech service"""
        now = time.time()
        # Refresh if token expires in less than 2 minutes
        if AzureSpeechService._cached_aad_token and AzureSpeechService._token_expiry > now + 120:
            return AzureSpeechService._cached_aad_token

        token = self._credential.get_token("https://cognitiveservices.azure.com/.default")
        AzureSpeechService._cached_aad_token = token.token
        AzureSpeechService._token_expiry = token.expires_on
        return token.token

    def _get_speech_config(self) -> speechsdk.SpeechConfig:
        """Get a SpeechConfig with fresh auth (AAD or key-based)"""
        if self._use_aad:
            token = self._refresh_aad_token()
            # For SpeechSynthesizer: aad#resourceId#token format
            if SPEECH_RESOURCE_ID:
                auth_token = f"aad#{SPEECH_RESOURCE_ID}#{token}"
            else:
                auth_token = f"aad#{token}"

            sc = speechsdk.SpeechConfig(auth_token=auth_token, region=SPEECH_REGION)
        else:
            sc = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)

        sc.speech_recognition_language = "en-AU"
        sc.speech_synthesis_voice_name = self.current_voice
        return sc

    def get_speech_token(self) -> Optional[dict]:
        """
        Get authorization token for client-side Speech SDK usage

        Returns:
            Dictionary with token, region and voice info, or None if not configured
        """
        if not self.enabled:
            return None

        try:
            voice_config = AVAILABLE_VOICES.get(self.voice_persona.lower(), AVAILABLE_VOICES["natasha"])

            if self._use_aad:
                # Get AAD token for client-side SDK
                token = self._refresh_aad_token()
                return {
                    "token": token,
                    "resourceId": SPEECH_RESOURCE_ID,
                    "region": SPEECH_REGION,
                    "language": "en-AU",
                    "voice": self.current_voice,
                    "voicePersona": self.voice_persona,
                    "voiceDescription": voice_config["description"],
                    "authType": "aad",
                }
            else:
                # Fallback: return API key for client-side SDK
                return {
                    "token": SPEECH_KEY,
                    "region": SPEECH_REGION,
                    "language": "en-AU",
                    "voice": self.current_voice,
                    "voicePersona": self.voice_persona,
                    "voiceDescription": voice_config["description"],
                    "authType": "key",
                }
        except Exception as e:
            print(f"❌ Error getting speech token: {str(e)}")
            return None

    def set_voice_persona(self, persona: str) -> bool:
        """Change the voice persona dynamically"""
        if not self.enabled:
            return False

        persona_lower = persona.lower()
        if persona_lower not in AVAILABLE_VOICES:
            print(f"⚠️ Unknown voice persona: {persona}")
            return False

        voice_config = AVAILABLE_VOICES[persona_lower]
        self.voice_persona = persona_lower
        self.current_voice = voice_config["name"]

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
            # Get fresh speech config (with refreshed token if AAD)
            speech_config = self._get_speech_config()

            # Create speech synthesizer
            speech_synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config, audio_config=None  # None = return audio data instead of playing
            )

            # Synthesize speech
            result = speech_synthesizer.speak_text_async(text).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return result.audio_data
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                print(f"❌ Speech synthesis canceled: {cancellation.reason}")
                if cancellation.reason == speechsdk.CancellationReason.Error:
                    print(f"❌ Error details: {cancellation.error_details}")
                    if "401" in str(cancellation.error_details):
                        print("❌ Azure Speech key is invalid or expired. Please update AZURE_SPEECH_KEY in .env")
                return None
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
            # Get fresh speech config
            speech_config = self._get_speech_config()

            # Create audio stream from bytes
            audio_stream = speechsdk.audio.PushAudioInputStream()
            audio_stream.write(audio_data)
            audio_stream.close()

            # Create audio config from stream
            audio_config = speechsdk.audio.AudioConfig(stream=audio_stream)

            # Create speech recognizer
            speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

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
    elif (
        voice_persona
        and hasattr(_speech_service, "voice_persona")
        and _speech_service.voice_persona != voice_persona.lower()
    ):
        # Update voice if different persona requested
        _speech_service.set_voice_persona(voice_persona)

    return _speech_service
