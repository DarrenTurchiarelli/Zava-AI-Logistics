# Last Mile Logistics Parcel Scanner Demo with Azure Cosmos DB Integration
# This script simulates a parcel barcode scanning system for logistics operations
# Covers the journey: Store Intake → Sorting Facility → Driver Delivery → Customer Handoff

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from cosmosdb_tools import (
    register_parcel, get_all_parcels, get_parcel_by_barcode, get_parcel_by_tracking_number,
    update_parcel_status, create_tracking_event, get_parcel_tracking_history,
    record_delivery_attempt, get_delivery_attempts, add_random_test_parcels
)
import random
import string

# Load environment variables
load_dotenv()

def generate_parcel_barcode():
    """Generate a random parcel barcode"""
    prefix = random.choice(['LP', 'EX', 'RG', 'OV', 'PR'])  # LastPost, Express, Regular, Overnight, Priority
    numbers = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    return f"{prefix}{numbers}"

def get_sample_parcels():
    """Get sample parcels for demonstration"""
    parcels = [
        {
            'sender_name': 'TechMart Electronics',
            'sender_address': '45 Collins Street, Melbourne CBD, Melbourne VIC 3000',
            'sender_phone': '+61 3 9123 4567',
            'recipient_name': 'Sarah Johnson',
            'recipient_address': '123 George Street, Sydney CBD, Sydney NSW 2000',
            'recipient_phone': '+61 2 8765 4321',
            'destination_postcode': '2000',
            'service_type': 'express',
            'weight': 1.2,
            'dimensions': '25x20x8cm',
            'declared_value': 299.99,
            'special_instructions': 'Fragile electronics - handle with care',
            'store_location': 'Store_Melbourne_CBD'
        },
        {
            'sender_name': 'Fashion Forward Ltd',
            'sender_address': '78 Bourke Street, Melbourne CBD, Melbourne VIC 3000',
            'sender_phone': '+61 3 9456 7890',
            'recipient_name': 'Michael Chen',
            'recipient_address': '456 King Street, Brisbane CBD, Brisbane QLD 4000',
            'recipient_phone': '+61 7 3987 6543',
            'destination_postcode': '4000',
            'service_type': 'standard',
            'weight': 0.8,
            'dimensions': '35x25x5cm',
            'declared_value': 89.99,
            'special_instructions': 'Gift wrapping included',
            'store_location': 'Store_Melbourne_Central'
        },
        {
            'sender_name': 'Medical Supplies Direct',
            'sender_address': '12 Macquarie Street, Sydney CBD, Sydney NSW 2000',
            'sender_phone': '+61 2 9234 5678',
            'recipient_name': 'Dr. Emma Wilson',
            'recipient_address': '789 Adelaide Street, Brisbane CBD, Brisbane QLD 4000',
            'recipient_phone': '+61 7 3567 8901',
            'destination_postcode': '4000',
            'service_type': 'overnight',
            'weight': 2.1,
            'dimensions': '30x20x15cm',
            'declared_value': 150.00,
            'special_instructions': 'Temperature sensitive - refrigerated transport required',
            'store_location': 'Store_Sydney_CBD'
        },
        {
            'sender_name': 'HomeOffice Solutions',
            'sender_address': '33 Eagle Street, Brisbane CBD, Brisbane QLD 4000',
            'sender_phone': '+61 7 3087 6543',
            'recipient_name': 'James Brown',
            'recipient_address': '101 Chapel Street, South Yarra, Melbourne VIC 3141',
            'recipient_phone': '+61 3 9345 6789',
            'destination_postcode': '3141',
            'service_type': 'registered',
            'weight': 5.4,
            'dimensions': '45x35x25cm',
            'declared_value': 450.00,
            'special_instructions': 'Office furniture - assembly required',
            'store_location': 'Store_Brisbane_CBD'
        },
        {
            'sender_name': 'BookWorld Online',
            'sender_address': '67 Swanston Street, Melbourne CBD, Melbourne VIC 3000',
            'sender_phone': '+61 3 9789 0123',
            'recipient_name': 'Lucy Martinez',
            'recipient_address': '234 Flinders Street, Adelaide CBD, Adelaide SA 5000',
            'recipient_phone': '+61 8 8456 7890',
            'destination_postcode': '5000',
            'service_type': 'standard',
            'weight': 1.8,
            'dimensions': '28x22x12cm',
            'declared_value': 45.50,
            'special_instructions': 'Educational materials - student delivery',
            'store_location': 'Store_Melbourne_CBD'
        }
    ]
    return parcels

