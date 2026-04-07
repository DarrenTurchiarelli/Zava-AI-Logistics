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


# ============================================================================
# OCR HELPER FUNCTIONS - Smart field extraction for parcel labels
# ============================================================================

# Australian state abbreviations
_AU_STATES = {
    "NSW": "NSW", "N.S.W.": "NSW", "N.S.W": "NSW", "NEW SOUTH WALES": "NSW",
    "VIC": "VIC", "V.I.C.": "VIC", "V.I.C": "VIC", "VICTORIA": "VIC",
    "QLD": "QLD", "Q.L.D.": "QLD", "Q.L.D": "QLD", "QUEENSLAND": "QLD",
    "SA": "SA", "S.A.": "SA", "S.A": "SA", "SOUTH AUSTRALIA": "SA",
    "WA": "WA", "W.A.": "WA", "W.A": "WA", "WESTERN AUSTRALIA": "WA",
    "TAS": "TAS", "T.A.S.": "TAS", "TASMANIA": "TAS",
    "NT": "NT", "N.T.": "NT", "N.T": "NT", "NORTHERN TERRITORY": "NT",
    "ACT": "ACT", "A.C.T.": "ACT", "A.C.T": "ACT", "AUSTRALIAN CAPITAL TERRITORY": "ACT",
}

_STATE_RE = re.compile(
    r"\b(NSW|VIC|QLD|SA|WA|TAS|NT|ACT|N\.?S\.?W\.?|V\.?I\.?C\.?|Q\.?L\.?D\.?|S\.?A\.?|W\.?A\.?|T\.?A\.?S\.?|N\.?T\.?|A\.?C\.?T\.?)\b",
    re.IGNORECASE,
)

_NOISE_PATTERNS = [
    r"Australia\s*Post", r"auspost", r"alia\s*Post",
    r"^SQUISH$", r"^Squish$", r"Squish\s*Me", r"^ME$",
    r"^PEERSIDE$", r"^Sendle$", r"^SENDLE$", r"^Aramex$", r"^ARAMEX$",
    r"^DHL$", r"^TNT$", r"^TOLL$", r"^FedEx$", r"^FEDEX$", r"^UPS$",
    r"Padded\s*Mailer", r"Pedded\s*Mailer", r"Padded\s*Mail", r"^Mailer$", r"^PM\d+$",
    r"TRACKING\s*AVAILABLE", r"IMPORTANT", r"Postage\s*n.t\s*paid",
    r"Pertoge\s*nel\s*paid", r"No\s*delivery\s*without", r"Affix\s*postage",
    r"Use.?\s*within\s*Austral", r"Uher\s*within", r"Uer\s*within",
    r"within\s*Austral", r"Australie\s*or\s*World", r"Australia\s*or\s*World",
    r"Recipient\s*mobile", r"fleetplent\s*mobile", r"or\s*email", r"@\s*email",
    r"Contact\s*[hn]ame", r"Company\s*name", r"Traditional\s*place",
    r"name\s*\(?if\s*known\)?", r"Street\s*address\s*o[fr]", r"PO\s*Box\s*number",
    r"Suburb\s*or\s*town", r"State,?\s*Postcode", r"Sign\s*here",
    r"Bilan\s*here", r"Sionhere", r"Signhere", r"^To:?$",
    r"^MA$", r"^MAT$", r"^FRIAL$", r"^ARTERIAL$",
    r"Aviation\s*Security", r"Dangerous\s*Goods", r"and\s*Dangerous",
    r"Declaration", r"Goods\s*Declaration", r"sender\s*acknowledges",
    r"carried\s*by\s*air", r"false\s*declaration", r"criminal\s*offence",
    r"cannot\s*be\s*carried", r"does\s*not\s*contain", r"other\s*than\s*those",
    r"which\s*Austral", r"is\s*permitted", r"erinin\s*any", r"dengerne\s*goods",
    r"Port\s*is\s*permitted", r"Post\s*is\s*permitted", r"Australin",
    r"MADE\s*WITH", r"MADE\s*HERE", r"made\s*with\s*recycled", r"recycled\s*material",
    r"^MADE$", r"^WITH$", r"^HERE$", r"^AT\s*LEAST$", r"AT\s*LEAST\s*\d+%",
    r"^RECY$", r"^CYCLED$", r"RECYCLED", r"^MATERIAL$", r"^MATERIALS$",
    r"^50%\.?$", r"^\d+%$",
    r"^POST$", r"^AUSTRALIA$", r"^AUST$", r"^AUSPOS$", r"^AUSTR$",
    r"^ALIA$", r"^RALIA$", r"^TRALIA$", r"^USTRALIA$",
    r"STARTRACK", r"Star\s*Track", r"^STAR$", r"^TRACK$",
    r"Express\s*Post", r"^EXPRESS$", r"Parcel\s*Post", r"^PARCEL$",
    r"eparcel", r"^eParcel$", r"MyPost", r"^MyPost$", r"Registered\s*Post", r"^REGISTERED$",
    r"YFX\s*\d+mm", r"^\d+\s*x\s*\d+mm$", r"^\d+mm$",
    r"^04\d{2}\s*\d{3}\s*\d{3}$", r"^04\d{8}$", r"04\d{2}\s*\d{3}\s*\d{3}",
    r"^\+?61\s*4", r"^\(0\d\)\s*\d{4}", r"^0\d\s*\d{4}\s*\d{4}$", r"^1[38]00\s*\d{3}\s*\d{3}$",
]
_NOISE_REGEX = [re.compile(p, re.IGNORECASE) for p in _NOISE_PATTERNS]


