"""
Parcels Blueprint - Parcel Operations and Tracking

Handles parcel registration, tracking, OCR scanning, and image analysis.
Includes both authenticated and public endpoints.
"""
from flask import Blueprint, render_template, request, redirect, flash, session, jsonify
from datetime import datetime, timezone
import base64
import uuid
import re
import os

from src.interfaces.web.middleware import login_required
from parcel_tracking_db import ParcelTrackingDB
from utils.async_helpers import run_async
from src.infrastructure.agents import parcel_intake_agent
from src.domain.services import ParcelService

parcels_bp = Blueprint('parcels', __name__)


@parcels_bp.route("/parcels")
@login_required
def list_parcels():
    """
    View all parcels with optional filters and pagination
    
    Query Parameters:
        status (str): Filter by current status
        state (str): Filter by destination state  
        page (int): Page number for pagination
        
    Access: All logged-in users
    """
    try:
        # Get filters and pagination from query parameters
        status_filter = request.args.get("status", None)
        state_filter = request.args.get("state", None)
        page = int(request.args.get("page", 1))
        per_page = 25

        async def get_all():
            async with ParcelTrackingDB() as db:
                all_parcels = await db.get_all_parcels()

                # Apply status filter if provided
                if status_filter:
                    all_parcels = [p for p in all_parcels if p.get("current_status") == status_filter]

                # Apply state filter if provided
                if state_filter:
                    all_parcels = [p for p in all_parcels if p.get("destination_state") == state_filter]

                # Calculate pagination
                total_parcels = len(all_parcels)
                total_pages = (total_parcels + per_page - 1) // per_page
                start_idx = (page - 1) * per_page
                end_idx = start_idx + per_page
                paginated_parcels = all_parcels[start_idx:end_idx]

                return {
                    "parcels": paginated_parcels,
                    "total": total_parcels,
                    "page": page,
                    "total_pages": total_pages,
                    "per_page": per_page,
                }

        result = run_async(get_all())

        # Get unique states for filter dropdown (only valid Australian states)
        async def get_states():
            valid_states = ["NSW", "VIC", "QLD", "SA", "WA", "ACT", "TAS", "NT"]
            async with ParcelTrackingDB() as db:
                all_parcels = await db.get_all_parcels()
                states = sorted(
                    set(
                        p.get("destination_state") 
                        for p in all_parcels 
                        if p.get("destination_state") in valid_states
                    )
                )
                return states

        available_states = run_async(get_states())

        return render_template(
            "all_parcels.html",
            parcels=result["parcels"],
            status_filter=status_filter,
            state_filter=state_filter,
            available_states=available_states,
            page=result["page"],
            total_pages=result["total_pages"],
            total_parcels=result["total"],
            per_page=result["per_page"],
        )
    except Exception as e:
        flash(f"Error loading parcels: {str(e)}", "danger")
        return render_template(
            "all_parcels.html",
            parcels=[],
            status_filter=None,
            state_filter=None,
            available_states=[],
            page=1,
            total_pages=0,
            total_parcels=0,
            per_page=25,
        )


