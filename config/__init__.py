"""
Config package - Configuration and company data
"""

from .company import get_company_info, COMPANY_NAME, COMPANY_PHONE, COMPANY_EMAIL
from .depots import get_closest_depot_to_address, get_depot_by_name

__all__ = [
    'get_company_info',
    'COMPANY_NAME',
    'COMPANY_PHONE',
    'COMPANY_EMAIL',
    'get_closest_depot_to_address',
    'get_depot_by_name'
]
