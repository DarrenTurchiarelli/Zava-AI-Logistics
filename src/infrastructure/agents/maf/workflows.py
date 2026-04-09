"""
MAF multi-agent workflows using SequentialBuilder and HandoffBuilder.

Two workflows are implemented here:

1. FraudDetectionWorkflow  (SequentialBuilder, replaces FraudToCustomerServiceWorkflow)
   fraud_agent ──► customer_service_agent
   With a conditional sub-step: if risk ≥ 0.85, identity_agent is injected
   between fraud and customer_service.

2. DispatcherWorkflow  (SequentialBuilder)
   dispatcher_agent  ──► optimization_agent
   Used for AI Auto-Assign manifest generation.

Usage::

    from src.infrastructure.agents.maf.workflows import run_fraud_workflow

    result = await run_fraud_workflow(
        message_content="Suspicious SMS asking for re-delivery fee",
        customer_name="Jane Smith",
        customer_email="jane@example.com",
        customer_phone="+61411123456",
    )
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

from dotenv import load_dotenv

load_dotenv(override=False)

from agent_framework.azure import AzureOpenAIAssistantsClient
from agent_framework.orchestrations import SequentialBuilder
from azure.identity.aio import DefaultAzureCredential, ManagedIdentityCredential

from src.infrastructure.agents.core.prompt_loader import get_agent_prompt
from src.infrastructure.agents.maf.tools import (
    search_parcels_by_recipient,
    track_parcel,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
_MODEL: str = (
    os.getenv("FOUNDRY_MODEL_DEPLOYMENT_NAME")
    or os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    or "gpt-4o"
)

_AGENT_IDS = {
    "fraud_risk": os.getenv("FRAUD_RISK_AGENT_ID", ""),
    "identity": os.getenv("IDENTITY_AGENT_ID", ""),
    "customer_service": os.getenv("CUSTOMER_SERVICE_AGENT_ID", ""),
    "dispatcher": os.getenv("DISPATCHER_AGENT_ID", ""),
    "optimization": os.getenv("OPTIMIZATION_AGENT_ID", ""),
}


def _credential():
    if os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true":
        return ManagedIdentityCredential()
    return DefaultAzureCredential(
        exclude_managed_identity_credential=True,
        exclude_visual_studio_code_credential=True,
        additionally_allowed_tenants=["*"],
    )


def _assistants_client(agent_key: str, middleware=None) -> AzureOpenAIAssistantsClient:
    """Build an AzureOpenAIAssistantsClient for the given agent key."""
    assistant_id = _AGENT_IDS.get(agent_key, "")
    kwargs = {
        "endpoint": _OPENAI_ENDPOINT,
        "deployment_name": _MODEL,
        "credential": _credential(),
        "api_version": "2024-05-01-preview",
    }
    if assistant_id:
        kwargs["assistant_id"] = assistant_id
    if middleware:
        kwargs["middleware"] = middleware
    return AzureOpenAIAssistantsClient(**kwargs)


def _load_prompt(agent_key: str, fallback: str = "") -> str:
    try:
        return get_agent_prompt(agent_key)
    except Exception:
        return fallback


def _parse_risk_score(text: str) -> float:
    """Extract a 0-1 risk score from agent output like 'RISK_SCORE: 0.87'."""
    match = re.search(r"RISK_SCORE:\s*([0-9.]+)", text, re.IGNORECASE)
    if match:
        try:
            return min(1.0, max(0.0, float(match.group(1))))
        except ValueError:
            pass
    # Fallback: look for percentage
    match = re.search(r"\b([0-9]{1,3})\s*%", text)
    if match:
        return float(match.group(1)) / 100.0
    return 0.0


# ---------------------------------------------------------------------------
# Fraud Detection Workflow
# ---------------------------------------------------------------------------

_FRAUD_INSTRUCTIONS_FALLBACK = (
    "You are Zava's Fraud Detection Agent. Analyse the provided message for fraud "
    "indicators such as phishing, impersonation, fee-fraud, or social engineering. "
    "Assign a risk score between 0.00 and 1.00 and include it in your response on a "
    "dedicated line formatted exactly as: RISK_SCORE: <value>. "
    "Categorise threats and recommend one of: NO_ACTION, WARN_CUSTOMER, "
    "VERIFY_IDENTITY, HOLD_PARCEL."
)

_IDENTITY_INSTRUCTIONS_FALLBACK = (
    "You are Zava's Identity Verification Agent. A high-risk fraud event has been "
    "detected. Verify the customer's details against the information provided. "
    "State clearly whether identity can be confirmed or not, and what follow-up is needed."
)

_CS_FRAUD_INSTRUCTIONS_FALLBACK = (
    "You are Zava's Customer Service Agent responding to a fraud alert. "
    "Draft a clear, empathetic message to the customer warning them about the "
    "suspicious activity. Include next steps and Zava's support contact details."
)


async def run_fraud_workflow(
    message_content: str,
    customer_name: str = "",
    customer_email: str = "",
    customer_phone: str = "",
    sender_email: str = "",
    activity_type: str = "message",
) -> Dict[str, Any]:
    """
    MAF-based replacement for FraudToCustomerServiceWorkflow.execute().

    Step 1 — Fraud Detection Agent  analyses the suspicious content.
    Step 2 — (conditional, risk ≥ 0.85) Identity Verification Agent verifies customer.
    Step 3 — Customer Service Agent  composes the customer-facing warning.

    Returns a dict with keys:
        fraud_analysis, risk_score, risk_level,
        identity_verification (optional), customer_notification,
        recommended_action, workflow_steps: list[dict]
    """
    if not _OPENAI_ENDPOINT:
        raise RuntimeError(
            "AZURE_OPENAI_ENDPOINT is not set."
        )

    # ------------------------------------------------------------------
    # Build initial fraud-analysis prompt
    # ------------------------------------------------------------------
    fraud_prompt = f"""
