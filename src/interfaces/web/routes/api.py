"""
API Blueprint - Utility and Service Endpoints

Provides Azure Maps address validation/autocomplete and Azure Speech synthesis/recognition.
All endpoints are publicly accessible for customer-facing features.
"""
from flask import Blueprint, request, jsonify, send_file, session
import os
import io
import requests
from datetime import datetime, timezone
from typing import Dict, Any

from services.maps_service import get_maps_service
from services.speech import get_speech_service, AVAILABLE_VOICES
from src.interfaces.web.middleware import login_required
from parcel_tracking_db import ParcelTrackingDB
from utils.async_helpers import run_async

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route("/validate-address", methods=["POST"])
def validate_address() -> tuple[Dict[str, Any], int]:
    """
    Validate address using Azure Maps Geocoding API
    
    Public endpoint for parcel registration and customer use.
    
    Returns:
        JSON with validation result, formatted address, and coordinates
    """
    data = request.get_json()
    address = data.get("address", "").strip()

    if not address:
        return jsonify({"valid": False, "error": "No address provided"}), 400

    try:
        maps = get_maps_service()
        result = maps.geocode_address_strict(address)

        if result and result["valid"]:
            return jsonify(
                {
                    "valid": True,
                    "formatted_address": result.get("formatted_address", address),
                    "latitude": result["coords"][0],
                    "longitude": result["coords"][1],
                    "confidence": result.get("confidence", 0.8),
                    "message": "Address validated successfully",
                }
            ), 200
        else:
            return jsonify({
                "valid": False,
                "unavailable": result.get("unavailable", False),
                "message": result.get("message", "Address could not be validated")
            }), 200

    except Exception as e:
        print(f"Address validation error: {e}")
        return jsonify({"valid": False, "error": str(e)}), 500


@api_bp.route("/autocomplete-address", methods=["GET"])
def autocomplete_address() -> tuple[Dict[str, Any], int]:
    """
    Get address suggestions using Azure Maps Search API
    
    Public endpoint for real-time address autocomplete in forms.
    
    Query Parameters:
        query (str): Partial address text (minimum 3 characters)
        
    Returns:
        JSON with list of address suggestions
    """
    query = request.args.get("query", "").strip()

    if not query or len(query) < 3:
        return jsonify({"suggestions": []}), 200

    try:
        subscription_key = os.getenv("AZURE_MAPS_SUBSCRIPTION_KEY", "")

        if not subscription_key:
            return jsonify({"suggestions": []}), 200

        # Use Azure Maps Search Address API
        url = "https://atlas.microsoft.com/search/address/json"
        params = {
            "api-version": "1.0",
            "subscription-key": subscription_key,
            "query": query,
            "countrySet": "AU",  # Australia only
            "limit": 5,
            "typeahead": True,
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            results = response.json()
            suggestions = []

            if "results" in results:
                for result in results["results"]:
                    address_data = result.get("address", {})
                    formatted = address_data.get("freeformAddress", "")

                    if formatted:
                        suggestions.append(
                            {
                                "address": formatted,
                                "type": result.get("type", ""),
                                "position": result.get("position", {}),
                            }
                        )

            return jsonify({"suggestions": suggestions}), 200
        else:
            return jsonify({"suggestions": []}), 200

    except Exception as e:
        print(f"Address autocomplete error: {e}")
        return jsonify({"suggestions": []}), 200


@api_bp.route("/speech/voices", methods=["GET"])
def get_voices():
    """
    Return the list of available Azure Neural voice personas.

    Public endpoint consumed by the chatbot voice selector dropdown.

    Returns:
        JSON with voices dict keyed by persona name
    """
    return jsonify({"voices": AVAILABLE_VOICES}), 200


@api_bp.route("/speech/synthesize", methods=["POST"])
def synthesize_speech():
    """
    Convert text to speech using Azure Speech Services
    
    Public endpoint - no authentication required for customer-facing TTS.
    
    Request Body:
        text (str): Text to convert to speech
        voice_persona (str, optional): Voice persona (default: 'natasha')
        
    Returns:
        WAV audio file as binary response
    """
    data = request.get_json()
    text = data.get("text", "")
    voice_persona = data.get("voice_persona", "natasha")

    if not text:
        return jsonify({"error": "Text is required"}), 400

    speech_service = get_speech_service(voice_persona=voice_persona)
    audio_data = speech_service.synthesize_speech(text)

    if audio_data:
        return send_file(
            io.BytesIO(audio_data), 
            mimetype="audio/wav", 
            as_attachment=False
        ), 200
    else:
        return jsonify({"error": "Speech synthesis failed"}), 500


@api_bp.route("/speech/recognize", methods=["POST"])
def recognize_speech():
    """
    Recognize speech from audio file (placeholder for future implementation)
    
    Request Body:
        audio (file): Audio file to transcribe
        
    Returns:
        JSON with recognized text
    """
    # TODO: Implement speech recognition using Azure Speech Services
    # This endpoint is reserved for future voice input functionality
    return jsonify({
        "error": "Speech recognition not yet implemented",
        "supported": False
    }), 501


@api_bp.route("/address-notes/add", methods=["POST"])
@login_required
def add_address_note():
    """Add a custom address note (drivers & admins)"""
    try:
        data = request.get_json()
        address = (data.get("address") or "").strip()
        note = (data.get("note") or "").strip()
        category = (data.get("category") or "general").strip()

        if not address or not note:
            return jsonify({"success": False, "error": "Address and note are required"}), 400

        user = session.get("user", {})
        driver_name = user.get("display_name") or user.get("username", "unknown")

        category_hints = {
            "safety": "[SAFETY] ",
            "access": "[ACCESS] ",
            "property": "[PROPERTY] ",
            "carded": "[CARDED] ",
        }
        prefix = category_hints.get(category, "")
        note_with_hint = (
            f"{prefix}{note}"
            if prefix and prefix.strip("[] ").lower() not in note.lower()
            else note
        )

        async def do_save():
            async with ParcelTrackingDB() as db:
                return await db.save_address_note(address, note_with_hint, driver_name)

        success = run_async(do_save())

        if success:
            return jsonify({
                "success": True,
                "message": "Note saved successfully",
                "note": {
                    "note": note_with_hint,
                    "category": category,
                    "driver_name": driver_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            })
        else:
            return jsonify({"success": False, "error": "Failed to save note"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/address-notes/dismiss", methods=["POST"])
@login_required
def dismiss_address_note():
    """Dismiss an address note that is no longer accurate (drivers & admins)"""
    try:
        data = request.get_json()
        address = (data.get("address") or "").strip()
        note_id = (data.get("note_id") or "").strip()

        if not address or not note_id:
            return jsonify({"success": False, "error": "Address and note_id are required"}), 400

        user = session.get("user", {})
        dismissed_by = user.get("display_name") or user.get("username", "unknown")

        async def do_dismiss():
            async with ParcelTrackingDB() as db:
                return await db.dismiss_address_note(address, note_id, dismissed_by)

        success = run_async(do_dismiss())

        if success:
            return jsonify({"success": True, "message": "Note dismissed successfully"})
        else:
            return jsonify({"success": False, "error": "Note not found"}), 404

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
