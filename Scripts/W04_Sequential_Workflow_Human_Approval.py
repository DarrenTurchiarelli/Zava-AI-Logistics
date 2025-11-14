# About: Create a sequential workflow of persistent Foundry agents for Last Mile Logistics Parcel Tracking
# The workflow manages parcel tracking from store registration → sorting facility → driver delivery → customer handoff
# Includes supervisor approval for exceptions and delivery issues
# Dependency: A03_Create_Multiple_Foundry_Agent_Persistent.py (to create the agents first)
# Ref: https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/orchestrations/sequential?pivots=programming-language-python
# Ref: https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/checkpoints?pivots=programming-language-python
# Ref: https://github.com/microsoft/agent-framework/tree/2397795c1dba1f9b6c6f2aaa1c490f362598bb9a/python/samples/getting_started/workflows
# Learning: The agent to resume from should not be the last agent in the workflow as it will not run again when resuming from checkpoint, so we save state up to the second last agent (Parcel Tracking Agent) in this case

import os
import asyncio
from random import randint
from typing import Annotated

from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential
from azure.ai.projects.aio import AIProjectClient
from agent_framework import ChatAgent
from pydantic import Field

from agent_framework import SequentialBuilder
from agent_framework import ChatMessage, Role, WorkflowStatusEvent, WorkflowOutputEvent # WorkflowCompletedEvent
from typing import Any
from agent_framework import WorkflowBuilder, WorkflowViz, InMemoryCheckpointStorage, FileCheckpointStorage, WorkflowCheckpoint, Message
import json
from dataclasses import asdict

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
AZURE_AI_MODEL_DEPLOYMENT_NAME = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")

# Replace with your created persistent agents IDs created in A03_Create_Multiple_Foundry_Agent_Persistent.py, could be set in environment variables too
# These agents will be repurposed for logistics operations:
# Data Analyser -> Parcel Intake Agent (processes new parcels from stores)
# Risk Assessor -> Sorting Facility Agent (handles parcel routing and exceptions)  
# Maintenance Scheduler -> Delivery Coordination Agent (manages driver assignments and delivery attempts)
parcel_intake_agent_id = 'asst_7On9SJLwwVrWpJjZsGn8OhyP' 
sorting_facility_agent_id = 'asst_vI74b67hcyr24qqYWHIy2iLF'
delivery_coordination_agent_id = 'asst_b1Txi7prs7l3d8pdBtoFwoQU'

# Database-based system for human approval results using Azure Cosmos DB
# Import Cosmos DB tools from separate module
import sys
sys.path.append('../')
from cosmosdb_tools import (
    get_all_scanned_items_sync as get_all_scanned_items,
    add_scanned_item_sync as add_scanned_item,
    request_human_approval_sync as request_human_approval,
    get_human_approval_status_sync as get_human_approval_status,
    get_all_pending_approvals_sync as get_all_pending_approvals,
    get_all_approved_items_sync as get_all_approved_items,
    approve_request_sync as approve_request,
    reject_request_sync as reject_request,
    add_random_approval_items_sync as add_random_approval_items
)

workflow_checkpoint_file_path = '../' # Directory to save checkpoint files when using FileCheckpointStorage
workflow_checkpoint_json = '../workflow_checkpoint.json'


# Tools for the logistics agents
def test_get_all_pending_approvals():
    """Test function to verify agent framework tool registration"""
    print("test_get_all_pending_approvals called")
    return [{"id": "test123", "status": "pending", "description": "Test approval"}]

def get_parcel_data(
    tracking_number: Annotated[str, Field(description="The tracking number of the parcel to get data for.")],
) -> dict:
    print(f'get_parcel_data called with tracking_number: {tracking_number}')
    """Get the parcel data (location, status, delivery attempts) for a given tracking number in JSON format."""
    location = f"Facility_{randint(1, 5)}"
    status_options = ["registered", "in_transit", "at_facility", "out_for_delivery", "delivered", "exception"]
    status = status_options[randint(0, len(status_options)-1)]
    delivery_attempts = randint(0, 3)
    timestamp = datetime.now().isoformat()

    data = { 
        "tracking_number": tracking_number,
        "current_location": location,
        "current_status": status,
        "delivery_attempts": delivery_attempts,
        "last_updated": timestamp,
        "estimated_delivery": datetime.now().isoformat()
    }
    print(f'parcel data: {data}')
    return data

def get_all_parcels_from_database() -> list:
    """Get all parcel tracking numbers from the database for processing"""
    return [item['barcode'] for item in get_all_scanned_items()]

def assign_driver_delivery(
    tracking_number: Annotated[str, Field(description="The tracking number of the parcel to assign for delivery.")],
    driver_id: Annotated[str, Field(description="The ID of the driver (e.g., DRV001, DRV002).")],    
) -> int:    
    """Assign a parcel to a driver for delivery, returns delivery assignment ID."""
    print(f"Parcel {tracking_number} assigned to driver {driver_id} for delivery.")
    remove_workflow_checkpoint_file() # Remove checkpoint file as workflow ends here
    return randint(9000, 9999)  # Simulated delivery assignment ID

