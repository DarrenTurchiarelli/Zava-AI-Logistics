"""
MAF HTTP server entry point for Zava Customer Service Agent.

Exposes the Customer Service Agent as an HTTP REST endpoint using the
azure.ai.agentserver.agentframework package.  This enables:
  - AI Toolkit Agent Inspector for interactive testing
  - agentdev CLI for local debugging with breakpoints
  - Full streaming via Server-Sent Events
  - Future: containerised deployment to Azure AI Foundry

Usage:
    # HTTP server (default — works with Agent Inspector):
    python src/infrastructure/agents/maf_agent_server.py --server

    # CLI mode (simpler, for quick terminal testing):
    python src/infrastructure/agents/maf_agent_server.py --cli

    # Wrapped with debugpy + agentdev for VS Code debugging:
    python -m debugpy --listen 127.0.0.1:5679 \\
           -m agentdev run src/infrastructure/agents/maf_agent_server.py \\
           --verbose --port 8088 -- --server
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Ensure the workspace root is on sys.path so `src.*` imports resolve whether
# this script is run directly (python maf_agent_server.py) or via agentdev.
_ROOT = Path(__file__).resolve().parents[3]  # …/Zava-AI-Logistics
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# NOTE: override=True so env vars in deployed environment take precedence
# over .env defaults.  This is intentional for server / container mode.
from dotenv import load_dotenv

load_dotenv(override=True)

# ---------------------------------------------------------------------------
# MAF SDK
# ---------------------------------------------------------------------------
from agent_framework import (
    AgentResponseUpdate,
    Content,
    Message,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)
from agent_framework.azure import AzureOpenAIAssistantsClient
from azure.identity.aio import DefaultAzureCredential, ManagedIdentityCredential, get_bearer_token_provider
from openai.lib.azure import AsyncAzureOpenAI

# NOTE: azure.ai.agentserver is imported lazily in run_server() to avoid its
# module-level init fetching an AZURE_OPENAI_API_KEY from the project discovery
# endpoint and polluting the environment, which breaks credential-based auth.
# NOTE: We build AsyncAzureOpenAI ourselves (passing async_client=...) so that
# AzureOpenAIAssistantsClient skips its env-var api_key lookup entirely.

# ---------------------------------------------------------------------------
# Local tools and prompt
# ---------------------------------------------------------------------------
from src.infrastructure.agents.core.prompt_loader import get_agent_prompt
from src.infrastructure.agents.maf.tools import (
    search_parcels_by_recipient,
    track_parcel,
    search_parcels_by_driver,
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
_CS_AGENT_ID: str = os.getenv("CUSTOMER_SERVICE_AGENT_ID", "")


def _credential():
    if os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true":
        return ManagedIdentityCredential()
    return DefaultAzureCredential(
        exclude_managed_identity_credential=True,
        exclude_visual_studio_code_credential=True,
        additionally_allowed_tenants=["*"],
    )


def _make_assistants_client(middleware=None) -> AzureOpenAIAssistantsClient:
    """Build an AzureOpenAIAssistantsClient for the Customer Service agent.

    We construct AsyncAzureOpenAI ourselves (using an Azure AD token provider
    from the DefaultAzureCredential) and pass it as async_client so that
    AzureOpenAIAssistantsClient skips its own env-var api_key resolution.
    This avoids a stale AZURE_OPENAI_API_KEY user env var from overriding
    credential-based auth on resources where key auth is disabled.
    """
    token_provider = get_bearer_token_provider(
        _credential(), "https://cognitiveservices.azure.com/.default"
    )
    async_openai = AsyncAzureOpenAI(
        azure_endpoint=_OPENAI_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version="2024-05-01-preview",
    )
    kwargs: dict = {
        "deployment_name": _MODEL,
        "assistant_id": _CS_AGENT_ID,
        "async_client": async_openai,
    }
    if middleware:
        kwargs["middleware"] = middleware
    return AzureOpenAIAssistantsClient(**kwargs)


# ---------------------------------------------------------------------------
# Executor: wraps the persistent MAF agent with the @handler contract
# ---------------------------------------------------------------------------

class CustomerServiceExecutor:
    """
    Wraps the Customer Service AzureAI agent as a MAF workflow executor.

    The @handler method is called by WorkflowBuilder for each incoming
    message.  It forwards the messages to the agent and streams the
    response back via ctx.yield_output().
    """

    def __init__(self, agent) -> None:
        self._agent = agent
        self.id = "zava-customer-service"

    @handler
    async def on_message(
        self,
        messages: list[Message],
        ctx: WorkflowContext,
    ) -> None:
        response = await self._agent.run(messages)
        await ctx.yield_output(
            AgentResponseUpdate(
                contents=[Content("text", text=str(response))],
                role="assistant",
                author_name=self.id,
            )
        )


# ---------------------------------------------------------------------------
# Build & serve
# ---------------------------------------------------------------------------

async def _build_workflow_agent():
    """
    Create the Customer Service agent using AzureOpenAIAssistantsClient and
    wrap it in a single-node WorkflowBuilder for HTTP server mode.
    """
    instructions = ""
    try:
        instructions = get_agent_prompt("customer-service")
    except Exception:
        pass

    client = _make_assistants_client()
    cs_agent_ctx = client.as_agent(
        name="zava-customer-service",
        instructions=instructions or None,
        tools=[track_parcel, search_parcels_by_recipient, search_parcels_by_driver],
    )
    cs_agent = await cs_agent_ctx.__aenter__()

    executor = CustomerServiceExecutor(cs_agent)
    workflow_agent = (
        WorkflowBuilder(start_executor=executor)
        .build()
        .as_agent(
            name="Zava Customer Service",
            instructions=instructions or None,
        )
    )
    return workflow_agent, cs_agent_ctx


async def run_server() -> None:
    """Start the HTTP server for the Agent Inspector."""
    # Import lazily so module-level init in agentserver does not run during CLI mode.
    from azure.ai.agentserver.agentframework import from_agent_framework  # noqa: PLC0415

    if not _OPENAI_ENDPOINT or not _CS_AGENT_ID:
        sys.exit(
            "❌  AZURE_OPENAI_ENDPOINT and CUSTOMER_SERVICE_AGENT_ID must be set.\n"
            "    Add them to your .env file and try again."
        )

    workflow_agent, _ctx = await _build_workflow_agent()
    print("✅  Zava Customer Service Agent ready — starting HTTP server …")
    await from_agent_framework(workflow_agent).run_async()


async def run_cli() -> None:
    """Interactive terminal loop — useful for quick smoke-tests."""
    if not _OPENAI_ENDPOINT or not _CS_AGENT_ID:
        sys.exit(
            "❌  AZURE_OPENAI_ENDPOINT and CUSTOMER_SERVICE_AGENT_ID must be set."
        )

    instructions = ""
    try:
        instructions = get_agent_prompt("customer-service")
    except Exception:
        pass

    client = _make_assistants_client()
    async with client.as_agent(
        name="zava-customer-service",
        instructions=instructions or None,
        tools=[track_parcel, search_parcels_by_recipient, search_parcels_by_driver],
    ) as agent:
        print("Zava Customer Service Agent  (type 'exit' to quit)\n")
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if user_input.lower() in {"exit", "quit"}:
                break
            if not user_input:
                continue
            result = await agent.run(user_input)
            print(f"\nAgent: {result}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Zava MAF Customer Service Agent server"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--server", action="store_true", help="Run as HTTP server (default)")
    group.add_argument("--cli", action="store_true", help="Run as interactive CLI")
    args = parser.parse_args()

    if args.cli:
        asyncio.run(run_cli())
    else:
        asyncio.run(run_server())
