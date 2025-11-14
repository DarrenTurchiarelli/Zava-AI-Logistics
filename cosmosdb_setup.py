# Azure Cosmos DB Setup and Testing Script for Last Mile Logistics
# This script sets up the Cosmos DB database and containers for parcel tracking, and provides testing functionality

import asyncio
import os
from dotenv import load_dotenv
from cosmosdb_tools import (
    register_parcel, get_all_parcels, add_random_test_parcels,
    request_supervisor_approval, get_all_pending_approvals, add_random_approval_requests,
    approve_request, reject_request, get_approval_status,
    cleanup_database, update_parcel_status, create_tracking_event
)

# Load environment variables
load_dotenv()

async def setup_cosmos_db():
    """Setup Cosmos DB with initial test data"""
    print("=== Setting up Azure Cosmos DB ===")
    
    # Check environment variables
    endpoint = os.getenv("COSMOS_DB_ENDPOINT")
    key = os.getenv("COSMOS_DB_KEY")
    
    if not endpoint or not key:
        print("ERROR: COSMOS_DB_ENDPOINT and COSMOS_DB_KEY environment variables must be set")
        print("Please update your .env file with your Cosmos DB credentials")
        return False
    
    print(f"Cosmos DB Endpoint: {endpoint}")
    print(f"Database Name: {os.getenv('COSMOS_DB_DATABASE_NAME', 'agent_workflow_db')}")
    
    try:
        # Add some initial test data
        print("\n=== Adding Test Parcels ===")
        test_parcels = await add_random_test_parcels(5)
        print(f"Added {len(test_parcels)} test parcels")
        
        # Display the parcels
        parcels = await get_all_parcels()
        for parcel in parcels:
            print(f"- {parcel['barcode']}: {parcel['recipient_name']} ({parcel['destination_postcode']}) - {parcel['service_type']}")
        
        # Add some approval requests
        print("\n=== Adding Test Approval Requests ===")
        approval_requests = await add_random_approval_requests(3)
        print(f"Added {len(approval_requests)} approval requests")
        
        # Display pending approvals
        pending = await get_all_pending_approvals()
        for approval in pending:
            print(f"- Request {approval['id']}: {approval['description']} (Priority: {approval['priority']})")
        
        print("\n=== Cosmos DB Setup Complete ===")
        return True
        
    except Exception as e:
        print(f"Error setting up Cosmos DB: {e}")
        return False

async def test_approval_workflow():
    """Test the approval workflow"""
    print("\n=== Testing Approval Workflow ===")
    
    try:
        # Get all parcels
        parcels = await get_all_parcels()
        if not parcels:
            print("No parcels found. Adding some test parcels first...")
            await add_random_test_parcels(3)
            parcels = await get_all_parcels()
        
        # Create an approval request for the first parcel
        if parcels:
            parcel = parcels[0]
            print(f"Creating approval request for parcel: {parcel['barcode']} - To: {parcel['recipient_name']}")
            
            request_id = await request_supervisor_approval(
                parcel_barcode=parcel['barcode'],
                request_type="delivery_redirect",
                description=f"Request delivery redirect for parcel to {parcel['recipient_name']}",
                priority="high"
            )
            
            print(f"Created approval request: {request_id}")
            
            # Check the approval status
            status = await get_approval_status(request_id)
            print(f"Initial status: {status['status']}")
            
            # Approve the request
            approved = await approve_request(request_id, "test_supervisor", "Approved for testing")
            if approved:
                print("Request approved successfully")
                
                # Check final status
                final_status = await get_approval_status(request_id)
                print(f"Final status: {final_status['status']} by {final_status['approved_by']}")
            
    except Exception as e:
        print(f"Error testing approval workflow: {e}")

async def display_database_contents():
    """Display all database contents"""
    print("\n=== Current Database Contents ===")
    
    try:
        # Display parcels
        print("\n--- Parcels ---")
        parcels = await get_all_parcels()
        if parcels:
            for i, parcel in enumerate(parcels, 1):
                print(f"{i}. Barcode: {parcel['barcode']}")
                print(f"   Tracking: {parcel['tracking_number']}")
                print(f"   From: {parcel['sender_name']}")
                print(f"   To: {parcel['recipient_name']} ({parcel['destination_postcode']})")
                print(f"   Service: {parcel['service_type']}")
                print(f"   Status: {parcel['current_status']}")
                print(f"   Location: {parcel['current_location']}")
                print(f"   Registered: {parcel['registration_timestamp']}")
                if parcel.get('special_instructions'):
                    print(f"   Special: {parcel['special_instructions']}")
                print()
        else:
            print("No parcels found")
        
        # Display pending approvals
        print("--- Pending Approvals ---")
        pending = await get_all_pending_approvals()
        if pending:
            for i, approval in enumerate(pending, 1):
                print(f"{i}. Request ID: {approval['id']}")
                print(f"   Parcel: {approval['parcel_barcode']}")
                print(f"   Type: {approval['request_type']}")
                print(f"   Description: {approval['description']}")
                print(f"   Priority: {approval['priority']}")
                print(f"   Requested: {approval['request_timestamp']}")
                print()
        else:
            print("No pending approvals found")
            
    except Exception as e:
        print(f"Error displaying database contents: {e}")

async def cleanup_all_data():
    """Clean up all data from the database"""
    print("\n=== Cleaning up database ===")
    try:
        await cleanup_database()
        print("Database cleaned up successfully")
    except Exception as e:
        print(f"Error cleaning up database: {e}")

async def main():
    """Main function to run setup and tests"""
    print("Azure Cosmos DB Setup and Testing")
    print("=" * 50)
    
    while True:
        print("\nOptions:")
        print("1. Setup Cosmos DB with test data")
        print("2. Test approval workflow")
        print("3. Display database contents")
        print("4. Clean up all data")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ")
        
        if choice == "1":
            await setup_cosmos_db()
        elif choice == "2":
            await test_approval_workflow()
        elif choice == "3":
            await display_database_contents()
        elif choice == "4":
            confirm = input("Are you sure you want to delete all data? (yes/no): ")
            if confirm.lower() == "yes":
                await cleanup_all_data()
        elif choice == "5":
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    asyncio.run(main())