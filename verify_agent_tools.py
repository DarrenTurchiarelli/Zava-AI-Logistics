"""
Verify that Cosmos DB tools are registered with the Azure AI Agent
"""
import asyncio
import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

async def verify_tools():
    """Verify the agent has tools registered"""
    
    # Get configuration from environment
    AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    CUSTOMER_SERVICE_AGENT_ID = os.getenv("CUSTOMER_SERVICE_AGENT_ID")
    
    if not AZURE_AI_PROJECT_ENDPOINT or not CUSTOMER_SERVICE_AGENT_ID:
        print("❌ Missing Azure AI configuration")
        print(f"   AZURE_AI_PROJECT_ENDPOINT: {'✓' if AZURE_AI_PROJECT_ENDPOINT else '✗'}")
        print(f"   CUSTOMER_SERVICE_AGENT_ID: {'✓' if CUSTOMER_SERVICE_AGENT_ID else '✗'}")
        return
    
    try:
        # Initialize Azure AI client
        credential = DefaultAzureCredential()
        client = AIProjectClient(
            endpoint=AZURE_AI_PROJECT_ENDPOINT,
            credential=credential
        )
        
        print(f"\n📡 Connected to Azure AI Project")
        print(f"   Agent ID: {CUSTOMER_SERVICE_AGENT_ID}")
        
        # Get agent configuration
        agent = client.agents.get_agent(CUSTOMER_SERVICE_AGENT_ID)
        
        print(f"\n🤖 Agent Details:")
        print(f"   Name: {agent.name}")
        print(f"   Model: {agent.model}")
        print(f"   ID: {agent.id}")
        
        print(f"\n🔧 Tools Configuration:")
        if agent.tools:
            print(f"   Total tools: {len(agent.tools)}")
            for i, tool in enumerate(agent.tools, 1):
                # Check if tool has function definition
                if hasattr(tool, 'function'):
                    print(f"\n   {i}. {tool.function.name}")
                    print(f"      Description: {tool.function.description}")
                    if hasattr(tool.function, 'parameters'):
                        params = tool.function.parameters.get('properties', {})
                        print(f"      Parameters: {', '.join(params.keys())}")
                elif hasattr(tool, 'type'):
                    print(f"\n   {i}. Tool type: {tool.type}")
                else:
                    print(f"\n   {i}. {tool}")
        else:
            print(f"   ❌ No tools registered!")
        
        print(f"\n📝 Agent Instructions (first 500 chars):")
        if agent.instructions:
            print(f"   {agent.instructions[:500]}...")
        else:
            print(f"   No instructions set")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(verify_tools())
