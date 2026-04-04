# Dispatcher Agent Skills

## Agent Overview

**Purpose:** Intelligent parcel-to-driver assignment  
**Type:** Operations optimization agent  
**Model:** gpt-4o  
**Environment Variable:** `DISPATCHER_AGENT_ID`

## Core Capabilities

### 1. Driver Assignment
- Geographic clustering
- Workload balancing
- Capacity optimization
- Priority-based distribution

### 2. Route Planning Support
- Delivery area analysis
- Distance calculations
- Stop sequencing
- Time window consideration

### 3. Workload Management
- Driver capacity tracking
- Overload prevention
- Balanced distribution
- Performance monitoring

### 4. Priority Handling
- Express delivery prioritization
- Time-sensitive parcels
- High-value shipments
- Special handling requirements

## Assignment Strategies

### Geographic Clustering
- Group parcels by delivery area
- Minimize travel distance
- Optimize delivery density
- Reduce fuel consumption

### Workload Balancing
- Even distribution across drivers
- Consider existing assignments
- Account for driver availability
- Respect capacity limits

### Priority-Based Assignment
- Express parcels assigned first
- Time-sensitive deliveries prioritized
- Standard parcels filled around priorities
- Balanced with efficiency

## Configuration

### Environment Variables
```bash
# Required
DISPATCHER_AGENT_ID=asst_XXX

# Shared (Required)
AZURE_AI_PROJECT_CONNECTION_STRING=host;sub;rg;project
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o

# Optional (Route Optimization)
AZURE_MAPS_SUBSCRIPTION_KEY=your-key
```

### External Integrations
- **Azure Maps API:** Distance calculations and route optimization
- **Cosmos DB:** Driver and parcel data
- **Manifest Generation:** Creates driver manifests

## Usage Examples

### Example 1: Auto-Assign All Unassigned Parcels
```python
from agents.base import dispatcher_agent

result = await dispatcher_agent({
    'action': 'auto_assign',
    'location': 'Sydney NSW',
    'date': '2026-03-17'
})

print(result['assignments'])
# {
#   'driver-001': ['LP123456', 'LP123457', ...],
#   'driver-002': ['LP789012', 'LP789013', ...],
#   ...
# }
```

### Example 2: Assign Specific Parcels
```python
result = await dispatcher_agent({
    'action': 'assign_parcels',
    'tracking_numbers': ['LP123456', 'LP123457'],
    'location': 'Melbourne VIC',
    'optimize_for': 'distance'
})
```

### Example 3: Balance Existing Workload
```python
result = await dispatcher_agent({
    'action': 'rebalance',
    'drivers': ['driver-001', 'driver-002', 'driver-003'],
    'location': 'Brisbane QLD'
})
```

## Response Format

### Standard Response Structure
```json
{
  "success": true,
  "total_parcels": 45,
  "total_drivers": 3,
  "assignments": {
    "driver-001": {
      "parcels": ["LP123456", "LP123457"],
      "count": 15,
      "area": "Sydney CBD",
      "estimated_distance_km": 32,
      "estimated_time_hours": 4.5
    },
    "driver-002": {
      "parcels": ["LP789012", "LP789013"],
      "count": 15,
      "area": "Eastern Suburbs",
      "estimated_distance_km": 28,
      "estimated_time_hours": 4.2
    },
    "driver-003": {
      "parcels": ["LP456789"],
      "count": 15,
      "area": "Inner West",
      "estimated_distance_km": 25,
      "estimated_time_hours": 3.8
    }
  },
  "unassigned": [],
  "reasoning": "Balanced by geographic clusters and workload capacity",
  "optimization_score": 0.89
}
```

## Integration Points

### Web Application
- **Route:** `/admin/manifests` → AI Auto-Assign button
- **File:** `logistics_admin.py` (Auto-assign endpoint)
- **Frontend:** `templates/admin_manifests.html`

### Manifest Generation
- **File:** `agents/manifest.py`
- **Process:** Dispatcher assigns → Manifest generator creates driver sheets
- **Output:** PDF manifests with routes and parcel details

### Azure Maps Integration
- **File:** `services/maps.py`
- **Functionality:** Distance calculations, route optimization
- **API:** Azure Maps Route API

## Assignment Algorithm

### Step-by-Step Process

1. **Data Collection**
   - Fetch unassigned parcels for location/date
   - Get available drivers and current workloads
   - Load capacity constraints

2. **Geographic Analysis**
   - Group parcels by postcode/suburb
   - Identify delivery clusters
   - Calculate cluster centroids

