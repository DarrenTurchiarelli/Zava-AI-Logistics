"""
MAF AzureAIClient-based agent caller.

Replaces the raw-OpenAI Assistants API polling loop in base.py with the
MAF SDK primitives:
  - AzureAIClient  (connects to Azure AI Foundry project)
  - as_agent()     (creates / reuses a named persistent agent)
  - agent.run()    (single-turn invocation with automatic tool dispatch)

Each agent is lazily constructed the first time it is called, then cached
for the process lifetime (persistent sessions).

Feature flag: set USE_MAF=true in .env to activate this path.  While
USE_MAF is absent or false the legacy call_azure_agent() in base.py is
used unchanged.
"""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv(override=False)

# ---------------------------------------------------------------------------
# MAF SDK imports
# ---------------------------------------------------------------------------
from agent_framework.azure import AzureAIClient
from azure.identity.aio import (
    DefaultAzureCredential,
    ManagedIdentityCredential,
)

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

_FOUNDRY_ENDPOINT: str = (
    os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    or ""
)
_MODEL: str = (
    os.getenv("FOUNDRY_MODEL_DEPLOYMENT_NAME")
    or os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    or "gpt-4o"
)

# Tool sets per agent role
_CUSTOMER_SERVICE_TOOLS = [
    track_parcel,
    search_parcels_by_recipient,
    search_parcels_by_driver,
]
_DISPATCHER_TOOLS = [
    get_pending_parcels_for_dispatch,
    get_available_drivers,
    get_delivery_statistics,
]
_OPTIMIZATION_TOOLS = [
    get_performance_metrics,
    get_delivery_statistics,
]
_DRIVER_TOOLS = [
    track_parcel,
    update_delivery_status,
]


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
# AzureAIClient factory
# ---------------------------------------------------------------------------

def get_maf_client(
    *,
    middleware: Optional[list] = None,
) -> AzureAIClient:
    """
    Build a fresh AzureAIClient connected to the Foundry project.

    A new client is returned each call; credential objects are async
    so they must not be shared across threads.
    """
    if not _FOUNDRY_ENDPOINT:
        raise RuntimeError(
            "FOUNDRY_PROJECT_ENDPOINT (or AZURE_AI_PROJECT_ENDPOINT) is not set. "
            "Add it to your .env file."
        )
    kwargs: Dict[str, Any] = {
        "project_endpoint": _FOUNDRY_ENDPOINT,
        "model_deployment_name": _MODEL,
        "credential": _make_credential(),
    }
    if middleware:
        kwargs["middleware"] = middleware
    return AzureAIClient(**kwargs)


# ---------------------------------------------------------------------------
# Per-agent name → tool list mapping
# ---------------------------------------------------------------------------

_AGENT_TOOL_MAP: Dict[str, list] = {
    "customer_service": _CUSTOMER_SERVICE_TOOLS,
    "fraud_risk": [],
    "identity": [],
    "dispatcher": _DISPATCHER_TOOLS,
    "parcel_intake": [],
    "sorting_facility": [],
    "delivery_coordination": [],
    "optimization": _OPTIMIZATION_TOOLS,
    "driver": _DRIVER_TOOLS,
}


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
    Invoke a named MAF agent and return a dict compatible with the
    legacy call_azure_agent() return shape.

    Args:
        agent_key:   Logical agent name used in _AGENT_TOOL_MAP, e.g.
                     'customer_service', 'fraud_risk', etc.
        message:     User / system message to send.
        context:     Optional extra context dict appended to the message.
        event_queue: Optional asyncio Queue for SSE streaming events.
        stream:      If True, enable MAF streaming (get_final_response).

    Returns:
        {
            "success": bool,
            "agent_key": str,
            "response": str | None,
            "tools_used": list[str],
            "error": str | None,          # present only on failure
        }
    """
    from src.infrastructure.agents.maf.middleware import LoggingMiddleware

    middleware = [LoggingMiddleware(event_queue=event_queue, agent_name=agent_key)]

    if context:
        context_str = f"\n\nContext:\n{json.dumps(context, indent=2, default=str)}"
        full_message = message + context_str
    else:
        full_message = message

    agent_tools = _AGENT_TOOL_MAP.get(agent_key, [])

    # Load system prompt from skills folder (falls back to empty string)
    try:
        instructions = get_agent_prompt(agent_key.replace("_", "-"))
    except Exception:
        instructions = ""

    tools_used: List[str] = []

    try:
        client = get_maf_client(middleware=middleware)
        async with client.as_agent(
            name=f"zava-{agent_key.replace('_', '-')}",
            instructions=instructions,
            tools=agent_tools if agent_tools else None,
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
