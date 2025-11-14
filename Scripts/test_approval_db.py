#!/usr/bin/env python3
"""
Test script to verify that all approval data is being read correctly from the approval_db.json file
"""

import json
import os

# Path to the approval database
approval_json_file = '../approval_db.json'

def test_approval_db_reading():
    """Test reading all entries from the approval database"""
    print("=== Testing Approval Database Reading ===")
    
    try:
        with open(approval_json_file, 'r') as f:
            approval_data = json.load(f)
            
        print(f"Successfully loaded approval data with {len(approval_data)} entries:")
        
        for equipment_id, data in approval_data.items():
            print(f"  - {equipment_id}: {data['action']} ({data['status']}) - {data['equipment_type']}")
            
        # Test filtering by status
        pending = {k: v for k, v in approval_data.items() if v.get("status") == "[PENDING]"}
        approved = {k: v for k, v in approval_data.items() if v.get("status") == "[APPROVED]"}
        rejected = {k: v for k, v in approval_data.items() if v.get("status") == "[REJECTED]"}
        
        print(f"\nFiltered results:")
        print(f"  - Pending: {len(pending)} items - {list(pending.keys())}")
        print(f"  - Approved: {len(approved)} items - {list(approved.keys())}")
        print(f"  - Rejected: {len(rejected)} items - {list(rejected.keys())}")
        
        return True
        
    except FileNotFoundError:
        print(f"ERROR: Approval file {approval_json_file} not found.")
        return False
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in approval file: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False

def test_individual_functions():
    """Test the individual functions from the main script"""
    print("\n=== Testing Individual Functions ===")
    
    # Copy the functions from the main script
    def get_all_pending_approvals():
        try:
            with open(approval_json_file, 'r') as f:
                approval_data = json.load(f)
                pending_approvals = {k: v for k, v in approval_data.items() if v.get("status") == "[PENDING]"}
                print(f"get_all_pending_approvals: Found {len(pending_approvals)} pending approval requests: {list(pending_approvals.keys())}")
                return pending_approvals
        except Exception as e:
            print(f"get_all_pending_approvals ERROR: {e}")
            return {}
    
    def get_all_approved_items():
        try:
            with open(approval_json_file, 'r') as f:
                approval_data = json.load(f)
                approved_items = {k: v for k, v in approval_data.items() if v.get("status") == "[APPROVED]"}
                print(f"get_all_approved_items: Found {len(approved_items)} approved items: {list(approved_items.keys())}")
                return approved_items
        except Exception as e:
            print(f"get_all_approved_items ERROR: {e}")
            return {}
    
    def get_all_equipment_from_approval_db():
        try:
            with open(approval_json_file, 'r') as f:
                approval_data = json.load(f)
                equipment_ids = list(approval_data.keys())
                print(f"get_all_equipment_from_approval_db: Found equipment IDs: {equipment_ids}")
                return equipment_ids
        except Exception as e:
            print(f"get_all_equipment_from_approval_db ERROR: {e}")
            return []
    
    # Test the functions
    pending = get_all_pending_approvals()
    approved = get_all_approved_items()
    all_equipment = get_all_equipment_from_approval_db()
    
    print(f"\nSummary:")
    print(f"  - Total equipment: {len(all_equipment)}")
    print(f"  - Pending approvals: {len(pending)}")
    print(f"  - Approved items: {len(approved)}")

if __name__ == "__main__":
    # Run the tests
    success = test_approval_db_reading()
    if success:
        test_individual_functions()
    else:
        print("Skipping function tests due to file reading error.")