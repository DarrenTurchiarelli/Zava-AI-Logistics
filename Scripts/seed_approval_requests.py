#!/usr/bin/env python3
"""Seed the delivery_attempts container with pending approval requests for the AI Insights demo."""
import asyncio
import sys
import uuid
import random
from datetime import datetime, timezone

sys.path.insert(0, ".")
from parcel_tracking_db import ParcelTrackingDB  # noqa: E402

TYPES = ["exception_handling", "return_to_sender", "delivery_redirect", "damage_claim", "delivery_confirmation"]
PRIORITIES = ["low", "medium", "high", "critical"]
REQUESTORS = ["System", "Customer Service", "Security", "Depot Manager", "Customs"]


async def run():
    async with ParcelTrackingDB() as db:
        all_p = await db.get_all_parcels()
        eligible = [p for p in all_p if "DC-" in p.get("store_location", "")]
        print(f"Eligible parcels: {len(eligible)}")
        sample = random.sample(eligible, min(15, len(eligible)))

        container = db.database.get_container_client(db.delivery_attempts_container)
        created = 0
        for p in sample:
            req_type = random.choice(TYPES)
            desc = req_type.replace("_", " ").title() + " for parcel " + p["barcode"]
            doc = {
                "id": str(uuid.uuid4()),
                "parcel_barcode": p["barcode"],
                "barcode": p["barcode"],
                "request_type": req_type,
                "description": desc,
                "priority": random.choice(PRIORITIES),
                "requested_by": random.choice(REQUESTORS),
                "status": "pending",
                "request_timestamp": datetime.now(timezone.utc).isoformat(),
                "parcel_dc": p.get("store_location", "DC-NSW-01"),
                "parcel_status": p.get("current_status", "At Depot"),
            }
            await container.create_item(body=doc)
            created += 1
        print(f"Created {created} approval requests in delivery_attempts container")


if __name__ == "__main__":
    asyncio.run(run())
