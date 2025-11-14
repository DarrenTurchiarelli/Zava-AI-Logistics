#!/usr/bin/env python3
"""
Create test approval requests for testing human intervention workflow
"""
import sys
import os
# Add parent directory to path to import cosmosdb_tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cosmosdb_tools import request_human_approval_sync, get_all_pending_approvals_sync, add_scanned_item_sync
import uuid
from datetime import datetime

def create_test_scenario():
    """Create a test scenario with parcels that need approval"""
    print("Creating test scenario for human intervention workflow...")
    
    # Add a damaged parcel
    print("Adding damaged parcel...")
    damaged_result = add_scanned_item_sync(
        barcode='DMG12345',
        item_name='Fragile Electronics Package',
        sender_name='TechStore Inc',
        recipient_name='John Doe',
        recipient_address='123 Tech Street, Seattle, WA'
    )
    
    # Create an approval request for this damaged parcel
    print("Creating approval request for damaged parcel...")
    request_human_approval_sync(
        item_barcode='DMG12345',
        request_type='damage_assessment',
        description='Package shows signs of damage during sorting. Requires supervisor approval for delivery or return to sender.'
    )
    
    # Add a suspicious parcel
    print("Adding suspicious parcel...")
    suspicious_result = add_scanned_item_sync(
        barcode='SUS67890',
        item_name='Unidentified Package',
        sender_name='Unknown Sender',
        recipient_name='Jane Smith',
        recipient_address='456 Mystery Lane, Portland, OR'
    )
    
    print("Creating approval request for suspicious parcel...")
    request_human_approval_sync(
        item_barcode='SUS67890',
        request_type='security_review',
        description='Package flagged for security review due to weight discrepancy. Requires security team approval before processing.'
    )
    
    print("\nTest scenario created successfully!")
    
    # Show current pending approvals
    print("\nCurrent pending approvals:")
    pending = get_all_pending_approvals_sync()
    for approval in pending:
        print(f"- Tracking ID: {approval.get('tracking_id', 'N/A')}")
        print(f"  Request Type: {approval.get('request_type', 'N/A')}")
        print(f"  Priority: {approval.get('priority', 'N/A')}")
        print(f"  Description: {approval.get('description', 'N/A')}")
        print()
    
    return len(pending)

if __name__ == "__main__":
    num_pending = create_test_scenario()
    print(f"\nCreated {num_pending} test approval requests for human intervention testing.")