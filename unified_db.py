#!/usr/bin/env python3
"""
Unified Database Interface for Last Mile Logistics Parcel Tracking

This module provides a consolidated interface for both:
1. Azure Cosmos DB (Production) - for agent workflows and logistics tracking
2. SQLite (Local Demo) - for local development and testing

Usage:
    from unified_db import get_database_interface
    
    # Get production Cosmos DB interface
    db = get_database_interface(use_cosmos=True)
    
    # Get local SQLite interface
    db = get_database_interface(use_cosmos=False)
"""

import os
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class UnifiedDatabaseInterface:
    """Unified interface for both Cosmos DB and SQLite operations"""
    
    def __init__(self, use_cosmos: bool = True):
        self.use_cosmos = use_cosmos
        
        if use_cosmos:
            # Import Cosmos DB functions
            from cosmosdb_tools import (
                get_all_scanned_items_sync, get_all_pending_approvals_sync,
                get_all_approved_items_sync, request_human_approval_sync,
                approve_request_sync, reject_request_sync, add_scanned_item_sync
            )
            self._get_scanned_items = get_all_scanned_items_sync
            self._get_pending_approvals = get_all_pending_approvals_sync
            self._get_approved_items = get_all_approved_items_sync
            self._request_approval = request_human_approval_sync
            self._approve_request = approve_request_sync
            self._reject_request = reject_request_sync
            self._add_scanned_item = add_scanned_item_sync
            print("✅ Using Azure Cosmos DB (Production)")
            
        else:
            # Import SQLite functions
            from database_setup import ApprovalDatabase
            from database_tools import (
                get_all_scanned_items, get_all_pending_approvals,
                get_all_approved_items, request_human_approval,
                approve_request, reject_request, add_scanned_item
            )
            self.db = ApprovalDatabase()
            self._get_scanned_items = get_all_scanned_items
            self._get_pending_approvals = get_all_pending_approvals
            self._get_approved_items = get_all_approved_items
            self._request_approval = request_human_approval
            self._approve_request = approve_request
            self._reject_request = reject_request
            self._add_scanned_item = add_scanned_item
            print("✅ Using SQLite Database (Local Demo)")
    
    def get_all_scanned_items(self) -> List[Dict[str, Any]]:
        """Get all scanned items/parcels"""
        try:
            return self._get_scanned_items()
        except Exception as e:
            print(f"Error retrieving scanned items: {e}")
            return []
    
    def get_pending_approvals(self) -> Union[List[Dict], Dict]:
        """Get all pending approval requests"""
        try:
            return self._get_pending_approvals()
        except Exception as e:
            print(f"Error retrieving pending approvals: {e}")
            return [] if self.use_cosmos else {}
    
    def get_approved_items(self) -> Union[List[Dict], Dict]:
        """Get all approved items"""
        try:
            return self._get_approved_items()
        except Exception as e:
            print(f"Error retrieving approved items: {e}")
            return [] if self.use_cosmos else {}
    
    def request_approval(self, item_barcode: str, request_type: str, description: str) -> Union[str, int]:
        """Request human approval for an item"""
        try:
            if self.use_cosmos:
                return self._request_approval(item_barcode, request_type, description)
            else:
                # For SQLite, we need to adapt the parameters
                return self._request_approval(
                    action=request_type,
                    equipment_id=item_barcode,
                    equipment_type="parcel",
                    item_barcode=item_barcode
                )
        except Exception as e:
            print(f"Error requesting approval: {e}")
            return "error" if self.use_cosmos else -1
    
    def approve_request(self, approval_id: Union[str, int], approver_name: str, notes: Optional[str] = None) -> bool:
        """Approve a pending request"""
        try:
            if self.use_cosmos:
                return self._approve_request(approval_id, approver_name, notes)
            else:
                return self._approve_request(int(approval_id), approver_name)
        except Exception as e:
            print(f"Error approving request: {e}")
            return False
    
    def reject_request(self, approval_id: Union[str, int], reason: str) -> bool:
        """Reject a pending request"""
        try:
            if self.use_cosmos:
                return self._reject_request(approval_id, reason)
            else:
                return self._reject_request(int(approval_id), reason)
        except Exception as e:
            print(f"Error rejecting request: {e}")
            return False
    
    def add_scanned_item(self, **kwargs) -> Union[str, int]:
        """Add a scanned item/parcel"""
        try:
            if self.use_cosmos:
                # For Cosmos DB, we need barcode, item_name, sender_name, recipient_name, recipient_address
                return self._add_scanned_item(**kwargs)
            else:
                # For SQLite, we need different parameters
                return self._add_scanned_item(**kwargs)
        except Exception as e:
            print(f"Error adding scanned item: {e}")
            return "error" if self.use_cosmos else -1

def get_database_interface(use_cosmos: Optional[bool] = None) -> UnifiedDatabaseInterface:
    """
    Get the appropriate database interface based on environment or parameter
    
    Args:
        use_cosmos: True for Cosmos DB, False for SQLite, None for auto-detect
    
    Returns:
        UnifiedDatabaseInterface instance
    """
    if use_cosmos is None:
        # Auto-detect based on environment variables
        cosmos_endpoint = os.getenv("COSMOS_DB_ENDPOINT")
        cosmos_key = os.getenv("COSMOS_DB_KEY")
        use_cosmos = bool(cosmos_endpoint and cosmos_key)
        
        if use_cosmos:
            print("🔍 Auto-detected: Azure Cosmos DB credentials found")
        else:
            print("🔍 Auto-detected: No Cosmos DB credentials, using SQLite")
    
    return UnifiedDatabaseInterface(use_cosmos=use_cosmos)

def test_database_interface():
    """Test function to demonstrate unified interface"""
    print("=== Testing Unified Database Interface ===")
    
    # Test both interfaces
    for use_cosmos in [True, False]:
        print(f"\n--- Testing {'Cosmos DB' if use_cosmos else 'SQLite'} ---")
        
        try:
            db = get_database_interface(use_cosmos=use_cosmos)
            
            # Test getting data
            items = db.get_all_scanned_items()
            print(f"📦 Scanned items: {len(items)}")
            
            pending = db.get_pending_approvals()
            pending_count = len(pending) if isinstance(pending, list) else len(pending)
            print(f"⏳ Pending approvals: {pending_count}")
            
            approved = db.get_approved_items()
            approved_count = len(approved) if isinstance(approved, list) else len(approved)
            print(f"✅ Approved items: {approved_count}")
            
        except Exception as e:
            print(f"❌ Error testing {'Cosmos DB' if use_cosmos else 'SQLite'}: {e}")

if __name__ == "__main__":
    test_database_interface()