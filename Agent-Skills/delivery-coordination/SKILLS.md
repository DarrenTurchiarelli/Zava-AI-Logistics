# Delivery Coordination Agent Skills

## Agent Overview

**Purpose:** Multi-stop delivery sequencing and customer notifications  
**Type:** Delivery operations agent  
**Model:** gpt-4o  
**Environment Variable:** `DELIVERY_COORDINATION_AGENT_ID`

## Core Capabilities

### 1. Delivery Route Sequencing
- Optimal stop order determination
- Multi-parcel route planning
- Time window management
- Traffic pattern consideration

### 2. Customer Notifications
- Automated SMS/email alerts
- Delivery time window updates
- Driver arrival notifications
- Delivery confirmation messages

### 3. Dynamic Route Adjustments
- Real-time route re-optimization
- Failed delivery handling
- Priority insertion
- Emergency rerouting

### 4. Time Window Management
- Delivery ETA calculations
- Time slot coordination
- Late delivery alerts
- Proactive customer updates

## Configuration

### Environment Variables
```bash
# Required
DELIVERY_COORDINATION_AGENT_ID=asst_XXX

# Shared (Required)
AZURE_AI_PROJECT_CONNECTION_STRING=host;sub;rg;project
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o

# Optional (Enhanced Features)
AZURE_MAPS_SUBSCRIPTION_KEY=your-key  # Route optimization
AZURE_COMMUNICATION_SERVICES_KEY=your-key  # SMS notifications
```

### External Integrations
- **Azure Maps:** Route optimization and ETAs
- **Azure Communication Services:** SMS delivery
- **Email Service:** Delivery notifications

## Usage Examples

### Example 1: Sequence Driver's Deliveries
```python
from agents.base import delivery_coordination_agent

result = await delivery_coordination_agent({
    'action': 'sequence_route',
    'driver_id': 'driver-001',
    'date': '2026-03-17',
    'start_location': 'Sydney Sort, 123 Industrial Rd'
})

print(result['optimized_sequence'])
# [
#   {'stop': 1, 'tracking_number': 'LP123456', 'address': '...', 'eta': '09:15'},
#   {'stop': 2, 'tracking_number': 'LP123457', 'address': '...', 'eta': '09:35'},
#   ...
# ]
```

### Example 2: Calculate Delivery Time Windows
```python
result = await delivery_coordination_agent({
    'action': 'calculate_time_windows',
    'driver_id': 'driver-002',
    'current_stop': 3,
    'remaining_stops': 12
})

print(result['time_windows'])
# {
#   'LP789012': {'earliest': '10:30', 'latest': '11:00'},
#   'LP789013': {'earliest': '11:05', 'latest': '11:35'},
#   ...
# }
```

### Example 3: Send Delivery Notifications
```python
result = await delivery_coordination_agent({
    'action': 'notify_customers',
    'tracking_numbers': ['LP123456', 'LP123457'],
    'notification_type': 'out_for_delivery',
    'estimated_arrival': '10:30-11:00'
})

print(result['notifications_sent'])
# {'sms': 2, 'email': 2}
```

### Example 4: Handle Failed Delivery
```python
result = await delivery_coordination_agent({
    'action': 'handle_failed_delivery',
    'tracking_number': 'LP456789',
    'failure_reason': 'recipient_not_home',
    'driver_id': 'driver-003'
})

print(result['rescheduled_date'])  # '2026-03-18'
print(result['customer_notified'])  # True
```

## Response Format

### Route Sequencing Response
```json
{
  "success": true,
  "driver_id": "driver-001",
  "optimized_sequence": [
    {
      "stop_number": 1,
      "tracking_number": "LP123456",
      "address": "15 George St, Sydney NSW 2000",
      "eta": "09:15",
      "service_time_minutes": 5,
      "distance_from_previous_km": 2.3
    },
    {
      "stop_number": 2,
      "tracking_number": "LP123457",
      "address": "42 Park Ave, Sydney NSW 2000",
      "eta": "09:35",
      "service_time_minutes": 5,
      "distance_from_previous_km": 3.1
    }
  ],
  "total_distance_km": 45.2,
  "estimated_completion_time": "16:30",
  "optimization_score": 0.91
}
```

### Notification Response
```json
{
  "success": true,
  "notifications_sent": {
    "sms": 15,
    "email": 15
  },
  "notification_type": "out_for_delivery",
  "delivery_window": "10:00-12:00",
  "failed": [],
  "timestamp": "2026-03-17T08:45:00Z"
}
```

## Notification Types

### Standard Notifications

1. **Parcel Received**
   - Sent when parcel enters system
   - Tracking number provided
   - Estimated delivery date

2. **Out for Delivery**
   - Morning of delivery day
   - Time window provided
   - Driver contact info

3. **Delivery Attempted**
   - Failed delivery notification
   - Reason for failure
   - Rescheduling options

4. **Delivered**
   - Confirmation with timestamp
   - Proof of delivery photo
   - Recipient name (if signed)

5. **Delayed**
   - Proactive delay notification
   - Updated delivery estimate
   - Reason for delay

## Route Optimization Logic

### Optimization Factors

1. **Geographic Clustering**
   - Group nearby deliveries
   - Minimize backtracking
   - Optimize for distance

