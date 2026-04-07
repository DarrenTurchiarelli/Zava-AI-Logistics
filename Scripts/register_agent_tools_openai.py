"""
Register Cosmos DB tools with AI Agents (Customer Service + Dispatcher).
Uses Azure OpenAI Assistants API directly.
Runs during deployment to enable agent data access.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

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

load_dotenv(override=True)

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
CUSTOMER_SERVICE_AGENT_ID = os.getenv("CUSTOMER_SERVICE_AGENT_ID")
DISPATCHER_AGENT_ID = os.getenv("DISPATCHER_AGENT_ID")

print("=" * 70)
print("Registering Cosmos DB Tools with Azure AI Agents")
print("=" * 70)
print()

if not AZURE_OPENAI_ENDPOINT:
    print("ERROR: AZURE_OPENAI_ENDPOINT not set")
    sys.exit(1)

if not CUSTOMER_SERVICE_AGENT_ID:
    print("ERROR: CUSTOMER_SERVICE_AGENT_ID not set")
    print("   Run create_foundry_agents_openai.py first")
    sys.exit(1)

print(f"Connecting to Azure OpenAI: {AZURE_OPENAI_ENDPOINT}")
print()

credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")
client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    azure_ad_token_provider=token_provider,
    api_version="2024-05-01-preview",
)

errors = 0

# ---------------------------------------------------------------------------
# Customer Service Agent
# ---------------------------------------------------------------------------
print("-" * 70)
print("Customer Service Agent")
print("-" * 70)
try:
    agent = client.beta.assistants.retrieve(CUSTOMER_SERVICE_AGENT_ID)
    print(f"  Found: {agent.name}  (current tools: {len(agent.tools) if agent.tools else 0})")

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

    updated = client.beta.assistants.update(
        CUSTOMER_SERVICE_AGENT_ID,
        tools=CUSTOMER_SERVICE_TOOLS,
        instructions=enhanced_instructions,
    )
    print(f"  Registered {len(updated.tools)} tools:")
    for t in updated.tools:
        if hasattr(t, "function"):
            print(f"    - {t.function.name}")
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
        agent = client.beta.assistants.retrieve(DISPATCHER_AGENT_ID)
        print(f"  Found: {agent.name}  (current tools: {len(agent.tools) if agent.tools else 0})")

        dispatcher_prompt = get_agent_prompt("dispatcher")

        updated = client.beta.assistants.update(
            DISPATCHER_AGENT_ID,
            tools=DISPATCHER_TOOLS,
            instructions=dispatcher_prompt,
        )
        print(f"  Registered {len(updated.tools)} tools:")
        for t in updated.tools:
            if hasattr(t, "function"):
                print(f"    - {t.function.name}")
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