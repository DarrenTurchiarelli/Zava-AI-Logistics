# Approval Agent Mode Demo Guide

This guide explains how to use the specialized approval demo parcels to demonstrate the AI-powered automatic approval/denial system.

## Overview

The approval demo system creates **11 specialized parcels** with specific characteristics that trigger different approval outcomes:

- ✅ **3 Auto-Approve parcels** - Low risk scenarios that are automatically approved
- ❌ **4 Auto-Deny parcels** - High risk scenarios that are automatically rejected
- ⚠️ **4 Manual Review parcels** - Complex scenarios requiring human judgment

## Quick Start

### 1. Generate Demo Parcels

```bash
# Navigate to the generators directory
cd c:\Workbench\lastmile\utils\generators

# Run the generator
python generate_sample_parcels.py

# Select option 3: Generate APPROVAL DEMO parcels
```

### 2. Configure Agent Mode

1. **Login** to the Zava web app as a depot manager:
   - Username: `depot_mgr`
   - Password: `depot123`

2. **Navigate** to the Approvals page

3. **Enable Agent Mode** and configure settings:
   - **Fraud Risk Thresholds:**
     - Auto-Approve if risk < 10%
     - Auto-Deny if risk > 70%
   - **Value Threshold:** $100 (auto-approve below this amount)
   - **Auto-Approve Options:**
     - ✅ Delivered parcels
     - ✅ Verified sender/recipient
   - **Auto-Deny Options:**
     - ✅ Blacklisted addresses
     - ✅ Duplicate requests
     - ✅ Missing documentation

4. **Select Distribution Centers** to process (or select all)

5. **Click "Process with AI Agent"**

### 3. Observe Results

Watch as the agent automatically processes each approval request with real-time explanations:

```
🤖 AI Agent Processing Approval Requests...

✅ APPROVING: Low risk (5% < 10%), standard value ($25 < $100) from DC: DC-SYD-001
❌ REJECTING: High fraud risk score: 85% (threshold: 70%)
⏭️  SKIPPING: No matching criteria (requires manual review)
```

---

## Demo Scenarios Explained

### ✅ Auto-Approve Scenarios (3 parcels)

#### 1. Low Risk + Low Value Parcel
- **Barcode:** `AP[RANDOM]AA`
- **Fraud Risk:** 5%
- **Value:** $25
- **Description:** "Standard delivery confirmation - Verified sender"
- **Trigger:** Fraud risk < 10% AND value < $100
- **Expected Outcome:** ✅ Auto-approved

#### 2. Delivered Status Confirmation
- **Barcode:** `AP[RANDOM]AB`
- **Fraud Risk:** 8%
- **Value:** $75
- **Status:** Delivered
- **Request Type:** delivery_confirmation
- **Trigger:** Status = "Delivered" AND type = "delivery_confirmation"
- **Expected Outcome:** ✅ Auto-approved

#### 3. Verified Recipient Request
- **Barcode:** `AP[RANDOM]AC`
- **Fraud Risk:** 3%
- **Value:** $95
- **Description:** Contains "Verified recipient"
- **Trigger:** "verified" in description AND low fraud risk
- **Expected Outcome:** ✅ Auto-approved

---

### ❌ Auto-Deny Scenarios (4 parcels)

#### 1. High Fraud Risk
- **Barcode:** `AP[RANDOM]DA`
- **Fraud Risk:** 85% (critical)
- **Value:** $1,500
- **Description:** "Multiple delivery address changes requested in short time"
- **Trigger:** Fraud risk > 70%
- **Expected Outcome:** ❌ Auto-denied with reason: "High fraud risk score: 85%"

#### 2. Blacklisted Address
- **Barcode:** `AP[RANDOM]DB`
- **Fraud Risk:** 45%
- **Value:** $200
- **Description:** Contains "blacklist address - multiple previous fraud incidents"
- **Trigger:** "blacklist" in description
- **Expected Outcome:** ❌ Auto-denied with reason: "Blacklisted address detected"

#### 3. Duplicate Request
- **Barcode:** `AP[RANDOM]DC`
- **Fraud Risk:** 35%
- **Value:** $150
- **Description:** "Duplicate address change request - already processed twice today"
- **Trigger:** "duplicate" in description
- **Expected Outcome:** ❌ Auto-denied with reason: "Duplicate request detected"

