"""
Register Cosmos DB tools with Azure AI Customer Service Agent
This script adds function calling capabilities to the agent for real-time data access
"""

import asyncio
import os

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential, get_bearer_token_provider
from dotenv import load_dotenv

from agent_tools import AGENT_TOOLS
from src.infrastructure.agents import get_agent_prompt
from config.company import COMPANY_EMAIL, COMPANY_NAME, COMPANY_PHONE

load_dotenv()

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
CUSTOMER_SERVICE_AGENT_ID = os.getenv("CUSTOMER_SERVICE_AGENT_ID")


async def register_tools():
    """Register Cosmos DB tools with the Customer Service Agent"""

    print("=" * 60)
    print("🔧 Registering Cosmos DB Tools with AI Agent")
    print("=" * 60)

    if not AZURE_OPENAI_ENDPOINT or not CUSTOMER_SERVICE_AGENT_ID:
        print("❌ Missing environment variables:")
        print(f"   AZURE_OPENAI_ENDPOINT: {'✓' if AZURE_OPENAI_ENDPOINT else '✗'}")
        print(f"   CUSTOMER_SERVICE_AGENT_ID: {'✓' if CUSTOMER_SERVICE_AGENT_ID else '✗'}")
        return

    try:
        # Initialize Azure OpenAI client with token credential (no API key)
        if os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true":
            credential = ManagedIdentityCredential()
        else:
            credential = DefaultAzureCredential(exclude_developer_cli_credential=True)

        token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")
        client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            azure_ad_token_provider=token_provider,
            api_version="2024-05-01-preview"
        )

        print(f"\n📡 Connected to Azure OpenAI")
        print(f"   Endpoint: {AZURE_OPENAI_ENDPOINT}")
        print(f"   Agent ID: {CUSTOMER_SERVICE_AGENT_ID}")

        # Get current agent configuration
        print(f"\n📋 Retrieving current agent configuration...")
        agent = client.beta.assistants.retrieve(CUSTOMER_SERVICE_AGENT_ID)

        print(f"   Agent Name: {agent.name}")
        print(f"   Model: {agent.model}")
        print(f"   Current Tools: {len(agent.tools) if agent.tools else 0}")

        # Update agent with Cosmos DB tools
        print(f"\n🔧 Registering {len(AGENT_TOOLS)} Cosmos DB tools...")

        for tool in AGENT_TOOLS:
            print(f"   ✓ {tool['function']['name']}: {tool['function']['description'][:60]}...")

        # Load system prompt from Agent-Skills folder
        print(f"\n📄 Loading system prompt from Agent-Skills/customer-service/...")
        base_prompt = get_agent_prompt("customer-service")
        
        # Enhance prompt with company-specific information
        enhanced_instructions = f"""{base_prompt}

## Company Information

- Company Name: {COMPANY_NAME}
- Support Phone: {COMPANY_PHONE}
- Support Email: {COMPANY_EMAIL}

## Tool Guidelines

**Available Tools:**
- `track_parcel_tool` - Look up parcel by tracking number
- `search_parcels_by_recipient_tool` - Search parcels by recipient details
- `get_delivery_statistics` - Get delivery performance statistics

**When to Use Tools:**
- Call `track_parcel` ONLY when customer provides or asks about a specific tracking number
- Call `search_parcels_by_recipient` ONLY when customer asks to find parcels by name/postcode
- Call `get_delivery_statistics` ONLY when customer asks about delivery stats
- NEVER call tools proactively for general inquiries (phone number, hours, services, etc.)

## Response Guidelines

- Answer the customer's actual question first
- Be conversational, friendly, and natural
- Keep responses concise and helpful
- Use plain text, avoid excessive markdown formatting
"""

        # Update the agent with new tools
        updated_agent = client.beta.assistants.update(
            CUSTOMER_SERVICE_AGENT_ID,
            tools=AGENT_TOOLS,
            instructions=enhanced_instructions,
        )

        print(f"\n✅ Successfully updated agent!")
        print(f"   Agent ID: {updated_agent.id}")
        print(f"   Tools registered: {len(updated_agent.tools)}")

        print(f"\n📝 Tool Registration Summary:")
        for i, tool in enumerate(AGENT_TOOLS, 1):
            print(f"   {i}. {tool['function']['name']}")
            print(f"      Description: {tool['function']['description']}")
            params = tool["function"]["parameters"]["properties"]
            print(f"      Parameters: {', '.join(params.keys())}")

        print(f"\n✅ Agent is now ready to use Cosmos DB tools for real-time data!")
        print(f"\n💡 Next Steps:")
        print(f"   1. Test the agent with: 'Track parcel DT202512090001'")
        print(f"   2. The agent will call track_parcel tool automatically")
        print(f"   3. Monitor tool calls in Azure AI Foundry portal")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(register_tools())
