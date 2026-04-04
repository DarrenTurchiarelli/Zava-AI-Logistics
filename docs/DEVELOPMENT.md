# Zava Development Guide

## Getting Started

### Prerequisites
- Python 3.11 or higher
- Azure subscription (for AI services)
- Azure CLI installed
- Git

### Local Development Setup

#### 1. Clone Repository
```bash
git clone <repository-url>
cd lastmile
```

#### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Configure Environment
```bash
# Copy template
cp .env.example .env

# Edit .env with your Azure credentials
# Required variables:
# - COSMOS_DB_ENDPOINT
# - COSMOS_CONNECTION_STRING (for local dev)
# - AZURE_AI_PROJECT_ENDPOINT
# - AZURE_AI_MODEL_DEPLOYMENT_NAME
# - FLASK_SECRET_KEY
# - All 8 agent IDs (see AGENTS.md)
```

#### 5. Initialize Database
```bash
# Create Cosmos DB containers
python Scripts/initialize_all_containers.py

# Generate demo data
python utils/generators/generate_fresh_test_data.py
```

#### 6. Run Application
```bash
# Development mode
$env:FLASK_ENV='development'
python app.py

# Or using new entry point
$env:FLASK_ENV='development'
python -c "from src.interfaces.web.app import create_app; app = create_app(); app.run(debug=True)"
```

## Project Structure

### Source Code Organization

```
src/                          # New architecture source code
├── interfaces/              # Presentation layer
│   └── web/                # Flask web application
│       ├── app.py          # Application factory
│       ├── routes/         # Blueprint routes
│       ├── middleware/     # Request/response middleware
│       └── templates/      # HTML templates
│
├── application/            # Application layer (CQRS)
│   ├── commands/          # Write operations
│   ├── queries/           # Read operations
│   └── dtos/              # Data transfer objects
│
├── domain/                # Domain layer (business logic)
│   ├── models/           # Domain entities (Parcel, Manifest, etc.)
│   ├── services/         # Domain services
│   ├── repositories/     # Repository interfaces
│   └── exceptions/       # Domain-specific exceptions
│
├── infrastructure/       # Infrastructure layer
│   ├── database/        # Cosmos DB implementation
│   ├── agents/          # Azure AI agent clients
│   ├── external_services/  # Azure Maps, Speech, Vision
│   └── auth/            # Authentication
│
└── shared/              # Shared utilities
    ├── logging/         # Logging configuration
    └── validators/      # Input validation

static/                  # Static web assets
templates/              # Legacy templates (being migrated)
agents/                 # AI agent implementations
config/                 # Configuration files
utils/                  # Utility scripts
workflows/              # Multi-agent workflows
tests/                  # Test suite
docs/                   # Documentation
```

### Legacy Files
The following files are being phased out in favor of the new `src/` architecture:

- `app.py` - Use `src/interfaces/web/app.py` instead
- `logistics_*.py` - Being migrated to domain models
- Root-level templates - Moved to `src/interfaces/web/templates/`

## Development Workflow

### 1. Feature Development

#### Create a New Feature
```bash
# 1. Create feature branch
git checkout -b feature/your-feature-name

# 2. Implement in appropriate layer
# - Domain model changes: src/domain/models/
# - Business logic: src/domain/services/
# - API endpoint: src/application/commands or queries
# - Web route: src/interfaces/web/routes/

# 3. Write tests
# - Unit tests: tests/unit/
# - Integration tests: tests/integration/
# - E2E tests: tests/e2e/

# 4. Run tests
pytest tests/

# 5. Commit and push
git add .
git commit -m "feat: Add your feature description"
git push origin feature/your-feature-name
```

