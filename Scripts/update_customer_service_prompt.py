"""
Update the Customer Service Agent with new system prompt
This updates the existing agent rather than recreating it
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.prompt_loader import get_agent_prompt

load_dotenv()

# Azure OpenAI settings
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
CUSTOMER_SERVICE_AGENT_ID = os.getenv("CUSTOMER_SERVICE_AGENT_ID")

def update_agent():
    """Update Customer Service Agent with new prompt"""
    
    if not AZURE_OPENAI_ENDPOINT:
        print("❌ ERROR: AZURE_OPENAI_ENDPOINT not set")
        return False

    if not CUSTOMER_SERVICE_AGENT_ID:
        print("❌ ERROR: CUSTOMER_SERVICE_AGENT_ID not set")
        return False
    
    try:
        # Create client
        if AZURE_OPENAI_API_KEY:
            print("🔑 Using API key authentication")
            client = AzureOpenAI(
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                api_key=AZURE_OPENAI_API_KEY,
                api_version="2024-05-01-preview"
            )
        else:
            print("🔐 Using managed identity authentication")
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default"
            )
            client = AzureOpenAI(
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                azure_ad_token_provider=token_provider,
                api_version="2024-05-01-preview"
            )
        
        print(f"\n📝 Updating Customer Service Agent...")
        print(f"   Agent ID: {CUSTOMER_SERVICE_AGENT_ID}")
        
        # Load updated prompt from Agent-Skills folder
        new_instructions = get_agent_prompt("customer-service")
        
        print(f"   Loaded new prompt ({len(new_instructions)} characters)")
        
        # Update the agent
        updated_agent = client.beta.assistants.update(
            assistant_id=CUSTOMER_SERVICE_AGENT_ID,
            instructions=new_instructions
        )
        
        print(f"✅ Agent updated successfully!")
        print(f"   Name: {updated_agent.name}")
        print(f"   Model: {updated_agent.model}")
        print(f"   Instructions length: {len(updated_agent.instructions)} chars")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating agent: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = update_agent()
    sys.exit(0 if success else 1)