def send_delivery_exception_alert(
    tracking_number: Annotated[str, Field(description="The tracking number of the parcel with exception.")],
    exception_type: Annotated[str, Field(description="The type of exception (e.g., damaged, lost, delivery_failed).")],    
) -> int:    
    """Send alert for delivery exception and notify relevant teams, returns alert ID."""    
    print(f"Delivery exception alert sent for parcel {tracking_number}: {exception_type}. Relevant teams notified.")
    remove_workflow_checkpoint_file() # Remove checkpoint file as workflow ends here
    return randint(100, 500)  # Simulated alert ID

def send_approval_rejection_notification(
    action: Annotated[str, Field(description="The action that was rejected (e.g., Return to Sender, Priority Delivery).")],
    tracking_number: Annotated[str, Field(description="The tracking number of the parcel involved.")],
    exception_type: Annotated[str, Field(description="The type of exception (e.g., damaged, lost, delivery_failed).")],    
) -> None:
    """Send notification that the requested action was rejected by supervisor."""
    print(f"Notification: Action '{action}' for parcel {tracking_number} with exception {exception_type} was rejected by supervisor, no action taken.")
    remove_workflow_checkpoint_file() # Remove checkpoint file as workflow ends here

def remove_workflow_checkpoint_file():
    """Utility function to remove existing workflow checkpoint file to start a new workflow run."""
    if os.path.exists(workflow_checkpoint_json):
        os.remove(workflow_checkpoint_json)
        print(f"Existing workflow checkpoint file {workflow_checkpoint_json} removed.")
    else:
        print(f"No existing workflow checkpoint file {workflow_checkpoint_json} found.")

def generate_random_tracking_number():
    """Generate a random tracking number for express or regular parcels"""
    import string
    parcel_type = "exp" if randint(0, 1) else "reg"
    numbers = ''.join([str(randint(0, 9)) for _ in range(8)])
    letter = string.ascii_uppercase[randint(0, 25)]
    return f"{parcel_type}{numbers}{letter}"