@parcels_bp.route("/parcels/register", methods=["GET", "POST"])
def register_parcel():
    """
    Register new parcel with Azure AI Parcel Intake Agent validation
    
    Public access - no authentication required for customer parcel registration.
    
    Features:
    - AI-powered validation and recommendations
    - Address verification
    - Lodgement photo upload
    - Service type suggestions
    """
    if request.method == "POST":
        try:
            # Get form data
            sender_name = request.form.get("sender_name")
            sender_address = request.form.get("sender_address")
            sender_phone = request.form.get("sender_phone")
            recipient_name = request.form.get("recipient_name")
            recipient_address = request.form.get("recipient_address")
            recipient_phone = request.form.get("recipient_phone")

            # Extract postcode from recipient address (Australian 4-digit postcodes)
            destination_postcode = None
            if recipient_address:
                postcode_match = re.search(r"\b(\d{4})\b", recipient_address)
                if postcode_match:
                    destination_postcode = postcode_match.group(1)

            service_type = request.form.get("service_type", "standard")
            weight = float(request.form.get("weight", 0))
            dimensions = request.form.get("dimensions", "")
            declared_value = float(request.form.get("declared_value", 0))
            special_instructions = request.form.get("special_instructions", "")

            # Handle lodgement photo upload
            lodgement_photo_base64 = None
            if "lodgement_photo" in request.files:
                photo_file = request.files["lodgement_photo"]
                if photo_file and photo_file.filename:
                    photo_bytes = photo_file.read()
                    lodgement_photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
                    print(f"📸 Lodgement photo captured ({len(lodgement_photo_base64)} bytes)")

            # Determine destination state from postcode
            destination_state = ParcelService.get_state_from_postcode(destination_postcode) if destination_postcode else "UNKNOWN"

            # Generate tracking number and barcode
            tracking_number = f"DT{uuid.uuid4().hex[:10].upper()}"
            barcode = f"BC{uuid.uuid4().hex[:12].upper()}"

            # Validate with Azure AI Parcel Intake Agent
            parcel_data = {
                "tracking_number": tracking_number,
                "sender_name": sender_name,
                "sender_address": sender_address,
                "recipient_name": recipient_name,
                "recipient_address": recipient_address,
                "destination_postcode": destination_postcode,
                "destination_state": destination_state,
                "service_type": service_type,
                "weight_kg": weight,
                "dimensions": dimensions,
                "declared_value": declared_value,
                "special_instructions": special_instructions,
            }

            async def validate_and_register():
                # Call Azure AI Parcel Intake Agent for validation
                validation_result = await parcel_intake_agent(parcel_data)

                # Log AI validation result
                if validation_result.get("success"):
                    print("[AI] Parcel Intake validation completed")
                    if "content" in validation_result:
                        print(f"[AI] Validation feedback: {validation_result['content'][:200]}...")

                # Register parcel in database (proceed even if AI validation fails)
                async with ParcelTrackingDB() as db:
                    result = await db.register_parcel(
                        barcode=barcode,
                        sender_name=sender_name,
                        sender_address=sender_address,
                        sender_phone=sender_phone,
                        recipient_name=recipient_name,
                        recipient_address=recipient_address,
                        recipient_phone=recipient_phone,
                        destination_postcode=destination_postcode,
                        destination_state=destination_state,
                        service_type=service_type.lower(),
                        weight=weight,
                        dimensions=dimensions,
                        declared_value=declared_value,
                        special_instructions=special_instructions,
                        store_location=session.get("store_location", "WebPortal"),
                    )

                    # Store lodgement photo if provided
                    if lodgement_photo_base64:
                        await db.store_lodgement_photo(
                            barcode=barcode,
                            photo_base64=lodgement_photo_base64,
                            uploaded_by=session.get("username", "customer"),
                        )
                        print(f"✅ Lodgement photo stored for {barcode}")

                    return result["tracking_number"], validation_result

            final_tracking, validation = run_async(validate_and_register())
            flash(f"Parcel registered successfully! Tracking: {final_tracking}", "success")

            # Show AI validation insights
            if validation.get("success") and validation.get("content"):
                ai_response = validation.get("content", "")

                # Parse AI recommendations
                if "recommend" in ai_response.lower() or "suggest" in ai_response.lower():
                    flash(f"💡 AI Recommendation: {ai_response[:200]}", "info")

                # Parse warnings
                if "warning" in ai_response.lower() or "issue" in ai_response.lower():
                    flash(f"⚠️ AI Alert: {ai_response[:200]}", "warning")

                # Store validation result in session for display on tracking page
                session["last_ai_validation"] = {
                    "tracking_number": final_tracking,
                    "feedback": ai_response,
                    "timestamp": datetime.now().isoformat(),
                }

            # Redirect to public tracking
            return redirect(f"/track?tracking={final_tracking}")

        except Exception as e:
            flash(f"Error registering parcel: {str(e)}", "danger")

    return render_template("register_parcel.html")


