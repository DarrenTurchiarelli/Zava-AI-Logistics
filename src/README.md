# Zava Logistics - Source Code Structure

**Modern enterprise architecture with clear separation of concerns**

## Directory Structure

```
src/
├── domain/                    # Business logic (pure Python, no frameworks)
│   ├── models/               # Domain models (Parcel, Manifest, Driver, etc.)
│   ├── services/             # Business logic services
│   └── exceptions.py         # Domain-specific exceptions
│
├── application/              # Use cases / application services
│   ├── commands/             # Write operations (CQRS pattern)
│   ├── queries/              # Read operations (CQRS pattern)
│   └── dto.py                # Data Transfer Objects
│
├── infrastructure/           # External dependencies
│   ├── database/
│   │   ├── cosmos_client.py  # Cosmos DB client
│   │   └── repositories/     # Data access implementations
│   ├── agents/               # Azure AI Foundry agents
│   │   └── tools/            # Agent function tools
│   ├── external_services/    # Azure Maps, Speech, Vision
│   └── auth/                 # Authentication & authorization
│
├── interfaces/               # Delivery mechanisms
│   ├── web/                  # Flask web application
│   │   ├── routes/          # Route handlers by domain
│   │   └── middleware/      # Auth, error handling, logging
│   └── cli/                 # Command-line interface
│       └── commands/
│
├── config/                   # Centralized configuration
│   ├── settings.py          # Pydantic-based settings
│   ├── constants.py         # Enums and constants
│   └── environments/        # Environment-specific overrides
│
└── shared/                   # Shared utilities
    ├── async_helpers.py
    └── logging_config.py
```

## Architecture Principles

### 1. **Dependency Rule**
Dependencies point inward. Domain layer has no external dependencies.

```
interfaces → application → domain
       ↓
infrastructure
```

### 2. **Separation of Concerns**
- **Domain**: Business logic, models, rules
- **Application**: Use cases, orchestration
- **Infrastructure**: External services, databases
- **Interfaces**: Web, CLI, API

### 3. **CQRS Pattern**
- **Commands**: Write operations that change state
- **Queries**: Read operations that return data

### 4. **Type Safety**
- Pydantic for configuration validation
- Type hints throughout
- Enums for constants

## Usage Examples

### Get Configuration
```python
from src.config import get_settings

settings = get_settings()
endpoint = settings.cosmos_db.endpoint
agent_id = settings.azure_ai.customer_service_agent_id
```

### Use Constants
```python
from src.config import ParcelStatus, UserRole, ServiceType

if parcel.status == ParcelStatus.IN_TRANSIT:
    # Handle in-transit parcel
    pass

if user.role == UserRole.ADMIN:
    # Allow admin action
    pass
```

### Handle Domain Exceptions
```python
from src.domain import ParcelNotFoundException

try:
    parcel = await get_parcel(tracking_number)
except ParcelNotFoundException as e:
    print(f"Error: {e.message}")
    print(f"Details: {e.details}")
```

## Migration from Old Structure

The old `logistics_*.py` files will be gradually migrated:
- `logistics_parcel.py` → `src/domain/models/parcel.py` + `src/domain/services/parcel_service.py`
- `logistics_customer.py` → `src/interfaces/web/routes/customer.py`
- `logistics_admin.py` → `src/interfaces/web/routes/admin.py`
- `parcel_tracking_db.py` → `src/infrastructure/database/cosmos_client.py`
- `user_manager.py` → `src/infrastructure/auth/user_manager.py`

## Testing Structure

Tests mirror the source structure:
```
tests/
├── unit/              # Fast tests, no external deps
│   ├── domain/
│   ├── application/
│   └── infrastructure/
├── integration/       # Tests with database, agents
└── e2e/              # Full system tests
```

## Key Files

| File | Purpose |
|------|---------|
| `config/settings.py` | Type-safe configuration with Pydantic |
| `config/constants.py` | All enums and constants |
| `domain/exceptions.py` | Domain-specific exceptions |
| `application/dto.py` | Data transfer objects |

## Benefits of This Structure

✅ **Clear boundaries**: Each layer has well-defined responsibilities  
✅ **Testable**: Domain logic is pure Python, easy to test  
✅ **Maintainable**: Easy to find and modify code  
✅ **Type-safe**: Pydantic validation prevents config errors  
✅ **Scalable**: New features fit into existing structure  
✅ **Professional**: Enterprise-grade architecture  

---

**Version:** 1.2.5  
**Last Updated:** April 3, 2026
