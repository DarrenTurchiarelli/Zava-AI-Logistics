"""
Diagnose Cosmos DB container status — read-only, no writes.
Checks which of the 10 required containers exist and reports missing ones.
Exit code 0 = all containers present, 1 = missing containers or connection error.
"""

import asyncio
import os
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential

REQUIRED_CONTAINERS = [
    "parcels",
    "tracking_events",
    "delivery_attempts",
    "feedback",
    "company_info",
    "suspicious_messages",
    "address_history",
    "users",
    "Manifests",
    "address_notes",
]


async def diagnose():
    connection_string = os.getenv("COSMOS_CONNECTION_STRING")
    endpoint = os.getenv("COSMOS_DB_ENDPOINT")
    database_name = os.getenv("COSMOS_DB_DATABASE_NAME", "logisticstracking")

    credential = None

    try:
        if connection_string:
            parts = dict(p.split("=", 1) for p in connection_string.split(";") if "=" in p)
            endpoint = parts.get("AccountEndpoint", endpoint)
            key = parts.get("AccountKey")
            client = CosmosClient(endpoint, key)
            print(f"Auth: connection string")
        elif endpoint:
            credential = DefaultAzureCredential()
            client = CosmosClient(endpoint, credential)
            print(f"Auth: Azure AD (DefaultAzureCredential)")
        else:
            print("ERROR: No Cosmos DB connection details found")
            print("  Set COSMOS_CONNECTION_STRING or COSMOS_DB_ENDPOINT")
            sys.exit(1)

        print(f"Endpoint : {endpoint}")
        print(f"Database : {database_name}")
        print()

        try:
            database = client.get_database_client(database_name)
            existing = {c["id"] async for c in database.list_containers()}
        except Exception as e:
            print(f"ERROR: Cannot connect to database '{database_name}': {e}")
            await client.close()
            sys.exit(1)

        print(f"{'Container':<28} Status")
        print("-" * 42)

        missing = []
        for name in REQUIRED_CONTAINERS:
            if name in existing:
                print(f"  {name:<26} ✓ exists")
            else:
                print(f"  {name:<26} ✗ MISSING")
                missing.append(name)

        extra = existing - set(REQUIRED_CONTAINERS)
        for name in sorted(extra):
            print(f"  {name:<26} (extra)")

        print()
        if missing:
            print(f"MISSING {len(missing)}/{len(REQUIRED_CONTAINERS)} containers: {', '.join(missing)}")
            await client.close()
            sys.exit(1)
        else:
            print(f"All containers present ({len(REQUIRED_CONTAINERS)}/{len(REQUIRED_CONTAINERS)})")
            await client.close()
            sys.exit(0)

    finally:
        if credential:
            await credential.close()


if __name__ == "__main__":
    asyncio.run(diagnose())
