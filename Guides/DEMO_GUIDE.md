# Driver Manifest Demo Guide

## Quick Start

### Generate Demo Data

Run this command to create sample parcels and driver manifests:

```bash
python generate_demo_manifests.py
```

This creates:
- **20 sample parcels** with realistic Sydney addresses
- **3 driver manifests** distributed across drivers
- All data ready for immediate demonstration

### Sample Drivers

| Driver ID | Driver Name | Parcels |
|-----------|-------------|---------|
| `driver-001` | John Smith | 6 |
| `driver-002` | Maria Garcia | 6 |
| `driver-003` | David Wong | 8 |
| `driver-004` | Mandy Musk | 16 |

### Demo Workflow

1. **View All Manifests (Admin)**
   - URL: http://127.0.0.1:5000/admin/manifests
   - See all active manifests for all drivers
   - Monitor delivery progress

2. **View Driver Manifest**
   - URL: http://127.0.0.1:5000/driver/manifest
   - Change `driver_id` in URL to test different drivers
   - See optimized route on embedded map
   - Mark deliveries as complete

3. **Create New Manifest**
   - Go to Admin Manifests page
   - Enter driver ID and name
   - Paste barcodes (comma or newline separated)
   - Click "Create Manifest"

### Sample Addresses

All deliveries are in Sydney CBD area:
- Macquarie Street (CBD)
- The Rocks
- Barangaroo
- George Street
- King Street
- North Sydney (across harbour)
- Pyrmont (waterfront)

### Route Optimization

**Without Azure Maps Key:**
- Uses mock optimization
- Estimates 5km and 10min per delivery
- Still shows map placeholder

**With Azure Maps Key:**
1. Add to `.env`:
   ```
   AZURE_MAPS_SUBSCRIPTION_KEY=your_key_here
   ```
2. Restart Flask app
3. Routes will optimize with real traffic data
4. Actual distances and times calculated

### Testing Delivery Completion

1. Open driver manifest view
2. Click "Complete" button next to any delivery
3. Watch progress bar update
4. Status changes to "completed" for that item
5. When all items completed, manifest status updates

### Sample Barcode Format

Generated barcodes follow pattern:
- `DT` + `YYYYMMDD` + `####`
- Example: `DT202512040001`

### Regenerating Demo Data

Running the script multiple times will:
- Create new parcels with new barcodes
- Create new manifests with unique IDs
- Keep existing data (no deletions)

To start fresh:
- Delete items from Cosmos DB containers
- Or change barcode prefix in script

## API Endpoints

### Get Driver Manifest
```http
GET /driver/manifest
```

Returns today's active manifest for the driver.

### Mark Delivery Complete
```http
POST /driver/manifest/<manifest_id>/complete/<barcode>
```

Marks a specific delivery as completed.

### Get All Manifests (Admin)
```http
GET /admin/manifests
```

Shows all active manifests for today.

### Create Manifest (Admin)
```http
POST /admin/manifests
Form Data:
  - driver_id: string
  - driver_name: string
  - barcodes: textarea (comma or newline separated)
```

## Customization

### Change Delivery Locations

Edit `SAMPLE_ADDRESSES` in `generate_demo_manifests.py`:

```python
SAMPLE_ADDRESSES = [
    {
        "recipient": "Name",
        "address": "Full Address",
        "phone": "+61 2 XXXX XXXX",
        "priority": "normal|urgent",
        "notes": "Delivery instructions"
    },
    # ... more addresses
]
```

### Add More Drivers

Edit `SAMPLE_DRIVERS` in `generate_demo_manifests.py`:

```python
SAMPLE_DRIVERS = [
    {"id": "driver-004", "name": "New Driver"},
    # ... more drivers
]
```

### Change Depot Location

Update `.env`:
```
DEPOT_ADDRESS=Your Warehouse Address
```

## Troubleshooting

### "Container not found" Error
Run the setup script first:
```bash
python setup_manifest_container.py
```

### No Manifests Showing
- Check that Flask app is running
- Verify you're using correct driver_id
- Check today's date matches manifest_date

### Route Not Optimizing
- Add `AZURE_MAPS_SUBSCRIPTION_KEY` to `.env`
- Check Azure Maps account is active
- Verify addresses are complete and valid

### Parcels Not Found
- Run `generate_demo_manifests.py` first
- Check barcodes match exactly
- Verify parcels were created successfully

## Production Considerations

Before using in production:

1. **Remove Demo Data**
   - Delete test parcels from database
   - Clear sample manifests

2. **Configure Real Data**
   - Set actual depot address
   - Add Azure Maps subscription key
   - Configure real driver IDs

3. **Security**
   - Add authentication to driver routes
   - Validate driver can only see their own manifests
   - Implement proper error handling

4. **Performance**
   - Enable Cosmos DB indexing
   - Cache route optimizations
   - Implement pagination for large manifest lists

## Support Files

- `setup_manifest_container.py` - Create Cosmos DB container
- `generate_demo_manifests.py` - Generate demo data
- `AZURE_MAPS_SETUP.md` - Azure Maps migration guide
- `MANIFEST_GUIDE.md` - Full feature documentation
