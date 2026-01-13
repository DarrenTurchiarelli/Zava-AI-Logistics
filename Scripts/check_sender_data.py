"""Quick check for sender data in parcels"""
import asyncio
import json

from parcel_tracking_db import ParcelTrackingDB


async def check_sender_data():
    async with ParcelTrackingDB() as db:
        parcels = await db.get_all_parcels()

        print(f"Total parcels: {len(parcels)}")
        print("\nSearching for parcels with tracking history and sender info...\n")

        parcels_with_history = []

        for parcel in parcels[:500]:  # Check first 500
            barcode = parcel.get("barcode")
            tracking_number = parcel.get("tracking_number")
            sender_name = parcel.get("sender_name")

            # Get tracking history
            events = await db.get_parcel_tracking_history(barcode)

            # Look for parcels with multiple events and sender info
            if events and len(events) >= 3 and sender_name and sender_name != "Unknown Sender":
                parcels_with_history.append(
                    {
                        "barcode": barcode,
                        "tracking_number": tracking_number,
                        "sender_name": sender_name,
                        "sender_address": parcel.get("sender_address"),
                        "recipient_name": parcel.get("recipient_name"),
                        "current_status": parcel.get("current_status"),
                        "event_count": len(events),
                        "events": events,
                    }
                )

        print(f"Found {len(parcels_with_history)} parcels with tracking history and sender info:")

        # Sort by event count
        parcels_with_history.sort(key=lambda x: x["event_count"], reverse=True)

        for p in parcels_with_history[:5]:
            print(f"\n{'='*60}")
            print(f"Barcode: {p['barcode']}")
            print(f"Tracking: {p['tracking_number']}")
            print(f"Sender: {p['sender_name']}")
            print(f"Sender Address: {p['sender_address']}")
            print(f"Recipient: {p['recipient_name']}")
            print(f"Current Status: {p['current_status']}")
            print(f"Total Events: {p['event_count']}")
            print(f"\nEvent History:")
            for i, event in enumerate(p["events"][:10], 1):
                timestamp = event.get("timestamp", "N/A")
                status = event.get("status", "N/A")
                location = event.get("location", "N/A")
                description = event.get("description", "N/A")
                print(f"  {i}. {timestamp}")
                print(f"     Status: {status} | Location: {location}")
                print(f"     {description}")


if __name__ == "__main__":
    asyncio.run(check_sender_data())
