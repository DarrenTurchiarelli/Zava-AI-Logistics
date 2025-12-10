# Driver Address Notes Feature

## Overview
Drivers can now add and view notes about delivery addresses (e.g., "Large dog in yard", "Use side gate", "Apartment buzzer broken"). These notes are saved permanently and displayed to future drivers delivering to the same address, improving delivery efficiency and driver safety.

## Features

### 1. **View Previous Address Notes**
- When viewing the manifest, drivers can see if previous drivers left notes about an address
- Notes are displayed with a badge showing the count: "3 note(s)"
- Click the badge to view all historical notes in a modal

### 2. **Add New Address Notes**
- When completing a delivery, drivers can optionally add a note about the address
- Notes are stored permanently and linked to the normalized address
- Future deliveries to the same address will display these notes

### 3. **Address Normalization**
- Addresses are normalized (lowercase, trimmed) for consistent matching
- Ensures notes are found regardless of minor address formatting differences

## How It Works

### Database Structure

#### Address Notes Collection (`address_notes`)
```json
{
    "id": "note_123_main_st_sydney_nsw_2000",
    "address": "123 Main St, Sydney, NSW 2000",
    "normalized_address": "123 main st sydney nsw 2000",
    "notes": [
        {
            "note": "Large dog in backyard - use front gate only",
            "driver_name": "John Smith",
            "timestamp": "2025-12-10T14:30:00Z"
        },
        {
            "note": "Customer prefers deliveries before 3 PM",
            "driver_name": "Jane Doe",
            "timestamp": "2025-12-09T10:15:00Z"
        }
    ],
    "created_at": "2025-12-09T10:15:00Z",
    "last_updated": "2025-12-10T14:30:00Z"
}
```

### Workflow

#### 1. Driver Views Manifest
```python
# app.py - driver_manifest route
async def fetch_address_notes():
    async with ParcelTrackingDB() as db:
        for item in manifest.get('items', []):
            address = item.get('recipient_address')
            if address:
                notes = await db.get_address_notes(address)
                if notes:
                    item['address_notes'] = notes
```

#### 2. Driver Completes Delivery
- Click "Complete" button on delivery item
- Modal opens showing:
  - Delivery details
  - Previous notes (if any)
  - Textarea to add new note (optional)
- Submit to mark delivery complete

#### 3. Note is Saved
```python
# parcel_tracking_db.py
async def mark_delivery_complete(manifest_id, barcode, driver_note=None):
    # Mark delivery complete
    # If note provided, save it
    if driver_note and delivery_address:
        await self.save_address_note(delivery_address, driver_note, driver_name)
```

#### 4. Note Appears for Future Deliveries
- Next time any driver delivers to that address
- Notes automatically load and display
- Driver can see all previous notes before delivery

## User Interface

### Manifest Table
```
┌────┬──────────┬───────────┬──────────────┬───────────────┐
│ #  │ Barcode  │ Recipient │ Address      │ Address Notes │
├────┼──────────┼───────────┼──────────────┼───────────────┤
│ 1  │ PKG123   │ John Doe  │ 123 Main St  │ 🗒️ 2 note(s) │
└────┴──────────┴───────────┴──────────────┴───────────────┘
```

### Notes Modal (Viewing)
```
╔═══════════════════════════════════════╗
║ 🗒️ Address Notes                     ║
╠═══════════════════════════════════════╣
║ Address: 123 Main St, Sydney         ║
║ ─────────────────────────────────────║
║ Previous Driver Notes:                ║
║                                       ║
║ ┌─────────────────────────────────┐ ║
║ │ Large dog in backyard           │ ║
║ │ 👤 John Smith - 2025-12-09      │ ║
║ └─────────────────────────────────┘ ║
║                                       ║
║ ┌─────────────────────────────────┐ ║
║ │ Customer prefers before 3 PM    │ ║
║ │ 👤 Jane Doe - 2025-12-08        │ ║
║ └─────────────────────────────────┘ ║
║                                       ║
║           [Close]                     ║
╚═══════════════════════════════════════╝
```

### Completion Modal (Adding Note)
```
╔═══════════════════════════════════════╗
║ ✅ Complete Delivery                 ║
╠═══════════════════════════════════════╣
║ Barcode: PKG123                       ║
║ Recipient: John Doe                   ║
║ Address: 123 Main St, Sydney          ║
║                                       ║
║ ℹ️ Previous Notes:                    ║
║   • Large dog in backyard             ║
║   • Customer prefers before 3 PM      ║
║                                       ║
║ ─────────────────────────────────────║
║ 🗒️ Add Note About This Address:      ║
║ ┌─────────────────────────────────┐ ║
║ │                                 │ ║
║ │                                 │ ║
║ │                                 │ ║
║ └─────────────────────────────────┘ ║
║ This note will help future drivers    ║
║                                       ║
║        [Cancel] [Mark as Delivered]   ║
╚═══════════════════════════════════════╝
```

