# Sorting Facility Agent Skills

## Agent Overview

**Purpose:** Facility capacity monitoring and routing decisions  
**Type:** Operations intelligence agent  
**Model:** gpt-4o  
**Environment Variable:** `SORTING_FACILITY_AGENT_ID`

## Core Capabilities

### 1. Capacity Monitoring
- Real-time facility load tracking
- Capacity threshold alerts
- Processing bottleneck identification
- Overflow prevention

### 2. Routing Decisions
- Facility assignment for incoming parcels
- Load balancing across facilities
- Priority-based routing
- Overflow handling

### 3. Processing Analytics
- Throughput monitoring
- Efficiency scoring
- Delay prediction
- Resource utilization

### 4. Alerts & Recommendations
- Capacity warnings
- Staffing requirements
- Equipment needs
- Process improvements

## Facility Network

### Current Facilities

| Facility | Location | Capacity | Service Area |
|----------|----------|----------|--------------|
| Sydney Sort | Sydney NSW | 5000/day | NSW Metro |
| Melbourne Hub | Melbourne VIC | 4000/day | VIC Metro |
| Brisbane Center | Brisbane QLD | 3500/day | QLD Metro |
| Perth Depot | Perth WA | 2500/day | WA Metro |

### Capacity Thresholds

- **Normal:** < 70% capacity (green)
- **Busy:** 70-85% capacity (yellow)
- **Critical:** 85-95% capacity (orange)
- **Overload:** > 95% capacity (red)

## Configuration

### Environment Variables
```bash
# Required
SORTING_FACILITY_AGENT_ID=asst_XXX

# Shared (Required)
AZURE_AI_PROJECT_CONNECTION_STRING=host;sub;rg;project
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o
```

### No External Tools
This agent uses reasoning based on facility data from Cosmos DB.

## Usage Examples

### Example 1: Check Facility Capacity
```python
from agents.base import sorting_facility_agent

result = await sorting_facility_agent({
    'action': 'check_capacity',
    'facility': 'Sydney Sort',
    'date': '2026-03-17'
})

print(result['current_load'])  # 3450 parcels
print(result['capacity_percent'])  # 69%
print(result['status'])  # 'normal'
```

### Example 2: Route Incoming Parcels
```python
result = await sorting_facility_agent({
    'action': 'route_parcels',
    'incoming_count': 500,
    'destination_state': 'NSW',
    'priority': 'standard'
})

print(result['assigned_facility'])  # 'Sydney Sort'
print(result['reasoning'])
# "Sydney Sort at 69% capacity can handle additional 500 parcels"
```

### Example 3: Predict Bottlenecks
```python
result = await sorting_facility_agent({
    'action': 'predict_bottleneck',
    'facility': 'Melbourne Hub',
    'time_window': 'next_4_hours'
})

print(result['bottleneck_probability'])  # 0.78
print(result['recommendations'])
# ['Add 2 sorters', 'Defer non-priority parcels', 'Alert management']
```

### Example 4: Overflow Handling
```python
result = await sorting_facility_agent({
    'action': 'handle_overflow',
    'facility': 'Brisbane Center',
    'overflow_count': 300
})

print(result['overflow_facility'])  # 'Gold Coast Depot'
print(result['alternate_routing'])
```

## Response Format

### Capacity Check Response
```json
{
  "success": true,
  "facility": "Sydney Sort",
  "date": "2026-03-17",
  "current_load": 3450,
  "capacity": 5000,
  "capacity_percent": 69,
  "status": "normal",
  "available_capacity": 1550,
  "alerts": [],
  "recommendations": ["Continue normal operations"],
  "processing_rate": {
    "parcels_per_hour": 625,
    "efficiency": 0.92
  }
}
```

### Routing Decision Response
```json
{
  "success": true,
  "assigned_facility": "Sydney Sort",
  "alternative_facilities": ["Parramatta Depot"],
  "routing_confidence": 0.95,
  "reasoning": "Primary facility within capacity, optimal for destination",
  "estimated_processing_time": "2 hours",
  "bottleneck_risk": "low"
}
```

## Routing Logic

### Decision Factors

1. **Geographic Proximity**
   - Distance to destination
   - Transport costs
   - Delivery time impact

2. **Current Capacity**
   - Available space
   - Processing capability
   - Staffing levels

3. **Service Priority**
   - Express parcels prioritized
   - Standard parcels balanced
   - Economy parcels flexible

