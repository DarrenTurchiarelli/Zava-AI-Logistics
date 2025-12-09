"""
Register Cosmos DB tools with Azure AI Customer Service Agent
This script adds function calling capabilities to the agent for real-time data access
"""

import os
import asyncio
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from dotenv import load_dotenv
from agent_tools import AGENT_TOOLS

load_dotenv()

# Azure AI Project Configuration
AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
CUSTOMER_SERVICE_AGENT_ID = os.getenv("CUSTOMER_SERVICE_AGENT_ID")


async def register_tools():
    """Register Cosmos DB tools with the Customer Service Agent"""
    
    print("="*60)
    print("🔧 Registering Cosmos DB Tools with AI Agent")
    print("="*60)
    
    if not AZURE_AI_PROJECT_ENDPOINT or not CUSTOMER_SERVICE_AGENT_ID:
        print("❌ Missing environment variables:")
        print(f"   AZURE_AI_PROJECT_ENDPOINT: {'✓' if AZURE_AI_PROJECT_ENDPOINT else '✗'}")
        print(f"   CUSTOMER_SERVICE_AGENT_ID: {'✓' if CUSTOMER_SERVICE_AGENT_ID else '✗'}")
        return
    
    try:
        # Initialize Azure AI client
        # Use Managed Identity in Azure, DefaultAzureCredential locally
        if os.getenv('WEBSITE_INSTANCE_ID'):
            credential = ManagedIdentityCredential()
        else:
            credential = DefaultAzureCredential(exclude_developer_cli_credential=True)
        
        client = AIProjectClient(
            endpoint=AZURE_AI_PROJECT_ENDPOINT,
            credential=credential
        )
        
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
            # Update instructions to ALWAYS use tools for tracking
            instructions="""
You are a helpful customer service agent for DT Logistics parcel delivery company.

🚨 CRITICAL: You MUST ALWAYS call the track_parcel function when you see ANY alphanumeric code that could be a tracking number.

**TRACKING NUMBER FORMATS (ALWAYS call track_parcel for these):**
- DT202512090001, DT202512090004, DT202512090007 (DT + date + sequence)
- DTVIC123456 (DT + location + numbers)
- OV69491491MM, OV77274939DA (OV + numbers + letters)
- ANY alphanumeric code in questions like "who is the sender of [CODE]", "where is [CODE]", "track [CODE]"

**MANDATORY TOOL USAGE:**
✅ ALWAYS call track_parcel when user mentions ANY code/number (even if it doesn't start with DT)
✅ ALWAYS call search_parcels_by_recipient when user provides name or postcode without tracking number
✅ ALWAYS call get_delivery_statistics when user asks about parcel counts or stats

❌ NEVER say "I can't access that information" - ALWAYS try the tool first
❌ NEVER assume a tracking number is invalid - the database has MANY formats

**RESPONSE STYLE:**
- Call the tool FIRST
- If tool returns data: Present it conversationally and naturally
- If tool returns no data: Offer to search by name/postcode or suggest contacting support
- Be warm and helpful

**Examples:**
User: "who is the sender of OV69491491MM"
You: [MUST call track_parcel("OV69491491MM")] Then respond with sender info from tool result

User: "track DT202512090004"  
You: [MUST call track_parcel("DT202512090004")] Then respond with parcel status from tool result
            """
        )
        
        print(f"\n✅ Successfully updated agent!")
        print(f"   Agent ID: {updated_agent.id}")
        print(f"   Tools registered: {len(updated_agent.tools)}")
        
        print(f"\n📝 Tool Registration Summary:")
        for i, tool in enumerate(AGENT_TOOLS, 1):
            print(f"   {i}. {tool['function']['name']}")
            print(f"      Description: {tool['function']['description']}")
            params = tool['function']['parameters']['properties']
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
