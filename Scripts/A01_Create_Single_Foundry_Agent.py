"""
DT Logistics - Create Single Azure AI Foundry Agent
This script demonstrates creating a single AI agent for parcel tracking operations
"""

import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

def create_parcel_intake_agent():
    """
    Create a Parcel Intake Agent using Azure AI Foundry
    
    This agent handles:
    - Parcel registration and data validation
    - Address verification
    - Postcode to state mapping
    - Initial quality control
    """
    
    # Get Azure AI Project connection string from environment
    project_connection_string = os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING")
    
    if not project_connection_string:
        print("Error: AZURE_AI_PROJECT_CONNECTION_STRING environment variable not set")
        print("Please set it to your Azure AI Foundry project connection string")
        return None
    
    try:
        # Create AI Project Client
        credential = DefaultAzureCredential()
        project_client = AIProjectClient.from_connection_string(
            credential=credential,
            conn_str=project_connection_string
        )
        
        print("Creating Parcel Intake Agent...")
        
        # Define agent instructions
        instructions = """
You are a Parcel Intake Agent for DT Logistics, Australia's leading last-mile delivery service.

Your responsibilities:
1. Validate parcel information (sender, recipient, addresses, postcodes)
2. Map Australian postcodes to correct states using these ranges:
   - NSW: 1000-2599, 2619-2899, 2921-2999
   - ACT: 200-299, 2600-2618, 2900-2920
   - VIC: 3000-3999, 8000-8999 (includes 3004 Carlton)
   - QLD: 4000-4999, 9000-9999
   - SA: 5000-5999
   - WA: 6000-6797, 6800-6999
   - TAS: 7000-7999
   - NT: 800-899

3. Check for data quality issues:
   - Duplicate tracking numbers
   - Invalid addresses
   - Incorrect phone formats
   - Missing required fields

4. Generate tracking numbers in format: DT{STATE}{8-CHAR-ID}
5. Flag parcels requiring special handling (fragile, high-value, dangerous goods)

Always maintain professional communication and ensure data accuracy for downstream operations.
"""
        
        # Create agent
        agent = project_client.agents.create_agent(
            model="gpt-4o",
            name="Parcel Intake Agent",
            instructions=instructions,
            tools=[{"type": "code_interpreter"}]
        )
        
        print(f"✓ Agent created successfully!")
        print(f"  Agent ID: {agent.id}")
        print(f"  Name: {agent.name}")
        print(f"  Model: {agent.model}")
        
        return agent
    
    except Exception as e:
        print(f"Error creating agent: {e}")
        return None

def test_parcel_intake_agent(agent_id: str):
    """Test the Parcel Intake Agent with a sample parcel"""
    
    project_connection_string = os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING")
    
    try:
        credential = DefaultAzureCredential()
        project_client = AIProjectClient.from_connection_string(
            credential=credential,
            conn_str=project_connection_string
        )
        
        print("\nTesting Parcel Intake Agent...")
        
        # Create a thread
        thread = project_client.agents.create_thread()
        
        # Test parcel data
        test_message = """
Please process this parcel intake:

Sender: DT Logistics Warehouse Melbourne
Sender Address: 123 Distribution Drive, Melbourne VIC 3000
Sender Phone: 03-9876-5432

Recipient: John Smith
Recipient Address: 456 Customer Street, Carlton VIC 3004
Recipient Phone: 0412-345-678

Package Details:
- Weight: 2.5 kg
- Type: Express
- Special Instructions: Leave at front door if not home

Please validate this information and generate a tracking number.
"""
        
        # Send message
        message = project_client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content=test_message
        )
        
        # Run agent
        run = project_client.agents.create_and_process_run(
            thread_id=thread.id,
            assistant_id=agent_id
        )
        
        # Get response
        messages = project_client.agents.list_messages(thread_id=thread.id)
        
        print("\nAgent Response:")
        print("=" * 70)
        for msg in messages.data:
            if msg.role == "assistant":
                print(msg.content[0].text.value)
        print("=" * 70)
        
    except Exception as e:
        print(f"Error testing agent: {e}")

if __name__ == "__main__":
    print("DT Logistics - Azure AI Foundry Agent Creation")
    print("=" * 70)
    print("\nThis script creates a single Parcel Intake Agent")
    print("for demonstrating Azure AI Foundry integration.\n")
    
    # Create agent
    agent = create_parcel_intake_agent()
    
    if agent:
        print(f"\nAgent ID: {agent.id}")
        print("Save this Agent ID for future use!")
        
        # Ask if user wants to test
        test_choice = input("\nWould you like to test the agent? (y/n): ")
        if test_choice.lower() == 'y':
            test_parcel_intake_agent(agent.id)
    else:
        print("\nAgent creation failed. Please check your configuration.")