4. **Processing Speed**
   - Current throughput
   - Expected delays
   - Equipment availability

### Routing Algorithm

```
IF destination in primary service area:
  IF primary facility capacity < 85%:
    ROUTE to primary facility
  ELSE IF secondary facility capacity < 70%:
    ROUTE to secondary facility
  ELSE:
    ALERT management, DEFER non-priority parcels
ELSE:
  ROUTE to nearest hub with capacity
```

## Integration Points

### Parcel Processing Flow
1. Parcels arrive at facility
2. Sorting Facility Agent assesses capacity
3. Agent routes to appropriate sorting lines
4. Monitors processing throughput
5. Alerts on bottlenecks
6. Recommends load balancing

### Database Integration
- **Container:** `parcels` (filter by `facility_location`)
- **Queries:** Count by facility and date
- **Updates:** Facility assignment changes

## Prompt Engineering

### Analysis Framework

The agent is instructed to:

1. **Monitor Continuously**
   - Track real-time capacity
   - Identify trends
   - Predict issues early

2. **Optimize Routing**
   - Balance load across network
   - Minimize processing delays
   - Respect service priorities

3. **Alert Proactively**
   - Warn before critical capacity
   - Suggest preventive actions
   - Escalate when needed

4. **Recommend Improvements**
   - Process optimization
   - Resource allocation
   - Efficiency gains

## Performance Metrics

### Facility KPIs
- Processing throughput: > 90% target
- Capacity utilization: 70-85% optimal
- Sorting accuracy: > 99.5%
- Processing time: < 2 hours average

### Network KPIs
- Load balance variance: < 20%
- Overflow incidents: < 5/month
- On-time sortation rate: > 98%

## Testing

### Test Scenarios

#### Normal Capacity
```python
result = await sorting_facility_agent({
    'action': 'check_capacity',
    'facility': 'Sydney Sort',
    'current_parcels': 3000
})
# Expected: status='normal', no alerts
```

#### Near Capacity
```python
result = await sorting_facility_agent({
    'action': 'check_capacity',
    'facility': 'Melbourne Hub',
    'current_parcels': 3600  # 90% of 4000
})
# Expected: status='critical', recommendations for overflow routing
```

#### Overflow Scenario
```python
result = await sorting_facility_agent({
    'action': 'handle_overflow',
    'facility': 'Brisbane Center',
    'current_parcels': 3400,  # 97% capacity
    'incoming_parcels': 300
})
# Expected: overflow routing to alternate facility
```

## Known Issues & Considerations

### Real-Time Data Lag
- Facility counts may be 5-10 minutes delayed
- Agent works with latest available data
- Critical decisions should verify current state

### Manual Overrides
- Facility managers can override routing decisions
- Emergency situations may require manual intervention
- Agent suggestions are recommendations

### Seasonal Variations
- Peak seasons (e.g., holidays) require capacity planning
- Agent should be informed of expected surges
- Temporary capacity expansions may be needed

## Troubleshooting

### Incorrect Capacity Calculations
```bash
# Verify parcel count queries
python parcel_tracking_db.py

# Check facility configuration
# Review date/time filtering logic
```

### Poor Routing Decisions
```bash
# Review agent prompt for routing logic
# Verify facility capacity data
# Check geographic service areas
```

### Agent Not Responding
```bash
# Verify agent ID
echo $env:SORTING_FACILITY_AGENT_ID

# Test connection
python -c "import asyncio; from agents.base import sorting_facility_agent; print('Connected')"
```

## Best Practices

### For Facility Managers
1. Monitor agent recommendations daily
2. Provide feedback on routing quality
3. Update capacity when equipment changes
4. Alert agent to planned downtime

### For Operations
1. Use agent for decision support, not replacement
2. Verify critical routing decisions manually
3. Track agent accuracy over time
4. Adjust prompts based on performance

## Future Enhancements

- Integration with facility management systems
- Predictive analytics for capacity planning
- Automated staff scheduling recommendations
- Equipment maintenance predictions
- Real-time sensor data integration

## Version History

- **v1.1.0** (2025-12): Added overflow handling
- **v1.0.0** (2025-11): Initial sorting facility agent

## Related Documentation

- [AGENTS.md](../../../AGENTS.md) - Complete agent system
- [agents/base.py](../../../agents/base.py) - Agent implementation
- [config/depots.py](../../../config/depots.py) - Facility configuration

---

**Last Updated:** March 17, 2026  
**Maintained By:** Zava Logistics Team
