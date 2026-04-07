"""
Chatbot Blueprint - Customer Service AI and Fraud Reporting

Handles customer service chatbot (authenticated and public),
voice interactions, SSE streaming, and fraud report submission.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, Response, stream_with_context
from datetime import datetime, timezone
import re
from typing import Any, Dict, Optional

from src.interfaces.web.middleware import login_required
from parcel_tracking_db import ParcelTrackingDB
from utils.async_helpers import run_async
from user_manager import UserManager
from src.infrastructure.agents import analyze_with_fraud_agent

chatbot_bp = Blueprint('chatbot', __name__)


async def call_customer_service_agent(
    query: str,
    tracking_number: str = None,
    thread_id: str = None,
    is_public: bool = False,
    customer_name: str = "Customer",
    additional_context: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Call Azure AI Customer Service Agent
    
    Args:
        query: User's question
        tracking_number: Optional tracking number for context
        thread_id: Optional conversation thread ID for persistence
        is_public: True for public chat widget, False for internal CS
        customer_name: Customer name for personalization
        additional_context: Any additional context to pass to agent
        
    Returns:
        Agent response dictionary
    """
    from src.infrastructure.agents import customer_service_agent
    
    # Build agent request
    context = {
        "customer_name": customer_name,
        "issue_type": "inquiry",
        "details": query,
        "public_mode": is_public,
    }
    
    # Add tracking number if provided
    if tracking_number:
        context["tracking_number"] = tracking_number
    
    # Merge additional context
    if additional_context:
        context.update(additional_context)
    
    # Call agent (it handles tracking lookup via tools)
    return await customer_service_agent(context, thread_id=thread_id)


@chatbot_bp.route("/customer_service/chatbot")
@login_required
def customer_service_chatbot():
    """
    Customer Service AI Chatbot Interface - Internal Use Only
    
    Access: Customer service and admin roles only
    """
    user = session.get("user")
    if not user or user.get("role") not in [UserManager.ROLE_CUSTOMER_SERVICE, UserManager.ROLE_ADMIN]:
        flash("Access denied. Customer service role required.", "danger")
        return redirect(url_for("admin.dashboard"))

    return render_template("customer_service_chatbot.html")


@chatbot_bp.route("/chat")
def public_chat():
    """
    Public chat page - No login required
    
    Customer-facing chatbot widget for tracking and support.
    """
    return render_template("public_chat.html")


