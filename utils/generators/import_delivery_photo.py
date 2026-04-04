#!/usr/bin/env python3
"""
Import a real delivery photo into Cosmos DB for a specific parcel.

Replaces any existing dummy delivery photo with the supplied image file.
Supports JPEG and PNG input.

Usage:
    python import_delivery_photo.py --tracking DT202512170037 --image static/images/delivery_sample.jpg
    python import_delivery_photo.py  # uses defaults above

The script is also called automatically by generate_bulk_realistic_data.py
when static/images/delivery_sample.jpg (or .png) exists.
"""

import argparse
import asyncio
import base64
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv()

from parcel_tracking_db import ParcelTrackingDB


def _find_image_file(base_dir: str) -> str | None:
    """Look for delivery_sample.jpg/.jpeg/.png in static/images relative to base_dir."""
    candidates = [
        os.path.join(base_dir, "static", "images", "delivery_sample.jpg"),
        os.path.join(base_dir, "static", "images", "delivery_sample.jpeg"),
        os.path.join(base_dir, "static", "images", "delivery_sample.png"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


async def import_photo(tracking_number: str, image_path: str, uploaded_by: str = "driver-003") -> bool:
    """
    Read an image file, encode it as base64, and store it as the delivery
    photo for the given parcel tracking number.

    Clears any existing delivery photos first so only the real image remains.
    """
    if not os.path.isfile(image_path):
        print(f"  ✗ Image file not found: {image_path}")
        return False

    # Read and encode the image
    with open(image_path, "rb") as f:
        raw_bytes = f.read()
    photo_b64 = base64.b64encode(raw_bytes).decode("utf-8")
    file_size_kb = len(raw_bytes) / 1024
    print(f"  ✓ Image loaded: {os.path.basename(image_path)} ({file_size_kb:.1f} KB)")

    async with ParcelTrackingDB() as db:
        # Locate the parcel
        parcel = await db.get_parcel_by_tracking_number(tracking_number)
        if not parcel:
            print(f"  ✗ Parcel not found: {tracking_number}")
            return False

        barcode = parcel.get("barcode") or parcel.get("id")
        print(f"  ✓ Parcel found: {tracking_number} (barcode: {barcode})")

        # Replace delivery_photos with the real image
        container = db.database.get_container_client(db.parcels_container)
        parcel["delivery_photos"] = [
            {
                "photo_data": photo_b64,
                "uploaded_by": uploaded_by,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]
        parcel["last_updated"] = datetime.now(timezone.utc).isoformat()
        await container.upsert_item(parcel)

        print(f"  ✓ Delivery photo stored for {tracking_number}")
        return True


async def main():
    parser = argparse.ArgumentParser(description="Import a delivery photo into Cosmos DB")
    parser.add_argument(
        "--tracking",
        default="DT202512170037",
        help="Parcel tracking number (default: DT202512170037)",
    )
    parser.add_argument(
        "--image",
        default=None,
        help="Path to image file (default: auto-detect static/images/delivery_sample.jpg|.png)",
    )
    parser.add_argument(
        "--driver",
        default="driver-003",
        help="Driver ID to attribute the photo to (default: driver-003)",
    )
    args = parser.parse_args()

    image_path = args.image
    if not image_path:
        image_path = _find_image_file(project_root)
        if not image_path:
            print("  ✗ No image file supplied and none found at static/images/delivery_sample.jpg/.png")
            print("    Save the image there and re-run, or pass --image <path>")
            sys.exit(1)

    print("=" * 60)
    print("  Import Delivery Photo")
    print("=" * 60)
    print(f"  Tracking : {args.tracking}")
    print(f"  Image    : {image_path}")
    print(f"  Driver   : {args.driver}")
    print()

    success = await import_photo(args.tracking, image_path, uploaded_by=args.driver)

    print()
    if success:
        print("✅ Photo imported successfully.")
    else:
        print("❌ Photo import failed.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
