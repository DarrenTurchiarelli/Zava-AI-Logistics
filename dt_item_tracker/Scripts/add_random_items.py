#!/usr/bin/env python3
"""
Test script for adding random approval items to the approval database
"""

import json
import os
from random import randint
from datetime import datetime
import string

# Path to the approval database
approval_json_file = '../approval_db.json'

def generate_random_tracking_number():
    """Generate a random tracking number for express or regular parcels"""
    parcel_type = "exp" if randint(0, 1) else "reg"
    numbers = ''.join([str(randint(0, 9)) for _ in range(8)])
    letter = string.ascii_uppercase[randint(0, 25)]
    return f"{parcel_type}{numbers}{letter}"

def add_random_approval_items(count=3):
    """Add random new items to the approval database"""
    equipment_types = ["pump", "valve", "compressor", "heat exchanger", "thermometer", "filter", "sensor", "motor"]
    actions = ["Routine Maintenance", "Pressure Check", "Temperature Calibration", "Filter Replacement", "Safety Inspection", "Emergency Shutdown", "Performance Audit"]
    statuses = ["[PENDING]", "[PENDING]", "[PENDING]", "[APPROVED]"]  # More pending than approved for realism
    
    try:
        # Read existing approval data
        existing_data = {}
        try:
            with open(approval_json_file, 'r') as f:
                existing_data = json.load(f)
                print(f"Existing items: {len(existing_data)}")
        except FileNotFoundError:
            print(f"Approval file {approval_json_file} not found, creating new file.")
        except json.JSONDecodeError:
            print(f"Error reading approval file {approval_json_file}, starting with empty data.")
        
        # Generate new random items
        new_items = {}
        for i in range(count):
            tracking_number = generate_random_tracking_number()
            # Ensure unique tracking numbers
            while tracking_number in existing_data or tracking_number in new_items:
                tracking_number = generate_random_tracking_number()
            
            new_items[tracking_number] = {
                "action": actions[randint(0, len(actions) - 1)],
                "equipment_id": tracking_number,
                "equipment_type": equipment_types[randint(0, len(equipment_types) - 1)],
                "status": statuses[randint(0, len(statuses) - 1)],
                "created_on": datetime.now().isoformat()
            }
            print(f"  {i+1}. {tracking_number} - {new_items[tracking_number]['action']} ({new_items[tracking_number]['status']})")
        
        # Merge with existing data
        existing_data.update(new_items)
        
        # Write updated data back to file
        with open(approval_json_file, 'w') as f:
            json.dump(existing_data, f, indent=4)
        
        print(f"\n✅ Successfully added {count} new random approval items!")
        print(f"Total items in database: {len(existing_data)}")
        return new_items
        
    except Exception as e:
        print(f"❌ Error adding random approval items: {e}")
        return {}

if __name__ == "__main__":
    print("=== Adding Random Approval Items ===")
    
    # Ask user how many items to add
    try:
        count = int(input("How many random items to add? (default 3): ") or "3")
    except ValueError:
        count = 3
    
    new_items = add_random_approval_items(count)
    
    if new_items:
        print(f"\n🎲 New tracking numbers generated:")
        for tracking_number in new_items:
            print(f"  - {tracking_number}")