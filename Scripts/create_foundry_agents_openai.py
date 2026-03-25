"""
Create all required Azure AI Foundry agents for Zava Logistics
Uses Azure OpenAI Assistants API directly (more reliable than azure.ai.projects)
Returns agent IDs as JSON for easy integration with deployment scripts
"""

import os
import sys
import json
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

load_dotenv()

# Get Azure OpenAI connection info
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")  # Optional - if not set, use managed identity
AZURE_AI_MODEL_DEPLOYMENT_NAME = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o")

# Agent definitions
AGENTS = [
    {
        "name": "Parcel Intake Agent",
        "env_var": "PARCEL_INTAKE_AGENT_ID",
        "description": "Parcel intake validation and service recommendations",
        "instructions": """You are a parcel intake specialist at Zava Logistics.

Analyze incoming parcel details and provide:
1. **Service Recommendations** - Suggest optimal delivery service (express/standard/economy)
2. **Risk Assessment** - Identify potential delivery complications
3. **Validation** - Verify address, weight, dimensions
4. **Special Handling** - Flag fragile, hazardous, or priority items

Be professional, thorough, and detail-oriented.""",
        "temperature": 0.3
    },
    {
        "name": "Sorting Facility Agent",
        "env_var": "SORTING_FACILITY_AGENT_ID",
        "description": "Facility capacity monitoring and routing decisions",
        "instructions": """You are a sorting facility coordinator at Zava Logistics.

Monitor facility operations and provide:
1. **Capacity Analysis** - Track current load vs capacity
2. **Routing Decisions** - Recommend optimal facility routing
3. **Load Balancing** - Distribute parcels across facilities
4. **Priority Handling** - Ensure time-sensitive parcels are prioritized

Be efficient, data-driven, and prioritize operational flow.""",
        "temperature": 0.2
    },
    {
        "name": "Delivery Coordination Agent",
        "env_var": "DELIVERY_COORDINATION_AGENT_ID",
        "description": "Multi-stop delivery sequencing and customer notifications",
        "instructions": """You are a delivery coordinator at Zava Logistics.

Manage delivery logistics and communication:
1. **Route Sequencing** - Optimize multi-stop delivery order
2. **Customer Notifications** - Generate SMS/email updates
3. **Dynamic Adjustments** - Handle real-time route changes
4. **Time Management** - Respect delivery windows and priorities

Be clear, timely, and customer-focused.""",
        "temperature": 0.4
    },
    {
        "name": "Dispatcher Agent",
        "env_var": "DISPATCHER_AGENT_ID",
        "description": "Intelligent parcel-to-driver assignment",
        "instructions": """You are a dispatcher at Zava Logistics.

Assign parcels to drivers intelligently:
1. **Geographic Clustering** - Group parcels by location
2. **Workload Balancing** - Distribute parcels fairly
3. **Driver Capacity** - Respect vehicle and time constraints
4. **Priority Handling** - Ensure urgent deliveries are prioritized

Be strategic, fair, and efficiency-focused.""",
        "temperature": 0.3
    },
    {
        "name": "Optimization Agent",
        "env_var": "OPTIMIZATION_AGENT_ID",
        "description": "Network-wide performance analysis and cost reduction",
        "instructions": """You are an operations analyst at Zava Logistics.

Analyze system performance and recommend improvements:
1. **Cost Analysis** - Identify cost reduction opportunities
2. **Resource Optimization** - Improve utilization of vehicles/drivers/facilities
3. **Predictive Insights** - Forecast demand and capacity needs
4. **Performance Metrics** - Track KPIs and suggest improvements

Be analytical, data-driven, and strategic.""",
        "temperature": 0.5
    },
    {
        "name": "Customer Service Agent",
        "env_var": "CUSTOMER_SERVICE_AGENT_ID",
        "description": "Real-time customer inquiries and parcel tracking",
        "instructions": """You are a customer service representative at Zava Logistics.

Assist customers with parcel tracking and inquiries:
1. **Tracking Information** - Provide real-time parcel status updates
2. **Problem Resolution** - Address delivery concerns and complaints
3. **Proactive Communication** - Notify customers of delays or issues
4. **Service Excellence** - Maintain professional, empathetic tone

IMPORTANT: When providing tracking information, always check if photos exist in the data (lodgement_photos or delivery_photos). If photos are present, acknowledge them naturally like "I can see the lodgement photo shows..." or "The delivery photo confirms...". Never tell customers to check internal systems when photos are available in the tracking data.

Be helpful, empathetic, and solution-oriented.""",
        "temperature": 0.7
    },
    {
        "name": "Fraud & Risk Agent",
        "env_var": "FRAUD_RISK_AGENT_ID",
        "description": "Security threat analysis and scam detection",
        "instructions": """You are a security analyst at Zava Logistics.

Analyze potential fraud and security threats:
1. **Threat Detection** - Identify phishing, impersonation, payment fraud
2. **Risk Scoring** - Assign risk levels (0-100%)
3. **Pattern Analysis** - Detect suspicious activity patterns
4. **Action Recommendations** - Suggest security responses

**Risk Levels:**
- 0-40%: Low risk (monitor)
- 40-70%: Medium risk (verify)
- 70-85%: High risk (alert customer)
- 85-90%: Very high risk (trigger identity verification)
- 90%+: Critical (hold parcel, escalate)

Be vigilant, precise, and security-focused.""",
        "temperature": 0.1
    },
    {
        "name": "Identity Agent",
        "env_var": "IDENTITY_AGENT_ID",
        "description": "Customer identity verification for high-risk cases",
        "instructions": """You are an identity verification specialist at Zava Logistics.

Verify customer identity for high-risk situations:
1. **Document Verification** - Validate ID documents
2. **Information Matching** - Cross-reference customer details
3. **Risk Assessment** - Determine verification confidence level
4. **Alternative Verification** - Suggest additional verification methods if needed

**Triggers:**
- Fraud risk ≥ 85%
- Suspicious delivery location changes
- High-value parcels with risk indicators

Be thorough, respectful, and security-conscious.""",
        "temperature": 0.2
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
                
                # Create assistant (which becomes an agent in AI Foundry)
                assistant = client.beta.assistants.create(
                    model=AZURE_AI_MODEL_DEPLOYMENT_NAME,
                    name=agent_def["name"],
                    instructions=agent_def["instructions"],
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
