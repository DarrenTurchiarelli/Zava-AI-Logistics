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
from agent_framework.azure import AzureAIClient
from azure.ai.agentserver.agentframework import from_agent_framework
from azure.identity.aio import DefaultAzureCredential, ManagedIdentityCredential

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


def _credential():
    if os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true":
        return ManagedIdentityCredential()
    return DefaultAzureCredential(
        exclude_managed_identity_credential=True,
        exclude_visual_studio_code_credential=True,
        additionally_allowed_tenants=["*"],
    )


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

async def _build_workflow_agent(maf_client: AzureAIClient):
    """
    Create the persistent Customer Service agent and wrap it in a
    single-node WorkflowBuilder, then call .as_agent() to produce a
    value suitable for from_agent_framework().
    """
    instructions = ""
    try:
        instructions = get_agent_prompt("customer-service")
    except Exception:
        pass

    cs_agent_ctx = maf_client.as_agent(
        name="zava-customer-service",
        instructions=instructions,
        tools=[track_parcel, search_parcels_by_recipient, search_parcels_by_driver],
    )
    # Enter the async context manager to get the live agent handle
    cs_agent = await cs_agent_ctx.__aenter__()

    executor = CustomerServiceExecutor(cs_agent)
    workflow_agent = (
        WorkflowBuilder(start_executor=executor)
        .build()
        .as_agent(
            name="Zava Customer Service",
            instructions=instructions,
        )
    )
    return workflow_agent, cs_agent_ctx


async def run_server() -> None:
    """Start the HTTP server for the Agent Inspector."""
    if not _FOUNDRY_ENDPOINT:
        sys.exit(
            "❌  FOUNDRY_PROJECT_ENDPOINT (or AZURE_AI_PROJECT_ENDPOINT) is not set.\n"
            "    Add it to your .env file and try again."
        )

    maf_client = AzureAIClient(
        project_endpoint=_FOUNDRY_ENDPOINT,
        model_deployment_name=_MODEL,
        credential=_credential(),
    )

    workflow_agent, _ctx = await _build_workflow_agent(maf_client)
    print("✅  Zava Customer Service Agent ready — starting HTTP server …")
    await from_agent_framework(workflow_agent).run_async()


async def run_cli() -> None:
    """Interactive terminal loop — useful for quick smoke-tests."""
    if not _FOUNDRY_ENDPOINT:
        sys.exit(
            "❌  FOUNDRY_PROJECT_ENDPOINT (or AZURE_AI_PROJECT_ENDPOINT) is not set."
        )

    instructions = ""
    try:
        instructions = get_agent_prompt("customer-service")
    except Exception:
        pass

    maf_client = AzureAIClient(
        project_endpoint=_FOUNDRY_ENDPOINT,
        model_deployment_name=_MODEL,
        credential=_credential(),
    )

    async with maf_client.as_agent(
        name="zava-customer-service",
        instructions=instructions,
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
