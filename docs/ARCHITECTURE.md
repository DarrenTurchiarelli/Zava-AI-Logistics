# Zava System Architecture

## Overview

Zava is an AI-powered last-mile delivery platform built using Clean Architecture principles with Domain-Driven Design (DDD). The system leverages 8 Azure AI Foundry agents for intelligent automation across the delivery workflow.

## Architecture Pattern

The system follows **Clean Architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Interfaces Layer                          │
│  (Web Routes, API Endpoints, CLI)                           │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                 Application Layer                            │
│  (Commands, Queries, Use Cases)                             │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                  Domain Layer                                │
│  (Models, Services, Business Logic)                         │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│               Infrastructure Layer                           │
│  (Database, External Services, AI Agents)                   │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
src/
├── interfaces/          # Presentation layer
│   ├── web/            # Flask web application
│   │   ├── routes/     # HTTP routes (blueprints)
│   │   ├── templates/  # HTML templates
│   │   └── middleware/ # Request/response middleware
│   └── cli/            # Command-line interface
│
├── application/         # Application layer
│   ├── commands/       # Write operations (CQRS)
│   ├── queries/        # Read operations (CQRS)
│   └── dtos/           # Data transfer objects
│
├── domain/             # Domain layer (business logic)
│   ├── models/         # Domain entities
│   ├── services/       # Domain services
│   ├── repositories/   # Repository interfaces
│   └── exceptions/     # Domain exceptions
│
├── infrastructure/     # Infrastructure layer
│   ├── database/       # Cosmos DB implementation
│   ├── agents/         # Azure AI agent clients
│   ├── external_services/  # Azure Maps, Speech, Vision
│   └── auth/           # Authentication/authorization
│
└── shared/             # Shared utilities
    ├── logging/        # Centralized logging
    └── validators/     # Input validation
```

## Core Domain Models

### 1. Parcel
Central entity representing a shipment through the logistics network.

**Key Properties:**
- Identifiers: `id`, `barcode`, `tracking_number`
- Sender/Recipient information
- Service type (standard, express, overnight, registered)
- Location tracking
- Status tracking (9 states)
- Delivery information
- Risk and compliance data
- Photo documentation

**Status Flow:**
```
REGISTERED → AT_DEPOT → IN_TRANSIT → OUT_FOR_DELIVERY → DELIVERED
                                              ↓
                                      FAILED_DELIVERY → RETURNED
                                              ↓
                                           HELD
```

### 2. Manifest
Driver delivery route for a day's deliveries.

**Key Properties:**
- `manifest_id`, `driver_id`, `date`
- Route sequence (optimized by Azure Maps)
- Parcel assignments
- Completion tracking

### 3. Driver
Driver profile and performance tracking.

**Key Properties:**
- Personal information
- Performance metrics
- Vehicle assignment
- Active manifests

### 4. ApprovalRequest
Authorization workflow for high-risk parcels.

**Key Properties:**
- Associated parcel
- Risk assessment
- Approval status
- AI decision + human override

### 5. FraudReport
Security incident tracking.

**Key Properties:**
- Incident details
- Risk categorization
- Investigation status
- AI analysis

## CQRS Pattern

### Commands (Write Operations)
Located in `src/application/commands/`

- `RegisterParcelCommand` - Register new parcel
- `UpdateParcelStatusCommand` - Update parcel status
- `CreateManifestCommand` - Create driver manifest
- `ApproveRequestCommand` - Process approval decision
- `ReportFraudCommand` - Report fraud incident

### Queries (Read Operations)
Located in `src/application/queries/`

- `GetParcelQuery` - Retrieve parcel by ID/tracking
- `SearchParcelsQuery` - Search parcels by criteria
- `GetManifestQuery` - Get driver manifest
- `GetApprovalRequestsQuery` - List pending approvals

## Infrastructure Services

### Database Layer
**Cosmos DB NoSQL** with partition strategy:

- **parcels** container: Partitioned by `store_location`
- **events** container: Partitioned by `barcode`
- **manifests** container: Partitioned by `driver_id`
- **users** container: Partitioned by `id`
- **approval_requests** container: Partitioned by `parcel_id`

### AI Agent Layer
**8 Azure AI Foundry Agents:**

1. **Customer Service Agent** - Real-time customer inquiries
   - Tools: `track_parcel_tool`, `search_parcels_by_recipient_tool`, `search_parcels_by_driver_tool`
   
2. **Fraud Detection Agent** - Security threat analysis
   
3. **Identity Verification Agent** - Customer verification
   
4. **Dispatcher Agent** - Intelligent parcel-to-driver assignment
   
5. **Parcel Intake Agent** - New parcel validation
   
6. **Sorting Facility Agent** - Facility capacity monitoring
   
7. **Delivery Coordination Agent** - Multi-stop delivery sequencing
   
8. **Optimization Agent** - Network-wide performance analysis

### External Services
- **Azure Maps** - Route optimization
- **Azure Speech** - Voice input/output
- **Azure Vision** - OCR and image analysis

## Authentication & Authorization

### User Roles
- `admin` - Full system access
- `driver` - Manifest and delivery operations
- `depot_mgr` - Depot operations and approvals
- `support` - Customer service operations
- `guest` - Read-only access

### Security
- Session-based authentication
- Role-based access control (RBAC)
- Managed Identity for Azure services (no keys in code)
- HTTPS only in production

## Data Flow Examples

### Parcel Registration Flow
```
1. User submits registration form
   ↓
