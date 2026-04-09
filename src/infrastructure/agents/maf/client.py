"""
MAF AzureOpenAIAssistantsClient-based agent caller.

Uses the MAF SDK's AzureOpenAIAssistantsClient which wraps the Azure OpenAI
Assistants API — the same API the existing asst_XXX agents were created with.
This gives us MAF's @tool dispatch, AgentMiddleware, and WorkflowBuilder on
top of the existing persistent Foundry agents, without requiring the newer
Azure AI Projects Agents API endpoint.

Feature flag: set USE_MAF=true in .env to activate this path.  While
USE_MAF is absent or false the legacy call_azure_agent() in base.py is
used unchanged.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv(override=False)

# ---------------------------------------------------------------------------
# MAF SDK imports
# ---------------------------------------------------------------------------
from agent_framework.azure import AzureOpenAIAssistantsClient
from azure.identity.aio import (
    DefaultAzureCredential,
    ManagedIdentityCredential,
    get_bearer_token_provider,
)
from openai.lib.azure import AsyncAzureOpenAI

# ---------------------------------------------------------------------------
# Prompt loader (existing helper)
# ---------------------------------------------------------------------------
from src.infrastructure.agents.core.prompt_loader import get_agent_prompt

# ---------------------------------------------------------------------------
# @tool-decorated Cosmos DB tools
# ---------------------------------------------------------------------------
from src.infrastructure.agents.maf.tools import (
    get_available_drivers,
    get_delivery_statistics,
    get_pending_parcels_for_dispatch,
    get_performance_metrics,
    search_parcels_by_driver,
    search_parcels_by_recipient,
    track_parcel,
    update_delivery_status,
)

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
_MODEL: str = (
    os.getenv("FOUNDRY_MODEL_DEPLOYMENT_NAME")
    or os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    or "gpt-4o"
)

# All agent IDs (existing asst_XXX persistent agents)
_AGENT_IDS: Dict[str, str] = {
    "customer_service": os.getenv("CUSTOMER_SERVICE_AGENT_ID", ""),
    "fraud_risk": os.getenv("FRAUD_RISK_AGENT_ID", ""),
    "identity": os.getenv("IDENTITY_AGENT_ID", ""),
    "dispatcher": os.getenv("DISPATCHER_AGENT_ID", ""),
    "parcel_intake": os.getenv("PARCEL_INTAKE_AGENT_ID", ""),
    "sorting_facility": os.getenv("SORTING_FACILITY_AGENT_ID", ""),
    "delivery_coordination": os.getenv("DELIVERY_COORDINATION_AGENT_ID", ""),
    "optimization": os.getenv("OPTIMIZATION_AGENT_ID", ""),
    "driver": os.getenv("DRIVER_AGENT_ID", ""),
}

# Tool sets per agent role (passed to as_agent so MAF handles dispatch)
_AGENT_TOOL_MAP: Dict[str, list] = {
    "customer_service": [track_parcel, search_parcels_by_recipient, search_parcels_by_driver],
    "fraud_risk": [],
    "identity": [],
    "dispatcher": [get_pending_parcels_for_dispatch, get_available_drivers, get_delivery_statistics],
    "parcel_intake": [],
    "sorting_facility": [],
    "delivery_coordination": [],
    "optimization": [get_performance_metrics, get_delivery_statistics],
    "driver": [track_parcel, update_delivery_status],
}


# ---------------------------------------------------------------------------
# Credential factory
# ---------------------------------------------------------------------------

def _make_credential():
    """Return the correct async credential for the runtime environment."""
    if os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true":
        return ManagedIdentityCredential()
    return DefaultAzureCredential(
        exclude_managed_identity_credential=True,
        exclude_visual_studio_code_credential=True,
        additionally_allowed_tenants=["*"],
    )


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

def get_maf_client(
    *,
    agent_key: str = "customer_service",
    middleware: Optional[list] = None,
) -> AzureOpenAIAssistantsClient:
    """
    Build an AzureOpenAIAssistantsClient wired to the given agent's asst_XXX ID.

    We construct AsyncAzureOpenAI ourselves with an Azure AD token provider so
    that AzureOpenAIAssistantsClient skips its own env-var api_key resolution.
    This avoids a stale AZURE_OPENAI_API_KEY user env var overriding credential
    auth on resources where key-based authentication is disabled.
    """
    if not _OPENAI_ENDPOINT:
        raise RuntimeError(
            "AZURE_OPENAI_ENDPOINT is not set. Add it to your .env file."
        )
    assistant_id = _AGENT_IDS.get(agent_key, "")
    if not assistant_id:
        raise RuntimeError(
            f"No agent ID configured for '{agent_key}'. "
            f"Set {agent_key.upper()}_AGENT_ID in your .env file."
        )

    token_provider = get_bearer_token_provider(
        _make_credential(), "https://cognitiveservices.azure.com/.default"
    )
    async_openai = AsyncAzureOpenAI(
        azure_endpoint=_OPENAI_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version="2024-05-01-preview",
    )
    kwargs: Dict[str, Any] = {
        "deployment_name": _MODEL,
        "assistant_id": assistant_id,
        "async_client": async_openai,
    }
    if middleware:
        kwargs["middleware"] = middleware

    return AzureOpenAIAssistantsClient(**kwargs)


# ---------------------------------------------------------------------------
# Core invocation function
# ---------------------------------------------------------------------------

async def call_maf_agent(
    agent_key: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    *,
    event_queue: Optional[Any] = None,
    stream: bool = False,
) -> Dict[str, Any]:
    """
    Invoke a named MAF agent via the OpenAI Assistants API.

    Returns a dict compatible with legacy call_azure_agent():
        {
            "success": bool,
            "agent_key": str,
            "response": str | None,
            "tools_used": list[str],
            "error": str | None,
        }
    """
    from src.infrastructure.agents.maf.middleware import LoggingMiddleware

    middleware = [LoggingMiddleware(event_queue=event_queue, agent_name=agent_key)]

    if context:
        context_str = f"\n\nContext:\n{json.dumps(context, indent=2, default=str)}"
        full_message = message + context_str
    else:
        full_message = message

    tools_used: List[str] = []
    agent_tools = _AGENT_TOOL_MAP.get(agent_key, []) or None

    # Load system prompt from skills folder (falls back to empty string)
    instructions = ""
    try:
        instructions = get_agent_prompt(agent_key.replace("_", "-"))
    except Exception:
        pass

    try:
        client = get_maf_client(agent_key=agent_key, middleware=middleware)
        async with client.as_agent(
            name=f"zava-{agent_key.replace('_', '-')}",
            instructions=instructions or None,
            tools=agent_tools,
        ) as agent:
            if stream:
                stream_result = await agent.run(full_message, stream=True)
                final = await stream_result.get_final_response()
                response_text = str(final)
            else:
                result = await agent.run(full_message)
                response_text = str(result)

        return {
            "success": True,
            "agent_key": agent_key,
            "response": response_text,
            "tools_used": tools_used,
        }

    except Exception as exc:
        error_msg = f"MAF agent '{agent_key}' failed: {exc}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "agent_key": agent_key,
            "response": None,
            "tools_used": tools_used,
            "error": error_msg,
        }

