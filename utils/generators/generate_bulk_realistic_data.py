#!/usr/bin/env python3
"""
Generate bulk realistic parcel data for comprehensive testing and demos

Creates:
- Thousands of realistic parcels across all states
- Specific demo parcels for Voice & Text Examples
- Driver manifests with delivery routes
- Approval requests
- Photo proof attachments
- Complete event histories

Usage:
    python generate_bulk_realistic_data.py [--count N]

Example:
    python generate_bulk_realistic_data.py --count 2000
"""

import asyncio
import os
import sys
import random
import base64
from datetime import datetime, timedelta
from typing import List, Dict
import argparse

from dotenv import load_dotenv

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from parcel_tracking_db import ParcelTrackingDB
from faker import Faker

load_dotenv()

# Initialize Faker for Australian data
fake = Faker('en_AU')

# Australian states and major cities
AUSTRALIAN_LOCATIONS = {
    'NSW': ['Sydney', 'Newcastle', 'Wollongong', 'Central Coast', 'Blue Mountains'],
    'VIC': ['Melbourne', 'Geelong', 'Ballarat', 'Bendigo', 'Shepparton'],
    'QLD': ['Brisbane', 'Gold Coast', 'Sunshine Coast', 'Townsville', 'Cairns'],
    'WA': ['Perth', 'Fremantle', 'Mandurah', 'Bunbury', 'Albany'],
    'SA': ['Adelaide', 'Mount Gambier', 'Whyalla', 'Murray Bridge', 'Port Augusta'],
    'TAS': ['Hobart', 'Launceston', 'Devonport', 'Burnie', 'Kingston'],
    'ACT': ['Canberra', 'Belconnen', 'Tuggeranong', 'Woden', 'Gungahlin'],
    'NT': ['Darwin', 'Alice Springs', 'Palmerston', 'Katherine', 'Nhulunbuy']
}

# Diverse recipient names (matching Voice & Text Examples)
COMMON_RECIPIENTS = [
    "Dr. Emma Wilson", "Sarah Johnson", "Michael Chen", "Olivia Brown",
    "William Taylor", "Sophia Anderson", "Benjamin Lee", "Charlotte Harris",
    "Daniel Kim", "Amelia White", "Lucas Thompson", "Mia Garcia",
    "Ethan Rodriguez", "Isabella Martinez", "James Anderson", "Emily Davis"
]

# Sample sender names/companies
SENDER_NAMES = [
    "Amazon Australia", "eBay Seller", "Woolworths", "Coles Online",
    "The Iconic", "MyDeal", "Kogan", "Catch.com.au", "Private Sender",
    "JB Hi-Fi", "Harvey Norman", "Bunnings", "Chemist Warehouse",
    "Myer", "David Jones", "Cotton On", "Country Road"
]

# Demo parcels for Voice & Text Examples (these must exist)
DEMO_PARCELS = [
    {
        'tracking_number': 'RG857954',
        'recipient_name': 'Dr. Emma Wilson',
        'sender_name': 'Amazon Australia',
        'status': 'Out For Delivery',
        'address': '123 Medical Centre Drive, Sydney NSW 2000',
        'phone': '+61 2 9555 1234',
        'state': 'NSW',
        'city': 'Sydney',
        'has_photo': True,
        'has_history': True,
        'assigned_driver': 'driver-001'
    },
    {
        'tracking_number': 'DT202512170037',
        'recipient_name': 'Sarah Johnson',
        'sender_name': 'Private Sender',
        'status': 'Delivered',
        'address': '456 Business Park Road, Perth WA 6000',
        'phone': '+61 8 9000 5678',
        'state': 'WA',
        'city': 'Perth',
        'has_photo': True,
        'has_history': True,
        'assigned_driver': 'driver-003'
    }
]

def generate_tracking_number(prefix: str = 'RG') -> str:
    """Generate realistic tracking number"""
    return f"{prefix}{random.randint(100000, 999999)}"