#### Example: Adding a New Command
```python
# src/application/commands/update_delivery_status_command.py
from src.domain.repositories.parcel_repository import ParcelRepository

class UpdateDeliveryStatusCommand:
    def __init__(self, parcel_repo: ParcelRepository):
        self.parcel_repo = parcel_repo
    
    async def execute(self, tracking_number: str, status: str):
        parcel = await self.parcel_repo.get_by_tracking_number(tracking_number)
        if not parcel:
            raise ValueError(f"Parcel not found: {tracking_number}")
        
        parcel.current_status = status
        await self.parcel_repo.update(parcel)
        
        return {"success": True, "tracking_number": tracking_number}
```

### 2. Working with AI Agents

#### Agent System Prompts
All agent prompts are managed in `Agent-Skills/` folder:

```
Agent-Skills/
  customer-service/
    system-prompt.md      # Agent instructions
    SKILLS.md            # Capabilities doc
  dispatcher/
    system-prompt.md
    SKILLS.md
  ...
```

#### Loading Agent Prompts
```python
from src.infrastructure.agents.core.prompt_loader import get_agent_prompt, get_agent_skills

# Load system prompt
prompt = get_agent_prompt("customer-service")

# Load skills documentation
skills = get_agent_skills("customer-service")
```

#### Testing Agent Integration
```python
# src/infrastructure/agents/core/base.py
from src.infrastructure.agents.core.base import customer_service_agent

result = await customer_service_agent({
    'details': 'Where is parcel DT123456?',
    'public_mode': True
})
```

### 3. Database Operations

#### Using Repository Pattern
```python
# Always use async context manager
from src.domain.repositories.parcel_repository import ParcelRepository

async def get_parcel_details(tracking_number: str):
    repo = ParcelRepository()
    parcel = await repo.get_by_tracking_number(tracking_number)
    return parcel
```

#### Adding New Repository Methods
```python
# src/domain/repositories/parcel_repository.py
async def find_by_date_range(self, start_date: str, end_date: str):
    """Find parcels within date range"""
    query = """
        SELECT * FROM c 
        WHERE c.registration_timestamp >= @start 
        AND c.registration_timestamp <= @end
    """
    parameters = [
        {"name": "@start", "value": start_date},
        {"name": "@end", "value": end_date}
    ]
    items = self.container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    )
    return [item async for item in items]
```

### 4. Adding Web Routes

#### Create New Blueprint
```python
# src/interfaces/web/routes/reports.py
from flask import Blueprint, render_template, session

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/dashboard')
async def dashboard():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    
    # Your logic here
    return render_template('reports/dashboard.html')
```

#### Register Blueprint
```python
# src/interfaces/web/app.py
from .routes.reports import reports_bp

def create_app(config=None):
    app = Flask(__name__)
    # ... other setup ...
    
    app.register_blueprint(reports_bp)
    
    return app
```

## Code Quality Guidelines

### Python Style
- Follow PEP 8
- Use type hints for function signatures
- Docstrings for all public functions/classes
- Max line length: 100 characters

### Naming Conventions
```python
# Files
snake_case.py

# Classes
class ParcelRepository:  # PascalCase

# Functions/methods
def get_parcel_by_id():  # snake_case

# Constants
MAX_RETRY_ATTEMPTS = 3  # UPPER_SNAKE_CASE

# Private methods
def _internal_helper():  # leading underscore
```

### Type Hints
```python
from typing import Dict, List, Optional, Any
from datetime import datetime

async def create_parcel(
    tracking_number: str,
    sender_name: str,
    weight: float,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a new parcel
    
    Args:
        tracking_number: Unique tracking identifier
        sender_name: Name of sender
        weight: Parcel weight in kg
        options: Additional options (optional)
    
    Returns:
        Created parcel data
    """
    pass
```

### Error Handling
```python
from src.domain.exceptions import ParcelNotFoundException

async def get_parcel(tracking_number: str):
    try:
        parcel = await repo.get_by_tracking_number(tracking_number)
        if not parcel:
            raise ParcelNotFoundException(tracking_number)
        return parcel
    except CosmosHttpResponseError as e:
        logger.error(f"Database error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
```

