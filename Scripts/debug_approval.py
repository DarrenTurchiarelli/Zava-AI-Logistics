#!/usr/bin/env python3
"""
Debug: Check if approval request was created in database
"""
import sys
import os
from dotenv import load_dotenv
# Add parent directory to path to import cosmosdb_tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from cosmosdb_tools import get_db_manager
import asyncio

async def debug_check_approval():
    """Debug function to check if approval was created"""
    print("=== Debug: Checking Approval Request in Database ===\n")
    
    db = await get_db_manager()
    container = db.database.get_container_client(db.delivery_attempts_container)
    
    # Get all items to see what's in the container
    print("All items in delivery_attempts_container:")
    query = "SELECT * FROM c"
    items = []
    async for item in container.query_items(query=query, enable_cross_partition_query=True):
        items.append(item)
    
    print(f"Total items: {len(items)}")
    
    approval_items = []
    for item in items:
        print(f"\nItem ID: {item.get('id', 'N/A')}")
        print(f"  Status: {item.get('status', 'N/A')}")
        print(f"  Request Type: {item.get('request_type', 'N/A')}")
        print(f"  Type: {item.get('type', 'N/A')}")
        print(f"  Parcel Barcode: {item.get('parcel_barcode', 'N/A')}")
        
        # Check if this looks like an approval request
        if item.get('request_type') and item.get('status'):
            approval_items.append(item)
    
    print(f"\n=== Found {len(approval_items)} approval-like items ===")
    for approval in approval_items:
        print(f"Approval: {approval.get('id')} - {approval.get('request_type')} - {approval.get('status')}")
    
    # Test the specific query used by get_all_pending_approvals
    print("\n=== Testing get_all_pending_approvals query ===")
    query = "SELECT * FROM c WHERE c.status = 'pending' AND c.request_type IS NOT NULL ORDER BY c.request_timestamp DESC"
    pending_items = []
    async for item in container.query_items(query=query, enable_cross_partition_query=True):
        pending_items.append(item)
    
    print(f"Pending approvals query returned: {len(pending_items)} items")
    for item in pending_items:
        print(f"  - {item.get('id')}: {item.get('request_type')} - {item.get('status')}")

if __name__ == "__main__":
    asyncio.run(debug_check_approval())