def generate_barcode(prefix: str = 'LP') -> str:
    """Generate barcode in LP format"""
    timestamp = datetime.now().strftime('%Y%m%d')
    sequence = random.randint(1000, 9999)
    return f"{prefix}{timestamp}{sequence}"

def generate_dummy_photo() -> str:
    """Generate dummy base64-encoded photo data"""
    # Simple 1x1 transparent PNG as base64
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

async def create_demo_parcel(db: ParcelTrackingDB, parcel_spec: Dict) -> str:
    """Create a specific demo parcel with full history and photos"""
    barcode = generate_barcode()
    
    # Register parcel
    parcel_doc = await db.register_parcel(
        barcode=barcode,
        tracking_number=parcel_spec['tracking_number'],
        sender_name=parcel_spec['sender_name'],
        sender_address=f"Warehouse, {parcel_spec['city']} {parcel_spec['state']}",
        sender_phone=fake.phone_number(),
        recipient_name=parcel_spec['recipient_name'],
        recipient_address=parcel_spec['address'],
        recipient_phone=parcel_spec['phone'],
        recipient_postcode=parcel_spec['address'].split()[-1] if len(parcel_spec['address'].split()) > 0 else '2000',
        weight=round(random.uniform(0.5, 25.0), 2),
        dimensions=f"{random.randint(10,50)}x{random.randint(10,50)}x{random.randint(5,30)}",
        service_type=random.choice(['standard', 'express', 'same-day']),
        store_location=f"DC-{parcel_spec['state']}-01"
    )
    
    if not parcel_doc:
        print(f"  ⚠ Failed to create demo parcel {parcel_spec['tracking_number']}")
        return None
    
    # Add lodgement photo if specified
    if parcel_spec.get('has_photo'):
        await db.add_lodgement_photos(barcode, [generate_dummy_photo()])
    
    # Create event history if specified
    if parcel_spec.get('has_history'):
        events = [
            ('Parcel Registered', 'Sender', 3),
            ('Collected from Sender', 'Depot', 2),
            ('Arrived at Sorting Facility', 'Depot', 1),
            ('Sorted and Ready', 'Depot', 1),
        ]
        
        if parcel_spec['status'] in ['Out For Delivery', 'Delivered']:
            events.append(('Out For Delivery', parcel_spec.get('assigned_driver', 'driver-001'), 0))
        
        if parcel_spec['status'] == 'Delivered':
            events.append(('Delivered', parcel_spec.get('assigned_driver', 'driver-001'), 0))
            # Add delivery photo
            await db.add_delivery_proof(
                barcode=barcode,
                photo_data=generate_dummy_photo(),
                signature_data=None,
                delivered_to=parcel_spec['recipient_name'],
                notes="Delivered successfully"
            )
        
        # Add events with realistic timestamps
        base_time = datetime.now() - timedelta(days=2)
        for i, (description, location, days_ago) in enumerate(events):
            event_time = base_time + timedelta(days=days_ago, hours=i)
            await db.log_event(
                barcode=barcode,
                event_timestamp=event_time,
                event_description=description,
                event_location=location,
                event_status=parcel_spec['status'] if i == len(events)-1 else 'In Transit'
            )
    
    # Assign to driver if specified
    if parcel_spec.get('assigned_driver'):
        await db.update_parcel_status(
            barcode=barcode,
            new_status=parcel_spec['status'],
            assigned_driver=parcel_spec['assigned_driver']
        )
    
    print(f"  ✓ Created demo parcel: {parcel_spec['tracking_number']} - {parcel_spec['recipient_name']}")
    return barcode

