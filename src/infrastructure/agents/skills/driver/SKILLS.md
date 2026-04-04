# Driver Agent Skills

## Agent Overview

**Purpose:** Real-time driver assistance and delivery support  
**Type:** Operational support agent for delivery drivers  
**Model:** gpt-4o  
**Environment Variable:** `DRIVER_AGENT_ID`

## Core Capabilities

### 1. Route Guidance
- Turn-by-turn navigation assistance
- Optimal stop sequence recommendations
- Traffic and road condition alerts
- Parking and access point suggestions

### 2. Parcel Information
- Display special handling instructions
- Show recipient contact details
- Indicate signature requirements
- Flag high-value or fragile items

### 3. Delivery Support
- Provide access codes and gate instructions
- Show safe drop locations
- Display customer delivery preferences
- Alert to delivery time windows

### 4. Issue Handling
- Guide through failed delivery process
- Help with customer contact
- Document delivery exceptions
- Support problem resolution

## Configuration

### Environment Variables
```bash
# Required
DRIVER_AGENT_ID=asst_XXX

# Shared (Required)
AZURE_AI_PROJECT_CONNECTION_STRING=host;sub;rg;project
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o
```

### No External Tools
This agent uses reasoning and provides guidance (no function calling).

## Usage Examples

### Example 1: Get Delivery Instructions
```python
from agents.base import driver_agent

result = await driver_agent({
    'action': 'get_delivery_info',
    'tracking_number': 'LP123456'
})

print(result['instructions'])
# "Apartment 5B - Use rear entrance. Gate code: 1234. 
#  Safe drop: Behind pot plant on balcony if no answer."
```

### Example 2: Report Delivery Exception
```python
result = await driver_agent({
    'action': 'report_exception',
    'tracking_number': 'LP789012',
    'exception_type': 'customer_not_home',
    'details': 'No answer at door, mailbox full'
})

print(result['next_steps'])
# "1. Take photo of door
#  2. Leave calling card
#  3. Mark as delivery attempted
#  4. Parcel will be redelivered tomorrow"
```

### Example 3: Get Next Stop Information
```python
result = await driver_agent({
    'action': 'next_stop',
    'driver_id': 'driver-001',
    'current_stop': 3
})

print(result['next_delivery'])
# "Stop 4 of 15
#  Address: 42 Park Ave, Sydney NSW 2000
#  Recipient: Jane Smith
#  ETA: 10:45 AM
#  Special: Signature required, fragile"
```

### Example 4: Get Access Instructions
```python
result = await driver_agent({
    'action': 'access_help',
    'address': '123 Security Building, Sydney'
})

print(result['access_instructions'])
# "Secure building - Intercom #15
#  After hours: Call customer 0400-XXX-XXX
#  No safe drop authorized for this building"
```

## Response Format

### Parcel Information Response
```json
{
  "success": true,
  "tracking_number": "LP123456",
  "recipient": {
    "name": "John Smith",
    "phone": "+61400123456",
    "address": "15 George St, Sydney NSW 2000"
  },
  "delivery_instructions": {
    "access_code": "1234",
    "gate_info": "Use rear entrance",
    "safe_drop": "Behind pot plant on balcony",
    "time_window": "10:00-12:00",
    "signature_required": false
  },
  "parcel_details": {
    "weight_kg": 2.5,
    "dimensions": "30x20x15cm",
    "fragile": false,
    "service_type": "standard"
  },
  "special_notes": "Customer prefers morning delivery"
}
```

### Exception Report Response
```json
{
  "success": true,
  "exception_id": "EXC-20260318-001",
  "tracking_number": "LP123456",
  "exception_type": "customer_not_home",
  "next_steps": [
    "Take photo of door/building",
    "Leave calling card with details",
    "Mark delivery as attempted",
    "Update parcel status in system"
  ],
  "rescheduled_date": "2026-03-19",
  "customer_notified": true
}
```

## Delivery Status Updates

### Status Types Drivers Can Set

| Status | When to Use | Requirements |
|--------|-------------|--------------|
| **Out for Delivery** | Picked up parcel from depot | Route started |
| **Delivery Attempted** | Customer unavailable or access issue | Photo, calling card |
| **Delivered** | Successfully delivered | Photo or signature |
| **Returned to Depot** | Unable to deliver, bringing back | Exception reason |

## Special Situations

### Customer Not Home
**Actions:**
1. Check for safe drop authorization
2. Leave calling card if no safe drop
3. Take photo of door/location
4. Contact customer if phone provided
5. Mark as attempted delivery
6. Return to depot or reschedule

### Access Issues
**Solutions:**
- Check special instructions for access codes
- Use intercom system
- Call customer for entry
- Contact building manager/security
- Document issue for office follow-up

### Damaged Parcel
**Procedure:**
1. Take photos of damage from multiple anglesError: the body array must not be empty
