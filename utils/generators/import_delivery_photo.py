#!/usr/bin/env python3
"""
Import a proof-of-delivery or proof-of-lodgement photo into Cosmos DB.

Delivery photos  - uploaded by the driver at the point of delivery.
Lodgement photos - uploaded by the sender at the point of lodgement.

Usage:
    # Delivery photo (default)
    python import_delivery_photo.py --tracking DT202512170037 --image static/images/delivery_sample.jpg

    # Lodgement photo (sender proof)
    python import_delivery_photo.py --tracking RG857954 --type lodgement --image static/images/lodgement_sample.jpg --uploader "sender-name"

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


def _find_image_file(base_dir: str, photo_type: str = "delivery") -> str | None:
    """Look for delivery_sample or lodgement_sample image in static/images."""
    name = "lodgement_sample" if photo_type == "lodgement" else "delivery_sample"
    candidates = [
        os.path.join(base_dir, "static", "images", f"{name}.jpg"),
        os.path.join(base_dir, "static", "images", f"{name}.jpeg"),
        os.path.join(base_dir, "static", "images", f"{name}.png"),
        # Fall back to delivery_sample for lodgement if no specific one exists
        os.path.join(base_dir, "static", "images", "delivery_sample.jpg"),
        os.path.join(base_dir, "static", "images", "delivery_sample.jpeg"),
        os.path.join(base_dir, "static", "images", "delivery_sample.png"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


async def import_photo(
    tracking_number: str,
    image_path: str,
    uploaded_by: str = "driver-003",
    photo_type: str = "delivery",
) -> bool:
    """
    Read an image file, encode it as base64, and store it as a proof photo
    for the given parcel tracking number.

    Args:
        tracking_number: Parcel tracking number or barcode
        image_path:      Path to the image file (JPEG or PNG)
        uploaded_by:     Identity of the uploader (driver ID or sender name)
        photo_type:      "delivery" (driver proof) or "lodgement" (sender proof)

    Clears any existing photos of that type first so only the imported image remains.
    """
    if not os.path.isfile(image_path):
        print(f"  X Image file not found: {image_path}")
        return False

    with open(image_path, "rb") as f:
        raw_bytes = f.read()
    photo_b64 = base64.b64encode(raw_bytes).decode("utf-8")
    file_size_kb = round(len(raw_bytes) / 1024, 1)
    print(f"  OK Image loaded: {os.path.basename(image_path)} ({file_size_kb} KB)")

    async with ParcelTrackingDB() as db:
        parcel = await db.get_parcel_by_tracking_number(tracking_number)
        if not parcel:
            print(f"  X Parcel not found: {tracking_number}")
            return False

        barcode = parcel.get("barcode") or parcel.get("id")
        print(f"  OK Parcel found: {tracking_number} (barcode: {barcode})")

        field = "delivery_photos" if photo_type == "delivery" else "lodgement_photos"
        container = db.database.get_container_client(db.parcels_container)
        parcel[field] = [
            {
                "photo_data": photo_b64,
                "uploaded_by": uploaded_by,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "photo_size_kb": file_size_kb,
            }
        ]
        parcel["last_updated"] = datetime.now(timezone.utc).isoformat()
        await container.upsert_item(parcel)

        label = "Delivery" if photo_type == "delivery" else "Lodgement"
        print(f"  OK {label} photo stored for {tracking_number} (uploaded_by={uploaded_by})")
        return True


async def main():
    parser = argparse.ArgumentParser(description="Import a proof photo into Cosmos DB")
    parser.add_argument(
        "--tracking",
        default="DT202512170037",
        help="Parcel tracking number (default: DT202512170037)",
    )
    parser.add_argument(
        "--image",
        default=None,
        help="Path to image file (default: auto-detect from static/images/)",
    )
    parser.add_argument(
        "--type",
        dest="photo_type",
        choices=["delivery", "lodgement"],
        default="delivery",
        help="Photo type: 'delivery' (driver) or 'lodgement' (sender). Default: delivery",
    )
    parser.add_argument(
        "--uploader",
        default=None,
        help="Who uploaded the photo (driver ID or sender name). Defaults to driver-003 for delivery, 'sender' for lodgement.",
    )
    args = parser.parse_args()

    default_uploader = "driver-003" if args.photo_type == "delivery" else "sender"
    uploaded_by = args.uploader or default_uploader

    image_path = args.image
    if not image_path:
        image_path = _find_image_file(project_root, args.photo_type)
        if not image_path:
            print(f"  X No image file supplied and none found at static/images/{args.photo_type}_sample.jpg/.png")
            print("    Save the image there and re-run, or pass --image <path>")
            sys.exit(1)

    print("=" * 60)
    print(f"  Import {args.photo_type.title()} Photo")
    print("=" * 60)
    print(f"  Tracking  : {args.tracking}")
    print(f"  Image     : {image_path}")
    print(f"  Uploaded by: {uploaded_by}")
    print()

    success = await import_photo(args.tracking, image_path, uploaded_by=uploaded_by, photo_type=args.photo_type)

    print()
    if success:
        print(f"OK {args.photo_type.title()} photo imported successfully.")
    else:
        print(f"FAIL {args.photo_type.title()} photo import failed.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

