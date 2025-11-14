# Last Mile Logistics Parcel Tracking with Azure Cosmos DB

This system provides comprehensive parcel tracking for last mile logistics operations, from store intake through to customer delivery. The solution uses Azure Cosmos DB for scalable data storage and supports real-time tracking throughout the delivery network.

## System Overview

### Logistics Journey
1. **Store Intake** - Parcels registered when received at stores
2. **Sorting Facility** - Parcels sorted and routed to appropriate facilities
3. **Driver Assignment** - Parcels assigned to delivery drivers
4. **Delivery Attempts** - Multiple delivery attempts with status tracking
5. **Customer Handoff** - Final delivery confirmation and receipt

### Database Architecture

**Database**: `logistics_tracking_db`

**Containers**:
1. **parcels** (Partition Key: `/destination_postcode`)
   - Core parcel information and tracking data
   
2. **tracking_events** (Partition Key: `/event_type`)
   - Real-time tracking events throughout the delivery journey
   
3. **delivery_attempts** (Partition Key: `/status`)
   - Delivery attempt records and supervisor approval requests

## Data Models

### Parcel Document
```json
{
  "id": "abc123-def456",
  "barcode": "LP654321",
  "tracking_number": "LP87654321AB",
  "sender_name": "TechMart Electronics",
  "sender_address": "45 Collins Street, Melbourne CBD, Melbourne VIC 3000",
  "sender_phone": "+61 3 9123 4567",
  "recipient_name": "Sarah Johnson",
  "recipient_address": "123 George Street, Sydney CBD, Sydney NSW 2000",
  "recipient_phone": "+61 2 8765 4321",
  "destination_postcode": "2000",
  "service_type": "express",
  "weight": 1.2,
  "dimensions": "25x20x8cm",
  "declared_value": 299.99,
  "special_instructions": "Fragile electronics - handle with care",
  "store_location": "Store_Melbourne_CBD",
  "registration_timestamp": "2024-11-14T10:30:00Z",
  "current_status": "registered",
  "current_location": "Store_Melbourne_CBD",
  "estimated_delivery": "2024-11-16T17:00:00Z",
  "delivery_attempts": 0,
  "is_delivered": false
}
```

### Tracking Event Document
```json
{
  "id": "event789-xyz012",
  "barcode": "LP654321",
  "event_type": "in_transit",
  "location": "Sorting_Facility_NSW",
  "description": "Parcel sorted and loaded for delivery route",
  "scanned_by": "logistics_staff_001",
  "timestamp": "2024-11-14T14:25:00Z",
  "additional_info": {
    "route": "Route_A",
    "driver": "DRV001"
  }
}
```

### Delivery Attempt Document
```json
{
  "id": "attempt456-qwe789",
  "barcode": "LP654321",
  "attempt_type": "delivery",
  "status": "failed",
  "driver_id": "DRV001",
  "location": "Customer_Address",
  "timestamp": "2024-11-15T16:45:00Z",
  "reason": "Customer not home",
  "next_attempt_date": "2024-11-16T09:00:00Z"
}
```

## Service Types

- **standard** - 5 business day delivery
- **express** - 2 business day delivery  
- **overnight** - Next business day delivery
- **registered** - 3 business day delivery with signature required

## Status Tracking

### Parcel Statuses
- `registered` - Initial registration at store
- `in_transit` - Moving between facilities
- `at_facility` - Arrived at sorting/distribution facility
- `out_for_delivery` - Assigned to driver for delivery
- `delivered` - Successfully delivered to customer
- `exception` - Issue requiring attention

### Event Types
- `registered` - Parcel entered system
- `in_transit` - Moving between locations
- `at_facility` - Arrived at facility
- `out_for_delivery` - On delivery vehicle
- `delivered` - Successfully delivered
- `delivery_attempt` - Attempted but failed delivery
- `exception` - Issue or problem occurred

## Setup Instructions

### 1. Create Azure Cosmos DB Account

Follow the standard Cosmos DB setup process for a SQL API account.

### 2. Configure Environment Variables

```env
AZURE_AI_PROJECT_ENDPOINT = "your-ai-foundry-endpoint"
AZURE_AI_MODEL_DEPLOYMENT_NAME = "gpt-4o"

# Azure Cosmos DB Configuration for Logistics Tracking
COSMOS_DB_ENDPOINT = "https://your-cosmos-account.documents.azure.com:443/"
COSMOS_DB_KEY = "your-primary-key-here"
COSMOS_DB_DATABASE_NAME = "logistics_tracking_db"
```

