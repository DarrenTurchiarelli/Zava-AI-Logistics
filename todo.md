.# TODO List

## High Priority

### Fix Driver Location Filtering
**Status:** Temporarily Disabled  
**Issue:** Location-based filtering removed all parcels because `destination_city` values don't match driver locations  
**Location:** `app.py` lines 2033-2054

**Steps to fix:**
1. Delete all existing parcels and manifests:
   ```powershell
   cd c:\Workbench\dt_item_scanner
   py Scripts\delete_all_demo_data.py
   ```

2. Regenerate demo data with fixed city extraction:
   ```powershell
   cd utils\generators
   py generate_demo_manifests.py
   ```

3. Re-enable the location filter in `app.py`:
   - Remove the comment block wrapping the filter code (lines 2036-2054)
   - The filter ensures drivers only see parcels for their assigned city

**Why this matters:**
- Improves driver efficiency by showing only relevant deliveries
- Reduces confusion from seeing parcels outside their delivery area
- Matches real-world logistics operations

**Current workaround:** Filter is commented out, all drivers see all parcels in their manifest

---

## Future Enhancements

### Route Optimization
- Verify all three route types (fastest, shortest, safest) use accurate Azure Maps data
- Test "Recalculate Routes" button with real manifest data

### Demo Data Generation
- Consider adding more realistic address variations
- Add edge cases (PO boxes, apartment buildings, rural addresses)
