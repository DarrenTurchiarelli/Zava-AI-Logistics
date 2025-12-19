# UI Integration Testing Guide

## Testing Address Intelligence (User-Facing)

### Test 1: Valid Address with AI Verification
**Steps:**
1. Start the application: `py app.py`
2. Navigate to: **Parcels → Register New Parcel**
3. Fill in the **Destination Address** field with:
   ```
   123 George Street, Sydney NSW 2000
   ```
4. Wait for validation to complete

**Expected Results:**
- ✅ Badge: "Valid Address" (green)
- 🤖 Badge: "AI Verified" (blue)
- Confidence score shown (e.g., "92% confidence")
- No warnings or complications
- Address auto-formatted if needed

---

### Test 2: Address with Typo Detection
**Steps:**
1. In the registration form, enter:
   ```
   45 Collins Street, Mellbourne VIC 3000
   ```
   (Note the typo: "Mellbourne" instead of "Melbourne")
2. Wait for validation

**Expected Results:**
- ⚠️ Warning box appears: "Possible typo detected. Did you mean: 45 Collins Street, Melbourne VIC 3000?"
- 🔵 Button: "Use Suggested Address"
- Clicking the button auto-corrects the address
- Re-validation shows "Valid Address" after correction

---

### Test 3: Delivery Complication Detection
**Steps:**
1. Enter a multi-tenant building address:
   ```
   100 Market Street, Sydney NSW 2000
   ```
2. Wait for validation

**Expected Results:**
- ✅ "Valid Address" badge
- ℹ️ Blue info box: "Delivery Notes:"
  - "Multi-tenant building - unit number recommended"
  - "Signature may be required"
- 💡 Green recommendation box showing suggestions

---

### Test 4: Rural/Remote Address Warning
**Steps:**
1. Enter a rural address:
   ```
   123 Outback Road, Bourke NSW 2840
   ```
2. Wait for validation

**Expected Results:**
- ✅ "Valid Address" badge (may still be valid)
- ⚠️ Complications shown:
  - "Remote/rural area delivery"
  - "Extended delivery time expected"
- Recommendations for service type upgrade

---

### Test 5: Incomplete Address Rejection
**Steps:**
1. Enter an incomplete address:
   ```
   Queen Street, Brisbane
   ```
   (Missing street number and postcode)
2. Wait for validation

**Expected Results:**
- ❌ "Invalid Address" badge (red)
- 🔴 Error box with warnings:
  - "Missing street number"
  - "Missing postcode"
  - "Address incomplete"

---

### Test 6: Fallback to Maps-Only (AI Unavailable)
**Steps:**
1. If Azure AI agents are not configured or unavailable
2. Enter any valid address:
   ```
   567 Bourke Street, Melbourne VIC 3000
   ```

**Expected Results:**
- ✅ "Valid Address" badge
- ⚠️ Small note: "Address validated (Maps only - AI unavailable)"
- No AI-powered features (typo detection, complications, recommendations)
- Basic validation still works via Azure Maps

---

## Testing Exception Resolution (Backend)

Since exception resolution happens automatically during delivery failures, you can test it programmatically:

### Test 1: Run the Test Script
```powershell
# From the Scripts directory
cd C:\Workbench\dt_item_scanner\Scripts
python test_exception_resolution.py
```

**Expected Output:**
- 8 test scenarios executed
- Each shows:
  - Recommended action
  - Confidence score
  - Auto-executable status
  - Customer message
  - Resolution time
- All tests should PASS ✅

---

### Test 2: Create a Real Exception Scenario
**Steps:**
1. Create a parcel via the UI
2. Assign it to a driver manifest
3. Mark delivery as failed with reason "Customer not home"
4. Check the approval/exception queue

**Expected Results:**
- System analyzes the exception
- Recommends action (e.g., "Auto Reschedule" or "Safe Place")
- Shows confidence score
- If confidence > 75%, auto-executes
- Customer receives personalized message

---

## Manual Integration Tests

### Test 1: End-to-End Parcel Registration
**Steps:**
1. Navigate to: **Parcels → Register New Parcel**
2. Fill in ALL fields:
   - **Sender Information**: Valid address
   - **Recipient Information**: Valid address (test with typo first)
   - **Parcel Details**: Weight, dimensions, value
   - **Service Type**: Express
3. Click "Register Parcel"

**Expected Results:**
- Address validation works during form fill
- AI detects and corrects typos
- Shows delivery complications if any
- Parcel registers successfully
- Can track the parcel afterward

---

### Test 2: Camera Scanner with Address Intelligence
**Steps:**
1. Navigate to: **Camera Scanner**
2. Take photo of shipping label
3. OCR extracts address
4. Address auto-populates in registration form

