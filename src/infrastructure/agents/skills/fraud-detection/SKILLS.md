# Fraud Detection Agent Skills

## Agent Overview

**Purpose:** Security threat analysis and scam detection  
**Type:** Security analysis and risk assessment agent  
**Model:** gpt-4o  
**Environment Variable:** `FRAUD_RISK_AGENT_ID`

## Core Capabilities

### 1. Threat Analysis
- Multi-category threat detection
- Phishing attempt identification
- Impersonation detection
- Payment fraud analysis

### 2. Risk Scoring
- 0-100% risk score calculation
- Confidence level assessment
- Evidence-based reasoning
- Threat categorization

### 3. Automated Response
- Workflow triggering at risk thresholds
- Customer notification generation
- Identity verification initiation
- Automatic parcel holds

## Analysis Categories

### Threat Types Detected

1. **Phishing Attempts**
   - Suspicious email domains
   - Fake tracking links
   - Credential harvesting attempts

2. **Impersonation Fraud**
   - Fake delivery driver claims
   - Company impersonation
   - Authority figure scams

3. **Payment Fraud**
   - Unauthorized payment requests
   - COD scams
   - Overpayment schemes

4. **Delivery Scams**
   - Address redirection fraud
   - Parcel interception attempts
   - Fake delivery notifications

## Risk Thresholds & Actions

### Automated Workflow Triggers

| Risk Score | Action | Triggered Agent |
|-----------|--------|-----------------|
| < 30% | Log for monitoring | None |
| 30-69% | Flag for review | None |
| ≥ 70% | Customer notification | Customer Service Agent |
| ≥ 85% | Identity verification | Identity Verification Agent |
| ≥ 90% | Auto-hold parcel | System (Automatic) |

## Configuration

### Environment Variables
```bash
# Required
FRAUD_RISK_AGENT_ID=asst_XXX

# Shared (Required)
AZURE_AI_PROJECT_CONNECTION_STRING=host;sub;rg;project
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o
```

### No External Tools Required
This agent uses reasoning only, no function calling.

## Usage Examples

### Example 1: Analyze Suspicious Message
```python
from agents.fraud import fraud_risk_agent

result = await fraud_risk_agent({
    'message_content': 'Your parcel is held. Click here and pay £50 customs fee immediately.',
    'sender_email': 'noreply@parcel-tracking-uk.xyz',
    'activity_type': 'email'
})

print(result['risk_score'])  # 95
print(result['threat_category'])  # "Payment Fraud, Phishing"
```

### Example 2: Verify Delivery Request
```python
result = await fraud_risk_agent({
    'message_content': 'I am the recipient, please deliver to different address: 123 New St',
    'sender_email': 'unknown@gmail.com',
    'customer_name': 'John Smith',
    'activity_type': 'address_change'
})
```

### Example 3: Check Payment Request
```python
result = await fraud_risk_agent({
    'message_content': 'Driver called asking for credit card to pay delivery fee',
    'activity_type': 'payment_request'
})
```

## Response Format

### Standard Response Structure
```json
{
  "success": true,
  "risk_score": 85,
  "confidence": 0.92,
  "threat_category": "Impersonation, Payment Fraud",
  "reasoning": "Multiple red flags detected...",
  "recommended_action": "Initiate identity verification",
  "evidence": [
    "Suspicious domain",
    "Urgent payment demand",
    "No tracking number provided"
  ],
  "workflow_triggered": true,
  "next_agent": "identity_verification"
}
```

## Workflow Integration

### Multi-Agent Workflow
**File:** `workflows/fraud_to_customer_service.py`

**Sequence:**
1. Fraud Detection Agent analyzes activity
2. If risk ≥70%: → Customer Service Agent (warning message)
3. If risk ≥85%: → Identity Verification Agent
4. If risk ≥90%: → Auto-hold parcel + SMS/email notification
5. Complete audit trail logged

**Trigger:**
```python
from workflows.fraud_to_customer_service import fraud_detection_to_customer_service_workflow

result = await fraud_detection_to_customer_service_workflow(
    message_content="Suspicious delivery request",
    customer_name="John Smith",
    customer_email="john@example.com",
    customer_phone="+61400000000"
)
```

