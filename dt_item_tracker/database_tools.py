# Updated tool functions for database-based approval system
import os
import asyncio
from random import randint
from typing import Annotated, List, Dict

from datetime import datetime
from pydantic import Field
from database_setup import ApprovalDatabase

# Initialize database connection
db = ApprovalDatabase()

def get_data(
    equipment_id: Annotated[str, Field(description="The ID of the equipment to get data for.")],
) -> dict:
    print(f'get_data called with equipment_id: {equipment_id}')
    """Get the data (temperature, pressure, flow rate) for a given equipment in JSON format."""
    pressure = randint(10, 100)  # PSI
    temperature = randint(60, 80)  # °C
    flow_rate = randint(20, 100)  # LPM
    timestamp = datetime.now().isoformat()

    data = { 
        "equipment_id": equipment_id,
        "pressure": str(pressure) + ' PSI',
        "temperature": str(temperature) + ' °C',
        "flow_rate": str(flow_rate) + ' LPM',
        "timestamp": timestamp
    }
    print(f'data: {data}')
    return data

def get_all_scanned_items() -> List[Dict]:
    """Get all scanned items from the database for analysis"""
    try:
        items = db.get_all_items(active_only=True)
        print(f"Found {len(items)} scanned items in database")
        return items
    except Exception as e:
        print(f"Error retrieving scanned items: {e}")
        return []

def get_all_equipment_from_approval_db() -> List[str]:
    """Get all equipment IDs from pending approval requests for analysis"""
    try:
        pending_approvals = db.get_pending_approvals()
        equipment_ids = [approval['equipment_id'] for approval in pending_approvals if approval['equipment_id']]
        print(f"Found equipment IDs in pending approvals: {equipment_ids}")
        return equipment_ids
    except Exception as e:
        print(f"Error retrieving equipment IDs: {e}")
        return []

def schedule_maintenance(
    equipment_id: Annotated[str, Field(description="The ID of the equipment to schedule maintenance for.")],
    equipment_type: Annotated[str, Field(description="The type of equipment (e.g., pump, valve).")],    
) -> int:    
    """Scheduling maintenance for the given equipment, returns maintenance request number."""
    print(f"Maintenance scheduled for {equipment_type} with ID {equipment_id}.")
    remove_workflow_checkpoint_file()  # Remove checkpoint file as workflow ends here
    return randint(9000, 9999)  # Simulated maintenance request number

def send_shutdown_equipment_notification(
    equipment_id: Annotated[str, Field(description="The ID of the equipment to shut down.")],
    equipment_type: Annotated[str, Field(description="The type of equipment (e.g., pump, valve).")],    
) -> int:    
    """Send notification for shutting down the given equipment and notifying relevant teams, returns notification ID."""    
    print(f"Shutdown protocol triggered for {equipment_type} with ID {equipment_id}. Relevant teams notified.")
    remove_workflow_checkpoint_file()  # Remove checkpoint file as workflow ends here
    return randint(100, 500)  # Simulated notification ID

def send_approval_rejection_notification(
    action: Annotated[str, Field(description="The action that was rejected (e.g., Schedule Maintenance, Immediate Shutdown).")],
    equipment_id: Annotated[str, Field(description="The ID of the equipment involved.")],
    equipment_type: Annotated[str, Field(description="The type of equipment (e.g., pump, valve).")],    
) -> None:
    """Send notification that the requested action was rejected by human approver."""
    print(f"Notification: Action '{action}' for {equipment_type} with ID {equipment_id} was rejected by human approver, no action taken.")
    remove_workflow_checkpoint_file()  # Remove checkpoint file as workflow ends here

def request_human_approval(
    action: Annotated[str, Field(description="The action requiring approval (e.g., Schedule Maintenance, Immediate Shutdown).")],
    equipment_id: Annotated[str, Field(description="The ID of the equipment involved.")],
    equipment_type: Annotated[str, Field(description="The type of equipment (e.g., pump, valve).")],    
    item_barcode: Annotated[str, Field(description="The barcode of the item associated with this approval request.")] = None,
) -> int:
    """Request human approval for critical actions via database system."""
    print(f"Human approval requested for action '{action}' on {equipment_type} with ID {equipment_id}.")
    
    try:
        # Find the item ID based on barcode if provided
        item_id = None
        if item_barcode:
            items = db.get_all_items()
            for item in items:
                if item['barcode'] == item_barcode:
                    item_id = item['id']
                    break
        
        # Create approval request in database
        approval_id = db.request_approval(
            item_id=item_id,
            action_type=action,
            equipment_id=equipment_id,
            equipment_type=equipment_type,
            request_reason=f"Critical action required for {equipment_type}"
        )
        
        print(f"Approval request {approval_id} created in database. Please update the status to approve or reject.")
        return approval_id
        
    except Exception as e:
        print(f"Error creating approval request: {e}")
        return -1

