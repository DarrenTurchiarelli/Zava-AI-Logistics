"""
MAF v1.0 agent caller using Agent + OpenAIChatClient.

Uses the MAF v1.0 SDK pattern:
  - Agent(client=OpenAIChatClient(...), instructions=..., tools=[...])
  - OpenAIChatClient with AsyncAzureOpenAI passed as async_client to bypass
    any stale AZURE_OPENAI_API_KEY env var (key auth is disabled on this resource)
  - Chat Completions / Responses API (api_version 2025-03-01-preview+)
  - No asst_XXX IDs needed -- instructions and tools live in Agent directly

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

from agent_framework import Agent
from agent_framework.openai import OpenAIChatCompletionClient
from azure.identity.aio import (
    DefaultAzureCredential,
    ManagedIdentityCredential,
    get_bearer_token_provider,
)
from openai.lib.azure import AsyncAzureOpenAI

from src.infrastructure.agents.core.prompt_loader import get_agent_prompt
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

_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
_MODEL: str = (
    os.getenv("FOUNDRY_MODEL_DEPLOYMENT_NAME")
    or os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    or "gpt-4o"
)

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


def _make_credential():
    if os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true":
        return ManagedIdentityCredential()
    return DefaultAzureCredential(
        exclude_managed_identity_credential=True,
        exclude_visual_studio_code_credential=True,
        additionally_allowed_tenants=["*"],
    )


def make_chat_client(middleware: Optional[list] = None) -> OpenAIChatCompletionClient:
    """Build an OpenAIChatClient wired to the Azure OpenAI endpoint."""
    if not _OPENAI_ENDPOINT:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT is not set. Add it to your .env file.")
    token_provider = get_bearer_token_provider(
        _make_credential(), "https://cognitiveservices.azure.com/.default"
    )
    async_openai = AsyncAzureOpenAI(
        azure_endpoint=_OPENAI_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version="2025-03-01-preview",
    )
    kwargs: Dict[str, Any] = {"model": _MODEL, "async_client": async_openai}
    if middleware:
        kwargs["middleware"] = middleware
    return OpenAIChatCompletionClient(**kwargs)


def make_agent(
    agent_key: str,
    *,
    client: Optional[OpenAIChatCompletionClient] = None,
    middleware: Optional[list] = None,
) -> Agent:
    """Build a MAF v1.0 Agent for the given agent_key."""
    instructions = ""
    try:
        instructions = get_agent_prompt(agent_key.replace("_", "-"))
    except Exception:
        pass
    agent_tools = _AGENT_TOOL_MAP.get(agent_key) or None
    chat_client = client or make_chat_client(middleware=middleware)
    return Agent(
        client=chat_client,
        name=f"zava-{agent_key.replace('_', '-')}",
        instructions=instructions or None,
        tools=agent_tools,
    )


async def call_maf_agent(
    agent_key: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    *,
    event_queue: Optional[Any] = None,
    stream: bool = False,
) -> Dict[str, Any]:
    """
    Invoke a named MAF agent; returns dict compatible with legacy call_azure_agent().
    """
    from src.infrastructure.agents.maf.middleware import LoggingMiddleware

    middleware = [LoggingMiddleware(event_queue=event_queue, agent_name=agent_key)]

    if context:
        context_str = f"\n\nContext:\n{json.dumps(context, indent=2, default=str)}"
        full_message = message + context_str
    else:
        full_message = message

    tools_used: List[str] = []

    try:
        agent = make_agent(agent_key, middleware=middleware)
        if stream:
            stream_result = await agent.run(full_message, stream=True)
            final = await stream_result.get_final_response()
            response_text = str(final)
        else:
            result = await agent.run(full_message)
            response_text = str(result)

        return {"success": True, "agent_key": agent_key, "response": response_text, "tools_used": tools_used}

    except Exception as exc:
        error_msg = f"MAF agent '{agent_key}' failed: {exc}"
        print(f"❌ {error_msg}")
        return {"success": False, "agent_key": agent_key, "response": None, "tools_used": tools_used, "error": error_msg}