async def register_parcel_interactive():
    """Interactive parcel registration (store intake)"""
    print("\n=== Store Parcel Registration ===")
    print("Enter parcel details (or 'q' to quit):")
    
    while True:
        barcode = input("\nParcel barcode (or press Enter for auto-generated): ").strip()
        if barcode.lower() == 'q':
            break
        
        if not barcode:
            barcode = generate_parcel_barcode()
            print(f"Generated barcode: {barcode}")
        
        # Check if barcode already exists
        existing_parcel = await get_parcel_by_barcode(barcode)
        if existing_parcel:
            print(f"Warning: Parcel with barcode {barcode} already exists!")
            continue
        
        # Sender information
        print("\n--- Sender Information ---")
        sender_name = input("Sender name: ").strip()
        if not sender_name:
            print("Sender name is required!")
            continue
        
        sender_address = input("Sender address: ").strip()
        if not sender_address:
            print("Sender address is required!")
            continue
        
        sender_phone = input("Sender phone [optional]: ").strip() or None
        
        # Recipient information
        print("\n--- Recipient Information ---")
        recipient_name = input("Recipient name: ").strip()
        if not recipient_name:
            print("Recipient name is required!")
            continue
        
        recipient_address = input("Recipient address: ").strip()
        if not recipient_address:
            print("Recipient address is required!")
            continue
        
        recipient_phone = input("Recipient phone [optional]: ").strip() or None
        
        destination_postcode = input("Destination postcode: ").strip()
        if not destination_postcode:
            print("Destination postcode is required!")
            continue
        
        # Parcel details
        print("\n--- Parcel Details ---")
        service_type = input("Service type (standard/express/overnight/registered) [standard]: ").strip()
        if not service_type:
            service_type = "standard"
        
        weight_str = input("Weight (kg) [optional]: ").strip()
        weight = float(weight_str) if weight_str else None
        
        dimensions = input("Dimensions (LxWxH cm) [optional]: ").strip() or None
        
        declared_value_str = input("Declared value (£) [optional]: ").strip()
        declared_value = float(declared_value_str) if declared_value_str else None
        
        special_instructions = input("Special instructions [optional]: ").strip() or None
        
        store_location = input("Store location [Store_Central]: ").strip()
        if not store_location:
            store_location = "Store_Central"
        
        try:
            # Register the parcel
            parcel = await register_parcel(
                barcode=barcode,
                sender_name=sender_name,
                sender_address=sender_address,
                sender_phone=sender_phone,
                recipient_name=recipient_name,
                recipient_address=recipient_address,
                recipient_phone=recipient_phone,
                destination_postcode=destination_postcode,
                service_type=service_type,
                weight=weight,
                dimensions=dimensions,
                declared_value=declared_value,
                special_instructions=special_instructions,
                store_location=store_location
            )
            
            print(f"\n✅ Parcel registered successfully!")
            print(f"Barcode: {parcel['barcode']}")
            print(f"Tracking Number: {parcel['tracking_number']}")
            print(f"Service Type: {parcel['service_type']}")
            print(f"Estimated Delivery: {parcel['estimated_delivery']}")
            print(f"Registration Time: {parcel['registration_timestamp']}")
            
        except Exception as e:
            print(f"❌ Error registering parcel: {e}")

async def register_sample_parcels():
    """Register predefined sample parcels"""
    print("\n=== Registering Sample Parcels ===")
    
    sample_parcels = get_sample_parcels()
    registered_count = 0
    
    for sample in sample_parcels:
        barcode = generate_parcel_barcode()
        
        try:
            parcel = await register_parcel(
                barcode=barcode,
                **sample
            )
            
            registered_count += 1
            print(f"✅ Registered: {barcode} - {sample['recipient_name']}")
            print(f"   Tracking: {parcel['tracking_number']} | Service: {sample['service_type']}")
            
        except Exception as e:
            print(f"❌ Error registering {barcode}: {e}")
    
    print(f"\nRegistered {registered_count} sample parcels successfully!")

async def view_recent_parcels():
    """View recently registered parcels"""
    print("\n=== Recent Parcels ===")
    
    try:
        parcels = await get_all_parcels()
        
        if not parcels:
            print("No parcels found.")
            return
        
        print(f"Found {len(parcels)} parcels:")
        print("-" * 120)
        
        for i, parcel in enumerate(parcels[:10], 1):  # Show last 10 parcels
            print(f"{i:2d}. Barcode: {parcel['barcode']} | Tracking: {parcel['tracking_number']}")
            print(f"    From: {parcel['sender_name']}")
            print(f"    To: {parcel['recipient_name']} ({parcel['destination_postcode']})")
            print(f"    Service: {parcel['service_type']} | Status: {parcel['current_status']}")
            print(f"    Location: {parcel['current_location']}")
            print(f"    Registered: {parcel['registration_timestamp']}")
            if parcel.get('special_instructions'):
                print(f"    Special: {parcel['special_instructions']}")
            print("-" * 120)
        
        if len(parcels) > 10:
            print(f"... and {len(parcels) - 10} more parcels")
            
    except Exception as e:
        print(f"Error retrieving parcels: {e}")