## Prompt Engineering

### Analysis Framework

The agent is instructed to:

1. **Identify Red Flags**
   - Suspicious domains
   - Urgent language
   - Payment requests
   - Authority impersonation
   - Unusual timing

2. **Assess Evidence**
   - Multiple indicators
   - Context consistency
   - Known scam patterns
   - Domain reputation

3. **Calculate Risk Score**
   - Severity of threats
   - Number of indicators
   - Potential impact
   - Confidence level

4. **Recommend Actions**
   - Immediate steps
   - Agent escalation
   - Customer notification
   - Security measures

## Integration Points

### Internal Integrations
- **Customer Service Agent:** Sends warnings to customers
- **Identity Verification Agent:** Triggers verification process
- **Parcel Tracking DB:** Logs fraud attempts, holds parcels

### External Integrations (Future)
- Fraud database lookups
- Email domain reputation APIs
- Phone number validation services

## Performance Metrics

### Analysis Speed
- Average analysis time: < 2 seconds
- Batch analysis: < 5 seconds for 10 items

### Accuracy Targets
- False positive rate: < 5%
- Detection rate: > 95% for known patterns
- Confidence threshold: > 80% for auto-actions

## Testing

### Test Cases

#### Low Risk (< 30%)
```python
result = await fraud_risk_agent({
    'message_content': 'When will my parcel arrive?',
    'sender_email': 'john.smith@gmail.com',
    'activity_type': 'inquiry'
})
# Expected: risk_score < 30
```

#### Medium Risk (30-69%)
```python
result = await fraud_risk_agent({
    'message_content': 'Please change delivery address urgently',
    'sender_email': 'unknown@tempmail.com',
    'activity_type': 'address_change'
})
# Expected: risk_score 40-60
```

#### High Risk (≥ 70%)
```python
result = await fraud_risk_agent({
    'message_content': 'Pay $50 customs fee now or parcel destroyed',
    'sender_email': 'noreply@fake-courier.com',
    'activity_type': 'payment_request'
})
# Expected: risk_score > 70, workflow triggered
```

## Known Patterns

### Common Scam Indicators

1. **Urgent Payment Demands**
   - "Pay within 24 hours"
   - "Immediate action required"
   - "Additional fees due"

2. **Suspicious Domains**
   - Recently registered domains
   - Typosquatting (e.g., "parce1-tracking.com")
   - Free email services for official communication

3. **Authority Impersonation**
   - Claims to be customs/police
   - Demands personal information
   - Threatens legal action

4. **Request Anomalies**
   - Address changes from unknown emails
   - Payment requests via phone/text
   - Credentials requested via email

## Troubleshooting

### Agent Not Responding
```bash
# Verify agent ID
echo $env:FRAUD_RISK_AGENT_ID

# Test Azure connection
python -c "import asyncio; from agents.fraud import fraud_risk_agent; print('Connected')"
```

### Incorrect Risk Scores
```bash
# Review agent instructions in Azure portal
# Check for prompt engineering improvements
# Validate test cases against known patterns
```

### Workflow Not Triggering
```bash
# Check risk threshold logic
# Verify Customer Service Agent connection
# Review workflow logs
```

## Security Considerations

### Data Privacy
- Sensitive information logged securely
- PII anonymized in logs where possible
- Audit trail for compliance

### False Positives
- Manual review process for borderline cases
- Customer feedback mechanism
- Continuous model improvement

## Version History

- **v1.2.0** (2025-12-18): Added workflow automation
- **v1.1.0** (2025-12): Multi-category threat detection
- **v1.0.0** (2025-11): Initial fraud detection agent

## Related Documentation

- [AGENTS.md](../../../AGENTS.md) - Complete agent system
- [workflows/fraud_to_customer_service.py](../../../workflows/fraud_to_customer_service.py) - Workflow implementation
- [agents/fraud.py](../../../agents/fraud.py) - Agent implementation

---

**Last Updated:** March 17, 2026  
**Maintained By:** Zava Logistics Team