@parcels_bp.route("/parcels/<tracking_number>")
@login_required
def track_specific_parcel(tracking_number: str):
    """
    Track specific parcel (authenticated view)
    
    Access: All logged-in users
    """
    parcel = None
    try:
        async def get_parcel():
            async with ParcelTrackingDB() as db:
                return await db.get_parcel_by_tracking_number(tracking_number)

        parcel = run_async(get_parcel())
        if not parcel:
            flash(f"Parcel not found: {tracking_number}", "warning")
    except Exception as e:
        flash(f"Error tracking parcel: {str(e)}", "danger")

    return render_template("track_parcel.html", parcel=parcel, tracking_number=tracking_number)


@parcels_bp.route("/track", methods=["GET", "POST"])
def track_parcel_public():
    """
    Public parcel tracking page - NO LOGIN REQUIRED
    
    Supports multiple tracking numbers (comma or semicolon separated).
    Shows full event history, delivery map (if out for delivery), and photos.
    """
    if request.method == "GET":
        return render_template("track_parcel_public.html", tracking_results=None)

    tracking_input = request.form.get("tracking_number", "").strip()

    if not tracking_input:
        flash("Please enter at least one tracking number", "warning")
        return render_template("track_parcel_public.html", tracking_results=None)

    # Parse multiple barcodes separated by comma or semicolon
    barcodes = [b.strip() for b in re.split(r"[,;]", tracking_input) if b.strip()]

    if not barcodes:
        flash("Please enter valid tracking numbers", "warning")
        return render_template("track_parcel_public.html", tracking_results=None)

    try:
        async def get_tracking_info(tracking_number):
            async with ParcelTrackingDB() as db:
                # Try to get parcel by barcode first
                parcel = await db.get_parcel_by_barcode(tracking_number)

                # If not found, try by tracking number
                if not parcel:
                    parcel = await db.get_parcel_by_tracking_number(tracking_number)

                if not parcel:
                    return None

                # Use the parcel's barcode for all subsequent lookups
                barcode = parcel.get("barcode")

                # Get tracking events
                events = await db.get_parcel_tracking_history(barcode)

                # Check if out for delivery
                manifest = await db.get_manifest_for_parcel(barcode)
                is_out_for_delivery = parcel.get("current_status") == "Out for Delivery"

                # If in active manifest with pending status, consider it out for delivery
                if manifest and manifest.get("status") == "active":
                    for item in manifest.get("items", []):
                        if item.get("barcode") == barcode and item.get("status") != "Delivered":
                            is_out_for_delivery = True
                            break

                # Set display status
                display_status = parcel.get("current_status")
                if is_out_for_delivery and display_status not in ["Delivered", "Out for Delivery"]:
                    display_status = "Out for Delivery"

                # Set last_updated to current time if None
                last_updated = parcel.get("last_updated")
                if not last_updated:
                    last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

                # Set expected delivery to today if in active manifest
                expected_delivery = parcel.get("expected_delivery_date")
                if is_out_for_delivery and manifest:
                    expected_delivery = datetime.now().strftime("%Y-%m-%d")

                return {
                    "barcode": parcel.get("barcode"),
                    "current_status": display_status,
                    "recipient_name": parcel.get("recipient_name"),
                    "recipient_phone": parcel.get("recipient_phone"),
                    "recipient_address": parcel.get("recipient_address"),
                    "sender_name": parcel.get("sender_name"),
                    "sender_phone": parcel.get("sender_phone"),
                    "sender_address": parcel.get("sender_address"),
                    "service_type": parcel.get("service_type", "standard"),
                    "weight": parcel.get("weight", 0),
                    "dimensions": parcel.get("dimensions", ""),
                    "declared_value": parcel.get("declared_value", 0),
                    "special_instructions": parcel.get("special_instructions", ""),
                    "expected_delivery": expected_delivery,
                    "last_updated": last_updated,
                    "events": events[::-1] if events else [],  # Reverse to show newest first
                    "lodgement_photos": parcel.get("lodgement_photos", []),
                    "delivery_photos": parcel.get("delivery_photos", []),
                }

        # Get tracking info for all barcodes
        async def get_all_tracking():
            results = []
            not_found = []
            for barcode in barcodes:
                data = await get_tracking_info(barcode)
                if data:
                    results.append(data)
                else:
                    not_found.append(barcode)
            return results, not_found

        tracking_results, not_found = run_async(get_all_tracking())

        # Show warnings for not found barcodes
        if not_found:
            flash(f'Tracking number(s) not found: {", ".join(not_found)}', "warning")

        if not tracking_results:
            flash("No tracking information found for the provided barcode(s)", "danger")
            return render_template("track_parcel_public.html", tracking_results=None)

        return render_template("track_parcel_public.html", tracking_results=tracking_results)

    except Exception as e:
        flash(f"Error retrieving tracking information: {str(e)}", "danger")
        return render_template("track_parcel_public.html", tracking_results=None)