def _normalize_state(state_text):
    if not state_text:
        return ""
    cleaned = state_text.upper().replace(".", "").strip()
    return _AU_STATES.get(cleaned, cleaned)


def _split_suburb_state(text):
    text = text.strip().rstrip(".")
    m = _STATE_RE.search(text)
    if m:
        state = _normalize_state(m.group(1))
        suburb = text[: m.start()].strip().rstrip(",").rstrip(".").strip()
        return suburb, state
    return text, ""


def _is_noise_text(text):
    text = text.strip()
    if len(text) < 2:
        return True
    for pattern in _NOISE_REGEX:
        if pattern.search(text):
            return True
    if text.isupper() and len(text) > 15 and " " in text:
        return True
    return False


def _is_valid_recipient_name(text):
    text = text.strip()
    if len(text) < 3:
        return False
    if _is_noise_text(text):
        return False
    if re.search(r"australia|auspost|post\b", text, re.IGNORECASE):
        return False
    if text[0].isdigit():
        return False
    cleaned_upper = text.upper().replace(".", "").strip()
    if cleaned_upper in _AU_STATES or cleaned_upper in _AU_STATES.values():
        return False
    if re.match(r"^\d{4}$", text):
        return False
    form_labels = ["street", "address", "mobile", "email", "suburb", "postcode", "phone", "contact"]
    if any(w in text.lower() for w in form_labels):
        return False
    letters = sum(1 for c in text if c.isalpha())
    if letters < len(text) * 0.5:
        return False
    return True


def _is_phone_number(text):
    digits = re.sub(r"\s+", "", text.strip())
    if re.match(r"^04\d{8}$", digits):
        return True
    if re.match(r"^0[2-9]\d{8}$", digits):
        return True
    if digits.startswith("+61") or digits.startswith("61"):
        return True
    return False


def _is_street_address(text):
    return bool(re.match(r"^(?:\d+|unit|apt|apartment|level|lot|shop|suite|floor)\s+", text, re.IGNORECASE))


def _get_state_from_postcode(postcode):
    try:
        pc = int(postcode)
        if 1000 <= pc <= 2599 or 2619 <= pc <= 2899 or 2921 <= pc <= 2999:
            return "NSW"
        if 2600 <= pc <= 2618 or 2900 <= pc <= 2920:
            return "ACT"
        if 3000 <= pc <= 3999 or 8000 <= pc <= 8999:
            return "VIC"
        if 4000 <= pc <= 4999 or 9000 <= pc <= 9999:
            return "QLD"
        if 5000 <= pc <= 5799 or 5800 <= pc <= 5999:
            return "SA"
        if 6000 <= pc <= 6797 or 6800 <= pc <= 6999:
            return "WA"
        if 7000 <= pc <= 7799 or 7800 <= pc <= 7999:
            return "TAS"
        if 800 <= pc <= 999:
            return "NT"
        if 200 <= pc <= 299:
            return "ACT"
    except (ValueError, TypeError):
        pass
    return ""


def _extract_barcode(text_lines):
    for line in text_lines:
        line = line.strip()
        if re.match(r"^[A-Z]{2}\d{12}$", line):
            return line
        if re.match(r"^[A-Z]{2}\d{8}[A-Z]{2}$", line):
            return line
    return ""


