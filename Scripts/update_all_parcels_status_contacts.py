"""
Update all parcels with proper status and contact information
"""
import asyncio
import random
from faker import Faker
from parcel_tracking_db import ParcelTrackingDB

fake = Faker('en_AU')

# Australian mobile number format: 04XX XXX XXX
def generate_au_mobile():
    """Generate Australian mobile number"""
    return f"04{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)}"

def generate_email(name):
    """Generate realistic email from name"""
    if not name:
        name = fake.name()
    
    # Clean name
    parts = name.lower().replace("dr. ", "").replace("mr. ", "").replace("ms. ", "").replace("mrs. ", "").split()
    if len(parts) >= 2:
        email_name = f"{parts[0]}.{parts[1]}"
    else:
        email_name = parts[0]
    
    domains = ["gmail.com", "outlook.com", "hotmail.com", "yahoo.com.au", "iinet.net.au", "optus.com.au"]
    return f"{email_name}@{random.choice(domains)}"

async def update_all_parcels():
    """Update all parcels with proper status and contact info"""
    print("=" * 60)
    print("Updating All Parcels - Status & Contact Information")
    print("=" * 60)
    
    async with ParcelTrackingDB() as db:
        # Get all parcels
        print("\n📦 Fetching all parcels...")
        all_parcels = await db.get_all_parcels()
        print(f"   Found {len(all_parcels)} parcels to update")
        
        container = db.database.get_container_client("parcels")
        
        updated_count = 0
        error_count = 0
        
        for parcel in all_parcels:
            try:
                # Check current_status and map to status field
                current_status = parcel.get("current_status", "registered")
                
                # Update the parcel document
                parcel["status"] = current_status  # Add status field
                
                # Update recipient contact info
                recipient_name = parcel.get("recipient_name", "Unknown")
                
                # 70% mobile, 30% landline, all get emails
                if random.random() < 0.7:
                    parcel["recipient_phone"] = generate_au_mobile()
                    parcel["recipient_phone_type"] = "mobile"
                else:
                    # Keep existing or generate landline (02, 03, 07, 08)
                    area_code = random.choice(["02", "03", "07", "08"])
                    parcel["recipient_phone"] = f"{area_code} {random.randint(1000, 9999)} {random.randint(1000, 9999)}"
                    parcel["recipient_phone_type"] = "landline"
                
                # Everyone gets email
                parcel["recipient_email"] = generate_email(recipient_name)
                
                # Update sender contact info if sender exists
                sender_name = parcel.get("sender_name")
                if sender_name and sender_name != "Unknown Sender":
                    # Senders more likely to be businesses with landlines
                    if random.random() < 0.5:
                        parcel["sender_phone"] = generate_au_mobile()
                        parcel["sender_phone_type"] = "mobile"
                    else:
                        area_code = random.choice(["02", "03", "07", "08"])
                        parcel["sender_phone"] = f"{area_code} {random.randint(1000, 9999)} {random.randint(1000, 9999)}"
                        parcel["sender_phone_type"] = "landline"
                    
                    parcel["sender_email"] = generate_email(sender_name)
                
                # Update in database
                await container.replace_item(
                    item=parcel['id'],
                    body=parcel
                )
                
                updated_count += 1
                
                if updated_count % 100 == 0:
                    print(f"   Progress: {updated_count}/{len(all_parcels)} updated...")
                
            except Exception as e:
                error_count += 1
                print(f"   ⚠️ Error updating parcel {parcel.get('barcode', 'unknown')}: {e}")
                continue
        
        print("\n" + "=" * 60)
        print("✅ Update Complete!")
        print("=" * 60)
        print(f"Updated: {updated_count} parcels")
        print(f"Errors: {error_count} parcels")
        
        # Show sample
        print("\n📋 Sample Updated Parcel:")
        sample = await db.get_all_parcels()
        if sample:
            p = sample[0]
            print(f"   Barcode: {p.get('barcode')}")
            print(f"   Status: {p.get('status')} (from current_status: {p.get('current_status')})")
            print(f"   Recipient: {p.get('recipient_name')}")
            print(f"   Phone: {p.get('recipient_phone')} ({p.get('recipient_phone_type')})")
            print(f"   Email: {p.get('recipient_email')}")
            if p.get('sender_name'):
                print(f"   Sender: {p.get('sender_name')}")
                print(f"   Sender Phone: {p.get('sender_phone')} ({p.get('sender_phone_type')})")
                print(f"   Sender Email: {p.get('sender_email')}")

if __name__ == "__main__":
    asyncio.run(update_all_parcels())