def get_human_approval_status(
    approval_id: Annotated[int, Field(description="The ID of the approval request to check.")] = None,
    equipment_id: Annotated[str, Field(description="The ID of the equipment involved.")] = None,
) -> str:
    """Check the human approval status from the database when the workflow is resumed"""
    try:
        if approval_id:
            # Check specific approval by ID
            pending_approvals = db.get_pending_approvals()
            approved_items = db.get_approved_items()
            
            # Check if it's still pending
            for approval in pending_approvals:
                if approval['id'] == approval_id:
                    return "[PENDING]"
            
            # Check if it's approved
            for approval in approved_items:
                if approval['id'] == approval_id:
                    return "[APPROVED]"
            
            return "[REJECTED]"
        
        elif equipment_id:
            # Check by equipment ID
            pending_approvals = db.get_pending_approvals()
            for approval in pending_approvals:
                if approval['equipment_id'] == equipment_id:
                    print(f"Approval status for equipment {equipment_id}: [PENDING]")
                    return "[PENDING]"
            
            approved_items = db.get_approved_items()
            for approval in approved_items:
                if approval['equipment_id'] == equipment_id:
                    print(f"Approval status for equipment {equipment_id}: [APPROVED]")
                    return "[APPROVED]"
            
            print(f"No approval request found for equipment ID {equipment_id}.")
            return "[NOT_FOUND]"
            
    except Exception as e:
        print(f"Error checking approval status: {e}")
        return "[ERROR]"

def get_all_pending_approvals() -> Dict:
    """Get all pending approval requests from the database"""
    try:
        pending_approvals = db.get_pending_approvals()
        # Convert to dictionary format similar to original JSON structure
        result = {}
        for approval in pending_approvals:
            key = approval['equipment_id'] or f"approval_{approval['id']}"
            result[key] = {
                "id": approval['id'],
                "action": approval['action_type'],
                "equipment_id": approval['equipment_id'],
                "equipment_type": approval['equipment_type'],
                "barcode": approval['barcode'],
                "item_number": approval['item_number'],
                "sender": approval['sender_name'],
                "recipient": approval['recipient_name'],
                "status": "[PENDING]",
                "created_on": approval['requested_at']
            }
        
        print(f"Found {len(result)} pending approval requests: {list(result.keys())}")
        return result
    except Exception as e:
        print(f"Error retrieving pending approvals: {e}")
        return {}

def get_all_approved_items() -> Dict:
    """Get all approved items from the database"""
    try:
        approved_items = db.get_approved_items()
        # Convert to dictionary format similar to original JSON structure
        result = {}
        for approval in approved_items:
            key = approval['equipment_id'] or f"approval_{approval['id']}"
            result[key] = {
                "id": approval['id'],
                "action": approval['action_type'],
                "equipment_id": approval['equipment_id'],
                "equipment_type": approval['equipment_type'],
                "barcode": approval['barcode'],
                "item_number": approval['item_number'],
                "sender": approval['sender_name'],
                "recipient": approval['recipient_name'],
                "status": "[APPROVED]",
                "approved_by": approval['approved_by'],
                "approved_at": approval['approved_at']
            }
        
        print(f"Found {len(result)} approved items: {list(result.keys())}")
        return result
    except Exception as e:
        print(f"Error retrieving approved items: {e}")
        return {}

def add_scanned_item(
    barcode: Annotated[str, Field(description="The barcode scanned from the item.")],
    item_number: Annotated[str, Field(description="The item/package number.")],
    sender_name: Annotated[str, Field(description="Name of the sender.")],
    recipient_name: Annotated[str, Field(description="Name of the recipient.")],
    recipient_address: Annotated[str, Field(description="Delivery address of the recipient.")],
    item_type: Annotated[str, Field(description="Type of item (e.g., electronics, documents, medical).")] = None,
    weight: Annotated[float, Field(description="Weight of the item in kg.")] = None,
    special_handling: Annotated[str, Field(description="Special handling requirements (e.g., fragile, temperature_controlled).")] = None,
) -> int:
    """Add a newly scanned item to the database"""
    try:
        item_id = db.add_scanned_item(
            barcode=barcode,
            item_number=item_number,
            sender_name=sender_name,
            recipient_name=recipient_name,
            recipient_address=recipient_address,
            item_type=item_type,
            weight=weight,
            special_handling=special_handling
        )
        print(f"Scanned item added successfully with ID: {item_id}")
        return item_id
    except Exception as e:
        print(f"Error adding scanned item: {e}")
        return -1

