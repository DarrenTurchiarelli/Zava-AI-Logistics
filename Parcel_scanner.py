#!/usr/bin/env python3
"""
Parcel Scanner Simulation for Approval Workflow System

This script simulates the parcel scanning process for packages/items
and demonstrates how to integrate with the agent workflow system.

Usage:
    python barcode_scanner_demo.py

Features:
- Simulate scanning parcels
- Add items to database with sender/recipient information
- Create approval requests for special handling
- View all scanned items and pending approvals
- Approve/reject requests manually
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, List

# Add parent directory to path to import database modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_setup import ApprovalDatabase
from database_tools import (
    add_scanned_item, get_all_scanned_items, get_all_pending_approvals,
    get_all_approved_items, approve_request, reject_request,
    request_human_approval, generate_random_tracking_number
)

class ParcelScannerSimulator:
    def __init__(self):
        self.db = ApprovalDatabase()
        self.scanner_id = "SCANNER_001"
        
    def simulate_parcel_scan(self) -> str:
        """Simulate scanning a parcel"""
        barcode = generate_random_tracking_number()
        print(f"📱 Parcel scanned: {barcode}")
        return barcode
    
    def get_item_details(self) -> Dict[str, str]:
        """Simulate getting item details from user input or external system"""
        
        # Sample data pools for realistic simulation
        senders = [
            "Amazon Fulfillment", "John Smith", "Medical Supply Co", "Tech Solutions Inc",
            "University Library", "Manufacturing Corp", "Alice Johnson", "Bob Wilson"
        ]
        
        recipients = [
            "Downtown Hospital", "Sarah Davis", "Research Lab Inc", "City Library",
            "Tech Startup LLC", "Emma Brown", "Distribution Center", "Mike Taylor"
        ]
        
        addresses = [
            "123 Collins Street, Melbourne, VIC 3000",
            "456 George Street, Sydney, NSW 2000", 
            "789 Queen Street, Brisbane, QLD 4000",
            "321 King William Street, Adelaide, SA 5000",
            "654 Murray Street, Perth, WA 6000",
            "987 Elizabeth Street, Hobart, TAS 7000",
            "147 Northbourne Avenue, Canberra, ACT 2600",
            "258 Smith Street, Darwin, NT 0800"
        ]
        
        item_types = [
            "electronics", "medical", "documents", "books", "clothing", 
            "fragile", "perishable", "hazardous", "valuable", "standard"
        ]
        
        special_handling_options = [
            "fragile", "temperature_controlled", "hazardous_materials", 
            "signature_required", "express", "insured", "confidential", None
        ]
        
        from random import randint, choice
        
        return {
            "item_number": f"PKG{randint(1000, 9999)}",
            "sender_name": choice(senders),
            "recipient_name": choice(recipients), 
            "recipient_address": choice(addresses),
            "item_type": choice(item_types),
            "weight": round(randint(1, 100) / 10.0, 1),  # 0.1 to 10.0 kg
            "dimensions": f"{randint(10, 50)}x{randint(10, 40)}x{randint(5, 30)}cm",
            "special_handling": choice(special_handling_options)
        }
    
    def scan_and_add_item(self) -> Dict:
        """Complete scan and add process"""
        print("\n" + "="*60)
        print("🔍 STARTING PARCEL SCAN PROCESS")
        print("="*60)
        
        # Step 1: Scan barcode
        barcode = self.simulate_parcel_scan()
        
        # Step 2: Get item details
        print("📋 Retrieving item details...")
        details = self.get_item_details()
        
        # Step 3: Display details
        print(f"\n📦 ITEM DETAILS:")
        print(f"   Barcode: {barcode}")
        print(f"   Item Number: {details['item_number']}")
        print(f"   From: {details['sender_name']}")
        print(f"   To: {details['recipient_name']}")
        print(f"   Address: {details['recipient_address']}")
        print(f"   Type: {details['item_type']}")
        print(f"   Weight: {details['weight']} kg")
        print(f"   Dimensions: {details['dimensions']}")
        print(f"   Special Handling: {details['special_handling'] or 'None'}")
        
        # Step 4: Add to database
        try:
            item_id = add_scanned_item(
                barcode=barcode,
                item_number=details['item_number'],
                sender_name=details['sender_name'],
                recipient_name=details['recipient_name'],
                recipient_address=details['recipient_address'],
                item_type=details['item_type'],
                weight=details['weight'],
                special_handling=details['special_handling']
            )
            
            print(f"✅ Item successfully added to database with ID: {item_id}")
            
            # Step 5: Check if approval needed
            approval_id = None
            if details['special_handling'] in ['fragile', 'hazardous_materials', 'temperature_controlled', 'valuable']:
                print(f"⚠️  Special handling required: {details['special_handling']}")
                print("🔄 Creating approval request...")
                
                approval_id = request_human_approval(
                    action="Process Special Handling",
                    equipment_id=barcode,
                    equipment_type="package",
                    item_barcode=barcode
                )
                
                if approval_id > 0:
                    print(f"📝 Approval request created with ID: {approval_id}")
                else:
                    print("❌ Failed to create approval request")
            
            result = {
                "item_id": item_id,
                "barcode": barcode,
                "approval_id": approval_id,
                "details": details
            }
            
            print("🎯 Scan process completed successfully!")
            return result
            
        except Exception as e:
            print(f"❌ Error during scan process: {e}")
            return {}
    
    def display_dashboard(self):
        """Display current system status"""
        print("\n" + "="*80)
        print("📊 SYSTEM DASHBOARD")
        print("="*80)
        
        # Show all scanned items
        all_items = get_all_scanned_items()
        print(f"\n📦 SCANNED ITEMS ({len(all_items)} total):")
        print("-" * 80)
        
        for item in all_items[-5:]:  # Show last 5 items
            print(f"   {item['barcode']} | {item['item_number']} | "
                  f"{item['sender_name']} → {item['recipient_name']} | "
                  f"{item['item_type']} | {item['special_handling'] or 'Standard'}")
        
        if len(all_items) > 5:
            print(f"   ... and {len(all_items) - 5} more items")
        
        # Show pending approvals
        pending = get_all_pending_approvals()
        print(f"\n⏳ PENDING APPROVALS ({len(pending)} total):")
        print("-" * 80)
        
        for key, approval in list(pending.items())[:5]:  # Show first 5
            print(f"   ID {approval.get('id', 'N/A')} | {approval['action']} | "
                  f"{approval['barcode']} | {approval['sender']} → {approval['recipient']}")
        
        if len(pending) > 5:
            print(f"   ... and {len(pending) - 5} more pending approvals")
        
        # Show approved items
        approved = get_all_approved_items()
        print(f"\n✅ APPROVED ITEMS ({len(approved)} total):")
        print("-" * 80)
        
        for key, approval in list(approved.items())[:3]:  # Show last 3
            print(f"   ID {approval.get('id', 'N/A')} | {approval['action']} | "
                  f"{approval['barcode']} | Approved by: {approval.get('approved_by', 'System')}")
        
        if len(approved) > 3:
            print(f"   ... and {len(approved) - 3} more approved items")
        
        print("="*80)

def interactive_demo():
    """Run interactive demo"""
    scanner = ParcelScannerSimulator()
    
    print("\n🚀 PARCEL SCANNER SIMULATION DEMO")
    print("Welcome to the Package Processing System!")
    
    while True:
        print("\n📋 MENU OPTIONS:")
        print("1. 📱 Scan new parcel")
        print("2. 📊 View dashboard")
        print("3. ✅ Approve pending request")
        print("4. ❌ Reject pending request") 
        print("5. 🔄 Run agent workflow (requires agents)")
        print("6. 🚪 Exit")
        
        try:
            choice = input("\nSelect option (1-6): ").strip()
            
            if choice == '1':
                scanner.scan_and_add_item()
                
            elif choice == '2':
                scanner.display_dashboard()
                
            elif choice == '3':
                pending = get_all_pending_approvals()
                if not pending:
                    print("❌ No pending approvals found")
                    continue
                
                print("\n⏳ PENDING APPROVALS:")
                for key, approval in pending.items():
                    print(f"   ID {approval.get('id', 'N/A')}: {approval['action']} for {approval['barcode']}")
                
                try:
                    approval_id = int(input("\nEnter approval ID to approve: "))
                    approver = input("Enter your name: ").strip() or "Manual Operator"
                    
                    success = approve_request(approval_id, approver)
                    if success:
                        print(f"✅ Approval request {approval_id} approved successfully!")
                    else:
                        print(f"❌ Failed to approve request {approval_id}")
                except ValueError:
                    print("❌ Invalid approval ID")
                    
            elif choice == '4':
                pending = get_all_pending_approvals()
                if not pending:
                    print("❌ No pending approvals found")
                    continue
                
                print("\n⏳ PENDING APPROVALS:")
                for key, approval in pending.items():
                    print(f"   ID {approval.get('id', 'N/A')}: {approval['action']} for {approval['barcode']}")
                
                try:
                    approval_id = int(input("\nEnter approval ID to reject: "))
                    reason = input("Enter rejection reason: ").strip() or "Manual rejection"
                    
                    success = reject_request(approval_id, reason)
                    if success:
                        print(f"❌ Approval request {approval_id} rejected successfully!")
                    else:
                        print(f"❌ Failed to reject request {approval_id}")
                except ValueError:
                    print("❌ Invalid approval ID")
                    
            elif choice == '5':
                print("🔄 To run the agent workflow:")
                print("   1. Ensure your Azure AI agents are set up")
                print("   2. Update agent IDs in W04_Sequential_Workflow_Human_Approval.py") 
                print("   3. Run: python W04_Sequential_Workflow_Human_Approval.py")
                print("   The agents will process all scanned items and pending approvals")
                
            elif choice == '6':
                print("👋 Goodbye! Thank you for using the Package Processing System.")
                break
                
            else:
                print("❌ Invalid option. Please select 1-6.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye! Thank you for using the Package Processing System.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Initialize database with sample data
    print("🔧 Initializing database...")
    db = ApprovalDatabase()
    
    # Add some sample data if database is empty
    all_items = get_all_scanned_items()
    if len(all_items) == 0:
        print("📦 Adding sample data...")
        db.add_sample_data()
    
    # Run interactive demo
    interactive_demo()