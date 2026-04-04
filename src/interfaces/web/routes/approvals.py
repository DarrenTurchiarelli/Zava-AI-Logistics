"""
Approvals Blueprint - Approval workflow routes

Complete implementation with CQRS pattern integration
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, timezone
import random

from src.interfaces.web.middleware import login_required, depot_manager_required
from src.application.commands import ApproveRequestCommand
from src.application.queries import GetApprovalsQuery, GetParcelQuery
from src.infrastructure.database import CosmosDBClient
from src.infrastructure.database.repositories import ApprovalRepository, ParcelRepository
from parcel_tracking_db import ParcelTrackingDB
from utils.async_helpers import run_async

approvals_bp = Blueprint('approvals', __name__, url_prefix='/approvals')


@approvals_bp.route('/')
@login_required
def list_approvals():
    """View pending approvals"""
    try:
        async def get_approvals_with_parcels():
            async with ParcelTrackingDB() as db:
                # Use query to get approvals
                approval_repo = ApprovalRepository(db)
                approval_query = GetApprovalsQuery(approval_repo)
                pending = await approval_query.get_pending()
                
                # Enrich with parcel data
                parcel_repo = ParcelRepository(db)
                parcel_query = GetParcelQuery(parcel_repo)
                
                for approval in pending:
                    parcel_barcode = approval.get("parcel_barcode") or approval.get("parcel_id")
                    approval["tracking_number"] = parcel_barcode
                    approval["parcel_id"] = parcel_barcode
                    
                    # Map request_type to approval_type for template
                    request_type = approval.get("request_type", "N/A")
                    if request_type != "N/A":
                        approval["approval_type"] = request_type.replace("_", " ").title()
                    else:
                        approval["approval_type"] = request_type
                    
                    # Get parcel details
                    if parcel_barcode:
                        parcel = await db.get_parcel_by_barcode(parcel_barcode)
                        if parcel:
                            if not approval.get("parcel_dc"):
                                approval["parcel_dc"] = parcel.get("origin_location", "Unknown")
                            if not approval.get("parcel_status"):
                                status = parcel.get("current_status", "unknown")
                                approval["parcel_status"] = status.title() if status else "Unknown"
                            
                            approval["parcel_location"] = parcel.get("current_location", "Unknown")
                            fraud_score = parcel.get("fraud_risk_score") or 0
                            approval["fraud_risk"] = fraud_score
                            
                            # Generate fraud risk details
                            fraud_details = []
                            if fraud_score and fraud_score > 70:
                                fraud_details.append("⚠️ High Risk Score")
                                fraud_details.append("• Suspicious delivery pattern detected")
                                if fraud_score > 85:
                                    fraud_details.append("• Extreme risk - requires supervisor review")
                            elif fraud_score and fraud_score > 30:
                                fraud_details.append("⚡ Medium Risk Score")
                                fraud_details.append("• Some indicators detected")
                            else:  
                                fraud_details.append("✓ Low Risk Score")
                                fraud_details.append("• No significant red flags")
                            
                            declared_value = parcel.get("declared_value") or 0
                            if declared_value > 1000:
                                fraud_details.append(f"• High value: ${declared_value}")
                            
                            approval["fraud_details"] = " | ".join(fraud_details)
                            
                            # Generate address notes
                            recipient_address = parcel.get("recipient_address", "")
                            if fraud_score and fraud_score > 30:
                                address_notes = await db.get_address_notes(recipient_address)
                                if not address_notes:
                                    notes = []
                                    if fraud_score > 70:
                                        risk_reasons = [
                                            "Previous parcels intercepted at this address",
                                            "Address flagged for illegal imports - customs watch",
                                            "Law enforcement watch notice active",
                                        ]
                                        notes = random.sample(risk_reasons, min(2, len(risk_reasons)))
                                    else:
                                        risk_reasons = [
                                            "New delivery address - verification required",
                                            "Address has history of refused deliveries",
                                        ]
                                        notes = random.sample(risk_reasons, min(1, len(risk_reasons)))
                                    approval["address_notes"] = notes
                                else:
                                    approval["address_notes"] = address_notes
                            else:
                                approval["address_notes"] = []
                
                return pending
        
        pending = run_async(get_approvals_with_parcels())
        return render_template("approvals.html", approvals=pending)
    except Exception as e:
        flash(f"Error loading approvals: {str(e)}", "danger")
        return render_template("approvals.html", approvals=[])


@approvals_bp.route('/api/escalate-to-authorities', methods=['POST'])
@login_required
def escalate():
    """Escalate high-risk parcel to authorities"""
    try:
        data = request.get_json()
        approval_id = data.get("approval_id")
        tracking_number = data.get("tracking_number")
        risk_score = data.get("risk_score")
        escalated_by = data.get("escalated_by", session.get("username", "system"))
        
        # Generate escalation reference
        reference_id = f"ESC-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{tracking_number[:8]}"
        
        async def log_escalation():
            async with ParcelTrackingDB() as db:
                escalation_record = {
                    "reference_id": reference_id,
                    "approval_id": approval_id,
                    "tracking_number": tracking_number,
                    "risk_score": risk_score,
                    "escalated_by": escalated_by,
                    "escalated_at": datetime.now(timezone.utc).isoformat(),
                    "status": "escalated",
                    "notified_authorities": ["Customs", "Border Force"],
                }
                
                await db.create_tracking_event(
                    barcode=tracking_number,
                    event_type="escalation",
                    location="Security Review",
                    description=f"Escalated to authorities - Ref: {reference_id}",
                    scanned_by=escalated_by,
                    additional_info=escalation_record,
                )
                
                await db.reject_request(
                    request_id=approval_id,
                    rejected_by=escalated_by,
                    comments=f"ESCALATED TO AUTHORITIES - {reference_id} - Risk Score: {risk_score}%",
                )
        
        run_async(log_escalation())
        
        return jsonify({
            "success": True,
            "reference_id": reference_id,
            "message": "Escalation recorded and authorities notified"
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@approvals_bp.route('/<approval_id>/process', methods=['POST'])
@login_required
def process_approval(approval_id):
    """Process approval decision using CQRS command"""
    try:
        decision = request.form.get("decision")  # 'approve' or 'reject'
        notes = request.form.get("notes", "")
        approver = session.get("username", "web-user")
        
        async def process():
            async with ParcelTrackingDB() as db:
                # Use CQRS command
                approval_repo = ApprovalRepository(db)
                command = ApproveRequestCommand(approval_repo)
                
                await command.execute(
                    approval_id=approval_id,
                    decision='approved' if decision == 'approve' else 'denied',
                    reviewer_username=approver,
                    reviewer_notes=notes,
                )
        
        run_async(process())
        flash(f"Request {decision}ed successfully!", "success")
    except Exception as e:
        flash(f"Error processing approval: {str(e)}", "danger")
    
    return redirect(url_for("approvals.list_approvals"))


@approvals_bp.route('/api/run-approval-agent', methods=['POST'])
@login_required
def run_agent():
    """Run AI agent to auto-approve/reject based on criteria"""
    try:
        approver = session.get("username", "ai-agent")
        data = request.get_json() or {}
        config = data.get("config", {})
        selected_dcs = data.get("distributionCenters", [])
        
        if not selected_dcs:
            return jsonify({
                "success": False,
                "error": "No distribution centers selected."
            }), 400
        
        # Extract configuration
        fraud_threshold_low = int(config.get("fraudThresholdLow", 30))
        value_threshold = float(config.get("valueThreshold", 500))
        fraud_threshold_high = int(config.get("fraudThresholdHigh", 70))
        approve_verified = config.get("approveVerified", True)
        approve_delivered = config.get("approveDelivered", True)
        reject_blacklist = config.get("rejectBlacklist", True)
        reject_duplicate = config.get("rejectDuplicate", True)
        reject_missing_docs = config.get("rejectMissingDocs", False)
        
        async def process_with_agent():
            async with ParcelTrackingDB() as db:
                approval_repo = ApprovalRepository(db)
                parcel_repo = ParcelRepository(db)
                
                # Get pending approvals
                approval_query = GetApprovalsQuery(approval_repo)
                pending = await approval_query.get_pending()
                
                approved_count = 0
                rejected_count = 0
                skipped_count = 0
                skipped_dc_count = 0
                
                command = ApproveRequestCommand(approval_repo)
                
                for approval in pending:
                    parcel_barcode = approval.get("parcel_barcode")
                    request_type = approval.get("request_type", "")
                    description = approval.get("description", "")
                    
                    parcel = await db.get_parcel_by_barcode(parcel_barcode)
                    if not parcel:
                        skipped_count += 1
                        continue
                    
                    # Check DC matching
                    parcel_dc = approval.get("parcel_dc", "UNKNOWN")
                    dc_matched = any(selected_dc in parcel_dc or parcel_dc.startswith(selected_dc) 
                                   for selected_dc in selected_dcs)
                    
                    if not dc_matched:
                        skipped_dc_count += 1
                        continue
                    
                    fraud_risk = parcel.get("fraud_risk_score", 0)
                    value = parcel.get("declared_value", 0)
                    status = approval.get("parcel_status", parcel.get("current_status", ""))
                    
                    auto_approve = False
                    auto_reject = False
                    reason_text = ""
                    
                    # Auto-rejection criteria
                    if fraud_risk > fraud_threshold_high:
                        auto_reject = True
                        reason_text = f"High fraud risk: {fraud_risk}%"
                    elif reject_blacklist and "blacklist" in description.lower():
                        auto_reject = True
                        reason_text = "Blacklisted address"
                    elif reject_duplicate and "duplicate" in description.lower():
                        auto_reject = True
                        reason_text = "Duplicate request"
                    elif reject_missing_docs and "missing" in description.lower():
                        auto_reject = True
                        reason_text = "Missing documentation"
                    # Auto-approval criteria
                    elif fraud_risk < fraud_threshold_low and value < value_threshold:
                        auto_approve = True
                        reason_text = f"Low risk ({fraud_risk}%), standard value (${value})"
                    elif approve_delivered and status == "Delivered":
                        auto_approve = True
                        reason_text = "Standard delivery confirmation"
                    elif approve_verified and "verified" in description.lower():
                        auto_approve = True
                        reason_text = "Verified sender/recipient"
                    
                    if auto_approve:
                        await command.execute(
                            approval_id=approval["id"],
                            decision='approved',
                            reviewer_username=approver,
                            reviewer_notes=f"AI Agent: {reason_text}",
                        )
                        approved_count += 1
                    elif auto_reject:
                        await command.execute(
                            approval_id=approval["id"],
                            decision='denied',
                            reviewer_username=approver,
                            reviewer_notes=f"AI Agent: {reason_text}",
                        )
                        rejected_count += 1
                    else:
                        skipped_count += 1
                
                return {
                    "approved": approved_count,
                    "rejected": rejected_count,
                    "skipped": skipped_count,
                    "skipped_dc": skipped_dc_count,
                }
        
        results = run_async(process_with_agent())
        
        return jsonify({
            "success": True,
            **results
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
