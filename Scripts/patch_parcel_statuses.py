#!/usr/bin/env python3
"""
One-off patch: reassign parcels stored as 'registered' to proper statuses.
Uses AzureCliCredential (local auth is disabled on the Cosmos DB account).
"""
import asyncio
import random
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import AzureCliCredential

ENDPOINT = "https://zava-dev-cosmos-qvsift.documents.azure.com:443/"
DATABASE = "logisticstracking"

# At Depot:Sorting:In Transit = 30:20:5 (matches generator weights)
STATUS_POOL = ["At Depot"] * 30 + ["Sorting"] * 20 + ["In Transit"] * 5


async def patch():
    credential = AzureCliCredential()
    async with CosmosClient(ENDPOINT, credential=credential) as client:
        db = client.get_database_client(DATABASE)
        container = db.get_container_client("parcels")

        query = "SELECT c.id, c.barcode, c.store_location FROM c WHERE c.current_status = 'registered'"
        items = [
            p
            async for p in container.query_items(query=query)
        ]
        print(f"Found {len(items)} parcels with status='registered'")

        if not items:
            print("Nothing to patch.")
        else:
            updated = 0
            errors = 0
            for p in items:
                new_status = random.choice(STATUS_POOL)
                pk = p.get("store_location") or "DC-NSW-01"
                try:
                    await container.patch_item(
                        item=p["id"],
                        partition_key=pk,
                        patch_operations=[
                            {"op": "replace", "path": "/current_status", "value": new_status}
                        ],
                    )
                    updated += 1
                    if updated % 100 == 0:
                        print(f"  Updated {updated}/{len(items)}...", end="\r")
                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"  WARN patch {p['id'][:8]}: {e}")

            print(f"\nDone.  Updated={updated}  Errors={errors}")

        # Final distribution
        print("\nFinal status distribution:")
        all_items = [
            p
            async for p in container.query_items("SELECT c.current_status FROM c")
        ]
        counts = {}
        for p in all_items:
            s = p.get("current_status", "unknown")
            counts[s] = counts.get(s, 0) + 1
        for k, v in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {k:25} {v}")
        print(f"  {'TOTAL':25} {sum(counts.values())}")

    await credential.close()


if __name__ == "__main__":
    asyncio.run(patch())