## Setup Instructions

### 1. Create Address Notes Container
```bash
cd "Test Scripts"
python setup_address_notes_container.py
```

This creates the `address_notes` container in Cosmos DB with:
- Partition key: `/normalized_address`
- Minimum throughput: 400 RU/s

### 2. Restart Flask Application
```bash
python app.py
```

### 3. Test the Feature
1. Login as driver (e.g., driver001)
2. Open "My Manifest"
3. Click "Complete" on any delivery
4. Add a note (e.g., "Large dog - use caution")
5. Submit
6. Note is saved!

## Use Cases

### Safety Warnings
- "Large aggressive dog in yard"
- "Slippery driveway when wet"
- "Low-hanging tree branch at entrance"
- "Beware of wasps near mailbox"

### Access Instructions
- "Use side gate, front is locked"
- "Ring bell twice for response"
- "Apartment buzzer broken - call customer"
- "Leave packages in garage"

### Customer Preferences
- "Customer works nights - deliver before 2 PM"
- "Leave at back door"
- "Do not ring bell - baby sleeping"
- "Customer prefers signature required"

### Special Circumstances
- "Elderly resident - may take time to answer"
- "Security cameras active"
- "Construction ongoing - park on street"
- "Multiple units - confirm unit number"

## Benefits

### For Drivers
- ⚠️ **Safety**: Know about hazards before arriving
- ⏰ **Efficiency**: Access instructions save time
- 📋 **Confidence**: Learn from experienced drivers
- 🎯 **Success**: Higher first-time delivery success rate

### For Operations
- 📈 **Better service**: Consistent delivery experience
- 💰 **Cost savings**: Fewer failed deliveries
- 👥 **Knowledge sharing**: Driver expertise preserved
- 📊 **Data insights**: Common issues identified

### For Customers
- 🏡 **Better experience**: Drivers know their preferences
- ⏱️ **Reliability**: Fewer delivery issues
- 🔒 **Security**: Special instructions followed
- 📞 **Less disruption**: Fewer confused driver calls

## Technical Details

### API Methods

#### `get_address_notes(address)`
Retrieves all notes for an address.

```python
notes = await db.get_address_notes("123 Main St, Sydney, NSW 2000")
# Returns: List of note objects with driver_name and timestamp
```

#### `save_address_note(address, note, driver_name)`
Saves a new note for an address.

```python
await db.save_address_note(
    "123 Main St, Sydney, NSW 2000",
    "Large dog in yard",
    "John Smith"
)
```

#### `mark_delivery_complete(manifest_id, barcode, driver_note)`
Marks delivery complete and optionally saves note.

```python
await db.mark_delivery_complete(
    "manifest_123",
    "PKG456",
    "Customer prefers back door"
)
```

### Database Queries

#### Find Notes by Address
```sql
SELECT * FROM c 
WHERE c.normalized_address = @address
```

#### Example Response
```json
{
    "notes": [
        {
            "note": "Large dog in yard",
            "driver_name": "John Smith",
            "timestamp": "2025-12-10T14:30:00Z"
        }
    ]
}
```

## Future Enhancements

### Potential Features
1. **Note Categories**: Tag notes (Safety, Access, Preference, etc.)
2. **Upvoting**: Drivers can upvote helpful notes
3. **Photo Attachments**: Add photos to notes
4. **Expiration**: Auto-expire old notes
5. **Admin Moderation**: Review and approve notes
6. **Search**: Search notes across all addresses
7. **Analytics**: Most common note types
8. **Notifications**: Alert drivers of new notes
9. **Voice Notes**: Record audio notes
10. **Translation**: Auto-translate notes

### Advanced Analytics
- Identify problematic addresses
- Track delivery success rate improvements
- Measure time savings
- Note quality scoring

## Privacy & Compliance

### Best Practices
- ✅ Keep notes professional and factual
- ✅ Focus on delivery-relevant information
- ❌ Don't include personal customer information
- ❌ Don't make discriminatory comments
- ❌ Don't share sensitive details

### Moderation
- Admins can view all notes
- Inappropriate notes can be removed
- Driver accountability maintained

## Testing

### Test Scenarios
1. **Add first note** to new address
2. **Add second note** to existing address
3. **View notes** on next delivery
4. **Complete without note** (optional field)
5. **Address variations** (case sensitivity, spacing)

### Expected Results
- Notes save successfully
- Notes display on manifest
- Multiple notes accumulate
- Notes survive across manifests

---

**Version:** 1.0  
**Date:** December 10, 2025  
**Status:** Production Ready
