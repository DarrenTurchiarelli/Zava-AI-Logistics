# logistics_common.py
# Common utilities and shared functions for logistics operations

import warnings
import os
import sys
import logging
import random
import string
import contextlib
from threading import Lock
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Comprehensive warning suppression
def setup_warning_suppression():
    """Set up comprehensive warning suppression for Azure/aiohttp"""
    warnings.filterwarnings('ignore', category=ResourceWarning)
    warnings.filterwarnings('ignore', message='Unclosed client session')
    warnings.filterwarnings('ignore', message='Unclosed connector')
    warnings.filterwarnings('ignore', message='SSL shutdown timed out')
    warnings.filterwarnings('ignore', message='Connection lost')
    warnings.filterwarnings('ignore', category=DeprecationWarning)
    warnings.simplefilter('ignore', ResourceWarning)
    
    # Completely suppress asyncio and aiohttp logging
    logging.getLogger('asyncio').setLevel(logging.CRITICAL)
    logging.getLogger('aiohttp').setLevel(logging.CRITICAL)
    logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.CRITICAL)
    logging.basicConfig(level=logging.CRITICAL)
    
    # Set environment variables for warning suppression
    os.environ['PYTHONWARNINGS'] = 'ignore::ResourceWarning'
    os.environ['AZURE_CLI_DISABLE_CONNECTION_VERIFICATION'] = 'true'

class WarningFilter:
    """Filter out specific messages from both stdout and stderr"""
    
    def __init__(self):
        self.original_stderr = None
        self.original_stdout = None
        self.lock = Lock()
        self.suppressed_messages = [
            "Unclosed client session",
            "Unclosed connector", 
            "SSL shutdown timed out",
            "Connection lost",
            "RuntimeWarning: Enable tracemalloc",
            "🔑 Connected to Cosmos DB using access key",
            "🔐 Key-based auth disabled, switching to Azure AD authentication",
            "🔐 Connected to Cosmos DB using Azure credentials", 
            "📦 Container ready:",
            "✅ Connected to database:",
            "Future exception was never retrieved",
            "TimeoutError: SSL shutdown timed out",
            "aiohttp.client_exceptions.ClientConnectionError"
        ]
    
    def __enter__(self):
        with self.lock:
            self.original_stderr = sys.stderr
            self.original_stdout = sys.stdout
            sys.stderr = self
            sys.stdout = self
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        with self.lock:
            sys.stderr = self.original_stderr
            sys.stdout = self.original_stdout
    
    def write(self, message):
        # Suppress specific warning messages
        if any(suppressed in message for suppressed in self.suppressed_messages):
            return
        # Write to original output stream based on current stream
        if sys.stderr == self:
            self.original_stderr.write(message)
        else:
            self.original_stdout.write(message)
    
    def flush(self):
        if hasattr(self, 'original_stderr') and self.original_stderr:
            self.original_stderr.flush()
        if hasattr(self, 'original_stdout') and self.original_stdout:
            self.original_stdout.flush()

# Global filter instance
_warning_filter = WarningFilter()

@contextlib.contextmanager 
def clean_output():
    """Context manager for clean output without aiohttp warnings"""
    # Already applied globally, just yield
    yield

def generate_parcel_barcode():
    """Generate a random parcel barcode"""
    prefix = random.choice(['LP', 'EX', 'RG', 'OV', 'PR'])  # LastPost, Express, Regular, Overnight, Priority
    numbers = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    return f"{prefix}{numbers}"

def get_australian_state_from_postcode(postcode):
    """Get Australian state from postcode using proper ranges"""
    if not postcode or not postcode.isdigit():
        return 'NSW'  # Default fallback
    
    postcode_int = int(postcode)
    
    # Australian postcode ranges
    if (200 <= postcode_int <= 299) or (2600 <= postcode_int <= 2699):
        return 'ACT'
    elif 1000 <= postcode_int <= 2999:
        return 'NSW'
    elif 3000 <= postcode_int <= 3999:
        return 'VIC'
    elif 4000 <= postcode_int <= 4999:
        return 'QLD'
    elif 5000 <= postcode_int <= 5999:
        return 'SA'
    elif 6000 <= postcode_int <= 6999:
        return 'WA'
    elif 7000 <= postcode_int <= 7999:
        return 'TAS'
    elif 800 <= postcode_int <= 999:
        return 'NT'
    else:
        return 'NSW'  # Default fallback

def get_australian_states():
    """Get sample Australian states mapping (for backwards compatibility)"""
    return {
        '2000': 'NSW', '2007': 'NSW', '2010': 'NSW',
        '3000': 'VIC', '3004': 'VIC', '3141': 'VIC', '3181': 'VIC',
        '4000': 'QLD', '4006': 'QLD', '4101': 'QLD',
        '5000': 'SA', '5006': 'SA',
        '6000': 'WA', '6008': 'WA',
        '7000': 'TAS', '7001': 'TAS',
        '0200': 'ACT'
    }

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
            'destination_state': 'NSW',
            'service_type': 'express',
            'weight': 1.2,
            'dimensions': '25x20x8cm',
            'declared_value': 299.99,
            'special_instructions': 'Fragile electronics - handle with care',
            'store_location': 'Store_Melbourne_CBD'
        },
        {
            'sender_name': 'Fashion Forward Boutique',
            'sender_address': '67 Chapel Street, Prahran, Melbourne VIC 3181',
            'sender_phone': '+61 3 8765 4321',
            'recipient_name': 'Michael Chen',
            'recipient_address': '456 Queen Street, Brisbane CBD, Brisbane QLD 4000',
            'recipient_phone': '+61 7 1234 5678',
            'destination_postcode': '4000',
            'destination_state': 'QLD',
            'service_type': 'standard',
            'weight': 0.8,
            'dimensions': '30x25x5cm',
            'declared_value': 149.50,
            'special_instructions': 'Gift wrapping included',
            'store_location': 'Store_Melbourne_Prahran'
        },
        {
            'sender_name': 'Medical Supply Co',
            'sender_address': '89 Hay Street, Perth CBD, Perth WA 6000',
            'sender_phone': '+61 8 9876 5432',
            'recipient_name': 'Dr. Emma Wilson',
            'recipient_address': '321 North Terrace, Adelaide CBD, Adelaide SA 5000',
            'recipient_phone': '+61 8 8123 4567',
            'destination_postcode': '5000',
            'destination_state': 'SA',
            'service_type': 'overnight',
            'weight': 2.5,
            'dimensions': '40x30x15cm',
            'declared_value': 750.00,
            'special_instructions': 'Temperature sensitive - keep cool',
            'store_location': 'Store_Perth_CBD'
        },
        {
            'sender_name': 'Organic Farm Fresh',
            'sender_address': '12 Main Street, Hobart, TAS 7000',
            'sender_phone': '+61 3 6234 5678',
            'recipient_name': 'James Rodriguez',
            'recipient_address': '789 Flinders Street, Melbourne CBD, Melbourne VIC 3000',
            'recipient_phone': '+61 3 9876 5432',
            'destination_postcode': '3000',
            'destination_state': 'VIC',
            'service_type': 'registered',
            'weight': 3.2,
            'dimensions': '35x25x20cm',
            'declared_value': 89.95,
            'special_instructions': 'Perishable goods - deliver by 5pm',
            'store_location': 'Store_Hobart'
        }
    ]
    return parcels

# Initialize warning suppression globally
setup_warning_suppression()
_warning_filter.__enter__()