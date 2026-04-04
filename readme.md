# 📦 Zava - AI-Powered Last Mile Delivery Platform

Parcel tracking system powered by **8 Azure AI Foundry Agents** with end-to-end intelligent automation. Built with Azure Cosmos DB, Azure Maps, Azure Speech Services, and Microsoft Agent Framework.

## 🚀 Quick Start

```powershell
# Web application
py app.py

# Command-line interface
python main.py
```

**Login:** admin / admin123 | **URL:** http://127.0.0.1:5000

---

## ✨ Key Features

- **8 Active AI Agents**: Customer service, fraud detection, dispatcher, optimization
- **Voice-Enabled Chat**: Azure Speech Services
- **Route Optimization**: Azure Maps with traffic analysis
- **Mobile-First UI**: Responsive design
- **Fraud Detection**: AI-powered threat analysis
- **Driver Manifests**: Automated route planning
- **Address Notes**: Auto-categorized delivery notes

---

## 🤖 AI Agents

See [AGENTS.md](AGENTS.md) for technical details. Agent prompts in `Agent-Skills/` folder.

1. **Customer Service** 🎧 - Real-time tracking
2. **Fraud Detection** 🛡️ - Security analysis  
3. **Identity Verification** 🔐 - High-risk validation
4. **Dispatcher** 📋 - Driver assignment
5. **Parcel Intake** 📦 - Service recommendations
6. **Sorting Facility** 🏭 - Capacity monitoring
7. **Delivery Coordination** 🚚 - Multi-stop sequencing
8. **Optimization** 📊 - Performance analysis

---

## 🛠️ Setup

```powershell
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # Edit with Azure credentials

# Initialize database
python Scripts/initialize_all_containers.py

# Generate demo data
python utils/generators/generate_fresh_test_data.py

# Run application (legacy)
py app.py

# Or use new architecture
python -c "from src.interfaces.web.app import create_app; app = create_app(); app.run(debug=True)"
```

**Environment (.env):**
```env
AZURE_AI_PROJECT_ENDPOINT="your-endpoint"
AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-4o"
COSMOS_DB_ENDPOINT="your-endpoint"
COSMOS_DB_DATABASE_NAME="logisticstracking"
COSMOS_CONNECTION_STRING="your-connection-string"  # For local dev
AZURE_MAPS_SUBSCRIPTION_KEY="your-key"
# + All 8 agent IDs (see AGENTS.md)
```

---

## 🚀 Azure Deployment

```powershell
# One-command deployment
.\deploy_to_azure.ps1

# Code only
.\deploy_to_azure.ps1 -CodeOnly
```

Deploys: Cosmos DB, AI Hub, OpenAI, Maps, Speech, Vision, 8 agents, RBAC, demo data.

**Automated Deployment (GitHub Actions):**
```
1. Setup: Follow .github/GITHUB_ACTIONS_SETUP.md
2. Go to: Actions → Deploy Infrastructure & Application
3. Click: Run workflow → Use defaults
4. Wait: 15-20 minutes
```

**See:** [`.github/README.md`](.github/README.md) for complete CI/CD workflow documentation.

---

## 🔧 Troubleshooting

**Access Denied:**
```powershell
# Wait 5 minutes for RBAC propagation, then:
az webapp restart --name <name> --resource-group RG-Zava-Frontend-dev

# Or use automated fix:
.\Scripts\force_fix_auth.ps1
```

**Database Connection:**
```bash
# Test connectivity
python parcel_tracking_db.py

# Diagnose containers
python Scripts/diagnose_containers.py

# Fix missing containers
.\Scripts\fix_azure_containers.ps1
```

**Agent Issues:**
```bash
# Verify login
az login

# Validate agent tools
python Scripts/validate_agent_tools.py

# Register tools
python Scripts/register_agent_tools_openai.py
```

**Testing:**
```bash
# Run all tests
pytest tests/

# Run specific test level
pytest tests/unit/       # Fast unit tests
pytest tests/integration/ # Integration tests
pytest tests/e2e/        # End-to-end tests

# Coverage report
pytest --cov=src --cov-report=html tests/
```

---

## 📚 Documentation

### Guides
- **[AGENTS.md](AGENTS.md)** - AI agent technical documentation
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture overview
- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Developer guide
- **[docs/TESTING.md](docs/TESTING.md)** - Testing strategy and guide
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Deployment guide

### Detailed Guides
- [Guides/DEMO_GUIDE.md](Guides/DEMO_GUIDE.md) - Full feature walkthrough
- [Guides/APPROVAL_DEMO_GUIDE.md](Guides/APPROVAL_DEMO_GUIDE.md) - AI approval workflow
- [Guides/DISPATCHER_AGENT_GUIDE.md](Guides/DISPATCHER_AGENT_GUIDE.md) - Dispatcher integration
- [Guides/USER_AUTH_GUIDE.md](Guides/USER_AUTH_GUIDE.md) - Authentication system

### Project Structure

```
src/                    # New Clean Architecture implementation
├── interfaces/        # Web routes, API endpoints
├── application/       # Commands, Queries (CQRS)
├── domain/           # Models, Services, Business Logic
├── infrastructure/   # Database, AI Agents, External Services
└── shared/           # Utilities, Logging

tests/                 # Comprehensive test suite
├── unit/             # Component tests
├── integration/      # Workflow tests
└── e2e/              # Full application tests

agents/               # AI agent implementations
Agent-Skills/         # Agent system prompts
config/              # Configuration files
utils/               # Utility scripts
workflows/           # Multi-agent workflows
```

**Telemetry:** https://ai.azure.com → Tracing / Monitoring

---

## 📄 License

Non-Commercial Open Source License

---

**Maintained by:** Microsoft Australia
