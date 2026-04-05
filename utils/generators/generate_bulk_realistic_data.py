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
import time
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

# Initialize Faker for Australian data (names/phones only — NOT addresses)
fake = Faker('en_AU')

# ── Distribution Centre mapping ───────────────────────────────────────────────
# Maps (state, city) → primary DC ID from the 40 physical Australian DCs.
# A parcel can originate at its state's DC and transit through hub DCs
# (e.g. VIC→MEL hub then SYD hub before NSW delivery).
STATE_DCS = {
    'NSW': ['DC-SYD-001', 'DC-SYD-002', 'DC-SYD-003', 'DC-NEW-001', 'DC-WOL-001',
            'DC-DUB-001', 'DC-TAM-001', 'DC-ARM-001', 'DC-ALB-001', 'DC-WAG-001'],
    'VIC': ['DC-MEL-001', 'DC-MEL-002', 'DC-MEL-003', 'DC-GEE-001', 'DC-BAL-001',
            'DC-BEN-001', 'DC-TRA-001', 'DC-SHP-001'],
    'QLD': ['DC-BNE-001', 'DC-BNE-002', 'DC-BNE-003', 'DC-GLD-001', 'DC-TWD-001',
            'DC-CAI-001', 'DC-TOW-001', 'DC-ROC-001'],
    'WA':  ['DC-PER-001', 'DC-PER-002', 'DC-BUN-001', 'DC-GER-001', 'DC-KAL-001'],
    'SA':  ['DC-ADL-001', 'DC-ADL-002', 'DC-MOU-001', 'DC-WHY-001', 'DC-POR-001'],
    'TAS': ['DC-HOB-001', 'DC-LAU-001'],
    'ACT': ['DC-CAN-001'],
    'NT':  ['DC-DAR-001'],
}
# Inter-state hub DCs — parcels crossing state lines typically pass through one
INTERSTATE_HUBS = ['DC-SYD-001', 'DC-MEL-001', 'DC-BNE-001', 'DC-PER-001', 'DC-ADL-001']


def pick_dc(state: str) -> str:
    """Pick a primary DC for a parcel based on its origin state."""
    options = STATE_DCS.get(state, ['DC-SYD-001'])
    return random.choice(options)