def _extract_postcode_bottom_right(text_with_positions):
    if not text_with_positions:
        return ""
    max_x = max(item["x"] for item in text_with_positions)
    max_y = max(item["y"] for item in text_with_positions)
    bottom_right = [i for i in text_with_positions if i["x"] > max_x * 0.6 and i["y"] > max_y * 0.7]
    for item in (bottom_right or text_with_positions):
        m = re.search(r"\b(\d{4})\b", item["text"])
        if m:
            pc = m.group(1)
            if 200 <= int(pc) <= 9999:
                return pc
    return ""


def _detect_address_region(text_with_positions):
    if not text_with_positions:
        return None
    candidates = [i for i in text_with_positions if not _is_noise_text(i["text"])]
    if not candidates:
        return None
    indicators = []
    for item in candidates:
        text = item["text"]
        score = 0
        if re.match(r"^[A-Z][a-z]+(\s+[A-Z][a-z]+){0,2}$", text):
            score += 2
        if re.match(r"^\d+\s+", text):
            score += 3
        if re.search(r"\b(St|Street|Rd|Road|Ave|Avenue|Dr|Drive|Pl|Place|Ct|Court|Cres|Crescent|Lane|Ln|Way)\b", text, re.IGNORECASE):
            score += 3
        if re.match(r"^[A-Z][a-z]+$", text) and len(text) > 3:
            score += 1
        if _STATE_RE.search(text):
            score += 2
        if re.search(r"\b\d{4}\b", text):
            score += 2
        if score > 0:
            indicators.append({**item, "score": score})
    if not indicators:
        return None
    min_x = min(i["x"] for i in indicators)
    max_x = max(i["x"] for i in indicators)
    min_y = min(i["y"] for i in indicators)
    max_y = max(i["y"] for i in indicators)
    w = max_x - min_x
    h = max_y - min_y
    return {"min_x": min_x - w * 0.1, "max_x": max_x + w * 0.1,
            "min_y": min_y - h * 0.1, "max_y": max_y + h * 0.1,
            "indicators": indicators}


def _extract_address_from_region(text_with_positions, region=None):
    result = {"name": "", "street": "", "suburb": "", "state": "", "postcode": "", "full_address": ""}
    if not text_with_positions:
        return result

    all_items = sorted(text_with_positions, key=lambda x: (x["y"], x["x"]))
    clean_lines = [
        item["text"].strip()
        for item in all_items
        if item["text"].strip() and len(item["text"].strip()) > 1
        and not _is_noise_text(item["text"])
        and not _is_phone_number(item["text"])
    ]

    name_line = street_line = suburb_line = postcode_value = state_value = None

    for line in clean_lines:
        if line in (name_line, street_line, suburb_line):
            continue

        pc_match = re.search(r"\b(\d{4})\b", line)
        if pc_match and not postcode_value:
            pc = pc_match.group(1)
            pc_int = int(pc)
            if 200 <= pc_int <= 9999 and not (400 <= pc_int <= 499):
                postcode_value = pc
                suburb, state = _split_suburb_state(line)
                if state:
                    state_value = state
                    if suburb and not suburb_line:
                        suburb_line = suburb
                continue

        if not state_value:
            suburb, state = _split_suburb_state(line)
            if state:
                state_value = state
                if suburb:
                    suburb_line = suburb
                continue

        if _is_street_address(line) and not street_line:
            if re.search(r"[A-Za-z]{2,}", line):
                street_line = line
                continue

        if not suburb_line and street_line:
            if line.isupper() and line.isalpha() and 3 <= len(line) <= 25:
                suburb_line = line
                continue

        if not name_line and not _is_street_address(line):
            if _is_valid_recipient_name(line):
                if suburb_line and line.upper() == suburb_line.upper():
                    continue
                name_line = line
                continue

    if postcode_value and not state_value:
        state_value = _get_state_from_postcode(postcode_value)

    result["name"] = name_line or ""
    result["street"] = street_line or ""
    result["suburb"] = suburb_line.title() if suburb_line else ""
    result["state"] = state_value or ""
    result["postcode"] = postcode_value or ""

    parts = []
    if result["street"]:
        parts.append(result["street"])
    suburb_parts = []
    if result["suburb"]:
        suburb_parts.append(result["suburb"])
    if result["state"]:
        suburb_parts.append(result["state"])
    if result["postcode"]:
        suburb_parts.append(result["postcode"])
    if suburb_parts:
        parts.append(" ".join(suburb_parts))
    result["full_address"] = ", ".join(parts)
    return result