#### 4. Missing Documentation
- **Barcode:** `AP[RANDOM]DD`
- **Fraud Risk:** 25%
- **Value:** $3,000
- **Description:** "Damage claim missing required photos and customs documentation"
- **Trigger:** "missing" in description
- **Expected Outcome:** ❌ Auto-denied with reason: "Missing required documentation"

---

### ⚠️ Manual Review Scenarios (4 parcels)

#### 1. Medium Risk + High Value
- **Barcode:** `AP[RANDOM]MA`
- **Fraud Risk:** 45% (medium)
- **Value:** $2,500 (high)
- **Description:** "High value electronics - recipient requests alternative delivery location"
- **Reason for Manual Review:** Risk between thresholds (10-70%) + high value requires human judgment
- **Expected Outcome:** ⏭️ Skipped for manual review

#### 2. Time-Sensitive Medical Delivery
- **Barcode:** `AP[RANDOM]MB`
- **Fraud Risk:** 12%
- **Value:** $1,200
- **Priority:** Critical
- **Description:** "Time-sensitive medical supplies - recipient traveling, requests delivery to clinic"
- **Reason for Manual Review:** Critical medical delivery with complex logistics
- **Expected Outcome:** ⏭️ Skipped for manual review

#### 3. Private Sale Dispute
- **Barcode:** `AP[RANDOM]MC`
- **Fraud Risk:** 38%
- **Value:** $800
- **Description:** "Recipient claims never ordered - private sale dispute"
- **Reason for Manual Review:** Legal dispute requiring investigation
- **Expected Outcome:** ⏭️ Skipped for manual review

#### 4. Lost Package Claim Conflict
- **Barcode:** `AP[RANDOM]MD`
- **Fraud Risk:** 22%
- **Value:** $450
- **Description:** "Recipient claims not received, tracking shows delivered to mail room"
- **Reason for Manual Review:** Conflicting information requires verification
- **Expected Outcome:** ⏭️ Skipped for manual review

---

## Agent Mode Configuration Options

### Fraud Risk Thresholds

| Threshold | Default | Description |
|-----------|---------|-------------|
| **Low Risk** | 10% | Auto-approve if fraud risk below this % |
| **High Risk** | 70% | Auto-deny if fraud risk above this % |
| **Medium Risk** | 10-70% | Requires manual review |

### Value Threshold

- **Default:** $100
- **Purpose:** Auto-approve low-value items below this amount (when combined with low fraud risk)
- **Example:** A $25 parcel with 5% fraud risk = auto-approve

### Auto-Approve Criteria

Enable these to automatically approve parcels that match:

- ✅ **Delivered parcels** - Parcels already delivered requesting delivery confirmation
- ✅ **Verified sender/recipient** - Description contains "verified"

### Auto-Deny Criteria

Enable these to automatically reject parcels that match:

- ✅ **Blacklisted addresses** - Description contains "blacklist"
- ✅ **Duplicate requests** - Description contains "duplicate"
- ✅ **Missing documentation** - Description contains "missing"

---

## Demo Walkthrough Script

Use this script when presenting the approval agent mode:

### Introduction (2 minutes)
*"Today I'll demonstrate our AI-powered approval agent that can automatically process routine approval requests, allowing depot managers to focus on complex cases requiring human judgment."*

### Setup (1 minute)
1. Show the Approvals page with pending requests
2. Point out the Agent Mode toggle
3. Explain the configurable thresholds

### Demo: Auto-Approve (2 minutes)
1. Enable Agent Mode with default settings
2. Process approvals
3. Point out the 3 auto-approved cases:
   - *"This $25 parcel has only 5% fraud risk - automatic approval"*
   - *"This was already delivered - routine confirmation approval"*
   - *"Verified recipient contact - approved immediately"*

### Demo: Auto-Deny (2 minutes)
1. Show the 4 auto-denied cases:
   - *"85% fraud risk - automatically blocked for security"*
   - *"Blacklisted address with fraud history - denied"*
   - *"Duplicate suspicious request - denied"*
   - *"Missing required documentation - denied pending completion"*

