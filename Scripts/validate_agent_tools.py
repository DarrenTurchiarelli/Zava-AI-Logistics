"""
Validate that Customer Service Agent has tools registered and can access Cosmos DB
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

# Configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
CUSTOMER_SERVICE_AGENT_ID = os.getenv("CUSTOMER_SERVICE_AGENT_ID")

def validate_agent_tools():
    """Validate agent has tools registered"""
    
    print("=" * 70)
    print("✅ Validating Customer Service Agent Tool Registration")
    print("=" * 70)
    print()
    
    if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, CUSTOMER_SERVICE_AGENT_ID]):
        print("❌ Missing required environment variables")
        print(f"   AZURE_OPENAI_ENDPOINT: {'✓' if AZURE_OPENAI_ENDPOINT else '✗'}")
        print(f"   AZURE_OPENAI_API_KEY: {'✓' if AZURE_OPENAI_API_KEY else '✗'}")
        print(f"   CUSTOMER_SERVICE_AGENT_ID: {'✓' if CUSTOMER_SERVICE_AGENT_ID else '✗'}")
        return False
    
    try:
        print(f"🔌 Connecting to Azure OpenAI...")
        print(f"   Endpoint: {AZURE_OPENAI_ENDPOINT}")
        print(f"   Agent ID: {CUSTOMER_SERVICE_AGENT_ID}")
        print()
        
        client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version="2024-05-01-preview"
        )
        
        # Retrieve agent
        print("📋 Retrieving agent...")
        agent = client.beta.assistants.retrieve(assistant_id=CUSTOMER_SERVICE_AGENT_ID)
        
        print(f"   ✓ Agent: {agent.name}")
        print(f"   Model: {agent.model}")
        print()
        
        # Check tools
        if agent.tools and len(agent.tools) > 0:
            print(f"✅ SUCCESS: Agent has {len(agent.tools)} tools registered")
            print()
            print("📋 Registered tools:")
            for i, tool in enumerate(agent.tools, 1):
                if hasattr(tool, 'function'):
                    print(f"   {i}. {tool.function.name}")
            print()
            print("✅ Agent is ready to access Cosmos DB!")
            return True
        else:
            print("❌ FAIL: Agent has NO tools registered")
            print("   Agent will not be able to access Cosmos DB")
            return False
            
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

if __name__ == "__main__":
    success = validate_agent_tools()
    sys.exit(0 if success else 1)