2. RegisterParcelCommand.execute()
   ↓
3. Parcel Intake Agent validates data
   ↓
4. ParcelRepository.create() saves to Cosmos DB
   ↓
5. Event logged in events container
   ↓
6. Success response to user
```

### Fraud Detection Flow
```
1. ParcelIntakeAgent detects high risk (score ≥70)
   ↓
2. FraudDetectionAgent analyzes activity
   ↓
3. If score ≥85: Identity Verification Agent triggered
   ↓
4. If score ≥90: Parcel automatically held
   ↓
5. ApprovalRequest created
   ↓
6. Customer notified via Customer Service Agent
```

### Delivery Flow
```
1. Dispatcher Agent assigns parcels to driver
   ↓
2. Manifest created with route optimization (Azure Maps)
   ↓
3. Driver scans parcel at delivery
   ↓
4. UpdateParcelStatusCommand.execute()
   ↓
5. Photo captured and stored
   ↓
6. Customer notified (SMS/email)
   ↓
7. Manifest updated with completion
```

## Performance Considerations

### Database Optimization
- Partition key strategy for parallel query execution
- Indexed properties for common queries
- Query optimization (avoid cross-partition queries)
- Connection pooling

### Caching Strategy
- Session caching for user data
- Agent response caching (when appropriate)
- Static asset caching (CSS, JS, images)

### Async Processing
- All database operations use `async/await`
- AI agent calls are non-blocking
- Background task processing for long-running operations

## Scalability

### Horizontal Scaling
- Stateless application design
- Session stored in Redis (future enhancement)
- Database auto-scales with Cosmos DB

### Vertical Scaling
- Azure App Service can scale to higher SKUs
- Cosmos DB Request Units (RU) can be increased

## Monitoring & Observability

### Application Insights
- Request/response tracking
- Exception monitoring
- Custom metrics for AI agent performance
- User activity tracking

### Logging
- Structured logging with `logging_config.py`
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Contextual logging with request IDs

### Health Checks
- Database connectivity
- AI agent availability
- External service status

## Future Enhancements

### Planned Features
1. **Event Sourcing** - Complete audit trail
2. **Redis Cache** - Distributed caching
3. **WebSockets** - Real-time updates
4. **GraphQL API** - Flexible query interface
5. **Microservices** - Service decomposition
6. **Kubernetes** - Container orchestration

### Technical Debt
- Complete repository implementations
- Add comprehensive integration tests
- Implement circuit breakers for external services
- Add rate limiting for API endpoints

## Development Principles

1. **Clean Architecture** - Dependency inversion
2. **Domain-Driven Design** - Business logic in domain layer
3. **SOLID Principles** - Single responsibility, etc.
4. **CQRS Pattern** - Separate read/write models
5. **Test-Driven Development** - Write tests first
6. **Continuous Integration** - Automated testing and deployment

## References

- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Domain-Driven Design by Eric Evans](https://www.domainlanguage.com/ddd/)
- [CQRS Pattern](https://martinfowler.com/bliki/CQRS.html)
- [Azure AI Foundry Documentation](https://learn.microsoft.com/azure/ai-studio/)
- [Azure Cosmos DB Best Practices](https://learn.microsoft.com/azure/cosmos-db/best-practice)