Analyse the following suspicious {activity_type} for fraud indicators.

Content: {message_content}
Sender email: {sender_email or 'unknown'}
Customer name: {customer_name or 'unknown'}
Customer email: {customer_email or 'not provided'}
Customer phone: {customer_phone or 'not provided'}

Provide a structured analysis with:
1. Threat category (phishing / impersonation / fee_fraud / social_engineering / none)
2. Specific indicators found
3. RISK_SCORE: <0.00–1.00>
4. Recommended action (NO_ACTION / WARN_CUSTOMER / VERIFY_IDENTITY / HOLD_PARCEL)
5. Justification
""".strip()

    workflow_steps: list[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Step 1: Fraud Detection
    # ------------------------------------------------------------------
    fraud_instructions = _load_prompt("fraud-detection", _FRAUD_INSTRUCTIONS_FALLBACK)
    fraud_response_text = ""

    try:
        async with _assistants_client("fraud_risk").as_agent(
            name="zava-fraud-detection",
            instructions=fraud_instructions,
        ) as fraud_agent:
            fraud_result = await fraud_agent.run(fraud_prompt)
            fraud_response_text = str(fraud_result)

        risk_score = _parse_risk_score(fraud_response_text)
        workflow_steps.append(
            {
                "step": 1,
                "agent": "Fraud Detection",
                "input_length": len(fraud_prompt),
                "risk_score": risk_score,
                "success": True,
            }
        )
    except Exception as exc:
        return {
            "success": False,
            "error": f"Fraud Detection Agent failed: {exc}",
            "workflow_steps": workflow_steps,
        }

    risk_score = _parse_risk_score(fraud_response_text)

    # Determine risk level
    if risk_score >= 0.90:
        risk_level = "critical"
        recommended_action = "HOLD_PARCEL"
    elif risk_score >= 0.85:
        risk_level = "very_high"
        recommended_action = "VERIFY_IDENTITY"
    elif risk_score >= 0.70:
        risk_level = "high"
        recommended_action = "WARN_CUSTOMER"
    elif risk_score >= 0.40:
        risk_level = "medium"
        recommended_action = "WARN_CUSTOMER"
    else:
        risk_level = "low"
        recommended_action = "NO_ACTION"

    # ------------------------------------------------------------------
    # Step 2 (conditional): Identity Verification — risk ≥ 0.85
    # ------------------------------------------------------------------
    identity_response_text: Optional[str] = None

    if risk_score >= 0.85:
        identity_prompt = (
            f"Verify customer: {customer_name or 'unknown'}, "
            f"email: {customer_email or 'not provided'}, "
            f"phone: {customer_phone or 'not provided'}. "
            f"Fraud risk: {risk_score:.0%}. "
            f"Fraud analysis summary:\n{fraud_response_text[:500]}"
        )
        identity_instructions = _load_prompt(
            "identity", _IDENTITY_INSTRUCTIONS_FALLBACK
        )
        try:
            async with _assistants_client("identity").as_agent(
                name="zava-identity",
                instructions=identity_instructions,
            ) as id_agent:
                id_result = await id_agent.run(identity_prompt)
                identity_response_text = str(id_result)

            workflow_steps.append(
                {
                    "step": 2,
                    "agent": "Identity Verification",
                    "triggered_by": f"risk_score={risk_score:.0%}",
                    "success": True,
                }
            )
        except Exception as exc:
            workflow_steps.append(
                {"step": 2, "agent": "Identity Verification", "success": False, "error": str(exc)}
            )

    # ------------------------------------------------------------------
    # Step 3: Customer Service notification (if risk ≥ 0.70)
    # ------------------------------------------------------------------
    cs_response_text: Optional[str] = None

    if risk_score >= 0.70:
        parts = [
            f"Send a fraud warning to customer: {customer_name or 'the customer'}.",
            f"Risk level: {risk_level} ({risk_score:.0%}).",
            f"Fraud analysis:\n{fraud_response_text[:600]}",
        ]
        if identity_response_text:
            parts.append(f"\nIdentity check result:\n{identity_response_text[:400]}")
        cs_prompt = "\n".join(parts)

        cs_instructions = _load_prompt("customer-service", _CS_FRAUD_INSTRUCTIONS_FALLBACK)
        try:
            async with _assistants_client("customer_service").as_agent(
                name="zava-customer-service",
                instructions=cs_instructions,
                tools=[track_parcel, search_parcels_by_recipient],
            ) as cs_agent:
                cs_result = await cs_agent.run(cs_prompt)
                cs_response_text = str(cs_result)

            workflow_steps.append(
                {
                    "step": len(workflow_steps) + 1,
                    "agent": "Customer Service",
                    "triggered_by": f"risk_score={risk_score:.0%}",
                    "success": True,
                }
            )
        except Exception as exc:
            workflow_steps.append(
                {
                    "step": len(workflow_steps) + 1,
                    "agent": "Customer Service",
                    "success": False,
                    "error": str(exc),
                }
            )

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
# Dispatcher Workflow  (SequentialBuilder demo)
# ---------------------------------------------------------------------------

_DISPATCHER_FALLBACK = (
    "You are Zava's Dispatcher Agent. Assign the provided pending parcels to available "
    "drivers using geographic clustering, workload balancing, and priority weighting. "
    "Return a structured manifest assignment list."
)

_OPTIMIZATION_FALLBACK = (
    "You are Zava's Optimization Agent. Review the manifest assignment produced by the "
    "Dispatcher Agent and suggest route or load-balance improvements to reduce fuel cost "
    "and delivery time."
)


async def run_dispatcher_workflow(
    state: str = "",
    manifest_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Two-stage SequentialBuilder workflow:
      dispatcher_agent → optimization_agent

    Returns dict with dispatcher_output, optimization_output.
    """
    if not _OPENAI_ENDPOINT:
        raise RuntimeError(
            "AZURE_OPENAI_ENDPOINT is not set."
        )

    context_str = (
        f"\n\nContext:\n{json.dumps(manifest_context, indent=2, default=str)}"
        if manifest_context
        else ""
    )
    initial_message = (
        f"Assign pending parcels to available drivers"
        f"{' in ' + state if state else ''}.{context_str}"
    )

    dispatcher_instructions = _load_prompt("dispatcher", _DISPATCHER_FALLBACK)
    optimization_instructions = _load_prompt("optimization", _OPTIMIZATION_FALLBACK)

    dispatcher_text = ""
    optimization_text = ""

    try:
        async with _assistants_client("dispatcher").as_agent(
            name="zava-dispatcher",
            instructions=dispatcher_instructions,
        ) as dispatcher_agent:
            async with _assistants_client("optimization").as_agent(
                name="zava-optimization",
                instructions=optimization_instructions,
            ) as optimization_agent:
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

        return {
            "success": True,
            "dispatcher_output": dispatcher_text,
            "optimization_output": optimization_text,
        }

    except Exception as exc:
        return {
            "success": False,
            "error": f"Dispatcher workflow failed: {exc}",
            "dispatcher_output": dispatcher_text,
            "optimization_output": optimization_text,
        }
