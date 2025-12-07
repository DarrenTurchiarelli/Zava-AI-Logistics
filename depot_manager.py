#!/usr/bin/env python3
"""
Depot Manager Module

Manages multiple depot locations across Australian states and provides
intelligent depot selection for route optimization based on delivery addresses.
"""

import os
import re
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class DepotManager:
    """Manages depot locations and provides intelligent depot selection"""
    
    # Australian state/territory codes
    STATES = ['NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'ACT', 'NT']
    
    def __init__(self):
        """Initialize depot manager with depot locations from environment"""
        self.depots = self._load_depots()
        
    def _load_depots(self) -> Dict[str, str]:
        """Load depot addresses from environment variables
        
        Returns:
            Dictionary mapping state codes to depot addresses
        """
        depots = {}
        for state in self.STATES:
            depot_key = f'DEPOT_{state}'
            depot_address = os.getenv(depot_key)
            if depot_address:
                depots[state] = depot_address
        
        # Fallback to default depot if no state-specific depots configured
        if not depots:
            default_depot = os.getenv('DEPOT_ADDRESS', '123 Industrial Drive, Sydney NSW 2000')
            depots['NSW'] = default_depot
            
        return depots
    
    def get_depot(self, state: str) -> Optional[str]:
        """Get depot address for a specific state
        
        Args:
            state: Australian state/territory code (e.g., 'NSW', 'VIC')
            
        Returns:
            Depot address for the state, or None if not found
        """
        state_upper = state.upper() if state else ''
        return self.depots.get(state_upper)
    
    def get_depot_for_address(self, address: str) -> str:
        """Extract state from address and return appropriate depot
        
        Args:
            address: Full delivery address string
            
        Returns:
            Depot address for the detected state, or default depot
        """
        state = self.extract_state_from_address(address)
        depot = self.get_depot(state) if state else None
        
        # Fallback to first available depot or default
        if not depot:
            depot = next(iter(self.depots.values()), 
                        os.getenv('DEPOT_ADDRESS', '123 Industrial Drive, Sydney NSW 2000'))
        
        return depot
    
    def get_depot_for_addresses(self, addresses: List[str]) -> str:
        """Determine best depot for a list of delivery addresses
        
        Selects depot based on the most common state in the address list.
        If addresses span multiple states, returns depot for the state 
        with the most deliveries.
        
        Args:
            addresses: List of delivery addresses
            
        Returns:
            Depot address for the most common state
        """
        if not addresses:
            return next(iter(self.depots.values()), 
                       os.getenv('DEPOT_ADDRESS', '123 Industrial Drive, Sydney NSW 2000'))
        
        # Count states in addresses
        state_counts = {}
        for address in addresses:
            state = self.extract_state_from_address(address)
            if state:
                state_counts[state] = state_counts.get(state, 0) + 1
        
        # Find most common state
        if state_counts:
            most_common_state = max(state_counts, key=state_counts.get)
            depot = self.get_depot(most_common_state)
            if depot:
                return depot
        
        # Fallback
        return next(iter(self.depots.values()), 
                   os.getenv('DEPOT_ADDRESS', '123 Industrial Drive, Sydney NSW 2000'))
    
    @staticmethod
    def extract_state_from_address(address: str) -> Optional[str]:
        """Extract Australian state/territory code from address string
        
        Looks for patterns like "NSW 2000", "VIC 3000", etc.
        
        Args:
            address: Address string to parse
            
        Returns:
            State code (e.g., 'NSW') or None if not found
        """
        if not address:
            return None
        
        # Pattern: state code followed by optional space and postcode
        # Examples: "NSW 2000", "VIC3000", "QLD 4000"
        pattern = r'\b(NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s*\d{4}\b'
        match = re.search(pattern, address.upper())
        
        if match:
            return match.group(1)
        
        # Alternative: look for state code anywhere in address
        for state in DepotManager.STATES:
            if f' {state} ' in f' {address.upper()} ':
                return state
        
        return None
    
    def list_depots(self) -> Dict[str, str]:
        """Get all configured depots
        
        Returns:
            Dictionary of state codes to depot addresses
        """
        return self.depots.copy()
    
    def get_default_depot(self) -> str:
        """Get the default depot address
        
        Returns:
            Default depot address (first configured depot or env default)
        """
        return os.getenv('DEPOT_ADDRESS') or next(iter(self.depots.values()), 
                                                   '123 Industrial Drive, Sydney NSW 2000')


# Convenience function for quick depot lookup
def get_depot_for_addresses(addresses: List[str]) -> str:
    """Quick helper to get best depot for a list of addresses
    
    Args:
        addresses: List of delivery addresses
        
    Returns:
        Appropriate depot address
    """
    manager = DepotManager()
    return manager.get_depot_for_addresses(addresses)


# Module-level instance for simple usage
_depot_manager = None

def get_depot_manager() -> DepotManager:
    """Get singleton depot manager instance"""
    global _depot_manager
    if _depot_manager is None:
        _depot_manager = DepotManager()
    return _depot_manager


if __name__ == "__main__":
    # Test the depot manager
    print("=" * 70)
    print("Depot Manager Test")
    print("=" * 70)
    print()
    
    manager = DepotManager()
    
    print("📍 Configured Depots:")
    for state, address in manager.list_depots().items():
        print(f"   {state}: {address}")
    print()
    
    # Test address parsing
    test_addresses = [
        "123 George Street, Sydney NSW 2000",
        "456 Collins Street, Melbourne VIC 3000",
        "789 Queen Street, Brisbane QLD 4000",
        "321 King William Street, Adelaide SA 5000",
    ]
    
    print("🧪 Testing Address Parsing:")
    for addr in test_addresses:
        state = manager.extract_state_from_address(addr)
        depot = manager.get_depot_for_address(addr)
        print(f"   Address: {addr}")
        print(f"   → State: {state}")
        print(f"   → Depot: {depot}")
        print()
    
    # Test multi-address depot selection
    print("📦 Testing Multi-Address Depot Selection:")
    print(f"   Addresses: {len(test_addresses)} deliveries")
    best_depot = manager.get_depot_for_addresses(test_addresses)
    print(f"   → Best Depot: {best_depot}")
    print()
    
    # Test with addresses in same state
    nsw_addresses = [
        "1 Macquarie Street, Sydney NSW 2000",
        "88 Cumberland Street, The Rocks NSW 2000",
        "100 Market Street, Sydney NSW 2000",
    ]
    print("📦 Testing NSW-only Addresses:")
    nsw_depot = manager.get_depot_for_addresses(nsw_addresses)
    print(f"   → Selected Depot: {nsw_depot}")
    print()
    
    print("✅ Depot Manager Test Complete")
