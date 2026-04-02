"""
Register Cosmos DB tools with Customer Service Agent
Uses Azure Open AI Assistants API directly (same pattern as create_foundry_agents_openai.py)
Runs during deployment to enable agent data access
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from agent_tools import AGENT_TOOLS
from agents.prompt_loader import get_agent_prompt
from config.company import COMPANY_EMAIL, COMPANY_NAME, COMPANY_PHONE

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

load_dotenv()

# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")  # Set during deployment
CUSTOMER_SERVICE_AGENT_ID = os.getenv("CUSTOMER_SERVICE_AGENT_ID")

print("=" * 70)
print("🔧 Registering Cosmos DB Tools with Customer Service Agent")
print("=" * 70)
print()

# Validate environment
if not AZURE_OPENAI_ENDPOINT:
    print("❌ AZURE_OPENAI_ENDPOINT not set")
    sys.exit(1)

if not CUSTOMER_SERVICE_AGENT_ID:
    print("❌ CUSTOMER_SERVICE_AGENT_ID not set")
    print("   Run create_foundry_agents_openai.py first")
    sys.exit(1)

if not AZURE_OPENAI_API_KEY:
    print("❌ AZURE_OPENAI_API_KEY not set")
    print("   This script requires API key during deployment")
    print("   The key is temporarily enabled, then disabled after registration")
    sys.exit(1)

print(f"📡 Connecting to Azure OpenAI")
print(f"   Endpoint: {AZURE_OPENAI_ENDPOINT}")
print(f"   Agent ID: {CUSTOMER_SERVICE_AGENT_ID}")
print()

# Create OpenAI client with API key
client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2024-05-01-preview"
)

try:
    # Get current agent
    print("📋 Retrieving agent...")
    agent = client.beta.assistants.retrieve(CUSTOMER_SERVICE_AGENT_ID)
    
    print(f"   ✓ Found: {agent.name}")
    print(f"   Model: {agent.model}")
    print(f"   Current tools: {len(agent.tools) if agent.tools else 0}")
    print()
    
    # Load system prompt
    print("📄 Loading system prompt from Agent-Skills/customer-service/...")
    base_prompt = get_agent_prompt("customer-service")
    
    # Enhance with company info and tool guidelines
    enhanced_instructions = f"""{base_prompt}

## Company Information

- Company Name: {COMPANY_NAME}
- Support Phone: {COMPANY_PHONE}
- Support Email: {COMPANY_EMAIL}

## Tool Guidelines

**Available Tools:**
- `track_parcel_tool` - Look up parcel by tracking number or barcode
- `search_parcels_by_recipient_tool` - Search by recipient name/postcode/address

**When to Use Tools:**
- Call `track_parcel_tool` when customer asks about a specific tracking number
- Call `search_parcels_by_recipient_tool` when searching by name/address
- NEVER call tools for general questions (hours, phone number, etc.)

## Response Guidelines

- Answer the customer's question directly
- Be conversational and natural  
- Keep responses concise
- Photos auto-display in UI - just acknowledge they exist
"""
    
    # Register tools
    print(f"🔧 Registering {len(AGENT_TOOLS)} Cosmos DB tools...")
    for tool in AGENT_TOOLS:
        print(f"   ✓ {tool['function']['name']}")
    print()
    
    # Update agent with tools
    updated_agent = client.beta.assistants.update(
        assistant_id=CUSTOMER_SERVICE_AGENT_ID,
        tools=AGENT_TOOLS,
        instructions=enhanced_instructions
    )
    
    print(f"✅ Successfully registered tools!")
    print(f"   Agent: {updated_agent.name}")
    print(f"   Tools: {len(updated_agent.tools)}")
    print()
    
    print("📝 Registered Tools:")
    for i, tool in enumerate(AGENT_TOOLS, 1):
        func_name = tool['function']['name']
        func_desc = tool['function']['description']
        print(f"   {i}. {func_name}")
        print(f"      {func_desc}")
    print()
    
    print("✅ Customer Service Agent ready!")
    print("   The agent can now access Cosmos DB for parcel tracking")
    print()
    
    sys.exit(0)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