2. **Time Windows**
   - Respect customer time preferences
   - Consider business hours
   - Account for access restrictions

3. **Service Priority**
   - Express deliveries first
   - Time-sensitive before standard
   - Special handling requirements

4. **Traffic Patterns**
   - Avoid peak traffic times
   - Use Azure Maps traffic data
   - Dynamic rerouting

### Optimization Algorithm

```
1. Group parcels by geographic cluster
2. Sort by priority (express > standard > economy)
3. Calculate optimal sequence per cluster
4. Merge clusters into efficient route
5. Calculate ETAs for each stop
6. Validate time windows
7. Adjust sequence if conflicts
8. Generate final route
```

## Integration Points

### Driver Mobile App
- Real-time route updates
- Turn-by-turn navigation
- Delivery status updates
- Customer contact info

### Customer Portal
- Track delivery progress
- View driver location
- Update delivery preferences
- Reschedule deliveries

### Web Dashboard
- **Route:** `/delivery/dashboard` (real-time view)
- **File:** `logistics_delivery.py`
- **Frontend:** `templates/delivery_map.html`

## Prompt Engineering

### Coordination Framework

The agent is instructed to:

1. **Optimize Intelligently**
   - Balance distance vs. time
   - Respect customer preferences
   - Consider driver capacity
   - Adapt to real-time changes

2. **Communicate Clearly**
   - Professional notification tone
   - Accurate time windows
   - Helpful contact information
   - Clear next steps

3. **Handle Exceptions**
   - Failed delivery procedures
   - Address issues
   - Special instructions
   - Customer unavailability

4. **Coordinate Proactively**
   - Send timely notifications
   - Alert to delays early
   - Provide accurate ETAs
   - Enable customer choices

## Performance Metrics

### Efficiency Metrics
- Route optimization score: > 0.85
- Average stops per hour: 8-10
- Total distance reduction: 15-25% vs. manual
- Time window adherence: > 95%

### Customer Satisfaction
- Notification delivery rate: > 99%
- Time window accuracy: ±30 minutes, 90%
- First-attempt delivery success: > 85%
- Customer satisfaction score: > 4.5/5

## Testing

### Test Scenarios

#### Small Route (5 stops)
```python
result = await delivery_coordination_agent({
    'action': 'sequence_route',
    'parcels': 5,
    'area': 'Sydney CBD'
})
# Expected: Logical sequence, minimal distance
```

#### Time Window Conflicts
```python
result = await delivery_coordination_agent({
    'action': 'sequence_route',
    'parcels': [
        {'tracking': 'LP001', 'time_window': '09:00-10:00'},
        {'tracking': 'LP002', 'time_window': '09:30-10:30'},  # Overlap
    ]
})
# Expected: Feasible sequence or conflict warning
```

#### Priority Insertion
```python
result = await delivery_coordination_agent({
    'action': 'insert_priority',
    'existing_route': [...],
    'new_parcel': {'tracking': 'LP999', 'priority': 'express'}
})
# Expected: Express parcel inserted early in route
```

## Known Issues & Considerations

### Real-Time Traffic
- Traffic data may be delayed
- Unexpected road closures not reflected immediately
- ETAs are estimates, not guarantees

### Customer Availability
- Notifications don't guarantee customer presence
- Time windows are estimates, not appointments
- Failed deliveries require rescheduling

### Route Rigidity
- Once driver starts, major changes disruptive
- Best optimized before route begins
- Mid-route adjustments should be minimal

## Troubleshooting

### Routes Not Optimized
```bash
# Check Azure Maps integration
python services/maps.py

# Verify parcel addresses are geocoded
# Review optimization algorithm settings
```

### Notifications Not Sending
```bash
# Check Azure Communication Services config
# Verify customer contact details in database
# Review notification logs
```

### Incorrect ETAs
```bash
# Validate traffic data integration
# Check service time estimates
# Review distance calculations
```

## Best Practices

### For Dispatchers
1. Generate routes early in the morning
2. Allow drivers to provide feedback
3. Monitor delivery progress throughout day
4. Adjust for real-world conditions

### For Drivers
1. Follow optimized sequence when practical
2. Report delays immediately
3. Update delivery status in real-time
4. Communicate with customers proactively

### For Developers
1. Cache route calculations to reduce API calls
2. Use batch notification APIs
3. Log all coordination decisions
4. Monitor agent performance metrics

## Future Enhancements

- Real-time driver GPS tracking integration
- Predictive delivery time machine learning
- Customer delivery preference learning
- Automated rescheduling workflows
- Integration with smart home devices

## Version History

- **v1.2.0** (2025-12-18): Added dynamic rerouting
- **v1.1.0** (2025-12): Integrated Azure Maps
- **v1.0.0** (2025-11): Initial delivery coordination agent

## Related Documentation

- [AGENTS.md](../../../AGENTS.md) - Complete agent system
- [agents/base.py](../../../agents/base.py) - Agent implementation
- [services/maps.py](../../../services/maps.py) - Route optimization
- [logistics_delivery.py](../../../logistics_delivery.py) - Delivery operations

---

**Last Updated:** March 17, 2026  
**Maintained By:** Zava Logistics Team
