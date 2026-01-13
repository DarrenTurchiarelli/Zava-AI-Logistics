"""
Zava - Sequential Workflow with Human Approval
Demonstrates AI agent workflow with human-in-the-loop approval for critical decisions
"""

import json
import os
import sys
import time
from datetime import datetime

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logistics_state_manager import StateManager, WorkflowState
from parcel_tracking_db import ParcelTrackingDatabase


def load_agent_config():
    """Load agent IDs from configuration"""
    config_path = os.path.join(os.path.dirname(__file__), "..", "agent_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return None


def simulate_human_approval(approval_request):
    """
    Simulate human approval process
    In production, this would be a UI/email notification
    """
    print("\n" + "=" * 70)
    print("🚨 HUMAN APPROVAL REQUIRED")
    print("=" * 70)
    print(f"Request ID: {approval_request['request_id']}")
    print(f"Request Type: {approval_request['request_type']}")
    print(f"Tracking Number: {approval_request['tracking_number']}")
    print(f"Requested By: {approval_request['requester_agent']}")
    print(f"\nReason: {approval_request['approval_reason']}")
    print(f"\nContext:")
    for key, value in approval_request["context_data"].items():
        print(f"  {key}: {value}")
    print("\n" + "-" * 70)

    # In demo mode, auto-approve after showing the request
    print("\n[DEMO MODE] Auto-approving after 2 seconds...")
    time.sleep(2)

    return {
        "approved": True,
        "reviewer": "Supervisor Mike",
        "review_notes": "Approved - Customer is high priority, weekend delivery authorized",
    }


def run_workflow_with_approval():
    """Execute a complete workflow including human approval"""

    print("Zava - Sequential Workflow with Human Approval")
    print("=" * 70)
    print()

    # Initialize systems
    try:
        db = ParcelTrackingDatabase()
        db.initialize_database()
        state_manager = StateManager()

        print("✓ Database initialized")
        print("✓ State manager initialized")
        print()
    except Exception as e:
        print(f"Error initializing systems: {e}")
        print("Note: Database operations will be simulated")
        db = None
        state_manager = StateManager()

    # Check for agent configuration
    config = load_agent_config()
    if not config:
        print("⚠️  Agent configuration not found")
        print("Run Scripts/A03_Create_Multiple_Foundry_Agent_Persistent.py first")
        print("\nContinuing with simulated workflow...")
        use_agents = False
    else:
        print("✓ Agent configuration loaded")
        use_agents = True

    # Initialize AI Project Client if agents available
    project_client = None
    if use_agents:
        try:
            project_connection_string = os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING")
            if project_connection_string:
                credential = DefaultAzureCredential()
                project_client = AIProjectClient.from_connection_string(
                    credential=credential, conn_str=project_connection_string
                )
                print("✓ Azure AI Project Client connected")
            else:
                print("⚠️  AZURE_AI_PROJECT_CONNECTION_STRING not set")
                use_agents = False
        except Exception as e:
            print(f"⚠️  Could not connect to Azure AI: {e}")
            use_agents = False

    print("\n" + "=" * 70)
    print("WORKFLOW EXECUTION")
    print("=" * 70)

    # Define test parcel
    tracking_number = "DTVIC12345678"
    parcel_data = {
        "tracking_number": tracking_number,
        "sender_name": "Zava Melbourne DC",
        "sender_address": "123 Distribution Drive, Melbourne VIC 3000",
        "sender_phone": "03-9876-5432",
        "recipient_name": "ABC Corporation",
        "recipient_address": "456 Business Park, Carlton VIC 3004",
        "recipient_phone": "03-8765-4321",
        "postcode": "3004",
        "state": "VIC",
        "weight_kg": 15.5,
        "package_type": "Express",
        "special_instructions": "High priority business delivery - requires weekend delivery",
        "status": "Registered",
    }

    # Step 1: Parcel Intake
    print("\n📥 STEP 1: PARCEL INTAKE AGENT")
    print("-" * 70)

    state_manager.register_parcel(tracking_number)

    if use_agents and project_client:
        try:
            thread = project_client.agents.create_thread()
            intake_agent_id = config["Parcel Intake Agent"]["id"]

            intake_prompt = f"""
Process this parcel intake:

Tracking: {tracking_number}
Sender: {parcel_data['sender_name']}
Recipient: {parcel_data['recipient_name']}
Address: {parcel_data['recipient_address']}
Postcode: {parcel_data['postcode']}
Weight: {parcel_data['weight_kg']} kg
Type: {parcel_data['package_type']}
Special Instructions: {parcel_data['special_instructions']}

Validate all information and confirm state mapping is correct.
"""

            project_client.agents.create_message(thread_id=thread.id, role="user", content=intake_prompt)

            run = project_client.agents.create_and_process_run(thread_id=thread.id, assistant_id=intake_agent_id)

            messages = project_client.agents.list_messages(thread_id=thread.id)
            response = messages.data[0].content[0].text.value
            print(response)

        except Exception as e:
            print(f"Error calling agent: {e}")
            print("Using simulated response...")
            print(f"✓ Parcel {tracking_number} validated")
            print(f"✓ Postcode 3004 correctly mapped to VIC")
            print(f"✓ All required fields present")
    else:
        print(f"✓ Parcel {tracking_number} registered")
        print(f"✓ Postcode {parcel_data['postcode']} → {parcel_data['state']}")
        print(f"✓ Weight: {parcel_data['weight_kg']} kg")
        print(f"✓ Type: {parcel_data['package_type']}")

    state_manager.transition_state(tracking_number, WorkflowState.IN_TRANSIT, "Parcel Intake Agent")
    state_manager.add_agent_message(tracking_number, "Parcel Intake Agent", "Parcel validated and accepted")

    # Step 2: Sorting Facility
    print("\n📦 STEP 2: SORTING FACILITY AGENT")
    print("-" * 70)

    if use_agents and project_client:
        try:
            sorting_agent_id = config["Sorting Facility Agent"]["id"]

            sorting_prompt = f"""
Process parcel {tracking_number} at sorting facility.

Package details:
- Destination: Carlton VIC 3004
- Weight: {parcel_data['weight_kg']} kg
- Type: {parcel_data['package_type']}
- Special Instructions: {parcel_data['special_instructions']}

Note: This parcel requires WEEKEND DELIVERY which is outside standard operating hours.
This requires supervisor approval.

Analyze the request and recommend approval decision.
"""

            project_client.agents.create_message(thread_id=thread.id, role="user", content=sorting_prompt)

            run = project_client.agents.create_and_process_run(thread_id=thread.id, assistant_id=sorting_agent_id)

            messages = project_client.agents.list_messages(thread_id=thread.id)
            response = messages.data[0].content[0].text.value
            print(response)

        except Exception as e:
            print(f"Error calling agent: {e}")
            print("Using simulated response...")
            print(f"✓ Parcel routed to Carlton VIC delivery zone")
            print(f"⚠️  Weekend delivery requested - requires approval")
    else:
        print(f"✓ Parcel sorted for Carlton VIC (3004)")
        print(f"⚠️  Special handling detected: Weekend delivery")
        print(f"⚠️  Requires supervisor approval")

    state_manager.transition_state(tracking_number, WorkflowState.AT_SORTING_FACILITY, "Sorting Facility Agent")

    # Step 3: Create Approval Request
    print("\n🔔 STEP 3: APPROVAL REQUEST")
    print("-" * 70)

    approval_request_data = {
        "request_id": f"APPR_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "request_type": "weekend_delivery",
        "tracking_number": tracking_number,
        "requester_agent": "Sorting Facility Agent",
        "approval_reason": "Weekend delivery required for business customer",
        "context_data": {
            "customer_name": parcel_data["recipient_name"],
            "customer_priority": "High",
            "delivery_address": parcel_data["recipient_address"],
            "package_type": parcel_data["package_type"],
            "requested_delivery": "Saturday 10:00-12:00",
            "business_justification": "Critical business delivery for high-value customer",
            "estimated_additional_cost": "$25",
        },
    }

    # Store approval request in database
    if db:
        try:
            db.create_approval_request(
                approval_type=approval_request_data["request_type"],
                tracking_number=tracking_number,
                driver_id="TBD",
                request_reason=approval_request_data["approval_reason"],
                request_details=approval_request_data["context_data"],
            )
            print("✓ Approval request stored in database")
        except Exception as e:
            print(f"Note: Database storage simulated ({e})")

    # Create approval request in state manager
    state_manager.create_approval_request(
        request_id=approval_request_data["request_id"],
        request_type=approval_request_data["request_type"],
        tracking_number=tracking_number,
        requester_agent=approval_request_data["requester_agent"],
        approval_reason=approval_request_data["approval_reason"],
        context_data=approval_request_data["context_data"],
    )

    print(f"✓ Approval request created: {approval_request_data['request_id']}")
    print(f"✓ Parcel state: {state_manager.get_current_state(tracking_number).value}")

    # Step 4: Human Approval
    print("\n👤 STEP 4: HUMAN APPROVAL PROCESS")
    print("-" * 70)

    approval_decision = simulate_human_approval(approval_request_data)

    # Process approval
    state_manager.process_approval(
        request_id=approval_request_data["request_id"],
        approved=approval_decision["approved"],
        reviewer=approval_decision["reviewer"],
        review_notes=approval_decision["review_notes"],
    )

    if approval_decision["approved"]:
        print(f"\n✅ APPROVED by {approval_decision['reviewer']}")
        print(f"Notes: {approval_decision['review_notes']}")

        # Step 5: Delivery Coordination
        print("\n🚚 STEP 5: DELIVERY COORDINATION AGENT")
        print("-" * 70)

        if use_agents and project_client:
            try:
                coordination_agent_id = config["Delivery Coordination Agent"]["id"]

                coordination_prompt = f"""
Approval received for parcel {tracking_number}.

Approval details:
- Approved by: {approval_decision['reviewer']}
- Notes: {approval_decision['review_notes']}
- Delivery window: Saturday 10:00-12:00
- Destination: Carlton VIC 3004

Assign to appropriate driver for weekend delivery execution.
"""

                project_client.agents.create_message(thread_id=thread.id, role="user", content=coordination_prompt)

                run = project_client.agents.create_and_process_run(
                    thread_id=thread.id, assistant_id=coordination_agent_id
                )

                messages = project_client.agents.list_messages(thread_id=thread.id)
                response = messages.data[0].content[0].text.value
                print(response)

            except Exception as e:
                print(f"Error calling agent: {e}")
                print("Using simulated response...")
                print(f"✓ Assigned to Driver DRV001 (experienced with business deliveries)")
                print(f"✓ Scheduled for Saturday 10:00-12:00")
        else:
            print(f"✓ Assigned to Driver DRV001")
            print(f"✓ Scheduled for Saturday delivery")

        state_manager.transition_state(tracking_number, WorkflowState.OUT_FOR_DELIVERY, "Delivery Coordination Agent")

    else:
        print(f"\n❌ REJECTED by {approval_decision['reviewer']}")
        print(f"Reason: {approval_decision.get('rejection_reason', 'Not specified')}")

    # Display workflow summary
    print("\n" + "=" * 70)
    print("WORKFLOW SUMMARY")
    print("=" * 70)

    print(f"\nParcel: {tracking_number}")
    print(f"Current State: {state_manager.get_current_state(tracking_number).value}")

    print("\nState History:")
    for state, timestamp in state_manager.get_parcel_history(tracking_number):
        print(f"  {timestamp.strftime('%H:%M:%S')} - {state.value}")

    print("\nAgent Messages:")
    for context in state_manager.get_agent_context(tracking_number):
        print(f"  [{context.agent_name}] {context.messages[0] if context.messages else 'No message'}")

    print("\n" + "=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)
    print(f"\n✅ Successfully demonstrated human approval workflow")
    print(f"✅ Parcel approved for weekend delivery")
    print(f"✅ Ready for driver assignment and delivery execution")


if __name__ == "__main__":
    try:
        run_workflow_with_approval()
    except KeyboardInterrupt:
        print("\n\nWorkflow interrupted by user")
    except Exception as e:
        print(f"\n\nError during workflow execution: {e}")
        import traceback

        traceback.print_exc()
