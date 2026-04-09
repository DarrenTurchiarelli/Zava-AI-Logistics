"""
MAF v1.0 multi-agent workflows using SequentialBuilder.

Two workflows:
1. FraudDetectionWorkflow -- fraud_agent -> [identity_agent] -> customer_service_agent
2. DispatcherWorkflow     -- dispatcher_agent -> optimization_agent (SequentialBuilder)
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

from dotenv import load_dotenv

load_dotenv(override=False)

from agent_framework import Agent
from agent_framework.orchestrations import SequentialBuilder

from src.infrastructure.agents.core.prompt_loader import get_agent_prompt
from src.infrastructure.agents.maf.client import make_agent, make_chat_client
from src.infrastructure.agents.maf.tools import (
    search_parcels_by_recipient,
    track_parcel,
)

_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")


def _load_prompt(agent_key: str, fallback: str = "") -> str:
    try:
        return get_agent_prompt(agent_key)
    except Exception:
        return fallback


def _parse_risk_score(text: str) -> float:
    match = re.search(r"RISK_SCORE:\s*([0-9.]+)", text, re.IGNORECASE)
    if match:
        try:
            return min(1.0, max(0.0, float(match.group(1))))
        except ValueError:
            pass
    match = re.search(r"\b([0-9]{1,3})\s*%", text)
    if match:
        return float(match.group(1)) / 100.0
    return 0.0


# ---------------------------------------------------------------------------
# Fallback instructions
# ---------------------------------------------------------------------------

_FRAUD_INSTRUCTIONS_FALLBACK = (
    "You are Zava's Fraud Detection Agent. Analyse the provided message for fraud "
    "indicators. Assign a risk score 0.00-1.00 on a dedicated line: RISK_SCORE: <value>. "
    "Recommend: NO_ACTION / WARN_CUSTOMER / VERIFY_IDENTITY / HOLD_PARCEL."
)
_IDENTITY_INSTRUCTIONS_FALLBACK = (
    "You are Zava's Identity Verification Agent. A high-risk fraud event was detected. "
    "Verify the customer's details and state whether identity is confirmed."
)
_CS_FRAUD_INSTRUCTIONS_FALLBACK = (
    "You are Zava's Customer Service Agent responding to a fraud alert. "
    "Draft a clear, empathetic warning to the customer with next steps."
)
_DISPATCHER_FALLBACK = (
    "You are Zava's Dispatcher Agent. Assign pending parcels to available drivers using "
    "geographic clustering, workload balancing, and priority. Return a manifest list."
)
_OPTIMIZATION_FALLBACK = (
    "You are Zava's Optimization Agent. Review the Dispatcher's manifest and suggest "
    "route or load-balance improvements to reduce cost and delivery time."
)


# ---------------------------------------------------------------------------
# Fraud Detection Workflow
# ---------------------------------------------------------------------------

async def run_fraud_workflow(
    message_content: str,
    customer_name: str = "",
    customer_email: str = "",
    customer_phone: str = "",
    sender_email: str = "",
    activity_type: str = "message",
) -> Dict[str, Any]:
    """
    Step 1 - Fraud Detection Agent analyses suspicious content.
    Step 2 - (conditional, risk >= 0.85) Identity Verification Agent.
    Step 3 - Customer Service Agent composes customer-facing warning (risk >= 0.70).
    """
    if not _OPENAI_ENDPOINT:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT is not set.")

    fraud_prompt = (
        f"Analyse the following suspicious {activity_type} for fraud indicators.\n\n"
        f"Content: {message_content}\n"
        f"Sender email: {sender_email or 'unknown'}\n"
        f"Customer name: {customer_name or 'unknown'}\n"
        f"Customer email: {customer_email or 'not provided'}\n"
        f"Customer phone: {customer_phone or 'not provided'}\n\n"
        "Provide: threat category, indicators, RISK_SCORE: <0.00-1.00>, "
        "recommended action, justification."
    )

    workflow_steps: list[Dict[str, Any]] = []
    chat_client = make_chat_client()

    # Step 1: Fraud Detection
    fraud_instructions = _load_prompt("fraud-detection", _FRAUD_INSTRUCTIONS_FALLBACK)
    fraud_agent = Agent(
        client=chat_client,
        name="zava-fraud-detection",
        instructions=fraud_instructions or None,
    )
    try:
        fraud_result = await fraud_agent.run(fraud_prompt)
        fraud_response_text = str(fraud_result)
        risk_score = _parse_risk_score(fraud_response_text)
        workflow_steps.append({"step": 1, "agent": "Fraud Detection", "risk_score": risk_score, "success": True})
    except Exception as exc:
        return {"success": False, "error": f"Fraud Detection Agent failed: {exc}", "workflow_steps": workflow_steps}

    # Determine risk level
    if risk_score >= 0.90:
        risk_level, recommended_action = "critical", "HOLD_PARCEL"
    elif risk_score >= 0.85:
        risk_level, recommended_action = "very_high", "VERIFY_IDENTITY"
    elif risk_score >= 0.70:
        risk_level, recommended_action = "high", "WARN_CUSTOMER"
    elif risk_score >= 0.40:
        risk_level, recommended_action = "medium", "WARN_CUSTOMER"
    else:
        risk_level, recommended_action = "low", "NO_ACTION"

    # Step 2 (conditional): Identity Verification
    identity_response_text: Optional[str] = None
    if risk_score >= 0.85:
        identity_prompt = (
            f"Verify customer: {customer_name or 'unknown'}, "
            f"email: {customer_email or 'not provided'}, "
            f"phone: {customer_phone or 'not provided'}. "
            f"Fraud risk: {risk_score:.0%}.\nFraud summary:\n{fraud_response_text[:500]}"
        )
        id_agent = Agent(
            client=make_chat_client(),  # fresh client per agent
            name="zava-identity",
            instructions=_load_prompt("identity", _IDENTITY_INSTRUCTIONS_FALLBACK) or None,
        )
        try:
            id_result = await id_agent.run(identity_prompt)
            identity_response_text = str(id_result)
            workflow_steps.append({"step": 2, "agent": "Identity Verification", "success": True})
        except Exception as exc:
            workflow_steps.append({"step": 2, "agent": "Identity Verification", "success": False, "error": str(exc)})

    # Step 3: Customer Service notification
    cs_response_text: Optional[str] = None
    if risk_score >= 0.70:
        parts = [
            f"Send a fraud warning to customer: {customer_name or 'the customer'}.",
            f"Risk level: {risk_level} ({risk_score:.0%}).",
            f"Fraud analysis:\n{fraud_response_text[:600]}",
        ]
        if identity_response_text:
            parts.append(f"\nIdentity check:\n{identity_response_text[:400]}")
        cs_agent = Agent(
            client=make_chat_client(),  # fresh client per agent
            name="zava-customer-service",
            instructions=_load_prompt("customer-service", _CS_FRAUD_INSTRUCTIONS_FALLBACK) or None,
            tools=[track_parcel, search_parcels_by_recipient],
        )
        try:
            cs_result = await cs_agent.run("\n".join(parts))
            cs_response_text = str(cs_result)
            workflow_steps.append({"step": len(workflow_steps) + 1, "agent": "Customer Service", "success": True})
        except Exception as exc:
            workflow_steps.append({"step": len(workflow_steps) + 1, "agent": "Customer Service", "success": False, "error": str(exc)})

    return {
        "success": True,
        "fraud_analysis": fraud_response_text,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "recommended_action": recommended_action,
        "identity_verification": identity_response_text,
        "customer_notification": cs_response_text,
        "workflow_steps": workflow_steps,
    }


# ---------------------------------------------------------------------------
# Dispatcher Workflow (SequentialBuilder)
# ---------------------------------------------------------------------------

async def run_dispatcher_workflow(
    state: str = "",
    manifest_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Two-stage SequentialBuilder: dispatcher_agent -> optimization_agent.
    Returns dict with dispatcher_output and optimization_output.
    """
    if not _OPENAI_ENDPOINT:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT is not set.")

    context_str = (
        f"\n\nContext:\n{json.dumps(manifest_context, indent=2, default=str)}"
        if manifest_context else ""
    )
    initial_message = f"Assign pending parcels to available drivers{' in ' + state if state else ''}.{context_str}"

    # Each agent needs its own client instance (different names/instructions)
    dispatcher_agent = Agent(
        client=make_chat_client(),
        name="zava-dispatcher",
        instructions=_load_prompt("dispatcher", _DISPATCHER_FALLBACK) or None,
    )
    optimization_agent = Agent(
        client=make_chat_client(),
        name="zava-optimization",
        instructions=_load_prompt("optimization", _OPTIMIZATION_FALLBACK) or None,
    )

    dispatcher_text = ""
    optimization_text = ""

    try:
        workflow = SequentialBuilder(
            participants=[dispatcher_agent, optimization_agent]
        ).build()

        outputs = []
        async for event in workflow.run(initial_message, stream=True):
            if hasattr(event, "type") and event.type == "output":
                outputs.append(event.data)

        if len(outputs) >= 1:
            dispatcher_text = str(outputs[0])
        if len(outputs) >= 2:
            optimization_text = str(outputs[1])

        return {"success": True, "dispatcher_output": dispatcher_text, "optimization_output": optimization_text}

    except Exception as exc:
        return {
            "success": False,
            "error": f"Dispatcher workflow failed: {exc}",
            "dispatcher_output": dispatcher_text,
            "optimization_output": optimization_text,
        }