async def main():
    async with (
        AzureCliCredential() as credential,
        AIProjectClient(
            endpoint=AZURE_AI_PROJECT_ENDPOINT, 
            credential=credential
        ) as project_client,
    ):        

        # Get required agents created previously (in A03_Create_Multiple_Foundry_Agent_Persistent.py)
        parcel_intake_foundry_agent = await project_client.agents.get_agent(agent_id=parcel_intake_agent_id)
        sorting_facility_foundry_agent = await project_client.agents.get_agent(agent_id=sorting_facility_agent_id)
        delivery_coordination_foundry_agent = await project_client.agents.get_agent(agent_id=delivery_coordination_agent_id)
        print("Foundry agents retrieved successfully.")

        try:
            # Create chat agents for each foundry agent with appropriate tool registration
            parcel_intake_chat_agent = ChatAgent(
                chat_client=AzureAIAgentClient(
                    project_client=project_client,
                    agent_id=parcel_intake_foundry_agent.id
                ),                
                instructions=parcel_intake_foundry_agent.instructions, # From existing agent or can be overridden here
                tools=[get_parcel_data, get_all_parcels_from_database, get_all_scanned_items],
                name=parcel_intake_foundry_agent.name,
                description=parcel_intake_foundry_agent.description
            ) 

            # # Test the parcel intake agent
            # result = await parcel_intake_chat_agent.run("Process new parcels from store intake")
            # print(result.text)

            sorting_facility_chat_agent = ChatAgent(
                chat_client=AzureAIAgentClient(
                    project_client=project_client,
                    agent_id=sorting_facility_foundry_agent.id,                    
                ),                
                instructions=sorting_facility_foundry_agent.instructions, # From existing agent or can be overridden here
                tools=[request_human_approval, get_all_pending_approvals, get_all_approved_items, add_scanned_item],
                name=sorting_facility_foundry_agent.name,
                description=sorting_facility_foundry_agent.description
            ) 

            delivery_coordination_chat_agent = ChatAgent(
                chat_client=AzureAIAgentClient(
                    project_client=project_client,
                    agent_id=delivery_coordination_foundry_agent.id
                ),
                instructions=delivery_coordination_foundry_agent.instructions, # From existing agent or can be overridden here
                tools=[get_human_approval_status, get_all_pending_approvals, get_all_approved_items, 
                       assign_driver_delivery, send_delivery_exception_alert, 
                       send_approval_rejection_notification, add_random_approval_items,
                       approve_request, reject_request], # Tools for human approval and actions
                name=delivery_coordination_foundry_agent.name,
                description=delivery_coordination_foundry_agent.description
            )

            print("Chat agents created successfully.")
            
            # Debug: Test the imported functions
            print(f"Testing sync functions:")
            try:
                parcels = get_all_scanned_items()
                print(f"get_all_scanned_items returned: {len(parcels) if parcels else 0} items")
                
                pending = get_all_pending_approvals()
                print(f"get_all_pending_approvals returned: {len(pending) if pending else 0} items")
                
                approved = get_all_approved_items()
                print(f"get_all_approved_items returned: {len(approved) if approved else 0} items")
                
                # Debug: Check function metadata
                print(f"get_all_pending_approvals function: {get_all_pending_approvals}")
                print(f"get_all_pending_approvals.__name__: {getattr(get_all_pending_approvals, '__name__', 'NO NAME')}")
                
            except Exception as e:
                print(f"Error testing sync functions: {e}")

            checkpoint_storage = InMemoryCheckpointStorage()
            # checkpoint_storage = FileCheckpointStorage(storage_path=workflow_checkpoint_file_path)
            print("Checkpoint storage initialized.")

            # Build the sequential workflow (parcel intake -> sorting facility -> delivery coordination)
            workflow = SequentialBuilder().participants([parcel_intake_chat_agent, sorting_facility_chat_agent, delivery_coordination_chat_agent]).with_checkpointing(checkpoint_storage).build()
            print("Sequential workflow built successfully.")

            # # Visualize the workflow - Uncomment if needed
            # viz = WorkflowViz(workflow)
            # # Mermaid diagram
            # print(viz.to_mermaid())
            # # DiGraph string
            # print(viz.to_digraph())

            # Check if workflow checkpoint file exists to resume from last checkpoint (Delete the file to start a new workflow run)
            if os.path.exists(workflow_checkpoint_json):                
                with open(workflow_checkpoint_json, 'r') as f:
                    checkpoint_data = json.load(f)
                    from_checkpoint = WorkflowCheckpoint.from_dict(checkpoint_data) # Resume from a given checkpoint
                    await checkpoint_storage.save_checkpoint(from_checkpoint) # Hydrate the checkpoint storage with the checkpoint data
                print("Checkpoint data loaded into checkpoint storage.")


            print("===== Running Workflow =====")

            # Run the workflow
            # completion: WorkflowCompletedEvent | None = None
            completion = None
            if os.path.exists(workflow_checkpoint_json): # Resume from last checkpoint
                print("Checkpoint found, resuming workflow from last checkpoint.") 
                events = workflow.run_stream_from_checkpoint(checkpoint_id = from_checkpoint.checkpoint_id,
                                                            #  responses = {f"request_id_{randint(100,999)}": "Rerun workflow"}
                                                             )

                # print(f'workflow._runner._ctx._messages: {workflow._runner._ctx._messages}')
            else: # Start a new workflow run
                print("No checkpoint found, starting a new workflow run.")                
                events = workflow.run_stream("Analyse all scanned parcels in the database and process any approved delivery requests. Check all pending approvals and items that need attention for shipping or delivery exceptions.")
            
            async for event in events:
                
                # print(f'event: {event}')

                # (Documentation incorrect)
                # if isinstance(event, WorkflowCompletedEvent):
                #     completion = event

                if isinstance(event, WorkflowOutputEvent):
                    completion = event
                    # print(f'event: {event}')

            approval_pending = False # Flag to indicate if human approval is pending (required) in this case we would have saved the workflow state to resume later
            if completion:
                print("----- Final output -----")
                messages: list[ChatMessage] | Any = completion.data
                for i, msg in enumerate(messages, start=1):
                    name = msg.author_name or ("assistant" if msg.role == Role.ASSISTANT else "user")
                    if msg.text and "[PENDING]" in msg.text:
                        approval_pending = True
                    print(f"{'-' * 60}\n{i:02d} [{name}]\n{msg.text}")

            print("===== Workflow Completed =====")

            # Get and display checkpoints
            print("===== Checkpoints =====")
            checkpoints = await checkpoint_storage.list_checkpoints()            

            # for ckp in checkpoints:
            #     print(f"Checkpoint data: {ckp}")

            # Save workflow state up to Risk Assessor Agent when approval is pending / required, the last Agent (Maintenance Scheduler) will keep checking for approval status when the workflow is resumed
            if checkpoints and approval_pending:
                print("Approval is pending, saving workflow state.")

                for ckp in reversed(checkpoints):
                    # Save state up to the Sorting Facility Agent so it resumes from there
                    if ckp.messages and ckp.messages.get('Sorting Facility Agent V2') is not None:
                        last_checkpoint = ckp
                        break
                # print(f"Last checkpoint: {last_checkpoint}")

                with open(workflow_checkpoint_json, 'w') as f:                    
                    json.dump(asdict(last_checkpoint), f, indent=4)
                print(f"Workflow state saved to {workflow_checkpoint_json}")
            else:
                print("Workflow state save not required.")
                
                # Automatically add random new items when workflow completes without pending approvals
                print("===== Adding Random New Items =====")
                new_items = add_random_approval_items(count=randint(2, 5))  # Add 2-5 random items
                if new_items:
                    print("New items added successfully. You can run the workflow again to process them.")

        except Exception as e:
            print(f'Error occurred: {e}')            

asyncio.run(main())