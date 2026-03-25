# Parcel Intake Agent Skills

## Agent Overview

**Purpose:** New parcel validation and recommendations  
**Type:** Operations support and validation agent  
**Model:** gpt-4o  
**Environment Variable:** `PARCEL_INTAKE_AGENT_ID`

## Core Capabilities

### 1. Service Type Recommendations
- Analyze parcel details
- Suggest appropriate service level
- Consider delivery urgency
- Account for parcel characteristics

### 2. Address Validation
- Verify address completeness
- Flag ambiguous addresses
- Identify delivery complications
- Suggest address corrections

### 3. Delivery Predictions
- Estimate delivery complexity
- Identify potential delays
- Flag special requirements
- Suggest handling instructions

### 4. Weight/Dimension Verification
- Check physical specifications
- Flag unusual measurements
- Recommend packaging improvements
- Verify service compatibility

## Service Type Matrix

### Available Service Types

| Service | Speed | Cost | Use Case |
|---------|-------|------|----------|
| Express | 1-2 days | High | Urgent deliveries |
| Standard | 3-5 days | Medium | General parcels |
| Economy | 5-7 days | Low | Non-urgent items |
| Same-Day | < 12 hours | Premium | Critical deliveries |

### Recommendation Factors
- Delivery deadline
- Parcel value
- Weight/dimensions
- Destination accessibility
- Customer preference

## Configuration

### Environment Variables
```bash
# Required
PARCEL_INTAKE_AGENT_ID=asst_XXX

# Shared (Required)
AZURE_AI_PROJECT_CONNECTION_STRING=host;sub;rg;project
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o
```

### No External Tools
This agent uses reasoning based on provided parcel data.

## Usage Examples

### Example 1: Recommend Service Type
```python
from agents.base import parcel_intake_agent

result = await parcel_intake_agent({
    'tracking_number': 'DT123456',
    'sender_name': 'John Smith',
    'recipient_address': '123 Main St, Sydney NSW 2000',
    'weight_kg': 1.5,
    'dimensions_cm': '30x20x15',
    'requested_service': 'standard',
    'delivery_deadline': '2026-03-20'
})

print(result['recommended_service'])  # 'express'
print(result['reasoning'])
# "Delivery deadline in 3 days requires express service for guaranteed on-time delivery"
```

### Example 2: Validate Address
```python
result = await parcel_intake_agent({
    'tracking_number': 'DT789012',
    'recipient_address': 'Unit 5, George St',  # Incomplete
    'sender_name': 'Jane Doe'
})

print(result['address_issues'])
# ['Missing postcode', 'Missing suburb/city', 'Ambiguous street number']
print(result['suggested_correction'])
# "Please provide complete address: Unit 5, [Building], George St, [Suburb] [State] [Postcode]"
```

### Example 3: Predict Delivery Complications
```python
result = await parcel_intake_agent({
    'tracking_number': 'DT456789',
    'recipient_address': 'Remote Station, 500km North of Alice Springs NT',
    'weight_kg': 25,
    'service_type': 'standard'
})

print(result['predicted_complications'])
# ['Remote location', 'Extended delivery time', 'Potential fuel surcharge']
print(result['recommendations'])
# ['Upgrade to specialty remote delivery service', 'Add 5-7 business days to estimate']
```

## Response Format

### Standard Response Structure
```json
{
  "success": true,
  "tracking_number": "DT123456",
  "validation_status": "approved",
  "recommended_service": "express",
  "service_upgrade_reason": "Delivery deadline requires faster service",
  "address_validation": {
    "valid": true,
    "issues": [],
    "suggestions": []
  },
  "delivery_prediction": {
    "estimated_days": 2,
    "confidence": 0.92,
    "complications": [],
    "special_requirements": []
  },
  "weight_dimension_check": {
    "within_limits": true,
    "service_compatible": true,
    "surcharges": []
  },
  "overall_assessment": "Parcel ready for processing. Recommend express service upgrade.",
  "confidence_score": 0.95
}
```

## Validation Rules

### Address Validation Checks

✅ **Required Components:**
- Street number and name
- Suburb/City
- State
- Postcode

⚠️ **Warning Flags:**
- PO Box without physical address
- Rural/remote locations
- Apartment without unit number
- Common misspellings

❌ **Rejection Criteria:**
- Missing postcode
- Invalid state abbreviation
- Incomplete address

### Weight/Dimension Limits

