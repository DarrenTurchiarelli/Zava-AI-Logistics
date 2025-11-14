#!/usr/bin/env python3
"""
Check what's in the approval database
"""
import sys
import os
import asyncio
# Add parent directory to path to import cosmosdb_tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cosmosdb_tools import get_db_manager

async def check_approvals():
    """Check what's in the approval database"""
    print("Checking approval database...")
    
    db = await get_db_manager()
    
    # Check delivery attempts container for approval requests
    container = db.database.get_container_client(db.delivery_attempts_container)
    
    print("\n=== All items in delivery_attempts container ===")
    query = "SELECT * FROM c"
    items = list(container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))
    
    print(f"Total items found: {len(items)}")
    
    for item in items:
        print(f"\nItem ID: {item.get('id')}")
        print(f"Type: {item.get('type', 'unknown')}")
        print(f"Status: {item.get('status', 'unknown')}")
        print(f"Request Type: {item.get('request_type', 'N/A')}")
        print(f"Description: {item.get('description', 'N/A')[:100]}...")
    
    # Filter for approval requests specifically
    print("\n=== Approval Requests Only ===")
    approval_query = "SELECT * FROM c WHERE c.type = 'approval_request'"
    approvals = list(container.query_items(
        query=approval_query,
        enable_cross_partition_query=True
    ))
    
    print(f"Approval requests found: {len(approvals)}")
    for approval in approvals:
        print(f"\n- ID: {approval['id']}")
        print(f"  Barcode: {approval.get('item_barcode', 'N/A')}")
        print(f"  Request Type: {approval.get('request_type', 'N/A')}")
        print(f"  Status: {approval.get('status', 'N/A')}")
        print(f"  Description: {approval.get('description', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(check_approvals())