def _extract_address_fallback(text_lines, text_with_positions=None):
    address_parts = []
    for i, line in enumerate(text_lines):
        if any(w in line.lower() for w in ["street", "st", "road", "rd", "avenue", "ave", "lane", "drive", "nsw", "vic", "qld", "sa", "wa", "tas", "nt", "act"]):
            address_parts.append(line)
            if i + 1 < len(text_lines):
                address_parts.append(text_lines[i + 1])
                if i + 2 < len(text_lines) and re.search(r"\d{4}", text_lines[i + 2]):
                    address_parts.append(text_lines[i + 2])
            break
    return ", ".join(address_parts) if address_parts else ""


def _extract_recipient_name_fallback(text_lines):
    for i, line in enumerate(text_lines):
        if line.lower().startswith("to:") or line.lower().startswith("recipient:"):
            if i + 1 < len(text_lines):
                return text_lines[i + 1].strip()
        if not re.match(r"^[A-Z]{2}\d", line) and len(line.split()) >= 2:
            return line.strip()
    return text_lines[0] if text_lines else ""


# ============================================================================


@parcels_bp.route("/api/analyze-image", methods=["POST"])
def analyze_image():
    """
    Analyze uploaded image with Azure AI Vision OCR

    Extracts text from parcel labels including:
    - Tracking barcodes
    - Recipient names
    - Addresses, suburb, state, and postcodes
    """
    try:
        if "image" not in request.files:
            return jsonify({"error": "No image provided"}), 400

        image_file = request.files["image"]
        if image_file.filename == "":
            return jsonify({"error": "No image selected"}), 400

        image_data = image_file.read()

        from azure.ai.vision.imageanalysis import ImageAnalysisClient
        from azure.ai.vision.imageanalysis.models import VisualFeatures
        from azure.identity import DefaultAzureCredential

        endpoint = os.getenv("AZURE_VISION_ENDPOINT")

        if not endpoint:
            return jsonify({
                "error": "Azure Vision not configured",
                "full_text": "Please set AZURE_VISION_ENDPOINT environment variable",
            }), 500

        credential = DefaultAzureCredential()
        client = ImageAnalysisClient(endpoint=endpoint, credential=credential)

        result = client.analyze(image_data=image_data, visual_features=[VisualFeatures.READ])

        full_text = ""
        text_lines = []
        text_with_positions = []

        if result.read and result.read.blocks:
            for block in result.read.blocks:
                for line in block.lines:
                    text_lines.append(line.text)
                    full_text += line.text + "\n"
                    if hasattr(line, "bounding_polygon") and line.bounding_polygon:
                        points = line.bounding_polygon
                        if len(points) >= 4:
                            avg_x = sum(p.x for p in points) / len(points)
                            avg_y = sum(p.y for p in points) / len(points)
                            text_with_positions.append({
                                "text": line.text,
                                "x": avg_x,
                                "y": avg_y,
                                "points": [(p.x, p.y) for p in points],
                            })

        barcode = _extract_barcode(text_lines)

        address_region = _detect_address_region(text_with_positions)
        address_data = _extract_address_from_region(text_with_positions, address_region)

        recipient_name = address_data.get("name", "")
        address = address_data.get("full_address", "")
        postcode = address_data.get("postcode", "")

        if not postcode:
            postcode = _extract_postcode_bottom_right(text_with_positions)
        if not address:
            address = _extract_address_fallback(text_lines, text_with_positions)
        if not recipient_name:
            recipient_name = _extract_recipient_name_fallback(text_lines)

        filtered_lines = [line for line in text_lines if not _is_noise_text(line)]
        filtered_text = "\n".join(filtered_lines) if filtered_lines else full_text.strip()

        return jsonify({
            "success": True,
            "full_text": filtered_text,
            "raw_text": full_text.strip(),
            "text_lines": text_lines,
            "filtered_lines": filtered_lines,
            "barcode": barcode,
            "address": address,
            "recipient_name": recipient_name,
            "postcode": postcode,
            "state": address_data.get("state", ""),
            "suburb": address_data.get("suburb", ""),
            "street": address_data.get("street", ""),
            "address_region_detected": address_region is not None,
        }), 200

    except ImportError:
        return jsonify({
            "error": "Azure AI Vision SDK not installed",
            "full_text": "Please install: pip install azure-ai-vision-imageanalysis",
        }), 500
    except Exception as e:
        return jsonify({"error": str(e), "full_text": f"Error: {str(e)}"}), 500


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