## Testing During Development

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test Types
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# E2E tests only
pytest tests/e2e/

# Specific test file
pytest tests/unit/domain/test_parcel_model.py

# Specific test case
pytest tests/unit/domain/test_parcel_model.py::TestParcelModel::test_create_parcel_with_required_fields
```

### Test Coverage
```bash
# Generate coverage report
pytest --cov=src tests/

# HTML coverage report
pytest --cov=src --cov-report=html tests/
# Open htmlcov/index.html in browser
```

### Watch Mode (for TDD)
```bash
# Install pytest-watch
pip install pytest-watch

# Run tests on file changes
ptw tests/
```

## Debugging

### VS Code Configuration
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Flask",
            "type": "python",
            "request": "launch",
            "module": "flask",
            "env": {
                "FLASK_APP": "src.interfaces.web:create_app()",
                "FLASK_ENV": "development",
                "FLASK_DEBUG": "1"
            },
            "args": ["run", "--no-debugger", "--no-reload"],
            "jinja": true
        },
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal"
        }
    ]
}
```

### Logging
```python
from utils.logging_config import setup_logging

logger = setup_logging("my_module")

logger.debug("Debug information")
logger.info("Informational message")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)
```

### Interactive Debugging
```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint()
breakpoint()
```

## Common Tasks

### Generate Demo Data
```bash
# Fresh test parcels
python utils/generators/generate_fresh_test_data.py

# Driver manifests
python utils/generators/generate_demo_manifests.py

# Approval demo parcels
python utils/generators/generate_sample_parcels.py

# Bulk realistic data
python utils/generators/generate_bulk_realistic_data.py --count 2000
```

### Database Management
```bash
# Initialize containers
python Scripts/initialize_all_containers.py

# Diagnose containers
python Scripts/diagnose_containers.py
```

### Agent Management
```bash
# Register agent tools
python register_agent_tools.py

# Validate tools
python Scripts/validate_agent_tools.py

# Update agent prompts
# Edit files in Agent-Skills/ folder
```

## Performance Optimization

### Database Queries
```python
# ✅ Good - uses partition key
await container.read_item(
    item=parcel_id,
    partition_key=store_location  # Fast!
)

# ❌ Bad - cross-partition query
query = "SELECT * FROM c WHERE c.id = @id"
# Slow across all partitions
```

### Async Operations
```python
# ✅ Good - parallel execution
results = await asyncio.gather(
    get_parcel(tracking1),
    get_parcel(tracking2),
    get_parcel(tracking3)
)

# ❌ Bad - sequential execution
result1 = await get_parcel(tracking1)
result2 = await get_parcel(tracking2)
result3 = await get_parcel(tracking3)
```

### Caching
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_state_from_postcode(postcode: str) -> str:
    """Cache postcode lookups"""
    # Lookup logic
    pass
```

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Set PYTHONPATH
$env:PYTHONPATH="$PWD;$PWD\src"
python your_script.py
```

#### Database Connection
```bash
# Test connection
python parcel_tracking_db.py

# Check environment variables
echo $env:COSMOS_DB_ENDPOINT
echo $env:USE_MANAGED_IDENTITY
```

#### Agent Errors
```bash
# Verify agent IDs
python -c "import os; print(os.getenv('CUSTOMER_SERVICE_AGENT_ID'))"

# Test agent
python -c "from agents.base import customer_service_agent; import asyncio; print(asyncio.run(customer_service_agent({'details': 'test'})))"
```

## Resources

- [Project README](../readme.md)
- [Agent Documentation](../AGENTS.md)
- [Architecture Guide](ARCHITECTURE.md)
- [Testing Guide](TESTING.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Azure AI Foundry Docs](https://learn.microsoft.com/azure/ai-studio/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Cosmos DB Python SDK](https://learn.microsoft.com/azure/cosmos-db/nosql/sdk-python)
