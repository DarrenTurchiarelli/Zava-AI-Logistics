# Identity Verification Agent Skills

## Agent Overview

**Purpose:** Customer identity verification for high-risk cases  
**Type:** Security verification agent  
**Model:** gpt-4o  
**Environment Variable:** `IDENTITY_AGENT_ID`

## Core Capabilities

### 1. Identity Verification
- Customer identity confirmation
- Employment status verification
- Address confirmation
- Contact detail validation

### 2. Risk Mitigation
- High-risk fraud case handling
- Secondary verification requests
- Evidence collection
- Verification result reporting

### 3. Automated Triggers
- Auto-invoked when fraud risk ≥85%
- Triggered by customer service requests
- Manual verification initiation
- Suspicious activity response

## Verification Methods

### Available Verification Types

1. **Identity Documents**
   - Government-issued ID
   - Passport verification
   - Driver's license validation

2. **Employment Verification**
   - Employer contact confirmation
   - Work email validation
   - Employment letter review

3. **Address Verification**
   - Utility bill confirmation
   - Lease agreement review
   - Government correspondence

4. **Contact Verification**
   - Phone number validation
   - Email verification link
   - SMS confirmation codes

## Configuration

### Environment Variables
```bash
# Required
IDENTITY_AGENT_ID=asst_XXX

# Shared (Required)
AZURE_AI_PROJECT_CONNECTION_STRING=host;sub;rg;project
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o
```

### No External Tools
This agent uses reasoning and generates verification requests (no function calling).

## Usage Examples

### Example 1: Automatic Trigger (Fraud ≥85%)
```python
from agents.base import identity_agent

# Called automatically by fraud detection workflow
result = await identity_agent({
    'customer_name': 'John Smith',
    'tracking_number': 'LP123456',
    'verification_request': 'High-risk fraud detected',
    'verification_reason': 'Address change request from suspicious email',
    'risk_score': 87
})
```

### Example 2: Manual Verification Request
```python
result = await identity_agent({
    'customer_name': 'Jane Doe',
    'verification_request': 'Verify employment status',
    'verification_reason': 'Large value parcel delivery',
    'requested_by': 'customer_service'
})
```

### Example 3: Document Verification
```python
result = await identity_agent({
    'customer_name': 'Bob Wilson',
    'verification_request': 'Verify identity with photo ID',
    'verification_reason': 'Address mismatch detected',
    'document_type': 'drivers_license'
})
```

## Response Format

### Standard Response Structure
```json
{
  "success": true,
  "verification_id": "VER-20260317-001",
  "customer_name": "John Smith",
  "verification_type": "identity_document",
  "instructions": "Please provide a clear photo of your driver's license...",
  "submission_method": "Email to verify@zavalogistics.com",
  "expiry": "2026-03-24T10:00:00Z",
  "status": "pending",
  "next_steps": [
    "Customer submits documents",
    "Manual review by security team",
    "Approval/rejection decision",
    "Customer notification"
  ]
}
```

## Workflow Integration

### Fraud Detection → Identity Verification
**Trigger Condition:** Fraud risk score ≥85%

**Workflow File:** `workflows/fraud_to_customer_service.py`

**Process:**
1. Fraud Detection Agent scores risk at 85%+
2. Identity Verification Agent automatically invoked
3. Generates verification request with specific requirements
4. Customer Service Agent sends request to customer
5. Manual review by security team
6. Result logged and actions taken

## Prompt Engineering

### Verification Request Generation

The agent is instructed to:

1. **Assess Risk Level**
   - Understand the fraud scenario
   - Determine appropriate verification level
   - Balance security with customer experience

2. **Generate Clear Instructions**
   - Specify required documents/information
   - Provide submission methods
   - Set reasonable deadlines
   - Explain verification purpose

3. **Consider Context**
   - Customer history
   - Parcel value
   - Delivery urgency
   - Security requirements

4. **Maintain Compliance**
   - GDPR compliance
   - Data privacy regulations
   - Customer rights
   - Documentation requirements

## Integration Points

### Internal Systems
- **Fraud Detection Agent:** Receives high-risk cases
- **Customer Service Agent:** Communicates with customers
- **Parcel Tracking DB:** Logs verification requests and results

### External Systems (Future)
- Identity verification APIs (e.g., ID.me)
- Government ID verification services
- Email/phone validation services

## Verification Levels

### Level 1: Basic Verification (Risk: 70-79%)
- Email confirmation
- Phone number validation
- Basic Q&A

### Level 2: Standard Verification (Risk: 80-89%)
- Photo ID required
- Address proof
- Contact verification

### Level 3: Enhanced Verification (Risk: 90%+)
- Government-issued ID
- Multiple proof points
- Video verification
- Manual security review

## Performance Metrics

### Processing Times
- Verification request generation: < 2 seconds
- Manual review SLA: 24 hours
- Customer response time: 48 hours average

### Success Rates
- Verification completion rate: 78%
- Approval rate: 65% of completed verifications
- False rejection rate: < 2%

## Testing

### Test Scenarios

#### Scenario 1: High-Risk Fraud
```python
result = await identity_agent({
    'customer_name': 'Test User',
    'verification_request': 'High-risk fraud detected',
    'verification_reason': 'Payment fraud attempt',
    'risk_score': 92
})
# Expected: Level 3 verification with multiple requirements
```

#### Scenario 2: Address Mismatch
```python
result = await identity_agent({
    'customer_name': 'Test User',
    'verification_request': 'Verify delivery address',
    'verification_reason': 'Address differs from sender information'
})
# Expected: Level 2 verification with address proof
```

## Known Issues & Considerations

### Customer Experience
- **Balance:** Security vs. convenience
- **Communication:** Clear, non-accusatory language
- **Support:** Provide assistance with verification process

### Manual Review Required
- Agent generates requests, doesn't approve/reject
- Human security team makes final decisions
- Agent provides recommendations only

### Privacy Concerns
- Sensitive documents must be handled securely
- Retention policies must be followed
- Customer consent required

## Troubleshooting

### Agent Not Triggered
```bash
# Check fraud workflow
# Verify agent ID is set
echo $env:IDENTITY_AGENT_ID

# Test workflow
python workflows/fraud_to_customer_service.py
```

### Verification Requests Not Sent
```bash
# Check Customer Service Agent integration
# Verify email/SMS configuration
# Review notification logs
```

## Security Best Practices

### Document Handling
- Secure upload mechanisms
- Encrypted storage
- Automatic expiry/deletion
- Access logging

### Data Protection
- GDPR compliance
- Right to be forgotten
- Data minimization
- Purpose limitation

## Version History

- **v1.1.0** (2025-12): Automated workflow integration
- **v1.0.0** (2025-11): Initial identity verification agent

## Related Documentation

- [AGENTS.md](../../../AGENTS.md) - Complete agent system
- [workflows/fraud_to_customer_service.py](../../../workflows/fraud_to_customer_service.py) - Fraud workflow
- [agents/base.py](../../../agents/base.py) - Agent implementation

---

**Last Updated:** March 17, 2026  
**Maintained By:** Zava Logistics Team