**Expected Results:**
- Address extracted from image
- AI validates the extracted address
- Shows typo corrections if OCR made mistakes
- User can accept or edit before submission

---

### Test 3: Existing Functionality Regression Tests

#### Basic Parcel Tracking (Should Still Work)
1. Navigate to: **Track Parcel**
2. Enter existing tracking number
3. View tracking history

**Expected:** Tracking works normally, no errors

#### Manifest Generation (Should Still Work)
1. Navigate to: **Admin → Generate Manifest**
2. Select driver and DC
3. Generate manifest

**Expected:** Route optimization works, no errors

#### Customer Service Chatbot (Should Still Work)
1. Navigate to: **Customer Service**
2. Ask: "Track parcel DT12345"
3. Get response

**Expected:** Chatbot responds correctly

#### Fraud Detection (Should Still Work)
1. Navigate to: **Report Fraud**
2. Submit suspicious message
3. Get risk analysis

**Expected:** Fraud agent analyzes correctly

---

## Performance Testing

### Test 1: Address Validation Speed
**Measure:** Time from address entry to validation result
**Expected:** < 3 seconds with AI, < 1 second with Maps fallback

### Test 2: Batch Validation
**Test:** Register 10 parcels in quick succession
**Expected:** All validate correctly, no timeout errors

---

## Error Handling Tests

### Test 1: AI Agent Timeout
**Simulate:** Azure AI Foundry agents slow or unavailable
**Expected:** Falls back to Azure Maps validation within 5 seconds

### Test 2: Invalid Azure AI Configuration
**Simulate:** Wrong agent ID in environment variables
**Expected:** 
- Shows "AI unavailable" message
- Falls back to Maps-only validation
- No application crash

### Test 3: Network Error During Validation
**Simulate:** Disconnect network while validating
**Expected:**
- Graceful error message
- "Validation unavailable" badge
- User can still submit (with warning)

---

## Browser Console Check

While testing the UI, open browser console (F12) and check for:

### ✅ No Errors Should Appear:
- No JavaScript errors
- No 500 server errors
- No uncaught exceptions

### ℹ️ Expected Console Messages:
- "Address validation: AI-powered result received"
- "Confidence: 92%"
- Debug info if DEBUG_MODE=true

---

## Automated Test Execution

### Run All Tests
```powershell
# Address Intelligence Tests
python Scripts\test_address_intelligence.py

# Exception Resolution Tests  
python Scripts\test_exception_resolution.py
```

### Expected Exit Codes
- **0** = All tests passed ✅
- **1** = Some tests failed ❌

---

## Rollback Plan (If Tests Fail)

If any critical functionality is broken:

1. **Revert Address Intelligence:**
   ```powershell
   git checkout main -- app.py
   git checkout main -- agents/base.py
   git checkout main -- templates/register_parcel.html
   ```

2. **Revert Exception Resolution:**
   ```powershell
   git checkout main -- logistics_ai.py
   ```

3. **Restart Application:**
   ```powershell
   py app.py
   ```

---

## Success Criteria

### ✅ All Tests Pass When:
1. **Address Intelligence:**
   - Valid addresses show green badge + AI verified badge
   - Typos detected and suggestions offered
   - Delivery complications predicted correctly
   - Recommendations shown when relevant
   - Fallback to Maps works when AI unavailable

2. **Exception Resolution:**
   - 8/8 test scenarios pass
   - Confidence scores reasonable (70%+)
   - Customer messages personalized
   - Auto-executable decisions make sense
   - Fallback rules work when AI unavailable

3. **Existing Functionality:**
   - Parcel tracking works
   - Manifest generation works
   - Chatbot works
   - Fraud detection works
   - No new errors in logs

4. **Performance:**
   - Address validation < 3 seconds
   - No application crashes
   - Graceful degradation when AI unavailable

---

## Troubleshooting Common Issues

### Issue: "AI agent unavailable" always shown
**Solution:** Check Azure AI Foundry environment variables:
```powershell
# Verify these are set correctly
echo $env:AZURE_AI_PROJECT_ENDPOINT
echo $env:PARCEL_INTAKE_AGENT_ID
echo $env:SORTING_FACILITY_AGENT_ID
```

### Issue: Validation takes too long (>5 seconds)
**Solution:** 
- Check network connection to Azure
- Verify Azure CLI authentication: `az account show`
- Enable DEBUG_MODE to see where delay occurs

### Issue: Address suggestions not showing
**Solution:**
- Check browser console for JavaScript errors
- Verify `/api/validate-address` endpoint returns data
- Test with: `curl -X POST http://localhost:5000/api/validate-address`

---

## Next Steps After Testing

1. ✅ Document any bugs found
2. ✅ Test on production-like environment
3. ✅ Load test with multiple users
4. ✅ Monitor AI agent costs/usage
5. ✅ Gather user feedback on AI features