async def create_realistic_parcel(db: ParcelTrackingDB, state: str, city: str, index: int) -> str:
    """Create a realistic parcel for a specific state/city"""
    
    tracking_prefix = random.choice(['RG', 'DT', 'LP', 'EX'])
    tracking_number = generate_tracking_number(tracking_prefix)
    barcode = generate_barcode()
    
    recipient_name = random.choice(COMMON_RECIPIENTS + [fake.name() for _ in range(3)])
    sender_name = random.choice(SENDER_NAMES)
    
    # Generate realistic Australian address
    street_number = random.randint(1, 999)
    street_name = fake.street_name()
    postcode = random.randint(2000, 6999) if state in ['NSW', 'ACT'] else random.randint(3000, 8999)
    
    address = f"{street_number} {street_name}, {city} {state} {postcode}"
    
    # Vary statuses for realism
    statuses = [
        ('At Depot', 30),
        ('Sorting', 20),
        ('Out For Delivery', 25),
        ('Delivered', 20),
        ('In Transit', 5)
    ]
    status = random.choices([s[0] for s in statuses], weights=[s[1] for s in statuses])[0]
    
    # Register parcel
    parcel_doc = await db.register_parcel(
        barcode=barcode,
        tracking_number=tracking_number,
        sender_name=sender_name,
        sender_address=f"Warehouse, {city} {state}",
        sender_phone=fake.phone_number(),
        recipient_name=recipient_name,
        recipient_address=address,
        recipient_phone=fake.phone_number(),
        recipient_postcode=str(postcode),
        weight=round(random.uniform(0.1, 30.0), 2),
        dimensions=f"{random.randint(10,60)}x{random.randint(10,60)}x{random.randint(5,40)}",
        service_type=random.choice(['standard', 'express', 'express', 'same-day']),  # More express
        store_location=f"DC-{state}-01"
    )
    
    if not parcel_doc:
        return None
    
    # Add realistic event history (50% of parcels)
    if random.random() < 0.5:
        base_time = datetime.now() - timedelta(days=random.randint(1, 7))
        await db.log_event(
            barcode=barcode,
            event_timestamp=base_time,
            event_description='Parcel Registered',
            event_location='Sender',
            event_status='Pending'
        )
        
        # Add more events for parcels in later stages
        if status in ['Delivered', 'Out For Delivery']:
            await db.log_event(
                barcode=barcode,
                event_timestamp=base_time + timedelta(hours=6),
                event_description='Arrived at Sorting Facility',
                event_location=f"DC-{state}-01",
                event_status='Sorting'
            )
    
    # Add photos for delivered parcels (30% chance)
    if status == 'Delivered' and random.random() < 0.3:
        await db.add_delivery_proof(
            barcode=barcode,
            photo_data=generate_dummy_photo(),
            signature_data=None,
            delivered_to=recipient_name,
            notes="Delivered successfully"
        )
    
    # Assign to drivers for out for delivery/delivered parcels
    if status in ['Out For Delivery', 'Delivered']:
        driver_num = random.randint(1, 57)
        driver_id = f"driver-{driver_num:03d}"
        await db.update_parcel_status(
            barcode=barcode,
            new_status=status,
            assigned_driver=driver_id
        )
    
    return barcode

