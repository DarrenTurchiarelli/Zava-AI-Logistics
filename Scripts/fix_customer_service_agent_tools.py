"""
Fix Customer Service Agent - Remove Built-in Tools
This script updates the Customer Service Agent to remove built-in tools (code_interpreter, Azure CLI)
that are causing "Failed to invoke the Azure CLI" errors.
The agent should only use custom function tools registered via register_agent_tools.py
"""

import os
import asyncio
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()

AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
CUSTOMER_SERVICE_AGENT_ID = os.getenv("CUSTOMER_SERVICE_AGENT_ID")


async def fix_agent():
    """Update Customer Service Agent to remove built-in tools"""
    
    print("="*70)
    print("🔧 Fixing Customer Service Agent - Removing Built-in Tools")
    print("="*70)
    
    if not AZURE_AI_PROJECT_ENDPOINT or not CUSTOMER_SERVICE_AGENT_ID:
        print("❌ Missing environment variables:")
        print(f"   AZURE_AI_PROJECT_ENDPOINT: {'✓' if AZURE_AI_PROJECT_ENDPOINT else '✗'}")
        print(f"   CUSTOMER_SERVICE_AGENT_ID: {'✓' if CUSTOMER_SERVICE_AGENT_ID else '✗'}")
        return
    
    async with (
        AzureCliCredential() as credential,
        AIProjectClient(
            endpoint=AZURE_AI_PROJECT_ENDPOINT, 
            credential=credential
        ) as project_client,
    ):
        try:
            # Get current agent configuration
            print(f"\n📡 Fetching agent: {CUSTOMER_SERVICE_AGENT_ID}")
            agent = await project_client.agents.get_agent(CUSTOMER_SERVICE_AGENT_ID)
            
            print(f"✅ Current agent configuration:")
            print(f"   Name: {agent.name}")
            print(f"   Model: {agent.model}")
            print(f"   Current tools: {agent.tools if hasattr(agent, 'tools') else 'None'}")
            
            # Update agent to remove all built-in tools
            # The agent will only use custom function tools registered via register_agent_tools.py
            print(f"\n🔄 Updating agent to remove built-in tools...")
            updated_agent = await project_client.agents.update_agent(
                assistant_id=CUSTOMER_SERVICE_AGENT_ID,
                tools=[]  # Empty tools list - only custom function tools will be available
            )
            
            print(f"✅ Agent updated successfully!")
            print(f"   Name: {updated_agent.name}")
            print(f"   Model: {updated_agent.model}")
            print(f"   Updated tools: {updated_agent.tools if hasattr(updated_agent, 'tools') else 'None'}")
            
            print("\n" + "="*70)
            print("✅ SUCCESS - Agent configured to use only custom function tools")
            print("="*70)
            print("\nNext steps:")
            print("1. Custom function tools (track_parcel, search_parcels_by_recipient, get_delivery_statistics)")
            print("   are registered via register_agent_tools.py")
            print("2. Test the chatbot with tracking number DT202512170037")
            print("3. Agent will no longer try to use Azure CLI or code_interpreter tools")
            
        except Exception as e:
            print(f"\n❌ Error updating agent: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(fix_agent())
