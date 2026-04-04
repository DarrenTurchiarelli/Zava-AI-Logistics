# Optimization Agent Skills

## Agent Overview

**Purpose:** Network-wide performance analysis and cost reduction  
**Type:** Strategic analytics and optimization agent  
**Model:** gpt-4o  
**Environment Variable:** `OPTIMIZATION_AGENT_ID`

## Core Capabilities

### 1. Performance Analysis
- Network-wide metrics monitoring
- Efficiency trend analysis
- Bottleneck identification
- Comparative performance tracking

### 2. Cost Reduction Insights
- Operational cost analysis
- Resource utilization optimization
- Process improvement identification
- ROI calculations

### 3. Predictive Analytics
- Demand forecasting
- Capacity planning
- Seasonal trend analysis
- Growth projections

### 4. Strategic Recommendations
- Resource allocation optimization
- Process automation opportunities
- Technology investment priorities
- Operational strategy improvements

## Analysis Domains

### 1. Route Optimization
- **Metrics:** Distance, fuel consumption, delivery time
- **Opportunities:** Better route planning, driver allocation
- **Impact:** 15-25% cost reduction potential

### 2. Facility Utilization
- **Metrics:** Capacity usage, throughput, processing time
- **Opportunities:** Load balancing, capacity expansion
- **Impact:** 10-20% efficiency improvement

### 3. Driver Performance
- **Metrics:** Deliveries per day, success rate, customer satisfaction
- **Opportunities:** Training, route optimization, workload balance
- **Impact:** 20-30% productivity increase

### 4. Customer Experience
- **Metrics:** On-time delivery, communication effectiveness, satisfaction scores
- **Opportunities:** Improved notifications, service level improvements
- **Impact:** Higher retention, fewer complaints

### 5. Cost Structure
- **Metrics:** Cost per delivery, operational overhead, resource costs
- **Opportunities:** Process automation, vendor optimization
- **Impact:** 10-15% cost reduction

## Configuration

### Environment Variables
```bash
# Required
OPTIMIZATION_AGENT_ID=asst_XXX

# Shared (Required)
AZURE_AI_PROJECT_CONNECTION_STRING=host;sub;rg;project
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o
```

### Data Sources
- **Cosmos DB:** Historical operational data
- **Azure App Insights:** Application performance metrics
- **Manual Input:** Cost data, resource allocations

## Usage Examples

### Example 1: Analyze Network Performance
```python
from agents.base import optimization_agent

result = await optimization_agent({
    'action': 'analyze_network',
    'time_period': 'last_30_days',
    'focus_area': 'overall'
})

print(result['key_metrics'])
# {
#   'total_deliveries': 15000,
#   'on_time_rate': 0.94,
#   'cost_per_delivery': 8.50,
#   'customer_satisfaction': 4.3
# }

print(result['optimization_opportunities'])
# [
#   {'area': 'Route Planning', 'potential_savings': '15%', 'priority': 'high'},
#   {'area': 'Facility Load Balancing', 'potential_savings': '8%', 'priority': 'medium'},
#   ...
# ]
```

### Example 2: Cost Reduction Analysis
```python
result = await optimization_agent({
    'action': 'analyze_costs',
    'time_period': 'last_quarter',
    'cost_categories': ['fuel', 'labor', 'facilities', 'technology']
})

print(result['cost_breakdown'])
# {'fuel': 35%, 'labor': 45%, 'facilities': 15%, 'technology': 5%}

print(result['reduction_recommendations'])
# [
#   {'category': 'fuel', 'recommendation': 'Route optimization', 'savings': '20%'},
#   {'category': 'labor', 'recommendation': 'Workload automation', 'savings': '10%'},
#   ...
# ]
```

### Example 3: Capacity Planning
```python
result = await optimization_agent({
    'action': 'forecast_capacity',
    'forecast_period': 'next_6_months',
    'include_seasonal': True
})

print(result['demand_forecast'])
# {
#   'Apr 2026': {'parcels': 18000, 'growth': '20%'},
#   'May 2026': {'parcels': 16000, 'growth': '7%'},
#   ...
# }

print(result['capacity_recommendations'])
# ['Add 1 driver in April', 'Increase Sydney facility capacity by 15%']
```

