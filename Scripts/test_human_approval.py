#!/usr/bin/env python3
"""
Create manual approval request and test human approval workflow
"""
import sys
import os
from dotenv import load_dotenv
# Add parent directory to path to import cosmosdb_tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from cosmosdb_tools import request_human_approval_sync, get_all_pending_approvals_sync, approve_request_sync, reject_request_sync

def test_human_approval_workflow():
    """Test the complete human approval workflow"""
    print("=== Testing Human Approval Workflow ===\n")
    
    # Step 1: Create an approval request
    print("Step 1: Creating approval request...")
    approval_result = request_human_approval_sync(
        item_barcode='TEST123',
        request_type='damage_assessment', 
        description='Test package shows signs of damage during sorting. Requires supervisor approval for delivery or return to sender.'
    )
    print(f"Approval request result: {approval_result}")
    
    # Step 2: Check pending approvals
    print("\nStep 2: Checking pending approvals...")
    pending = get_all_pending_approvals_sync()
    print(f"Found {len(pending)} pending approvals:")
    
    approval_id = None
    for approval in pending:
        print(f"\n📋 Approval Request:")
        print(f"   ID: {approval.get('id', 'N/A')}")
        print(f"   Item Barcode: {approval.get('item_barcode', 'N/A')}")
        print(f"   Type: {approval.get('request_type', 'N/A')}")
        print(f"   Priority: {approval.get('priority', 'N/A')}")
        print(f"   Status: {approval.get('status', 'N/A')}")
        print(f"   Description: {approval.get('description', 'N/A')}")
        print(f"   Requested By: {approval.get('requested_by', 'N/A')}")
        print(f"   Requested At: {approval.get('requested_at', 'N/A')}")
        
        # Save the first approval ID for testing
        if approval_id is None and approval.get('status') == 'pending':
            approval_id = approval.get('id')
    
    # Step 3: Test approval
    if approval_id:
        print(f"\nStep 3: Approving request {approval_id}...")
        approve_result = approve_request_sync(
            approval_id=approval_id,
            approver_name='Test Supervisor',
            notes='Approved for testing - damage is minimal and package can be delivered'
        )
        print(f"Approval result: {approve_result}")
        
        # Check status after approval
        print("\nStep 4: Checking approvals after approval...")
        pending_after = get_all_pending_approvals_sync()
        print(f"Pending approvals after approval: {len(pending_after)}")
        
        return True
    else:
        print("\n❌ No approval ID found to test approval process")
        return False

if __name__ == "__main__":
    success = test_human_approval_workflow()
    if success:
        print("\n✅ Human approval workflow test completed successfully!")
    else:
        print("\n❌ Human approval workflow test failed!")