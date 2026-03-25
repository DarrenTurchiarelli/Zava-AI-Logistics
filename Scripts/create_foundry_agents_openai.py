"""
Create all required Azure AI Foundry agents for Zava Logistics
Uses Azure OpenAI Assistants API directly (more reliable than azure.ai.projects)
Returns agent IDs as JSON for easy integration with deployment scripts
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# Add parent directory to path to import from agents module
sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.prompt_loader import get_agent_prompt

load_dotenv()

# Get Azure OpenAI connection info
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")  # Optional - if not set, use managed identity
AZURE_AI_MODEL_DEPLOYMENT_NAME = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o")

# Agent definitions - load prompts from Agent-Skills folder
AGENTS = [
    {
        "name": "Parcel Intake Agent",
        "env_var": "PARCEL_INTAKE_AGENT_ID",
        "description": "Parcel intake validation and service recommendations",
        "prompt_folder": "parcel-intake",
        "temperature": 0.3
    },
    {
        "name": "Sorting Facility Agent",
        "env_var": "SORTING_FACILITY_AGENT_ID",
        "description": "Facility capacity monitoring and routing decisions",
        "prompt_folder": "sorting-facility",
        "temperature": 0.2
    },
    {
        "name": "Delivery Coordination Agent",
        "env_var": "DELIVERY_COORDINATION_AGENT_ID",
        "description": "Multi-stop delivery sequencing and customer notifications",
        "prompt_folder": "delivery-coordination",
        "temperature": 0.4
    },
    {
        "name": "Dispatcher Agent",
        "env_var": "DISPATCHER_AGENT_ID",
        "description": "Intelligent parcel-to-driver assignment",
        "prompt_folder": "dispatcher",
        "temperature": 0.3
    },
    {
        "name": "Optimization Agent",
        "env_var": "OPTIMIZATION_AGENT_ID",
        "description": "Network-wide performance analysis and cost reduction",
        "prompt_folder": "optimization",
        "temperature": 0.5
    },
    {
        "name": "Customer Service Agent",
        "env_var": "CUSTOMER_SERVICE_AGENT_ID",
        "description": "Real-time customer inquiries and parcel tracking",
        "prompt_folder": "customer-service",
        "temperature": 0.7
    },
    {
        "name": "Fraud & Risk Agent",
        "env_var": "FRAUD_RISK_AGENT_ID",
        "description": "Security threat analysis and scam detection",
        "prompt_folder": "fraud-detection",
        "temperature": 0.1
    },
    {
        "name": "Identity Agent",
        "env_var": "IDENTITY_AGENT_ID",
        "description": "Customer identity verification for high-risk cases",
        "prompt_folder": "identity-verification",
        "temperature": 0.2
    },
    {
        "name": "Driver Agent",
        "env_var": "DRIVER_AGENT_ID",
        "description": "Driver delivery execution and proof of delivery",
        "prompt_folder": "driver",
        "temperature": 0.4
    }
]


def create_agents():
    """Create all required agents and return their IDs"""
    
    if not AZURE_OPENAI_ENDPOINT:
        print("ERROR: AZURE_OPENAI_ENDPOINT not set", file=sys.stderr)
        return None

    agent_ids = {}
    
    try:
        # Create Azure OpenAI client (use API key if available, otherwise managed identity)
        if AZURE_OPENAI_API_KEY:
            print("Using API key authentication")
            client = AzureOpenAI(
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                api_key=AZURE_OPENAI_API_KEY,
                api_version="2024-05-01-preview"  # Assistants API version
            )
        else:
            print("Using managed identity authentication")
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default"
            )
            client = AzureOpenAI(
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                azure_ad_token_provider=token_provider,
                api_version="2024-05-01-preview"  # Assistants API version
            )
        
        print("🚀 Creating Azure AI Foundry Agents (via Azure OpenAI Assistants)...")
        print("=" * 60)
        
        for agent_def in AGENTS:
            try:
                print(f"Creating {agent_def['name']}...", end=" ", flush=True)
                
                # Load system prompt from Agent-Skills folder
                instructions = get_agent_prompt(agent_def["prompt_folder"])
                
                # Create assistant (which becomes an agent in AI Foundry)
                assistant = client.beta.assistants.create(
                    model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
                    name=agent_def["name"],
                    instructions=instructions,
                    description=agent_def["description"],
                    temperature=agent_def["temperature"]
                )
                
                agent_ids[agent_def["env_var"]] = assistant.id
                print(f"✓ {assistant.id}")
                
            except Exception as e:
                print(f"✗ Failed: {e}", file=sys.stderr)
                # Continue with other agents
        
        print("=" * 60)
        print(f"✅ Created {len(agent_ids)}/{len(AGENTS)} agents successfully")
        
        if len(agent_ids) == len(AGENTS):
            print("\n📋 Agent IDs:")
            for env_var, agent_id in agent_ids.items():
                print(f"  {env_var}={agent_id}")
        
        return agent_ids
                
    except Exception as e:
        print(f"ERROR: Failed to create agents: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


def main():
    """Create agents and output as JSON"""
    agent_ids = create_agents()
    
    if agent_ids:
        # Output as JSON for easy parsing by PowerShell
        print("\n" + json.dumps(agent_ids, indent=2))
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
