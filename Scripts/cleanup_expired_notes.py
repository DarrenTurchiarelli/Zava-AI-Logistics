#!/usr/bin/env python3
"""
Cleanup Expired Address Notes

Scans the address_notes container and removes expired note entries.
Notes that are past their expires_at date are pruned. If all notes in a
document are expired, the entire document is deleted.

Can be run manually or scheduled (e.g., daily via cron / Azure Timer Function).

Usage:
    python Scripts/cleanup_expired_notes.py            # Dry run (preview)
    python Scripts/cleanup_expired_notes.py --apply     # Actually delete expired notes
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import AzureCliCredential, DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()


async def cleanup_expired_notes(dry_run: bool = True):
    """Scan and remove expired address notes."""

    endpoint = os.getenv("COSMOS_DB_ENDPOINT")
    database_name = os.getenv("COSMOS_DB_DATABASE_NAME", "agent_workflow_db")
    connection_string = os.getenv("COSMOS_CONNECTION_STRING")

    if not endpoint and not connection_string:
        print("❌ COSMOS_DB_ENDPOINT or COSMOS_CONNECTION_STRING not configured")
        return

    print(f"{'🔍 DRY RUN' if dry_run else '🗑️  APPLYING'} - Cleaning expired address notes")
    print(f"   Database: {database_name}")
    print(f"   Time now: {datetime.now(timezone.utc).isoformat()}")
    print()

    # Connect to Cosmos DB
    if connection_string:
        client = CosmosClient.from_connection_string(connection_string)
    else:
        try:
            credential = AzureCliCredential()
        except Exception:
            credential = DefaultAzureCredential()
        client = CosmosClient(endpoint, credential)

    stats = {
        "documents_scanned": 0,
        "notes_expired": 0,
        "notes_kept": 0,
        "documents_pruned": 0,
        "documents_deleted": 0,
        "legacy_notes": 0,
    }

    async with client:
        database = client.get_database_client(database_name)
        container = database.get_container_client("address_notes")

        now = datetime.now(timezone.utc)

        # Scan all address note documents
        query = "SELECT * FROM c"
        async for doc in container.query_items(query=query, parameters=[]):
            stats["documents_scanned"] += 1
            address = doc.get("address", "?")
            all_notes = doc.get("notes", [])
            active_notes = []
            expired_count = 0

            for note in all_notes:
                expires_at_str = note.get("expires_at")
                if expires_at_str:
                    try:
                        expires_at = datetime.fromisoformat(expires_at_str)
                        if expires_at <= now:
                            expired_count += 1
                            category = note.get("category", "general")
                            print(f"   ⏰ EXPIRED [{category}] {address[:50]} — \"{note.get('note', '')[:60]}\"")
                            continue
                    except (ValueError, TypeError):
                        pass

                # Legacy note without expires_at
                if not expires_at_str:
                    stats["legacy_notes"] += 1

                active_notes.append(note)

            stats["notes_expired"] += expired_count
            stats["notes_kept"] += len(active_notes)

            if expired_count > 0:
                if not dry_run:
                    normalized = doc.get("normalized_address", address.strip().lower())
                    if active_notes:
                        doc["notes"] = active_notes
                        doc["last_updated"] = now.isoformat()
                        await container.replace_item(item=doc["id"], body=doc)
                        stats["documents_pruned"] += 1
                    else:
                        await container.delete_item(item=doc["id"], partition_key=normalized)
                        stats["documents_deleted"] += 1
                        print(f"   🗑️ Deleted empty document for: {address}")
                else:
                    if not active_notes:
                        stats["documents_deleted"] += 1
                    else:
                        stats["documents_pruned"] += 1

    print()
    print("=" * 55)
    print(f"📊 Results {'(DRY RUN)' if dry_run else '(APPLIED)'}:")
    print(f"   Documents scanned:  {stats['documents_scanned']}")
    print(f"   Notes expired:      {stats['notes_expired']}")
    print(f"   Notes kept:         {stats['notes_kept']}")
    print(f"   Legacy (no expiry): {stats['legacy_notes']}")
    print(f"   Documents pruned:   {stats['documents_pruned']}")
    print(f"   Documents deleted:  {stats['documents_deleted']}")
    print()

    if dry_run and stats["notes_expired"] > 0:
        print("💡 Run with --apply to actually remove expired notes:")
        print("   python Scripts/cleanup_expired_notes.py --apply")
    elif not dry_run:
        print("✅ Cleanup complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup expired address notes from Cosmos DB")
    parser.add_argument("--apply", action="store_true", help="Actually delete expired notes (default is dry run)")
    args = parser.parse_args()

    asyncio.run(cleanup_expired_notes(dry_run=not args.apply))