@parcels_bp.route("/camera-scanner")
def camera_scanner():
    """
    Camera scanner page for OCR and barcode detection
    
    Public access for easy parcel lodgement photo capture.
    """
    return render_template("camera_scanner.html")


@parcels_bp.route("/api/analyze-image", methods=["POST"])
def analyze_image():
    """
    Analyze uploaded image with Azure AI Vision OCR
    
    Extracts text from parcel labels including:
    - Tracking barcodes
    - Recipient names  
    - Addresses and postcodes
    
    Returns:
        JSON with extracted fields and confidence scores
    """
    try:
        if "image" not in request.files:
            return jsonify({"error": "No image provided"}), 400

        image_file = request.files["image"]
        if image_file.filename == "":
            return jsonify({"error": "No image selected"}), 400

        # Read image data
        image_data = image_file.read()

        # Call Azure AI Vision OCR
        from azure.ai.vision.imageanalysis import ImageAnalysisClient
        from azure.ai.vision.imageanalysis.models import VisualFeatures
        from azure.identity import DefaultAzureCredential

        endpoint = os.getenv("AZURE_VISION_ENDPOINT")

        if not endpoint:
            return jsonify({
                "error": "Azure Vision not configured",
                "full_text": "Please set AZURE_VISION_ENDPOINT environment variable",
            }), 500

        # Create client using DefaultAzureCredential (Managed Identity)
        credential = DefaultAzureCredential()
        client = ImageAnalysisClient(endpoint=endpoint, credential=credential)

        # Analyze image
        result = client.analyze(image_data=image_data, visual_features=[VisualFeatures.READ])

        # Extract all text with position information
        full_text = ""
        text_lines = []

        if result.read and result.read.blocks:
            for block in result.read.blocks:
                for line in block.lines:
                    text_lines.append(line.text)
                    full_text += line.text + "\n"

        # TODO: Implement smart field extraction (barcode, name, address, postcode)
        # For now, return raw text
        return jsonify({
            "success": True,
            "full_text": full_text,
            "lines": text_lines,
            "barcode": None,  # TODO: Extract barcode
            "recipient_name": None,  # TODO: Extract name
            "address": None,  # TODO: Extract address
            "postcode": None,  # TODO: Extract postcode
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@parcels_bp.route("/api/track")
def api_track_parcel():
    """
    API: Track parcel by tracking number
    
    Query Parameters:
        tracking (str): Tracking number to lookup
        
    Returns:
        JSON with parcel status and event history
    """
    tracking_number = request.args.get("tracking")
    
    if not tracking_number:
        return jsonify({"error": "Tracking number required"}), 400
    
    try:
        async def get_tracking():
            async with ParcelTrackingDB() as db:
                parcel = await db.get_parcel_by_tracking_number(tracking_number)
                if not parcel:
                    return None
                
                events = await db.get_parcel_tracking_history(parcel.get("barcode"))
                
                return {
                    "tracking_number": tracking_number,
                    "status": parcel.get("current_status"),
                    "location": parcel.get("current_location"),
                    "events": events[::-1] if events else []
                }
        
        result = run_async(get_tracking())
        
        if not result:
            return jsonify({"error": "Parcel not found"}), 404
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