### Example 4: Driver Performance Optimization
```python
result = await optimization_agent({
    'action': 'analyze_driver_performance',
    'driver_ids': ['driver-001', 'driver-002', 'driver-003'],
    'metrics': ['deliveries_per_day', 'success_rate', 'customer_feedback']
})

print(result['performance_summary'])
print(result['recommendations_per_driver'])
```

## Response Format

### Network Analysis Response
```json
{
  "success": true,
  "analysis_period": "2026-02-15 to 2026-03-17",
  "key_metrics": {
    "total_deliveries": 15000,
    "on_time_delivery_rate": 0.94,
    "average_cost_per_delivery": 8.50,
    "customer_satisfaction": 4.3,
    "driver_utilization": 0.82,
    "facility_utilization": 0.75
  },
  "performance_trends": {
    "delivery_volume": {"trend": "increasing", "rate": "8% per month"},
    "cost_per_delivery": {"trend": "stable", "variance": "±2%"},
    "satisfaction": {"trend": "improving", "rate": "0.1 points per month"}
  },
  "optimization_opportunities": [
    {
      "area": "Route Optimization",
      "current_efficiency": 0.78,
      "target_efficiency": 0.90,
      "potential_savings": "15% cost reduction",
      "implementation_priority": "high",
      "estimated_effort": "2 weeks",
      "recommendations": [
        "Implement AI-powered route sequencing",
        "Use real-time traffic data",
        "Train dispatchers on new tools"
      ]
    },
    {
      "area": "Facility Load Balancing",
      "current_efficiency": 0.75,
      "target_efficiency": 0.85,
      "potential_savings": "10% throughput increase",
      "implementation_priority": "medium",
      "estimated_effort": "1 month",
      "recommendations": [
        "Redistribute parcels during peak times",
        "Add temporary staffing for overflow",
        "Automate sorting processes"
      ]
    }
  ],
  "risk_factors": [
    "Peak season capacity constraints (Dec 2026)",
    "Driver retention challenges",
    "Fuel price volatility"
  ],
  "confidence_score": 0.87
}
```

## Analysis Frameworks

### Performance Metrics Categories

1. **Operational Efficiency**
   - Deliveries per driver per day
   - First-attempt delivery success rate
   - Average delivery time
   - Route optimization score

2. **Cost Metrics**
   - Cost per delivery
   - Fuel efficiency (km per liter)
   - Labor cost percentage
   - Overhead allocation

3. **Customer Metrics**
   - On-time delivery rate
   - Customer satisfaction score
   - Complaint rate
   - Net Promoter Score (NPS)

4. **Resource Utilization**
   - Driver utilization rate (70-85% optimal)
   - Facility capacity utilization (70-85% optimal)
   - Vehicle utilization
   - Technology adoption rate

### Optimization Prioritization Matrix

| Impact | Effort | Priority |
|--------|--------|----------|
| High | Low | Critical - Implement immediately |
| High | Medium | High - Plan for next quarter |
| High | High | Strategic - Long-term roadmap |
| Medium | Low | Quick Wins - Implement opportunistically |
| Low | High | Avoid - Poor ROI |

## Integration Points

### Data Sources

1. **Cosmos DB**
   - Historical parcel data
   - Delivery performance metrics
   - Driver performance data
   - Facility utilization stats

2. **Azure Application Insights**
   - Application performance
   - API response times
   - Error rates
   - User behavior analytics

3. **Manual Inputs**
   - Cost data (fuel, salaries, overhead)
   - Strategic goals
   - Market conditions
   - Competitive analysis

### Reporting & Dashboards

- **Executive Dashboard:** `/admin/analytics` (high-level KPIs)
- **Operations Dashboard:** `/admin/performance` (operational metrics)
- **Agent Dashboard:** `/admin/agents` (AI agent performance)

## Prompt Engineering

### Strategic Analysis Framework

The agent is instructed to:

1. **Analyze Comprehensively**
   - Examine multiple data sources
   - Identify correlations and patterns
   - Consider external factors
   - Validate findings with data

2. **Prioritize Strategically**
   - Balance quick wins with long-term gains
   - Consider implementation feasibility
   - Account for resource constraints
   - Align with business objectives

