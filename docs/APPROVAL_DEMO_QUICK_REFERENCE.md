# Approval Demo Quick Reference Card

## 🚀 Quick Start
```bash
cd c:\Workbench\lastmile\utils\generators
python generate_sample_parcels.py
# Select option 3: Generate APPROVAL DEMO parcels
```

## 📊 Demo Parcels Overview

| Category | Count | Outcome |
|----------|-------|---------|
| ✅ Auto-Approve | 3 | Automatically approved |
| ❌ Auto-Deny | 4 | Automatically rejected |
| ⚠️ Manual Review | 4 | Flagged for human review |
| **TOTAL** | **11** | **Complete demo set** |

## ⚙️ Recommended Settings

| Setting | Value | Purpose |
|---------|-------|---------|
| Low Risk Threshold | 10% | Auto-approve below |
| High Risk Threshold | 70% | Auto-deny above |
| Value Threshold | $100 | Auto-approve below (with low risk) |
| All Checkboxes | ✅ Enabled | Enable all auto-approve/deny rules |

## 📝 Talking Points by Category

### ✅ Auto-Approve (3 parcels)
- **Low risk + low value** → "5% risk, $25 value - safe to approve"
- **Delivered + confirmation** → "Already delivered - routine approval"  
- **Verified recipient** → "Customer verified - approved immediately"

### ❌ Auto-Deny (4 parcels)
- **High fraud risk (85%)** → "Security risk - automatic block"
- **Blacklisted address** → "Known fraud location - denied"
- **Duplicate request** → "Suspicious repeat request - denied"
- **Missing docs** → "Incomplete - pending documentation"

### ⚠️ Manual Review (4 parcels)
- **Medium risk + high value** → "$2,500 electronics - needs your judgment"
- **Medical emergency** → "Critical delivery - complex logistics"
- **Legal dispute** → "Private sale conflict - investigation needed"
- **Tracking conflict** → "Claims not received but tracking shows delivered"

## 🎯 Demo Flow (10 minutes)

| Time | Step | Action |
|------|------|--------|
| 0:00 | Intro | Show Approvals page |
| 1:00 | Setup | Enable Agent Mode + configure |
| 2:00 | Run | Click "Process with AI Agent" |
| 3:00 | Auto-Approve | Explain 3 approved cases |
| 5:00 | Auto-Deny | Explain 4 denied cases |
| 7:00 | Manual Review | Explain 4 escalated cases |
| 9:00 | Summary | "11 cases in seconds - 3x efficiency" |

## 🔍 Expected Results

```
🤖 AI Agent Processing Approval Requests...
✅ Approved: 3
❌ Rejected: 4
⏭️  Skipped: 4 (manual review)
```

## 🎨 Barcode Patterns (for tracking)

- `AP[...]AA-AC` = Auto-Approve parcels
- `AP[...]DA-DD` = Auto-Deny parcels  
- `AP[...]MA-MD` = Manual review parcels

## 💡 Key Messages

1. **Speed:** "Processes 11 requests in seconds vs. hours manually"
2. **Consistency:** "Same decision criteria every time - no human error"
3. **Focus:** "Frees managers for complex cases requiring expertise"
4. **Audit:** "Every decision logged with AI explanation"
5. **Flexibility:** "Thresholds adjustable to your risk tolerance"

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| No approvals | Generate demo data first |
| All skipped | Lower thresholds or select "All DCs" |
| Wrong outcomes | Check settings match recommended |

## 🧹 Cleanup
```bash
python generate_sample_parcels.py
# Option 4: Delete only approval requests
```

---
**Print this card for easy reference during demos!**
