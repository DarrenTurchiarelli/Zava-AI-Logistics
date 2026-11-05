"""Validate or explicitly register the dedicated Foundry Demand Planning agent."""

import argparse
import json
import os
import sys
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.infrastructure.agents.demand_planner_chat import agent_definition


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", action="store_true", help="Explicitly create a new remote agent version.")
    parser.add_argument("--name", default="demand-planner", help="Dedicated Foundry agent name.")
    parser.add_argument("--model", help="Existing project model deployment; defaults to application configuration.")
    args = parser.parse_args()
    load_dotenv(override=False)
    definition = agent_definition(args.model or os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o"))
    if not args.register:
        print(json.dumps({"name": args.name, "definition": definition.as_dict()}, indent=2))
        print("Local definition only. No agent registered or Azure resources changed.", file=sys.stderr)
        return
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "").strip()
    if not endpoint:
        parser.error("AZURE_AI_PROJECT_ENDPOINT must identify the target Foundry project.")
    with DefaultAzureCredential(
        exclude_managed_identity_credential=True, exclude_visual_studio_code_credential=True,
    ) as credential, AIProjectClient(endpoint=endpoint, credential=credential) as client:
        agent = client.agents.create_version(
            agent_name=args.name,
            description="Read-only parcel demand and capacity planning with deterministic workload, simulation and cost-comparison tools.",
            definition=definition,
        )
    print(f"DEMAND_PLANNER_AGENT_NAME={agent.name}")
    print(f"DEMAND_PLANNER_AGENT_VERSION={agent.version}")


if __name__ == "__main__":
    main()
