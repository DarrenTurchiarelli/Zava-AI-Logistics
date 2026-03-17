"""
Register Cosmos DB tools with Azure AI Customer Service Agent
This script adds function calling capabilities to the agent for real-time data access
"""

import asyncio
import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from dotenv import load_dotenv

from agent_tools import AGENT_TOOLS
from config.company import COMPANY_EMAIL, COMPANY_NAME, COMPANY_PHONE

load_dotenv()

# Azure AI Project Configuration
AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
CUSTOMER_SERVICE_AGENT_ID = os.getenv("CUSTOMER_SERVICE_AGENT_ID")


async def register_tools():
    """Register Cosmos DB tools with the Customer Service Agent"""

    print("=" * 60)
    print("🔧 Registering Cosmos DB Tools with AI Agent")
    print("=" * 60)

    if not AZURE_AI_PROJECT_ENDPOINT or not CUSTOMER_SERVICE_AGENT_ID:
        print("❌ Missing environment variables:")
        print(f"   AZURE_AI_PROJECT_ENDPOINT: {'✓' if AZURE_AI_PROJECT_ENDPOINT else '✗'}")
        print(f"   CUSTOMER_SERVICE_AGENT_ID: {'✓' if CUSTOMER_SERVICE_AGENT_ID else '✗'}")
        return

    try:
        # Initialize Azure AI client
        # Use Managed Identity when explicitly enabled (Azure deployment)
        if os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true":
            credential = ManagedIdentityCredential()
        else:
            credential = DefaultAzureCredential(exclude_developer_cli_credential=True)

        client = AIProjectClient(endpoint=AZURE_AI_PROJECT_ENDPOINT, credential=credential)

        print(f"\n📡 Connected to Azure AI Project")
        print(f"   Endpoint: {AZURE_AI_PROJECT_ENDPOINT}")
        print(f"   Agent ID: {CUSTOMER_SERVICE_AGENT_ID}")

        # Get current agent configuration
        print(f"\n📋 Retrieving current agent configuration...")
        agent = client.agents.get_agent(CUSTOMER_SERVICE_AGENT_ID)

        print(f"   Agent Name: {agent.name}")
        print(f"   Model: {agent.model}")
        print(f"   Current Tools: {len(agent.tools) if agent.tools else 0}")

        # Update agent with Cosmos DB tools
        print(f"\n🔧 Registering {len(AGENT_TOOLS)} Cosmos DB tools...")

        for tool in AGENT_TOOLS:
            print(f"   ✓ {tool['function']['name']}: {tool['function']['description'][:60]}...")

        # Update the agent with new tools
        updated_agent = client.agents.update_agent(
            agent_id=CUSTOMER_SERVICE_AGENT_ID,
            tools=AGENT_TOOLS,
            instructions=f"""You are a helpful customer service agent for {COMPANY_NAME} parcel delivery.

CORE PRINCIPLE:
- ALWAYS answer the customer's actual question first
- Only use tools or show parcel data when the customer specifically asks about a parcel, tracking, or delivery
- For general questions (phone number, business hours, services, etc.), answer directly from your knowledge and the context provided - do NOT call any tools

TOOL USAGE (only when relevant):
- Call track_parcel ONLY when the customer provides or asks about a specific tracking number
- Call search_parcels_by_recipient ONLY when the customer asks to find parcels by name/postcode
- Call get_delivery_statistics ONLY when the customer asks about delivery stats
- NEVER call tools proactively for general inquiries

RESPONSE STYLE:
- Be conversational, friendly, and natural
- Answer the question asked - don't volunteer unrelated parcel information
- Keep responses concise and helpful
- Use plain text, avoid excessive markdown formatting

WHEN SHOWING PARCEL DATA (only if asked):
- Use • bullets with blank lines between events
- Each detail on its own line

PHOTO HANDLING (only when parcel data is shown):
- When parcel data shows lodgement_photos or delivery_photos exist (non-empty arrays):
  * Acknowledge they are on file
  * Do NOT say "displayed below" or "attached" unless the context says photos will be auto-displayed
- When no photos exist (empty arrays), don't mention photos at all""",
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