# ── Real GNAF-verified Australian street pools ────────────────────────────────
# Format: (min_number, max_number, street_name, suburb, postcode)
# All streets are real and exist in the Geocoded National Address File (GNAF).
REAL_STREET_POOLS = {
    # ── NSW ──────────────────────────────────────────────────────────────────
    ('NSW', 'Sydney'): [
        (1, 600, 'George Street', 'Sydney', '2000'),
        (1, 350, 'Pitt Street', 'Sydney', '2000'),
        (1, 350, 'Castlereagh Street', 'Sydney', '2000'),
        (1, 450, 'Elizabeth Street', 'Sydney', '2000'),
        (1, 500, 'Kent Street', 'Sydney', '2000'),
        (1, 300, 'Clarence Street', 'Sydney', '2000'),
        (1, 200, 'York Street', 'Sydney', '2000'),
        (1, 300, 'Sussex Street', 'Sydney', '2000'),
        (1, 400, 'Market Street', 'Sydney', '2000'),
        (1, 300, 'King Street', 'Sydney', '2000'),
        (1, 250, 'Hunter Street', 'Sydney', '2000'),
        (1, 200, 'Bridge Street', 'Sydney', '2000'),
        (1, 180, 'Macquarie Street', 'Sydney', '2000'),
        (1,  30, 'Bligh Street', 'Sydney', '2000'),
        (1, 100, 'Bond Street', 'Sydney', '2000'),
        (1, 300, 'Miller Street', 'North Sydney', '2060'),
        (1, 400, 'Pacific Highway', 'North Sydney', '2060'),
        (1, 200, 'Berry Street', 'North Sydney', '2060'),
        (1, 300, 'Harris Street', 'Pyrmont', '2009'),
        (1, 200, 'Union Street', 'Pyrmont', '2009'),
        (1, 700, 'Crown Street', 'Surry Hills', '2010'),
        (1, 400, 'Foveaux Street', 'Surry Hills', '2010'),
        (1, 600, 'Cleveland Street', 'Surry Hills', '2010'),
        (1, 500, 'King Street', 'Newtown', '2042'),
        (1, 400, 'Enmore Road', 'Newtown', '2042'),
        (1, 400, 'Church Street', 'Parramatta', '2150'),
        (1, 300, 'Smith Street', 'Parramatta', '2150'),
        (1, 200, 'Marsden Street', 'Parramatta', '2150'),
        (1, 400, 'Victoria Road', 'Parramatta', '2150'),
        (1, 400, 'Anzac Parade', 'Kensington', '2033'),
        (1, 350, 'High Street', 'Randwick', '2031'),
        (1, 500, 'Oxford Street', 'Darlinghurst', '2010'),
        (1, 400, 'Victoria Street', 'Darlinghurst', '2010'),
        (1, 600, 'Parramatta Road', 'Camperdown', '2050'),
        (1, 300, 'Missenden Road', 'Camperdown', '2050'),
        (1, 400, 'Illawarra Road', 'Marrickville', '2204'),
        (1, 500, 'Marrickville Road', 'Marrickville', '2204'),
        (1, 300, 'New South Head Road', 'Edgecliff', '2027'),
        (1, 400, 'Old South Head Road', 'Bondi Junction', '2022'),
        (1, 300, 'Campbell Parade', 'Bondi Beach', '2026'),
    ],
    ('NSW', 'Newcastle'): [
        (1, 400, 'Hunter Street', 'Newcastle', '2300'),
        (1, 200, 'King Street', 'Newcastle', '2300'),
        (1, 300, 'Darby Street', 'Cooks Hill', '2300'),
        (1, 300, 'Beaumont Street', 'Hamilton', '2303'),
        (1, 200, 'Glebe Road', 'Honeysuckle', '2300'),
        (1, 300, 'Pacific Highway', 'Charlestown', '2290'),
        (1, 200, 'Belford Street', 'Broadmeadow', '2292'),
        (1, 300, 'Maitland Road', 'Mayfield', '2304'),
    ],
    ('NSW', 'Wollongong'): [
        (1, 300, 'Crown Street', 'Wollongong', '2500'),
        (1, 200, 'Keira Street', 'Wollongong', '2500'),
        (1, 200, 'Church Street', 'Wollongong', '2500'),
        (1, 400, 'Princes Highway', 'Dapto', '2530'),
        (1, 300, 'Corrimal Street', 'Wollongong', '2500'),
        (1, 200, 'Market Street', 'Wollongong', '2500'),
    ],
    # ── VIC ──────────────────────────────────────────────────────────────────
    ('VIC', 'Melbourne'): [
        (1, 600, 'Collins Street', 'Melbourne', '3000'),
        (1, 600, 'Bourke Street', 'Melbourne', '3000'),
        (1, 400, 'Flinders Street', 'Melbourne', '3000'),
        (1, 400, 'Swanston Street', 'Melbourne', '3000'),
        (1, 600, 'Elizabeth Street', 'Melbourne', '3000'),
        (1, 300, 'Spencer Street', 'Melbourne', '3000'),
        (1, 200, 'King Street', 'Melbourne', '3000'),
        (1, 400, 'William Street', 'Melbourne', '3000'),
        (1, 400, 'Queen Street', 'Melbourne', '3000'),
        (1, 400, 'Exhibition Street', 'Melbourne', '3000'),
        (1, 200, 'Spring Street', 'Melbourne', '3000'),
        (1, 200, 'Lonsdale Street', 'Melbourne', '3000'),
        (1, 500, 'Clarendon Street', 'South Melbourne', '3205'),
        (1, 300, 'City Road', 'South Melbourne', '3205'),
        (1, 400, 'Brunswick Street', 'Fitzroy', '3065'),
        (1, 300, 'Smith Street', 'Fitzroy', '3065'),
        (1, 400, 'Johnston Street', 'Fitzroy', '3065'),
        (1, 300, 'Fitzroy Street', 'St Kilda', '3182'),
        (1, 200, 'Acland Street', 'St Kilda', '3182'),
        (1, 500, 'Bridge Road', 'Richmond', '3121'),
        (1, 500, 'Swan Street', 'Richmond', '3121'),
        (1, 400, 'Church Street', 'Richmond', '3121'),
        (1, 400, 'Chapel Street', 'Prahran', '3181'),
        (1, 300, 'High Street', 'Prahran', '3181'),
        (1, 600, 'Sydney Road', 'Brunswick', '3056'),
        (1, 300, 'Nicholson Street', 'Carlton', '3053'),
        (1, 300, 'Lygon Street', 'Carlton', '3053'),
        (1, 400, 'Glenferrie Road', 'Hawthorn', '3122'),
    ],
    ('VIC', 'Geelong'): [
        (1, 300, 'Moorabool Street', 'Geelong', '3220'),
        (1, 200, 'Malop Street', 'Geelong', '3220'),
        (1, 200, 'Ryrie Street', 'Geelong', '3220'),
        (1, 400, 'Pakington Street', 'Geelong West', '3218'),
        (1, 300, 'Shannon Avenue', 'Geelong West', '3218'),
    ],
    # ── QLD ──────────────────────────────────────────────────────────────────
    ('QLD', 'Brisbane'): [
        (1, 300, 'Queen Street', 'Brisbane City', '4000'),
        (1, 400, 'Adelaide Street', 'Brisbane City', '4000'),
        (1, 500, 'Ann Street', 'Brisbane City', '4000'),
        (1, 400, 'George Street', 'Brisbane City', '4000'),
        (1, 200, 'Creek Street', 'Brisbane City', '4000'),
        (1, 200, 'Eagle Street', 'Brisbane City', '4000'),
        (1, 400, 'Mary Street', 'Brisbane City', '4000'),
        (1, 300, 'Charlotte Street', 'Brisbane City', '4000'),
        (1, 300, 'Edward Street', 'Brisbane City', '4000'),
        (1, 300, 'William Street', 'Brisbane City', '4000'),
        (1, 300, 'Grey Street', 'South Brisbane', '4101'),
        (1, 400, 'Melbourne Street', 'South Brisbane', '4101'),
        (1, 500, 'Brunswick Street', 'Fortitude Valley', '4006'),
        (1, 300, 'Logan Road', 'Woolloongabba', '4102'),
        (1, 300, 'Main Street', 'Kangaroo Point', '4169'),
        (1, 400, 'Wickham Street', 'Fortitude Valley', '4006'),
        (1, 500, 'Old Cleveland Road', 'Coorparoo', '4151'),
        (1, 400, 'Ipswich Road', 'Woolloongabba', '4102'),
        (1, 400, 'Gympie Road', 'Kedron', '4031'),
        (1, 300, 'Cavendish Road', 'Coorparoo', '4151'),
    ],
    ('QLD', 'Gold Coast'): [
        (1, 400, 'Cavill Avenue', 'Surfers Paradise', '4217'),
        (1, 300, 'Gold Coast Highway', 'Surfers Paradise', '4217'),
        (1, 200, 'Orchid Avenue', 'Surfers Paradise', '4217'),
        (1, 300, 'Elkhorn Avenue', 'Surfers Paradise', '4217'),
        (1, 400, 'Bundall Road', 'Bundall', '4217'),
        (1, 300, 'Ferry Road', 'Southport', '4215'),
        (1, 300, 'Scarborough Street', 'Southport', '4215'),
    ],
    ('QLD', 'Sunshine Coast'): [
        (1, 300, 'Aerodrome Road', 'Maroochydore', '4558'),
        (1, 200, 'Ocean Street', 'Maroochydore', '4558'),
        (1, 200, 'Sunshine Beach Road', 'Noosa Heads', '4567'),
        (1, 400, 'Nicklin Way', 'Warana', '4575'),
        (1, 200, 'Bulcock Street', 'Caloundra', '4551'),
    ],
    # ── WA ───────────────────────────────────────────────────────────────────
    ('WA', 'Perth'): [
        (1, 500, 'St Georges Terrace', 'Perth', '6000'),
        (1, 500, 'Hay Street', 'Perth', '6000'),
        (1, 500, 'Murray Street', 'Perth', '6000'),
        (1, 400, 'William Street', 'Perth', '6000'),
        (1, 300, 'Barrack Street', 'Perth', '6000'),
        (1, 200, 'Pier Street', 'Perth', '6000'),
        (1, 300, 'Wellington Street', 'Perth', '6000'),
        (1, 300, 'Aberdeen Street', 'Northbridge', '6003'),
        (1, 300, 'James Street', 'Northbridge', '6003'),
        (1, 300, 'Beaufort Street', 'Mount Lawley', '6050'),
        (1, 200, 'Rokeby Road', 'Subiaco', '6008'),
        (1, 500, 'Stirling Highway', 'Nedlands', '6009'),
        (1, 200, 'Broadway', 'Nedlands', '6009'),
        (1, 400, 'Albany Highway', 'Victoria Park', '6100'),
        (1, 300, 'Canning Highway', 'Applecross', '6153'),
        (1, 400, 'Grand Promenade', 'Bedford', '6052'),
        (1, 300, 'Walter Road', 'Morley', '6062'),
    ],
    ('WA', 'Fremantle'): [
        (1, 200, 'High Street', 'Fremantle', '6160'),
        (1, 200, 'Market Street', 'Fremantle', '6160'),
        (1, 300, 'William Street', 'Fremantle', '6160'),
        (1, 200, 'Queen Street', 'Fremantle', '6160'),
        (1, 300, 'South Terrace', 'Fremantle', '6160'),
        (1, 300, 'Hampton Road', 'Fremantle', '6160'),
    ],
    # ── SA ───────────────────────────────────────────────────────────────────
    ('SA', 'Adelaide'): [
        (1, 400, 'King William Street', 'Adelaide', '5000'),
        (1, 200, 'Grenfell Street', 'Adelaide', '5000'),
        (1, 100, 'Hindley Street', 'Adelaide', '5000'),
        (1, 400, 'Rundle Street', 'Adelaide', '5000'),
        (1, 300, 'Pulteney Street', 'Adelaide', '5000'),
        (1, 400, 'North Terrace', 'Adelaide', '5000'),
        (1, 300, 'Wakefield Street', 'Adelaide', '5000'),
        (1, 400, 'Hutt Street', 'Adelaide', '5000'),
        (1, 200, 'Grote Street', 'Adelaide', '5000'),
        (1, 300, 'Currie Street', 'Adelaide', '5000'),
        (1, 400, 'The Parade', 'Norwood', '5067'),
        (1, 400, 'Unley Road', 'Unley', '5061'),
        (1, 200, 'Jetty Road', 'Glenelg', '5045'),
        (1, 400, 'Main North Road', 'Prospect', '5082'),
        (1, 300, 'Port Road', 'Hindmarsh', '5007'),
    ],
    # ── TAS ──────────────────────────────────────────────────────────────────
    ('TAS', 'Hobart'): [
        (1, 200, 'Collins Street', 'Hobart', '7000'),
        (1, 300, 'Elizabeth Street', 'Hobart', '7000'),
        (1, 300, 'Liverpool Street', 'Hobart', '7000'),
        (1, 200, 'Harrington Street', 'Hobart', '7000'),
        (1, 400, 'Macquarie Street', 'Hobart', '7000'),
        (1, 100, 'Salamanca Place', 'Battery Point', '7004'),
        (1, 200, 'Sandy Bay Road', 'Sandy Bay', '7005'),
        (1, 200, 'New Town Road', 'New Town', '7008'),
    ],
    ('TAS', 'Launceston'): [
        (1, 300, 'Brisbane Street', 'Launceston', '7250'),
        (1, 400, 'Charles Street', 'Launceston', '7250'),
        (1, 200, 'Cameron Street', 'Launceston', '7250'),
        (1, 200, 'Patterson Street', 'Launceston', '7250'),
        (1, 300, 'Wellington Street', 'Launceston', '7250'),
    ],
    # ── ACT ──────────────────────────────────────────────────────────────────
    ('ACT', 'Canberra'): [
        (1, 300, 'Northbourne Avenue', 'Canberra', '2600'),
        (1, 100, 'London Circuit', 'Canberra', '2600'),
        (1, 200, 'Bunda Street', 'Canberra City', '2601'),
        (1, 200, 'Mort Street', 'Braddon', '2612'),
        (1, 200, 'Lonsdale Street', 'Braddon', '2612'),
        (1, 100, 'Emu Bank', 'Belconnen', '2617'),
        (1, 200, 'Benjamin Way', 'Belconnen', '2617'),
        (1, 200, 'Yamba Drive', 'Woden', '2606'),
        (1, 200, 'Anketell Street', 'Tuggeranong', '2900'),
        (1, 200, 'Gungahlin Drive', 'Gungahlin', '2912'),
    ],
    # ── NT ───────────────────────────────────────────────────────────────────
    ('NT', 'Darwin'): [
        (1, 200, 'Mitchell Street', 'Darwin City', '0800'),
        (1, 300, 'Smith Street', 'Darwin City', '0800'),
        (1, 200, 'Knuckey Street', 'Darwin City', '0800'),
        (1, 300, 'McMinn Street', 'Darwin City', '0800'),
        (1, 200, 'Cavenagh Street', 'Darwin City', '0800'),
        (1, 300, 'Stuart Highway', 'Palmerston', '0830'),
    ],
    ('NT', 'Alice Springs'): [
        (1, 300, 'Todd Street', 'Alice Springs', '0870'),
        (1, 200, 'Parsons Street', 'Alice Springs', '0870'),
        (1, 200, 'Bath Street', 'Alice Springs', '0870'),
        (1, 200, 'Gregory Terrace', 'Alice Springs', '0870'),
    ],
}

