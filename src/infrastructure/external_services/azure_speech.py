"""
Azure Speech Service

Provides speech-to-text and text-to-speech capabilities using Azure AI Speech.
"""

import os
from typing import Optional

import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

load_dotenv()


class AzureSpeechService:
    """
    Azure Speech service for voice input/output
    
    Supports both managed identity and API key authentication.
    """
    
    # Available Australian English neural voices
    VOICES = {
        "natasha": "en-AU-NatashaNeural",  # Warm, friendly female
        "william": "en-AU-WilliamNeural",  # Confident male
        "annette": "en-AU-AnnetteNeural",  # Cheerful female
        "darren": "en-AU-DarrenNeural",    # Warm male narrator
    }
    
    def __init__(self, voice_persona: str = "natasha"):
        self.voice_persona = voice_persona
        self.region = os.getenv("AZURE_SPEECH_REGION", "australiaeast")
        self.key = os.getenv("AZURE_SPEECH_KEY", "")
        self.enabled = False
        
        # Get voice name
        self.current_voice = self.VOICES.get(voice_persona.lower(), self.VOICES["natasha"])
        
        # Initialize
        if self.key:
            self.enabled = True
            print(f"🎙️  Speech service initialized ({voice_persona})")
        else:
            print("[SPEECH] WARNING: Azure Speech key not configured")
    
    def text_to_speech(self, text: str, output_file: Optional[str] = None) -> bool:
        """
        Convert text to speech
        
        Args:
            text: Text to synthesize
            output_file: Optional audio file path (.wav)
            
        Returns:
            True if successful
        """
        if not self.enabled:
            print("[SPEECH] Service not enabled")
            return False
        
        try:
            speech_config = speechsdk.SpeechConfig(subscription=self.key, region=self.region)
            speech_config.speech_synthesis_voice_name = self.current_voice
            
            if output_file:
                audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
                synthesizer = speechsdk.SpeechSynthesizer(
                    speech_config=speech_config,
                    audio_config=audio_config
                )
            else:
                synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
            
            result = synthesizer.speak_text_async(text).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return True
            else:
                print(f"[SPEECH] Synthesis failed: {result.reason}")
                return False
        
        except Exception as e:
            print(f"[SPEECH] Error: {e}")
            return False
    
    def speech_to_text(self, audio_file: Optional[str] = None) -> Optional[str]:
        """
        Convert speech to text
        
        Args:
            audio_file: Optional audio file path (uses microphone if None)
            
        Returns:
            Transcribed text or None if failed
        """
        if not self.enabled:
            print("[SPEECH] Service not enabled")
            return None
        
        try:
            speech_config = speechsdk.SpeechConfig(subscription=self.key, region=self.region)
            
            if audio_file:
                audio_config = speechsdk.audio.AudioConfig(filename=audio_file)
                recognizer = speechsdk.SpeechRecognizer(
                    speech_config=speech_config,
                    audio_config=audio_config
                )
            else:
                recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config)
            
            result = recognizer.recognize_once_async().get()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return result.text
            else:
                print(f"[SPEECH] Recognition failed: {result.reason}")
                return None
        
        except Exception as e:
            print(f"[SPEECH] Error: {e}")
            return None