async def track_parcel():
    """Track a parcel by barcode or tracking number"""
    print("\n=== Track Parcel ===")
    
    identifier = input("Enter barcode or tracking number: ").strip()
    if not identifier:
        print("Barcode or tracking number is required!")
        return
    
    try:
        # Try to find by barcode first
        parcel = await get_parcel_by_barcode(identifier)
        
        # If not found by barcode, try tracking number
        if not parcel:
            parcel = await get_parcel_by_tracking_number(identifier)
        
        if parcel:
            print("\n✅ Parcel found:")
            print(f"Barcode: {parcel['barcode']}")
            print(f"Tracking Number: {parcel['tracking_number']}")
            print(f"From: {parcel['sender_name']}")
            print(f"To: {parcel['recipient_name']}")
            print(f"Address: {parcel['recipient_address']}")
            print(f"Service: {parcel['service_type']}")
            print(f"Status: {parcel['current_status']}")
            print(f"Location: {parcel['current_location']}")
            print(f"Delivery Attempts: {parcel['delivery_attempts']}")
            print(f"Delivered: {'Yes' if parcel['is_delivered'] else 'No'}")
            
            if parcel.get('weight'):
                print(f"Weight: {parcel['weight']} kg")
            if parcel.get('dimensions'):
                print(f"Dimensions: {parcel['dimensions']}")
            if parcel.get('declared_value'):
                print(f"Declared Value: £{parcel['declared_value']}")
            if parcel.get('special_instructions'):
                print(f"Special Instructions: {parcel['special_instructions']}")
            
            print(f"Estimated Delivery: {parcel['estimated_delivery']}")
            
            # Show tracking history
            print("\n--- Tracking History ---")
            tracking_events = await get_parcel_tracking_history(parcel['barcode'])
            if tracking_events:
                for event in tracking_events:
                    print(f"• {event['timestamp']}: {event['event_type'].upper()}")
                    print(f"  Location: {event['location']}")
                    print(f"  Description: {event['description']}")
                    print(f"  Scanned by: {event['scanned_by']}")
                    print()
            else:
                print("No tracking events found.")
        else:
            print(f"❌ No parcel found with identifier: {identifier}")
            
    except Exception as e:
        print(f"Error tracking parcel: {e}")

async def simulate_logistics_operations():
    """Simulate various logistics operations"""
    print("\n=== Simulate Logistics Operations ===")
    
    try:
        parcels = await get_all_parcels()
        if not parcels:
            print("No parcels found. Please register some parcels first.")
            return
        
        operations = [
            ("Sort at facility", "in_transit", "Sorting_Facility_North"),
            ("Load on vehicle", "out_for_delivery", "Delivery_Vehicle_DV001"),
            ("Delivery attempt", "out_for_delivery", "Customer_Address"),
            ("Delivered", "delivered", "Customer_Address")
        ]
        
        # Take a random parcel
        parcel = random.choice(parcels)
        print(f"Simulating operations for parcel: {parcel['tracking_number']}")
        
        for description, status, location in operations:
            await update_parcel_status(
                barcode=parcel['barcode'],
                status=status,
                location=location,
                scanned_by=f"logistics_system_{random.randint(1, 99)}"
            )
            print(f"✅ {description}: {status} at {location}")
        
        print("\nSimulation completed!")
        
    except Exception as e:
        print(f"Error simulating operations: {e}")

async def main():
    """Main logistics parcel scanner demo"""
    print("Last Mile Logistics Parcel Scanner with Azure Cosmos DB")
    print("=" * 60)
    
    # Check environment variables
    if not os.getenv("COSMOS_DB_ENDPOINT") or not os.getenv("COSMOS_DB_KEY"):
        print("ERROR: COSMOS_DB_ENDPOINT and COSMOS_DB_KEY environment variables must be set")
        print("Please update your .env file with your Cosmos DB credentials")
        return
    
    while True:
        print("\nLogistics Operations Menu:")
        print("1. Register parcel (store intake)")
        print("2. Register sample parcels")
        print("3. View recent parcels")
        print("4. Track parcel")
        print("5. Simulate logistics operations")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        try:
            if choice == "1":
                await register_parcel_interactive()
            elif choice == "2":
                await register_sample_parcels()
            elif choice == "3":
                await view_recent_parcels()
            elif choice == "4":
                await track_parcel()
            elif choice == "5":
                await simulate_logistics_operations()
            elif choice == "6":
                print("Exiting logistics parcel scanner demo...")
                break
            else:
                print("Invalid choice. Please try again.")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())