3. **Recommend Actionably**
   - Provide specific, concrete recommendations
   - Include implementation steps
   - Estimate effort and impact
   - Suggest success metrics

4. **Communicate Clearly**
   - Use data visualization concepts
   - Explain complex insights simply
   - Provide executive summaries
   - Support with evidence

## Performance Metrics

### Analysis Quality
- Insight accuracy: > 90%
- Recommendation ROI: > 300%
- Implementation success rate: > 75%
- stakeholder satisfaction: > 4.2/5

### Processing Performance
- Network analysis: < 30 seconds
- Cost analysis: < 20 seconds
- Forecast generation: < 45 seconds

## Testing

### Test Scenarios

#### Healthy Operations
```python
result = await optimization_agent({
    'action': 'analyze_network',
    'time_period': 'last_30_days',
    'baseline_performance': 'good'
})
# Expected: Minor optimization opportunities, positive trends
```

#### Underperforming Area
```python
result = await optimization_agent({
    'action': 'analyze_network',
    'focus_area': 'delivery_success_rate',
    'current_rate': 0.78  # Low
})
# Expected: Critical recommendations, root cause analysis
```

#### Cost Reduction Focus
```python
result = await optimization_agent({
    'action': 'analyze_costs',
    'target_reduction': 0.15,  # 15%
    'protected_areas': ['quality', 'safety']
})
# Expected: Cost reduction strategies preserving quality
```

## Known Limitations

### Data Dependency
- Insights quality depends on data completeness
- Historical data may not predict future accurately
- External factors (economy, competition) not fully captured

### Implementation Complexity
- Recommendations require human judgment
- Change management challenges not addressed
- Political/organizational factors not considered

### Predictive Accuracy
- Forecasts are probabilistic, not certain
- Unexpected events can invalidate predictions
- Models require periodic retraining

## Troubleshooting

### Inaccurate Analysis
```bash
# Verify data quality
python Scripts/check_current_data.py

# Review time period selection
# Check for data anomalies
# Validate analysis assumptions
```

### Poor Recommendations
```bash
# Review agent prompt for strategic context
# Provide more detailed business goals
# Include constraint information
# Validate with domain experts
```

### Agent Not Responding
```bash
# Verify agent ID
echo $env:OPTIMIZATION_AGENT_ID

# Test connection
python -c "import asyncio; from agents.base import optimization_agent; print('Connected')"
```

## Best Practices

### For Executives
1. Run monthly performance reviews
2. Track recommendation implementation
3. Measure ROI of changes
4. Share insights with teams

### For Operations Managers
1. Validate recommendations with front-line staff
2. Pilot changes before full rollout
3. Monitor impact of optimizations
4. Provide feedback to improve agent

### For Analysts
1. Ensure data quality and completeness
2. Context-aware analysis (seasonality, events)
3. Cross-validate agent insights
4. Document decision rationale

## Use Cases

### Monthly Performance Review
- Analyze previous month's operations
- Identify trends and anomalies
- Generate improvement recommendations
- Track progress on previous recommendations

### Budget Planning
- Forecast demand for next period
- Estimate resource requirements
- Calculate expected costs
- Justify budget requests with data

### Strategic Planning
- Long-term capacity planning
- Technology investment priorities
- Market expansion opportunities
- Competitive positioning

### Continuous Improvement
- Identify process bottlenecks
- Suggest automation opportunities
- Benchmark against industry standards
- Monitor implementation progress

## Future Enhancements

- Machine learning for predictive analytics
- Real-time optimization recommendations
- Integration with financial systems
- Competitive intelligence integration
- Automated A/B testing of strategies
- Natural language query interface

## Version History

- **v1.2.0** (2025-12-18): Added predictive analytics
- **v1.1.0** (2025-12): Enhanced cost analysis
- **v1.0.0** (2025-11): Initial optimization agent

## Related Documentation

- [AGENTS.md](../../../AGENTS.md) - Complete agent system
- [agents/base.py](../../../agents/base.py) - Agent implementation
- [Admin Analytics Dashboard](../../../templates/admin_analytics.html) - Visualization

---

**Last Updated:** March 17, 2026  
**Maintained By:** Zava Logistics Team