| Service | Max Weight | Max Dimensions | Notes |
|---------|-----------|----------------|-------|
| Express | 25kg | 100x50x50cm | Surcharge > 20kg |
| Standard | 30kg | 120x60x60cm | Standard rates |
| Economy | 35kg | 150x75x75cm | Heavy item fee applies |

## Integration Points

### Parcel Creation Workflow
1. Customer submits parcel details
2. Parcel Intake Agent validates and recommends
3. System presents recommendations to customer
4. Customer confirms or adjusts service
5. Parcel created in database

### Web Application
- **Route:** `/api/parcels/validate` (POST)
- **File:** `logistics_parcel.py`
- **Frontend:** `templates/store_parcel_intake.html`

## Prompt Engineering

### Analysis Framework

The agent is instructed to:

1. **Evaluate Completeness**
   - Check all required fields
   - Identify missing information
   - Suggest what's needed

2. **Assess Feasibility**
   - Review physical constraints
   - Check service compatibility
   - Identify limitations

3. **Predict Challenges**
   - Analyze delivery complexity
   - Consider geographic factors
   - Flag special requirements

4. **Provide Recommendations**
   - Suggest optimal service
   - Explain reasoning clearly
   - Offer alternatives

5. **Calculate Confidence**
   - Assess data quality
   - Consider edge cases
   - Provide certainty level

## Performance Metrics

### Processing Speed
- Validation time: < 1 second
- Batch validation: < 5 seconds for 20 parcels

### Accuracy Targets
- Service recommendation accuracy: > 95%
- Address validation accuracy: > 98%
- Delivery prediction accuracy: > 85%

## Testing

### Test Cases

#### Valid Parcel - Standard Service
```python
result = await parcel_intake_agent({
    'tracking_number': 'TEST001',
    'recipient_address': '123 Main St, Sydney NSW 2000',
    'weight_kg': 2.5,
    'service_type': 'standard'
})
# Expected: Approved, no issues
```

#### Invalid Address
```python
result = await parcel_intake_agent({
    'tracking_number': 'TEST002',
    'recipient_address': 'George St',  # Incomplete
    'weight_kg': 1.0
})
# Expected: Address validation failure with suggestions
```

#### Service Upgrade Needed
```python
result = await parcel_intake_agent({
    'tracking_number': 'TEST003',
    'recipient_address': '456 Park Ave, Melbourne VIC 3000',
    'weight_kg': 1.5,
    'service_type': 'economy',
    'delivery_deadline': '2026-03-19'  # Tomorrow
})
# Expected: Recommend express service upgrade
```

## Known Issues & Considerations

### Address Data Quality
- Relies on customer-provided information
- No integration with address validation APIs (yet)
- Manual verification may be needed

### Service Cost Not Calculated
- Agent suggests service type only
- Pricing calculated separately
- Cost factors mentioned in recommendations

### Predictive Limitations
- Based on historical patterns
- Cannot account for unforeseen events
- Weather/traffic not considered in real-time

## Troubleshooting

### Agent Not Responding
```bash
# Verify agent ID
echo $env:PARCEL_INTAKE_AGENT_ID

# Test connection
python -c "import asyncio; from agents.base import parcel_intake_agent; print('Connected')"
```

### Incorrect Recommendations
```bash
# Review agent instructions
# Check input data quality
# Validate service type mappings
# Consider prompt engineering improvements
```

## Best Practices

### For Store Staff
1. Provide complete information
2. Review agent recommendations
3. Ask customer for clarification when needed
4. Override if customer preferences differ

### For Integration
1. Validate input data before calling agent
2. Present recommendations clearly to users
3. Log agent decisions for analysis
4. Collect feedback on accuracy

## Future Enhancements

- Integration with Australia Post address validation API
- Real-time delivery time estimates via Azure Maps- Automated pricing calculations
- Machine learning for improved predictions
- Historical data analysis for accuracy improvements

## Version History

- **v1.1.0** (2025-12): Added delivery complication predictions
- **v1.0.0** (2025-11): Initial parcel intake agent

## Related Documentation

- [AGENTS.md](../../../AGENTS.md) - Complete agent system
- [agents/base.py](../../../agents/base.py) - Agent implementation
- [logistics_parcel.py](../../../logistics_parcel.py) - Parcel management

---

**Last Updated:** March 17, 2026  
**Maintained By:** Zava Logistics Team