3. **Priority Sorting**
   - Separate express/priority parcels
   - Assign time-sensitive items first
   - Fill remaining capacity with standard parcels

4. **Driver Assignment**
   - Match clusters to drivers
   - Balance workload across team
   - Optimize for distance/time

5. **Validation**
   - Check capacity limits
   - Verify service type compatibility
   - Confirm no conflicts

6. **Optimization**
   - Fine-tune assignments
   - Swap parcels if needed
   - Maximize efficiency score

## Prompt Engineering

### Key Instructions

The agent is instructed to:

1. **Understand Constraints**
   - Driver capacity limits (typically 15-25 parcels)
   - Working hours (8-hour shifts)
   - Service type requirements
   - Vehicle capacity

2. **Optimize Intelligently**
   - Minimize total distance
   - Balance workloads fairly
   - Respect priority levels
   - Consider traffic patterns

3. **Explain Reasoning**
   - Document assignment logic
   - Provide optimization metrics
   - Flag potential issues
   - Suggest improvements

4. **Handle Edge Cases**
   - Insufficient drivers for workload
   - Extreme distances
   - Special handling requirements
   - Time window conflicts

## Performance Metrics

### Optimization Goals
- Average distance per driver: < 35km
- Workload balance variance: < 15%
- Express delivery success rate: > 98%
- Assignment processing time: < 10 seconds

### Success Indicators
- Driver utilization: 80-95%
- On-time delivery rate: > 95%
- Fuel efficiency improvement: 20% vs manual
- Customer satisfaction: > 4.5/5

## Testing

### Test Scenarios

#### Scenario 1: Small Workload (10 parcels, 2 drivers)
```python
result = await dispatcher_agent({
    'action': 'auto_assign',
    'location': 'Sydney NSW',
    'parcel_count': 10
})
# Expected: Balanced 5-5 split
```

#### Scenario 2: High Priority Mix
```python
result = await dispatcher_agent({
    'action': 'auto_assign',
    'location': 'Melbourne VIC',
    'include_express': True
})
# Expected: Express parcels assigned first, evenly distributed
```

#### Scenario 3: Geographic Clustering
```python
result = await dispatcher_agent({
    'action': 'auto_assign',
    'location': 'Brisbane QLD',
    'optimize_for': 'distance'
})
# Expected: Parcels grouped by suburb/area
```

## Known Issues & Considerations

### Azure Maps Dependency
- Requires valid subscription key
- Falls back to simple postcode clustering if unavailable
- Rate limits may apply for large batches

### Manual Override
- System allows manual reassignment
- Agent suggestions are recommendations
- Final decision rests with dispatch manager

### Real-Time Updates
- Assignments based on snapshot in time
- Driver availability may change
- Parcels may be added after assignment

## Troubleshooting

### Agent Not Assigning
```bash
# Check agent ID
echo $env:DISPATCHER_AGENT_ID

# Test query
python -c "import asyncio; from agents.base import dispatcher_agent; print('Connected')"

# Verify parcels exist
python Scripts/check_current_data.py
```

### Poor Assignment Quality
```bash
# Check Azure Maps integration
python services/maps.py

# Verify parcel geolocation data
# Review agent prompt for optimization instructions
```

### Assignment Failures
```bash
# Check driver capacity constraints
# Verify Cosmos DB connectivity
# Review error logs in Azure portal
```

## Best Practices

### For Administrators
1. Run auto-assign early in the day
2. Review assignments before finalizing
3. Allow drivers to provide feedback
4. Adjust constraints based on performance

### For Developers
1. Cache Azure Maps results to reduce API calls
2. Batch process assignments for efficiency
3. Log optimization metrics for analysis
4. Monitor agent performance and adjust prompts

## Version History

- **v1.2.0** (2025-12-18): Added geographic clustering
- **v1.1.0** (2025-12): Integrated with Azure Maps
- **v1.0.0** (2025-11): Initial dispatcher agent

## Related Documentation

- [AGENTS.md](../../../AGENTS.md) - Complete agent system
- [Guides/DISPATCHER_AGENT_GUIDE.md](../../../Guides/DISPATCHER_AGENT_GUIDE.md) - Detailed guide
- [agents/manifest.py](../../../agents/manifest.py) - Manifest generation
- [services/maps.py](../../../services/maps.py) - Route optimization

---

**Last Updated:** March 17, 2026  
**Maintained By:** Zava Logistics Team