### Demo: Manual Review (2 minutes)
1. Show the 4 cases flagged for human review:
   - *"$2,500 electronics with medium risk - needs your judgment"*
   - *"Critical medical delivery with complex logistics - escalated to you"*
   - *"Legal dispute requiring investigation - human expertise needed"*
   - *"Conflicting tracking information - requires verification"*

### Conclusion (1 minute)
*"The agent processed 11 requests in seconds: 3 routine approvals, 4 clear denials, and 4 complex cases escalated to human experts. This allows depot managers to handle 3x more volume while ensuring quality decisions."*

---

## Advanced Configuration

### Custom Fraud Risk Thresholds

Adjust thresholds based on your organization's risk tolerance:

#### Conservative (Low risk tolerance)
```
Low Risk:  < 5%
High Risk: > 50%
Value:     < $50
```
Result: More manual reviews, fewer automatic decisions

#### Balanced (Recommended)
```
Low Risk:  < 10%
High Risk: > 70%
Value:     < $100
```
Result: Optimal balance of automation and oversight

#### Aggressive (High automation)
```
Low Risk:  < 20%
High Risk: > 85%
Value:     < $200
```
Result: Maximum automation, minimum manual reviews

### Distribution Center Filtering

You can process approvals for specific DCs only:

```
Select DC: DC-SYD-001, DC-MEL-001
Result: Only processes parcels from Sydney and Melbourne DCs
```

This is useful for:
- Regional managers overseeing specific locations
- Testing agent mode on a subset before full rollout
- Handling DC-specific policies or constraints

---

## Troubleshooting

### Issue: No approvals processed
**Cause:** No pending approvals in database  
**Solution:** Run option 3 in generate_sample_parcels.py to create demo data

### Issue: All approvals skipped
**Cause:** Thresholds too strict or DC filtering too narrow  
**Solution:** Adjust thresholds or select "All DCs"

### Issue: Wrong outcomes
**Cause:** Agent configuration doesn't match demo expectations  
**Solution:** Use recommended settings:
- Low risk: 10%
- High risk: 70%
- Value: $100
- All checkboxes enabled

### Issue: Demo parcels not appearing
**Cause:** Database connection issues  
**Solution:** Verify .env file has correct Cosmos DB credentials

---

## Technical Details

### Parcel Creation Logic

Demo parcels are created with specific characteristics:

```python
# Auto-approve example
parcel["fraud_risk_score"] = 5.0  # Below 10% threshold
parcel["declared_value"] = 25.00   # Below $100 threshold
description = "... Verified sender"  # Verified keyword
```

### Barcode Prefixes

Easy identification of demo parcel types:

- `AP[...]AA-AC` - Auto-Approve parcels
- `AP[...]DA-DD` - Auto-Deny parcels
- `AP[...]MA-MD` - Manual review parcels

### Database Containers

Demo data stored in:
- **Parcels:** `parcels` container
- **Approval Requests:** `delivery_attempts` container (same as production)

---

## Cleanup

To remove demo data after demonstration:

```bash
python generate_sample_parcels.py

# Select option 4: Delete only approval requests
# or
# Select option 5: Delete all test data
```

**Warning:** Option 5 deletes ALL data including regular test parcels!

---

## Integration with Other Demos

### Combine with Fraud Detection Agent
Generate demo parcels → Run fraud analysis → Process approvals  
*Shows complete security workflow*

### Combine with Dispatcher Agent
Create demo parcels → Auto-process approvals → Assign to drivers  
*Shows end-to-end automation*

### Combine with Customer Service Agent
Approval denied → Customer inquiry → Agent explains reason  
*Shows customer communication workflow*

---

## Best Practices

1. **Always explain the thresholds** before running the demo
2. **Show one category at a time** (approve, deny, manual)
3. **Highlight the time savings** compared to manual review
4. **Demonstrate adjustment of thresholds** to show flexibility
5. **Point out the audit trail** in agent comments

---

## Support

For issues or questions:
- Check AGENTS.md for agent configuration details
- See DEMO_GUIDE.md for general demo instructions
- Review app.py lines 1620-1700 for agent mode logic

---

**Last Updated:** March 26, 2026  
**Version:** 1.0  
**Maintained By:** Darren Turchiarelli
