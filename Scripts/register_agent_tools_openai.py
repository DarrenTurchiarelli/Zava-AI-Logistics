"""Register Cosmos DB function tools with Microsoft Foundry prompt agents."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FunctionTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.infrastructure.agents.tools.cosmos_tools import CUSTOMER_SERVICE_TOOLS, DISPATCHER_TOOLS
from src.infrastructure.agents.core.prompt_loader import get_agent_prompt
from config.company import COMPANY_EMAIL, COMPANY_NAME, COMPANY_PHONE

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

load_dotenv(override=False)

AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
AZURE_AI_MODEL_DEPLOYMENT_NAME = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o")
CUSTOMER_SERVICE_AGENT_ID = os.getenv("CUSTOMER_SERVICE_AGENT_ID")
DISPATCHER_AGENT_ID = os.getenv("DISPATCHER_AGENT_ID")

print("=" * 70)
print("Registering Cosmos DB Tools with Azure AI Agents")
print("=" * 70)
print()

if not AZURE_AI_PROJECT_ENDPOINT:
    print("ERROR: AZURE_AI_PROJECT_ENDPOINT not set")
    sys.exit(1)

if not CUSTOMER_SERVICE_AGENT_ID:
    print("ERROR: CUSTOMER_SERVICE_AGENT_ID not set")
    print("   Run create_foundry_agents_openai.py first")
    sys.exit(1)

print(f"Connecting to Microsoft Foundry: {AZURE_AI_PROJECT_ENDPOINT}")
print()

client = AIProjectClient(
    endpoint=AZURE_AI_PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)

errors = 0


def convert_function_tools(tool_definitions):
    return [
        FunctionTool(
            name=tool["function"]["name"],
            description=tool["function"].get("description"),
            parameters=tool["function"]["parameters"],
            strict=False,
        )
        for tool in tool_definitions
    ]

# ---------------------------------------------------------------------------
# Customer Service Agent
# ---------------------------------------------------------------------------
print("-" * 70)
print("Customer Service Agent")
print("-" * 70)
try:
    base_prompt = get_agent_prompt("customer-service")
    enhanced_instructions = f"""{base_prompt}

## Company Information

- Company Name: {COMPANY_NAME}
- Support Phone: {COMPANY_PHONE}
- Support Email: {COMPANY_EMAIL}

## Tool Guidelines

**Available Tools:**
- `track_parcel` - Look up parcel by tracking number or barcode
- `search_parcels_by_recipient` - Search by recipient name/postcode/address
- `search_parcels_by_driver` - Search by driver name or ID
- `get_delivery_statistics` - Return delivery counts and status breakdown

**When to Use Tools:**
- Call `track_parcel` when customer asks about a specific tracking number
- Call `search_parcels_by_recipient` when searching by name/address
- NEVER call tools for general questions (hours, phone number, etc.)

## Response Guidelines

- Answer the customer question directly
- Be conversational and natural
- Keep responses concise
- Photos auto-display in UI - just acknowledge they exist
"""

    customer_service_tools = convert_function_tools(CUSTOMER_SERVICE_TOOLS)
    updated = client.agents.create_version(
        agent_name=CUSTOMER_SERVICE_AGENT_ID,
        description="Real-time customer inquiries and parcel tracking",
        metadata={"display_name": "Customer Service Agent"},
        definition=PromptAgentDefinition(
            model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
            instructions=enhanced_instructions,
            temperature=0.7,
            tools=customer_service_tools,
        ),
    )
    print(f"  Registered {len(customer_service_tools)} tools in version {updated.version}:")
    for tool in customer_service_tools:
        print(f"    - {tool.name}")
    print("  Customer Service Agent ready")
    print()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    errors += 1

# ---------------------------------------------------------------------------
# Dispatcher Agent
# ---------------------------------------------------------------------------
print("-" * 70)
print("Dispatcher Agent")
print("-" * 70)
if not DISPATCHER_AGENT_ID:
    print("  WARNING: DISPATCHER_AGENT_ID not set - skipping")
    print()
else:
    try:
        dispatcher_prompt = get_agent_prompt("dispatcher")
        dispatcher_tools = convert_function_tools(DISPATCHER_TOOLS)
        updated = client.agents.create_version(
            agent_name=DISPATCHER_AGENT_ID,
            description="Intelligent parcel-to-driver assignment",
            metadata={"display_name": "Dispatcher Agent"},
            definition=PromptAgentDefinition(
                model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
                instructions=dispatcher_prompt,
                temperature=0.3,
                tools=dispatcher_tools,
            ),
        )
        print(f"  Registered {len(dispatcher_tools)} tools in version {updated.version}:")
        for tool in dispatcher_tools:
            print(f"    - {tool.name}")
        print("  Dispatcher Agent ready")
        print()
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback; traceback.print_exc()
        errors += 1

if errors:
    print(f"Completed with {errors} error(s)")
    sys.exit(1)
else:
    print("All agents registered successfully")
    sys.exit(0)