### 3. Install Dependencies

```bash
pip install -r cosmosdb_requirements.txt
```

### 4. Initialize Database

```bash
python cosmosdb_setup.py
```

## Usage

### Parcel Registration Demo

```bash
python barcode_scanner_cosmosdb_demo.py
```

Features:
- Interactive parcel registration
- Sample parcel generation
- Real-time tracking lookup
- Logistics operation simulation

### Agent Workflow

```bash
python Scripts/W04_Sequential_Workflow_Human_Approval.py
```

The workflow implements three specialized agents:
1. **Parcel Intake Agent** - Processes new parcels from stores
2. **Sorting Facility Agent** - Handles routing and exceptions
3. **Delivery Coordination Agent** - Manages driver assignments and deliveries

## API Functions

### Core Parcel Operations
- `register_parcel()` - Register new parcel in system
- `get_all_parcels()` - Retrieve all parcels
- `get_parcel_by_barcode()` - Find parcel by barcode
- `get_parcel_by_tracking_number()` - Find parcel by tracking number
- `update_parcel_status()` - Update parcel status and location

### Tracking Operations
- `create_tracking_event()` - Record tracking event
- `get_parcel_tracking_history()` - Get full tracking history
- `get_parcels_by_status()` - Filter parcels by status
- `get_parcels_by_location()` - Filter parcels by location

### Delivery Operations
- `record_delivery_attempt()` - Log delivery attempt
- `get_delivery_attempts()` - Get delivery history
- `get_driver_deliveries()` - Get driver's delivery assignments

### Supervisor Approvals
- `request_supervisor_approval()` - Request approval for exceptions
- `get_approval_status()` - Check approval status
- `approve_request()` - Approve pending request
- `reject_request()` - Reject pending request

## Logistics Workflow Features

### Exception Handling
- Damaged package processing
- Lost package investigations
- Delivery address corrections
- Customer unavailable procedures

### Supervisor Approval Types
- `exception_handling` - Process delivery exceptions
- `return_to_sender` - Return undeliverable packages
- `delivery_redirect` - Change delivery address
- `damage_claim` - Process damage claims
- `lost_package` - Handle lost package cases

### Real-time Tracking
- GPS-based location updates
- Delivery attempt logging
- Customer notification triggers
- Exception alert system

## Performance Optimization

### Partitioning Strategy
- **Parcels**: Partitioned by destination postcode for geographic distribution
- **Tracking Events**: Partitioned by event type for query optimization
- **Delivery Attempts**: Partitioned by status for operational efficiency

### Indexing
- Automatic indexing on frequently queried fields
- Custom indexes for tracking number lookups
- Geospatial indexing for location-based queries

### Throughput Management
- Development: 400 RU/s per container
- Production: Auto-scale based on traffic patterns
- Peak handling during holiday seasons

## Integration Points

### External Systems
- Store POS systems for parcel registration
- Driver mobile apps for status updates
- Customer notification systems
- Fleet management systems

### API Endpoints
- REST APIs for real-time tracking
- Webhook notifications for status changes
- Bulk upload APIs for batch operations
- Analytics APIs for reporting

## Monitoring and Analytics

### Key Metrics
- Parcel volume by location
- Delivery success rates
- Average delivery times
- Exception rates and types

### Operational Dashboards
- Real-time package flow
- Driver performance metrics
- Facility utilization rates
- Customer satisfaction scores

## Security and Compliance

### Data Protection
- Customer PII encryption
- Secure API access
- Audit trail logging
- GDPR compliance features

### Access Control
- Role-based permissions
- API key management
- Network security rules
- Data retention policies

## Troubleshooting

### Common Issues
1. **High RU consumption** - Optimize query patterns
2. **Slow tracking lookups** - Check indexing strategy
3. **Data inconsistency** - Review partition key distribution
4. **Failed deliveries** - Monitor exception handling workflow

### Debug Tools
- Azure Portal monitoring
- Custom logging systems
- Performance metrics tracking
- Error alerting systems

## Future Enhancements

### Advanced Features
- Machine learning delivery prediction
- Route optimization algorithms
- Predictive exception handling
- Customer preference learning

### Scalability Improvements
- Multi-region deployment
- Automated scaling policies
- Disaster recovery procedures
- Performance optimization

## Support and Documentation

- Technical documentation in `/docs`
- API reference guide
- Troubleshooting guides
- Best practices documentation