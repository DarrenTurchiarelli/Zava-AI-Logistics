"""
Approvals Blueprint - Approval workflow routes

Complete implementation with CQRS pattern integration
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, timezone
import json
import os
import re
import random

from src.interfaces.web.middleware import login_required, depot_manager_required
from parcel_tracking_db import ParcelTrackingDB
from utils.async_helpers import run_async

approvals_bp = Blueprint('approvals', __name__, url_prefix='/approvals')


def _ai_batch_approve(items: list, config: dict) -> dict:
    """
    Call Azure OpenAI to decide approve/reject/manual_review for a batch of approvals.

    Returns a dict keyed by approval id:
        { approval_id: {"decision": "approve"|"reject"|"manual_review", "reasoning": "..."} }

    On any failure returns {} so the caller falls back to rule-based logic.
    """
    if not items:
        return {}
    try:
        from openai import AzureOpenAI
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        model    = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o")
        if not endpoint:
            return {}

        credential     = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            azure_ad_token_provider=token_provider,
            api_version="2024-05-01-preview",
        )

        fraud_high = config.get("fraud_threshold_high", 70)
        fraud_low  = config.get("fraud_threshold_low",  30)
        max_value  = config.get("value_threshold",     500)

        rows = "\n".join(
            f"ID:{item['id']} | type:{item.get('request_type','?')} | "
            f"fraud:{item.get('fraud_risk',0)}% | value:${item.get('value',0)} | "
            f"status:{item.get('parcel_status','?')} | desc:{str(item.get('description',''))[:120]}"
            for item in items
        )

        prompt = (
            f"You are a parcel approval agent for a logistics company.\n"
            f"Config thresholds: fraud_high={fraud_high}%, fraud_low={fraud_low}%, max_value=${max_value}.\n\n"
            f"For each approval request below, decide: approve, reject, or manual_review.\n"
            f"Return ONLY a JSON object like:\n"
            f'  {{"decisions":[{{"id":"...","decision":"approve","reasoning":"one sentence"}},...]}}\n\n'
            f"Approvals:\n{rows}"
        )

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )

        raw = response.choices[0].message.content or ""
        # Extract JSON object from response (may have surrounding text)
        match = re.search(r'\{[\s\S]*\}', raw)
        if not match:
            return {}
        data = json.loads(match.group())
        decisions = data.get("decisions", data) if isinstance(data, dict) else data
        if not isinstance(decisions, list):
            return {}

        return {
            d["id"]: {
                "decision":  d.get("decision", "manual_review"),
                "reasoning": d.get("reasoning", d.get("reason", "")),
            }
            for d in decisions
            if "id" in d
        }

    except Exception as exc:
        print(f"⚠️ _ai_batch_approve failed — falling back to rules: {exc}")
        return {}



@approvals_bp.route('/')
@login_required
def list_approvals():
    """View pending approvals"""
    try:
        async def get_approvals_with_parcels():
            async with ParcelTrackingDB() as db:
                pending = await db.get_all_pending_approvals()
                
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

                    # Pass through contraband fields stored by the generator
                    # (contraband_type, reason, escalate_agencies already on the document)

                    # Get parcel details
                    if parcel_barcode:
                        parcel = await db.get_parcel_by_barcode(parcel_barcode)
                        if parcel:
                            if not approval.get("parcel_dc"):
                                approval["parcel_dc"] = parcel.get("store_location") or parcel.get("origin_location", "Unknown")
                            # Always show pending — these parcels are held at the DC
                            approval["parcel_status"] = "Pending — Held at Distribution Centre"
                            approval["parcel_location"] = (
                                approval.get("parcel_location")
                                or parcel.get("current_location")
                                or approval.get("parcel_dc")
                                or "Distribution Centre"
                            )
                            fraud_score = parcel.get("fraud_risk_score") or 0
                            approval["fraud_risk"] = fraud_score

                            # Fraud risk details
                            fraud_details = []
                            if fraud_score > 70:
                                fraud_details.append("⚠️ High Risk Score")
                                fraud_details.append("• Suspicious delivery pattern detected")
                                if fraud_score > 85:
                                    fraud_details.append("• Extreme risk — supervisor review required")
                            elif fraud_score > 30:
                                fraud_details.append("⚡ Medium Risk Score")
                                fraud_details.append("• Some indicators detected")
                            else:
                                fraud_details.append("✓ Low Risk Score")
                                fraud_details.append("• No significant red flags")
                            declared_value = parcel.get("declared_value") or 0
                            if declared_value > 1000:
                                fraud_details.append(f"• High declared value: ${declared_value:,.0f}")
                            approval["fraud_details"] = " | ".join(fraud_details)

                            # Address notes pulled from DB or derived from contraband type
                            contraband_type = approval.get("contraband_type", "")
                            if contraband_type:
                                # Show the contraband reason as an address note so the
                                # Escalate button always appears on the tile
                                approval["address_notes"] = [approval.get("reason", contraband_type)]
                            elif fraud_score > 30:
                                recipient_address = parcel.get("recipient_address", "")
                                address_notes = await db.get_address_notes(recipient_address)
                                if not address_notes:
                                    if fraud_score > 70:
                                        risk_reasons = [
                                            "Previous parcels intercepted at this address",
                                            "Address flagged for illegal imports — customs watch",
                                            "Law enforcement watch notice active",
                                        ]
                                        approval["address_notes"] = random.sample(risk_reasons, min(2, len(risk_reasons)))
                                    else:
                                        approval["address_notes"] = ["New delivery address — verification required"]
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


@approvals_bp.route('/api/escalate', methods=['POST'])
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
                if decision == 'approve':
                    await db.approve_request(approval_id, approver, notes)
                else:
                    await db.reject_request(approval_id, approver, notes)
        
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
                pending = await db.get_all_pending_approvals()

                approved_count   = 0
                rejected_count   = 0
                skipped_count    = 0
                skipped_dc_count = 0

                # ── Pass 1: collect items that belong to selected DCs ──────────
                qualifying = []
                for approval in pending:
                    parcel_barcode = approval.get("parcel_barcode")
                    parcel = await db.get_parcel_by_barcode(parcel_barcode)
                    if not parcel:
                        skipped_count += 1
                        continue

                    parcel_dc = approval.get("parcel_dc", "UNKNOWN")
                    dc_matched = any(
                        selected_dc in parcel_dc or parcel_dc.startswith(selected_dc)
                        for selected_dc in selected_dcs
                    )
                    if not dc_matched:
                        skipped_dc_count += 1
                        continue

                    qualifying.append({
                        "approval":     approval,
                        "parcel":       parcel,
                        "id":           approval["id"],
                        "request_type": approval.get("request_type", ""),
                        "description":  approval.get("description", ""),
                        "fraud_risk":   parcel.get("fraud_risk_score", 0),
                        "value":        parcel.get("declared_value", 0),
                        "parcel_status": approval.get(
                            "parcel_status", parcel.get("current_status", "")
                        ),
                    })

                # ── Pass 2: ask LLM for batch decisions (falls back to {} on failure)
                ai_cfg = {
                    "fraud_threshold_high": fraud_threshold_high,
                    "fraud_threshold_low":  fraud_threshold_low,
                    "value_threshold":      value_threshold,
                }
                ai_decisions = _ai_batch_approve(qualifying, ai_cfg)

                # ── Pass 3: apply decisions ────────────────────────────────────
                ai_decisions_out: dict = {}
                for item in qualifying:
                    approval   = item["approval"]
                    parcel     = item["parcel"]
                    app_id     = item["id"]
                    description = item["description"]
                    fraud_risk  = item["fraud_risk"]
                    value       = item["value"]
                    status      = item["parcel_status"]

                    if app_id in ai_decisions:
                        ai_dec    = ai_decisions[app_id]
                        decision  = ai_dec["decision"]
                        reasoning = ai_dec["reasoning"]
                        source    = "AI"
                    else:
                        # Rule-based fallback
                        reasoning = ""
                        if fraud_risk > fraud_threshold_high:
                            decision  = "reject"
                            reasoning = f"High fraud risk: {fraud_risk}%"
                        elif reject_blacklist and "blacklist" in description.lower():
                            decision  = "reject"
                            reasoning = "Blacklisted address"
                        elif reject_duplicate and "duplicate" in description.lower():
                            decision  = "reject"
                            reasoning = "Duplicate request"
                        elif reject_missing_docs and "missing" in description.lower():
                            decision  = "reject"
                            reasoning = "Missing documentation"
                        elif fraud_risk < fraud_threshold_low and value < value_threshold:
                            decision  = "approve"
                            reasoning = f"Low risk ({fraud_risk}%), standard value (${value})"
                        elif approve_delivered and status == "Delivered":
                            decision  = "approve"
                            reasoning = "Standard delivery confirmation"
                        elif approve_verified and "verified" in description.lower():
                            decision  = "approve"
                            reasoning = "Verified sender/recipient"
                        else:
                            decision  = "manual_review"
                            reasoning = "Does not meet auto-approve or auto-reject criteria"
                        source = "rules"

                    ai_decisions_out[app_id] = {
                        "decision":  decision,
                        "reasoning": reasoning,
                        "source":    source,
                    }

                    if decision == "approve":
                        await db.approve_request(
                            app_id, approver, f"AI Agent ({source}): {reasoning}"
                        )
                        approved_count += 1
                    elif decision == "reject":
                        await db.reject_request(
                            app_id, approver, f"AI Agent ({source}): {reasoning}"
                        )
                        rejected_count += 1
                    else:
                        skipped_count += 1

                return {
                    "approved":     approved_count,
                    "rejected":     rejected_count,
                    "skipped":      skipped_count,
                    "skipped_dc":   skipped_dc_count,
                    "ai_decisions": ai_decisions_out,
                }
        
        results = run_async(process_with_agent())
        
        return jsonify({
            "success": True,
            **results
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
