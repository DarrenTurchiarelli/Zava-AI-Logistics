"""
Services package - External service integrations
"""

from .speech import AzureSpeechService, get_speech_service
from .maps import BingMapsRouter, get_optimized_route

__all__ = [
    'AzureSpeechService',
    'get_speech_service',
    'BingMapsRouter',
    'get_optimized_route'
]