@chatbot_bp.route("/api/chatbot", methods=["POST"])
@chatbot_bp.route("/api/chatbot/query", methods=["POST"])
@login_required
def chatbot_query():
    """
    Process chatbot query - Internal customer service use
    
    Features:
    - Conversation thread persistence
    - Photo attachment (delivery/lodgement)
    - Tracking number extraction
    
    Access: Customer service and admin roles only
    """
    user = session.get("user")
    if not user or user.get("role") not in [UserManager.ROLE_CUSTOMER_SERVICE, UserManager.ROLE_ADMIN]:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json()
    query = data.get("query", "")
    tracking_number = data.get("tracking_number")
    thread_id = data.get("thread_id")

    if not query:
        return jsonify({"error": "Query is required"}), 400

    async def process():
        response = await call_customer_service_agent(
            query=query,
            tracking_number=tracking_number,
            thread_id=thread_id,
            is_public=False,
            customer_name=user.get("full_name", user.get("username", "Agent")),
        )
        return response

    try:
        result = run_async(process())

        if isinstance(result, dict) and not result.get("success", True):
            error_msg = result.get("error", "Unknown agent error")
            print(f"❌ Customer service agent error: {error_msg}")
            return jsonify({
                "response": "I was unable to retrieve that information from our database at this time. Please try again or contact support directly.",
                "error": error_msg,
                "agent_error": True,
            }), 503

        response_text = _extract_response_text(result)
        if not response_text or response_text == "No response from assistant":
            return jsonify({
                "response": "I was unable to retrieve a response from the agent. Please try again.",
                "agent_error": True,
            }), 503

        # Attach photo data when agent response references them
        delivery_photos, lodgement_photos = _extract_photos_if_mentioned(response_text, query, tracking_number)

        response_data = {"response": response_text}
        if isinstance(result, dict) and result.get("thread_id"):
            response_data["thread_id"] = result["thread_id"]
        if isinstance(result, dict) and result.get("tools_used"):
            response_data["tools_used"] = result["tools_used"]
        if delivery_photos:
            response_data["delivery_photos"] = delivery_photos
        if lodgement_photos:
            response_data["lodgement_photos"] = lodgement_photos

        return jsonify(response_data), 200
    except Exception as e:
        print(f"❌ chatbot_query exception: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e), "agent_error": True}), 500


@chatbot_bp.route("/api/chatbot/voice", methods=["POST"])
@login_required
def chatbot_voice():
    """
    Process voice query (speech-to-text + chatbot + text-to-speech)
    
    Access: Customer service and admin roles only
    """
    # TODO: Implement speech recognition + chatbot + TTS pipeline
    return jsonify({
        "error": "Voice processing not yet implemented",
        "supported": False
    }), 501


@chatbot_bp.route("/api/chatbot/stream")
@login_required
def chatbot_stream():
    """
    Server-Sent Events (SSE) streaming for real-time chatbot responses
    
    Access: Customer service and admin roles only
    """
    user = session.get("user")
    if not user or user.get("role") not in [UserManager.ROLE_CUSTOMER_SERVICE, UserManager.ROLE_ADMIN]:
        return jsonify({"error": "Access denied"}), 403

    # TODO: Implement SSE streaming with Azure AI Agent
    def generate():
        yield "data: {\"type\": \"message\", \"content\": \"Streaming not yet implemented\"}\n\n"
    
    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@chatbot_bp.route("/api/chatbot/track/<tracking_number>")
@login_required
def chatbot_track(tracking_number):
    """Direct parcel tracking lookup for the chatbot UI"""
    user = session.get("user")
    if not user or user.get("role") not in [UserManager.ROLE_CUSTOMER_SERVICE, UserManager.ROLE_ADMIN]:
        return jsonify({"error": "Access denied"}), 403

    async def lookup():
        async with ParcelTrackingDB() as db:
            parcel = await db.get_parcel_by_tracking_number(tracking_number)
            if not parcel:
                parcel = await db.get_parcel_by_barcode(tracking_number)
            return parcel

    try:
        parcel = run_async(lookup())
        if not parcel:
            return jsonify({"error": f"Parcel {tracking_number} not found"}), 404

        status = parcel.get("current_status", "Unknown")
        location = parcel.get("current_location", "Unknown")
        recipient = parcel.get("recipient_name", "Unknown")
        response_text = (
            f"Parcel **{tracking_number}** — Status: **{status}** | "
            f"Location: {location} | Recipient: {recipient}"
        )
        return jsonify({"response": response_text, "parcel": parcel}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chatbot_bp.route("/api/chatbot/location/<tracking_number>")
@login_required
def chatbot_location(tracking_number):
    """Direct parcel location lookup for the chatbot UI"""
    user = session.get("user")
    if not user or user.get("role") not in [UserManager.ROLE_CUSTOMER_SERVICE, UserManager.ROLE_ADMIN]:
        return jsonify({"error": "Access denied"}), 403

    async def lookup():
        async with ParcelTrackingDB() as db:
            parcel = await db.get_parcel_by_tracking_number(tracking_number)
            if not parcel:
                parcel = await db.get_parcel_by_barcode(tracking_number)
            return parcel

    try:
        parcel = run_async(lookup())
        if not parcel:
            return jsonify({"error": f"Parcel {tracking_number} not found"}), 404

        location = parcel.get("current_location", "Unknown")
        status = parcel.get("current_status", "Unknown")
        eta = parcel.get("estimated_delivery", "Unknown")
        response_text = (
            f"Parcel **{tracking_number}** is currently at **{location}** "
            f"(Status: {status}). Estimated delivery: {eta}."
        )
        return jsonify({"response": response_text}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chatbot_bp.route("/api/public/chatbot", methods=["POST"])
def public_chatbot():
    """
    Public chatbot for all users - Limited access, no internal data
    
    Accessible to both anonymous and authenticated users.
    Provides basic tracking and support without exposing sensitive operations.
    """
    user = session.get("user")
    is_logged_in = user is not None

    data = request.get_json()
    query = data.get("query", "")
    tracking_number = data.get("tracking_number")
    thread_id = data.get("thread_id")

    if not query:
        return jsonify({"error": "Query is required"}), 400

    async def process():
        customer_name = user.get("username") if (is_logged_in and user) else "Guest"
        additional_context = {
            "user_role": user.get("role") if (is_logged_in and user) else "public",
            "is_authenticated": is_logged_in,
        }
        
        response = await call_customer_service_agent(
            query=query,
            tracking_number=tracking_number,
            thread_id=thread_id,
            is_public=True,
            customer_name=customer_name,
            additional_context=additional_context,
        )
        return response

    try:
        result = run_async(process())

        if isinstance(result, dict) and not result.get("success", True):
            error_msg = result.get("error", "Unknown agent error")
            print(f"❌ Public chatbot agent error: {error_msg}")
            return jsonify({
                "response": "I was unable to retrieve that information right now. Please try again in a moment.",
                "error": error_msg,
                "agent_error": True,
            }), 503

        response_text = _extract_response_text(result)
        if not response_text or response_text == "No response from assistant":
            return jsonify({
                "response": "I was unable to retrieve a response. Please try again.",
                "agent_error": True,
            }), 503

        response_text = _clean_structured_markers(response_text)
        delivery_photos, _ = _extract_photos_if_mentioned(response_text, query, tracking_number)

        response_data = {"response": response_text}
        if isinstance(result, dict) and result.get("thread_id"):
            response_data["thread_id"] = result["thread_id"]
        if delivery_photos:
            response_data["delivery_photos"] = delivery_photos

        return jsonify(response_data), 200
    except Exception as e:
        print(f"❌ public_chatbot exception: {e}")
        import traceback; traceback.print_exc()
        return jsonify({
            "response": "I was unable to retrieve that information right now. Please try again.",
            "error": str(e),
            "agent_error": True,
        }), 503


@chatbot_bp.route("/api/public/chatbot/voice", methods=["POST"])
def public_chatbot_voice():
    """
    Public voice chatbot (speech-to-text + chatbot + text-to-speech)
    
    No authentication required.
    """
    # TODO: Implement public voice interface
    return jsonify({
        "error": "Voice processing not yet implemented",
        "supported": False
    }), 501


@chatbot_bp.route("/api/public/chatbot/stream")
def public_chatbot_stream():
    """
    Public SSE streaming for real-time chatbot responses
    
    No authentication required.
    """
    # TODO: Implement public SSE streaming
    def generate():
        yield "data: {\"type\": \"message\", \"content\": \"Streaming not yet implemented\"}\n\n"
    
    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@chatbot_bp.route("/fraud/report", methods=["GET", "POST"])
def report_fraud():
    """
    Report suspicious message - Publicly accessible with automated workflow
    
    Features:
    - Text and file upload support
    - AI-powered fraud analysis
    - Automatic workflow trigger for high-risk cases
    - Identity verification for critical threats
    """
    analysis = None
    workflow_result = None

    if request.method == "POST":
        try:
            message_content = request.form.get("message_content", "").strip()
            sender_info = request.form.get("sender_info", "unknown").strip()

            # Optional: Customer contact info for workflow
            reporter_name = request.form.get("reporter_name", "").strip()
            reporter_email = request.form.get("reporter_email", "").strip()
            reporter_phone = request.form.get("reporter_phone", "").strip()

            # Check if file was uploaded
            file_text = ""
            if "fraud_file" in request.files:
                file = request.files["fraud_file"]
                if file and file.filename:
                    filename = file.filename.lower()
                    try:
                        if filename.endswith((".txt", ".eml", ".msg")):
                            raw = file.read()
                            file_text = raw.decode("utf-8", errors="replace")
                        else:
                            # For images and unsupported types, include filename as context
                            file_text = f"[Uploaded file: {file.filename}]"
                    except Exception:
                        file_text = f"[Uploaded file: {file.filename}]"

            # Combine manual text and file text
            combined_message = message_content or file_text

            if not combined_message:
                flash("Please provide either a message or upload a file to analyze.", "warning")
                return render_template("report_fraud.html", analysis=None)

            # Analyze with AI agent
            analysis = run_async(analyze_with_fraud_agent(combined_message, sender_info))

            # Trigger Fraud → Customer Service Workflow if high risk
            if analysis.confidence_score >= 0.7 and reporter_email:
                from workflows.fraud_to_customer_service import fraud_detection_to_customer_service_workflow

                workflow_result = run_async(
                    fraud_detection_to_customer_service_workflow(
                        message_content=combined_message,
                        sender_info={
                            "sender": sender_info,
                            "message_type": "email" if "@" in sender_info else "sms",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                        customer_info={
                            "name": reporter_name or "Customer",
                            "email": reporter_email,
                            "phone": reporter_phone,
                        },
                        trigger_type="customer_report",
                    )
                )

                flash("High-risk fraud detected! Customer protection workflow activated.", "warning")

            # Store in database
            async def store_report():
                async with ParcelTrackingDB() as db:
                    ai_data = {
                        "threat_level": analysis.threat_level.value,
                        "fraud_category": analysis.fraud_category.value,
                        "confidence_score": analysis.confidence_score,
                        "recommended_actions": analysis.recommended_actions,
                        "alert_security_team": analysis.alert_security_team,
                        "related_patterns": analysis.related_patterns,
                    }
                    return await db.store_suspicious_message(
                        message_content=combined_message,
                        sender_info=sender_info,
                        risk_indicators=analysis.risk_indicators,
                        ai_analysis=ai_data,
                    )

            run_async(store_report())

        except Exception as e:
            flash(f"Error analyzing message: {str(e)}", "danger")

    return render_template("report_fraud.html", analysis=analysis, workflow_result=workflow_result)


@chatbot_bp.route("/api/fraud-analysis", methods=["POST"])
def api_fraud_analysis():
    """
    API: Analyze text for fraud patterns
    
    Request Body:
        message (str): Message content to analyze
        sender (str, optional): Sender information
        
    Returns:
        JSON with fraud analysis results
    """
    data = request.get_json()
    message = data.get("message", "")
    sender = data.get("sender", "unknown")

    if not message:
        return jsonify({"error": "Message required"}), 400

    try:
        analysis = run_async(analyze_with_fraud_agent(message, sender))
        
        return jsonify({
            "threat_level": analysis.threat_level.value,
            "fraud_category": analysis.fraud_category.value,
            "confidence_score": analysis.confidence_score,
            "risk_indicators": analysis.risk_indicators,
            "recommended_actions": analysis.recommended_actions,
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Helper Functions
# ============================================================================

def _extract_response_text(result: Any) -> str:
    """Extract response text from nested Azure AI agent response formats"""
    if isinstance(result, dict):
        response_obj = result.get("response", "")
        if isinstance(response_obj, str):
            return response_obj
        elif isinstance(response_obj, dict):
            if response_obj.get("type") == "text" and response_obj.get("text"):
                if isinstance(response_obj["text"], dict):
                    return response_obj["text"].get("value", str(response_obj))
                else:
                    return str(response_obj["text"])
            elif response_obj.get("value"):
                return response_obj["value"]
            else:
                return str(response_obj)
        else:
            return str(response_obj) if response_obj else ""
    elif isinstance(result, str):
        return result
    
    # Fallback
    return str(result) if result else "I'm sorry, I wasn't able to process that request."


def _clean_structured_markers(text: str) -> str:
    """Remove structured markers from AI response for public display"""
    # Extract customer communication if present
    if "Customer Communication:" in text:
        match = re.search(
            r"\*\*Customer Communication:\*\*\s*(.+?)(?:\n\n\*\*|$)", 
            text, 
            re.DOTALL
        )
        if match:
            return match.group(1).strip()
    
    # Remove structured markers
    cleaned = re.sub(
        r"\s*,?\s*\[(?:Issue Type|Resolution Option|Customer Communication|Follow-up Required|Satisfaction Score):[^\]]*\]",
        "",
        text,
    )
    cleaned = re.sub(
        r"\[(?:Issue Type|Resolution Option|Customer Communication|Follow-up Required|Satisfaction Score):[^\]]*\],?\s*",
        "",
        cleaned,
    )
    
    return cleaned.strip(", ").strip()


def _extract_photos_if_mentioned(response_text: str, query: str, tracking_number: str = None) -> tuple:
    """
    Extract delivery/lodgement photos if mentioned in response
    
    Returns:
        Tuple of (delivery_photos, lodgement_photos)
    """
    delivery_photos = []
    lodgement_photos = []
    
    # Check if response OR query mentions photos/proof
    photo_keywords = ("photo", "delivery photo", "proof")
    response_mentions_photo = any(kw in response_text.lower() for kw in photo_keywords)
    query_mentions_photo = any(kw in query.lower() for kw in photo_keywords)
    if not response_mentions_photo and not query_mentions_photo:
        return delivery_photos, lodgement_photos
    
    # Extract tracking number from query or parameter
    tracking_pattern = r"\b(DTVIC\d+|DT\d+|[A-Z]{2}\d{5,}|[A-Z]{2}\d{8,}[A-Z]{2}|[A-Z]{2,4}\d{3,}[A-Z]{1,3}\d{3,})\b"
    
    tracking_num = None
    matches = re.findall(tracking_pattern, query, re.IGNORECASE)
    if matches:
        tracking_num = matches[0].upper()
    elif tracking_number:
        tracking_num = tracking_number.upper()
    else:
        # Try extracting from response
        response_matches = re.findall(tracking_pattern, response_text, re.IGNORECASE)
        if response_matches:
            tracking_num = response_matches[0].upper()
    
    if not tracking_num:
        return delivery_photos, lodgement_photos
    
    # Fetch photos from database
    try:
        async def get_photos():
            async with ParcelTrackingDB() as db:
                parcel = await db.get_parcel_by_tracking_number(tracking_num)
                if parcel:
                    return parcel.get("delivery_photos", []), parcel.get("lodgement_photos", [])
                return [], []
        
        delivery_photos, lodgement_photos = run_async(get_photos())
    except Exception as e:
        print(f"Error retrieving photos: {e}")
    
    return delivery_photos, lodgement_photos