async def main():
    parser = argparse.ArgumentParser(description='Generate bulk realistic parcel data')
    parser.add_argument('--count', type=int, default=2000, help='Number of parcels to generate (default: 2000)')
    args = parser.parse_args()
    
    total_parcels = args.count
    
    print("=" * 80)
    print("🚀 BULK REALISTIC DATA GENERATOR")
    print("=" * 80)
    print(f"Target: {total_parcels:,} parcels across all Australian states")
    print()
    
    async with ParcelTrackingDB() as db:
        # Step 1: Create specific demo parcels for Voice & Text Examples
        print("📋 Step 1: Creating Demo Parcels for Voice & Text Examples")
        print("-" * 80)
        
        demo_created = 0
        for demo_spec in DEMO_PARCELS:
            barcode = await create_demo_parcel(db, demo_spec)
            if barcode:
                demo_created += 1
        
        print(f"\n✓ Created {demo_created} demo parcels")
        print()
        
        # Step 2: Create bulk realistic parcels distributed across states
        print(f"📦 Step 2: Creating {total_parcels:,} Realistic Parcels")
        print("-" * 80)
        
        # Distribute parcels across states proportionally to population
        state_weights = {
            'NSW': 0.32,  # 32% - most populous
            'VIC': 0.26,  # 26%
            'QLD': 0.20,  # 20%
            'WA': 0.11,   # 11%
            'SA': 0.07,   # 7%
            'TAS': 0.02,  # 2%
            'ACT': 0.02,  # 2%
            'NT': 0.01    # 1%
        }
        
        created_count = 0
        failed_count = 0
        
        for state, weight in state_weights.items():
            state_parcel_count = int(total_parcels * weight)
            cities = AUSTRALIAN_LOCATIONS[state]
            
            print(f"\n  📍 {state} - Creating {state_parcel_count:,} parcels...")
            
            for i in range(state_parcel_count):
                city = random.choice(cities)
                barcode = await create_realistic_parcel(db, state, city, i)
                
                if barcode:
                    created_count += 1
                else:
                    failed_count += 1
                
                # Progress indicator every 100 parcels
                if (i + 1) % 100 == 0:
                    print(f"    Progress: {i+1}/{state_parcel_count} parcels", end='\r')
            
            print(f"    ✓ Completed {state}: {state_parcel_count:,} parcels")
        
        print()
        print("=" * 80)
        print("📊 GENERATION SUMMARY")
        print("=" * 80)
        print(f"  Demo parcels created:     {demo_created}")
        print(f"  Bulk parcels created:     {created_count:,}")
        print(f"  Failed:                   {failed_count:,}")
        print(f"  Total parcels created:    {demo_created + created_count:,}")
        print()
        
        # Step 3: Generate statistics
        print("📈 Step 3: Database Statistics")
        print("-" * 80)
        
        all_parcels = await db.get_all_parcels()
        print(f"  Total parcels in database: {len(all_parcels):,}")
        
        # Status breakdown
        status_counts = {}
        for parcel in all_parcels:
            status = parcel.get('current_status', 'Unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"\n  📋 Status Distribution:")
        for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(all_parcels)) * 100
            print(f"    {status:20} {count:6,} ({percentage:5.1f}%)")
        
        # State breakdown
        state_counts = {}
        for parcel in all_parcels:
            address = parcel.get('recipient_address', '')
            for state in AUSTRALIAN_LOCATIONS.keys():
                if state in address:
                    state_counts[state] = state_counts.get(state, 0) + 1
                    break
        
        print(f"\n  🗺️  State Distribution:")
        for state, count in sorted(state_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(all_parcels)) * 100 if len(all_parcels) > 0 else 0
            print(f"    {state}:  {count:6,} ({percentage:5.1f}%)")
        
        # Verify demo parcels exist
        print(f"\n  🎯 Demo Parcel Verification:")
        for demo_spec in DEMO_PARCELS:
            parcel = await db.search_parcels_by_tracking(demo_spec['tracking_number'])
            if parcel:
                print(f"    ✓ {demo_spec['tracking_number']:20} - {demo_spec['recipient_name']}")
            else:
                print(f"    ✗ {demo_spec['tracking_number']:20} - NOT FOUND")
        
        print()
        print("=" * 80)
        print("✅ BULK DATA GENERATION COMPLETE!")
        print("=" * 80)
        print()
        print("🎤 Voice & Text Examples Ready:")
        print("  • 'Track parcel RG857954'")
        print("  • 'Photo proof for parcel DT202512170037'")
        print("  • 'Show me the full history for RG857954'")
        print("  • 'Who sent parcel RG857954?'")
        print("  • 'Find parcels for Dr. Emma Wilson'")
        print("  • 'Show me delivery statistics for Western Australia'")
        print()

if __name__ == "__main__":
    asyncio.run(main())