def approve_request(
    approval_id: Annotated[int, Field(description="The ID of the approval request to approve.")],
    approved_by: Annotated[str, Field(description="Name/ID of the person approving the request.")],
) -> bool:
    """Approve a pending approval request"""
    try:
        success = db.update_approval_status(approval_id, "APPROVED", approved_by=approved_by)
        if success:
            print(f"Approval request {approval_id} has been approved by {approved_by}")
        else:
            print(f"Failed to approve request {approval_id}")
        return success
    except Exception as e:
        print(f"Error approving request: {e}")
        return False

def reject_request(
    approval_id: Annotated[int, Field(description="The ID of the approval request to reject.")],
    rejection_reason: Annotated[str, Field(description="Reason for rejecting the request.")],
) -> bool:
    """Reject a pending approval request"""
    try:
        success = db.update_approval_status(approval_id, "REJECTED", rejection_reason=rejection_reason)
        if success:
            print(f"Approval request {approval_id} has been rejected. Reason: {rejection_reason}")
        else:
            print(f"Failed to reject request {approval_id}")
        return success
    except Exception as e:
        print(f"Error rejecting request: {e}")
        return False

# Utility functions
def remove_workflow_checkpoint_file():
    """Utility function to remove existing workflow checkpoint file to start a new workflow run."""
    workflow_checkpoint_json = '../workflow_checkpoint.json'
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

def add_random_approval_items(count=3):
    """Add random new scanned items to the database after workflow completion"""
    try:
        import string
        item_types = ["electronics", "documents", "medical", "fragile", "clothing", "books", "tools", "food"]
        senders = ["John Smith", "Alice Johnson", "Bob Wilson", "Carol Davis", "Emma Brown", "David Lee", "Sarah Jones", "Mike Taylor"]
        recipients = ["Tech Corp", "Medical Center", "University Library", "Home Office", "Research Lab", "Distribution Center"]
        addresses = [
            "123 Main St, New York, NY 10001",
            "456 Oak Ave, Los Angeles, CA 90210", 
            "789 Pine Rd, Chicago, IL 60601",
            "321 Elm St, Houston, TX 77001",
            "654 Maple Dr, Phoenix, AZ 85001",
            "987 Cedar Ln, Philadelphia, PA 19101"
        ]
        handling_types = ["fragile", "temperature_controlled", "confidential", "express", "standard", None]
        
        new_items = []
        for i in range(count):
            barcode = generate_random_tracking_number()
            item_number = f"PKG{randint(1000, 9999)}"
            
            try:
                item_id = db.add_scanned_item(
                    barcode=barcode,
                    item_number=item_number,
                    sender_name=senders[randint(0, len(senders) - 1)],
                    recipient_name=recipients[randint(0, len(recipients) - 1)],
                    recipient_address=addresses[randint(0, len(addresses) - 1)],
                    item_type=item_types[randint(0, len(item_types) - 1)],
                    weight=round(randint(1, 50) / 10.0, 1),  # Random weight between 0.1 and 5.0 kg
                    special_handling=handling_types[randint(0, len(handling_types) - 1)]
                )
                
                # Create approval request for some items
                if randint(0, 1):  # 50% chance to create approval request
                    approval_id = db.request_approval(
                        item_id=item_id,
                        action_type="Process Shipment",
                        equipment_id=f"scanner_{item_id}",
                        equipment_type="barcode_scanner",
                        request_reason="Special handling or verification required"
                    )
                    new_items.append({"item_id": item_id, "barcode": barcode, "approval_id": approval_id})
                else:
                    new_items.append({"item_id": item_id, "barcode": barcode, "approval_id": None})
                    
            except Exception as e:
                print(f"Error adding random item {i}: {e}")
        
        print(f"Added {len(new_items)} new random scanned items")
        return new_items
        
    except Exception as e:
        print(f"Error adding random approval items: {e}")
        return []

if __name__ == "__main__":
    # Test the functions
    print("=== Testing Database Functions ===")
    
    # Add sample data
    db.add_sample_data()
    
    # Test getting all items
    items = get_all_scanned_items()
    print(f"Total scanned items: {len(items)}")
    
    # Test pending approvals
    pending = get_all_pending_approvals()
    print(f"Pending approvals: {len(pending)}")
    
    # Test adding random items
    new_items = add_random_approval_items(2)
    print(f"Added {len(new_items)} new items")