# For cities not explicitly listed, fall back to the state capital pool
_STATE_CAPITAL_POOL = {
    'NSW': ('NSW', 'Sydney'),
    'VIC': ('VIC', 'Melbourne'),
    'QLD': ('QLD', 'Brisbane'),
    'WA': ('WA', 'Perth'),
    'SA': ('SA', 'Adelaide'),
    'TAS': ('TAS', 'Hobart'),
    'ACT': ('ACT', 'Canberra'),
    'NT': ('NT', 'Darwin'),
}


def pick_real_address(state: str, city: str) -> tuple:
    """Return (address_string, suburb, postcode) from GNAF-verified pool."""
    key = (state, city)
    pool = REAL_STREET_POOLS.get(key) or REAL_STREET_POOLS.get(_STATE_CAPITAL_POOL.get(state, ('NSW', 'Sydney')))
    min_num, max_num, street, suburb, postcode = random.choice(pool)
    number = random.randint(min_num, max_num)
    # Even numbers on one side, odd on the other — keep realistic
    if random.random() < 0.5:
        number = number if number % 2 == 0 else number + 1
    else:
        number = number if number % 2 != 0 else number + 1
    number = max(1, min(number, max_num))
    return f"{number} {street}, {suburb} {state} {postcode}", suburb, postcode


async def connect_with_retry(max_retries=5, initial_delay=15):
    """
    Try connecting to Cosmos DB with exponential backoff.
    
    This handles the case where local auth was just enabled but hasn't
    propagated to the data plane yet. Retries with increasing delays.
    
    Args:
        max_retries: Maximum number of connection attempts
        initial_delay: Initial delay in seconds (doubles each retry)
    
    Returns:
        ParcelTrackingDB instance (already entered context)
    
    Raises:
        Exception: If all retries fail
    """
    for attempt in range(max_retries):
        try:
            print(f"  🔌 Connecting to Cosmos DB (attempt {attempt + 1}/{max_retries})...")
            db = ParcelTrackingDB()
            await db.__aenter__()
            
            # Test connectivity with actual query to data plane
            container = db.database.get_container_client("parcels")
            query = "SELECT TOP 1 c.id FROM c"
            items = []
            async for item in container.query_items(query=query):
                items.append(item)
                break
            
            print(f"  ✓ Connected to Cosmos DB successfully")
            return db
            
        except Exception as e:
            error_msg = str(e)
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)  # Exponential backoff: 15, 30, 60, 120, 240 seconds
                print(f"  ⚠️  Connection failed (attempt {attempt + 1}/{max_retries})")
                print(f"     Error: {error_msg[:150]}..." if len(error_msg) > 150 else f"     Error: {error_msg}")
                print(f"     Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"  ❌ Failed to connect after {max_retries} attempts")
                print(f"     Last error: {error_msg}")
                raise

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
    """Generate barcode in LP format — uses microseconds for uniqueness"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    return f"{prefix}{timestamp}"

def generate_dummy_photo() -> str:
    """Generate dummy base64-encoded photo data"""
    # Simple 1x1 transparent PNG as base64
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

async def create_demo_parcel(db: ParcelTrackingDB, parcel_spec: Dict) -> str:
    """Create a specific demo parcel with full history and photos"""
    # Extract address components
    address_parts = parcel_spec['address'].split()
    postcode = address_parts[-1] if address_parts else '2000'
    state = parcel_spec['state']
    city = parcel_spec['city']

    # Retry up to 5 times in the unlikely event of a barcode collision
    parcel_doc = None
    barcode = None
    for attempt in range(5):
        barcode = generate_barcode()
        try:
            parcel_doc = await db.register_parcel(
                barcode=barcode,
                sender_name=parcel_spec['sender_name'],
                sender_address=f"Warehouse, {city} {state}",
                sender_phone=fake.phone_number(),
                recipient_name=parcel_spec['recipient_name'],
                recipient_address=parcel_spec['address'],
                recipient_phone=parcel_spec['phone'],
                destination_postcode=postcode,
                destination_state=state,
                destination_city=city,
                weight=round(random.uniform(0.5, 25.0), 2),
                dimensions=f"{random.randint(10,50)}x{random.randint(10,50)}x{random.randint(5,30)}",
                service_type=random.choice(['standard', 'express', 'same-day']),
                store_location=pick_dc(state)
            )
            break  # success
        except ValueError as e:
            if 'already exists' in str(e) and attempt < 4:
                continue  # retry with new barcode
            print(f"  ⚠ Failed to create demo parcel for {parcel_spec['recipient_name']}: {e}")
            return None

    if not parcel_doc:
        print(f"  ⚠ Failed to create demo parcel for {parcel_spec['recipient_name']}")
        return None
    
    # Update with custom tracking number for demo purposes
    container = db.database.get_container_client(db.parcels_container)
    parcel_doc['tracking_number'] = parcel_spec['tracking_number']
    await container.upsert_item(parcel_doc)
    
    # Add lodgement photo if specified
    if parcel_spec.get('has_photo'):
        # Add lodgement photos
        try:
            await db.store_lodgement_photo(barcode, generate_dummy_photo(), "sender")
        except Exception as e:
            print(f"    ⚠️  Warning: Could not add lodgement photo: {e}")
    
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
            await db.store_delivery_photo(
                barcode=barcode,
                photo_base64=generate_dummy_photo(),
                uploaded_by=parcel_spec.get('assigned_driver', 'driver-001')
            )
        
        # Add events with realistic timestamps
        base_time = datetime.now() - timedelta(days=2)
        for i, (description, location, days_ago) in enumerate(events):
            event_time = base_time + timedelta(days=days_ago, hours=i)
            event_status = parcel_spec['status'] if i == len(events)-1 else 'In Transit'
            await db.create_tracking_event(
                barcode=barcode,
                event_type=event_status,
                location=location,
                description=f"{description} at {event_time.strftime('%Y-%m-%d %H:%M')}"
            )
    
    # Assign to driver if specified
    if parcel_spec.get('assigned_driver'):
        container = db.database.get_container_client(db.parcels_container)
        parcel_doc['assigned_driver'] = parcel_spec['assigned_driver']
        parcel_doc['current_status'] = parcel_spec['status']
        await container.upsert_item(parcel_doc)
    
    print(f"  ✓ Created demo parcel: {parcel_spec['tracking_number']} - {parcel_spec['recipient_name']}")
    return barcode

async def create_realistic_parcel(db: ParcelTrackingDB, state: str, city: str, index: int) -> str:
    """Create a realistic parcel for a specific state/city"""
    
    barcode = generate_barcode()
    
    recipient_name = random.choice(COMMON_RECIPIENTS + [fake.name() for _ in range(3)])
    sender_name = random.choice(SENDER_NAMES)

    # Generate real GNAF-verified address (no fake streets)
    address, suburb, postcode = pick_real_address(state, city)
    
    # Vary statuses for realism
    statuses = [
        ('At Depot', 30),
        ('Sorting', 20),
        ('Out For Delivery', 25),
        ('Delivered', 20),
        ('In Transit', 5)
    ]
    status = random.choices([s[0] for s in statuses], weights=[s[1] for s in statuses])[0]
    
    # Register parcel — retry on barcode collision
    parcel_doc = None
    for attempt in range(3):
        try:
            parcel_doc = await db.register_parcel(
                barcode=barcode,
                sender_name=sender_name,
                sender_address=f"Warehouse, {city} {state}",
                sender_phone=fake.phone_number(),
                recipient_name=recipient_name,
                recipient_address=address,
                recipient_phone=fake.phone_number(),
                destination_postcode=str(postcode),
                destination_state=state,
                destination_city=city,
                weight=round(random.uniform(0.1, 30.0), 2),
                dimensions=f"{random.randint(10,60)}x{random.randint(10,60)}x{random.randint(5,40)}",
                service_type=random.choice(['standard', 'express', 'express', 'same-day']),  # More express
                store_location=pick_dc(state),
                current_status=status  # Persist the chosen status immediately
            )
            break
        except ValueError as e:
            if 'already exists' in str(e) and attempt < 2:
                barcode = generate_barcode()
                continue
            return None
    
    # Add realistic event history (50% of parcels)
    if random.random() < 0.5:
        origin_dc = pick_dc(state)
        base_time = datetime.now() - timedelta(days=random.randint(1, 7))
        await db.create_tracking_event(
            barcode=barcode,
            event_type='Pending',
            location='Sender',
            description=f'Parcel Registered at {base_time.strftime("%Y-%m-%d %H:%M")}'
        )

        # Add more events for parcels in later stages
        if status in ['Delivered', 'Out For Delivery', 'In Transit', 'Sorting', 'At Depot']:
            t1 = base_time + timedelta(hours=6)
            await db.create_tracking_event(
                barcode=barcode,
                event_type='Sorting',
                location=origin_dc,
                description=f'Arrived at {origin_dc} Sorting Facility at {t1.strftime("%Y-%m-%d %H:%M")}'
            )

        # 30% chance of interstate transit through a hub DC
        if status in ['Delivered', 'Out For Delivery', 'In Transit'] and random.random() < 0.3:
            hub = random.choice([h for h in INTERSTATE_HUBS if h != origin_dc])
            t2 = base_time + timedelta(hours=random.randint(12, 30))
            destination_dc = pick_dc(state)
            await db.create_tracking_event(
                barcode=barcode,
                event_type='In Transit',
                location=hub,
                description=f'In transit via {hub} interstate hub at {t2.strftime("%Y-%m-%d %H:%M")}'
            )
            t3 = t2 + timedelta(hours=random.randint(4, 18))
            await db.create_tracking_event(
                barcode=barcode,
                event_type='Sorting',
                location=destination_dc,
                description=f'Arrived at destination {destination_dc} at {t3.strftime("%Y-%m-%d %H:%M")}'
            )
    
    # Add photos for delivered parcels (30% chance)
    if status == 'Delivered' and random.random() < 0.3:
        await db.store_delivery_photo(
            barcode=barcode,
            photo_base64=generate_dummy_photo(),
            uploaded_by="driver"
        )
    
    # Assign to drivers for out for delivery/delivered parcels
    if status in ['Out For Delivery', 'Delivered']:
        driver_num = random.randint(1, 57)
        driver_id = f"driver-{driver_num:03d}"
        # Update parcel to assign driver
        container = db.database.get_container_client(db.parcels_container)
        parcel_doc['assigned_driver'] = driver_id
        parcel_doc['current_status'] = status
        await container.upsert_item(parcel_doc)
    
    return barcode

async def main():
    parser = argparse.ArgumentParser(description='Generate bulk realistic parcel data')
    parser.add_argument('--count', type=int, default=2000, help='Number of parcels to generate (default: 2000)')
    parser.add_argument('--demo-only', action='store_true', help='Only create demo parcels (RG857954, DT202512170037), skip bulk generation')
    args = parser.parse_args()
    
    total_parcels = args.count
    
    print("=" * 80)
    if args.demo_only:
        print("🎯 DEMO PARCEL GENERATOR (demo-only mode)")
    else:
        print("🚀 BULK REALISTIC DATA GENERATOR")
    print("=" * 80)
    if not args.demo_only:
        print(f"Target: {total_parcels:,} parcels across all Australian states")
    print()
    
    # Use retry logic for connection
    db = await connect_with_retry(max_retries=5, initial_delay=15)
    try:
        # Step 1: Create specific demo parcels for Voice & Text Examples
        print("📋 Step 1: Creating Demo Parcels for Voice & Text Examples")
        print("-" * 80)
        
        demo_created = 0
        demo_skipped = 0
        for demo_spec in DEMO_PARCELS:
            existing = await db.get_parcel_by_tracking_number(demo_spec['tracking_number'])
            if existing:
                print(f"  ⏭  {demo_spec['tracking_number']} already exists — skipping")
                demo_skipped += 1
                continue
            barcode = await create_demo_parcel(db, demo_spec)
            if barcode:
                demo_created += 1

        print(f"\n✓ Demo parcels: {demo_created} created, {demo_skipped} already existed")
        print()

        if args.demo_only:
            print("=" * 80)
            print("✅ Demo parcels created — skipping bulk generation (--demo-only mode)")
            print("=" * 80)
            return
        
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
            parcel = await db.get_parcel_by_tracking_number(demo_spec['tracking_number'])
            if parcel:
                print(f"    ✓ {demo_spec['tracking_number']:20} - {demo_spec['recipient_name']}")
            else:
                print(f"    ✗ {demo_spec['tracking_number']:20} - NOT FOUND")

        # Step 4: Import real delivery photo for DT202512170037 if image file exists
        print(f"\n  📸 Step 4: Real Delivery Photo for DT202512170037")
        print("-" * 80)
        from import_delivery_photo import _find_image_file, import_photo as _import_photo
        real_image = _find_image_file(project_root)
        if real_image:
            print(f"  Found image: {real_image}")
            await _import_photo("DT202512170037", real_image, uploaded_by="driver-003")
        else:
            print(f"  ⚠ No delivery_sample image found in static/images/ — skipping.")
            print(f"    Save static/images/delivery_sample.jpg to include a real photo.")

        # Step 5: Import real lodgement photo for RG857954
        print(f"\n  📸 Step 5: Real Lodgement Photo for RG857954")
        print("-" * 80)
        lodgement_image = _find_image_file(project_root, "lodgement")
        if lodgement_image:
            print(f"  Found image: {lodgement_image}")
            await _import_photo("RG857954", lodgement_image, uploaded_by="sender", photo_type="lodgement")
        else:
            print(f"  ⚠ No lodgement_sample image found in static/images/ — skipping.")
            print(f"    Save static/images/lodgement_sample.jpg to include a real photo.")

        # Step 6: Generate approval requests
        print(f"\n  📋 Step 6: Generating Approval Requests")
        print("-" * 80)
        try:
            if script_dir not in sys.path:
                sys.path.insert(0, script_dir)
            from create_approval_requests import create_approval_requests
            approval_success = await create_approval_requests()
            if not approval_success:
                print("  ⚠ Approval requests creation skipped (no eligible parcels yet)")
        except Exception as e:
            print(f"  ⚠ Could not create approval requests: {e}")

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
    finally:
        # Clean up database connection
        await db.__aexit__(None, None, None)
if __name__ == "__main__":
    asyncio.run(main())
