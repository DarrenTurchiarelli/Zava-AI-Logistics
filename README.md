# Zava — AI-Powered Last Mile Delivery Platform

Parcel tracking and logistics management platform powered by **8 Azure AI Foundry agents** with end-to-end intelligent automation. Built with Python/Flask, Azure Cosmos DB, Azure Maps, Azure Speech Services, and the Microsoft Agent Framework.

---

## Features

- **8 AI Foundry Agents** — Customer service, fraud detection, identity verification, dispatcher, parcel intake, sorting facility, delivery coordination, optimisation
- **AI Insights Dashboard** — Live agent analysis with 15-second timeout fallback, dynamic peak demand forecasting, health monitoring
- **Multi-agent Fraud Workflow** — Fraud Detection → Customer Service → Identity Verification chain, auto-triggered at configurable risk thresholds
- **AI Approval Engine** — Automated parcel approval/denial with configurable risk thresholds and audit trail
- **Customer Service Chatbot** — Azure AI Foundry persistent threads, tool-trace panel, GPT-4o attribution badge
- **Driver Manifests** — Auto-assigned routes with Azure Maps optimisation
- **Voice Interface** — Azure Speech Services (speech-to-text + text-to-speech)
- **Address Validation** — Azure Maps geocoding with graceful degradation on timeout
- **Parcel Registration** — OCR via Azure Vision, lodgement photo capture
- **Real-time Tracking** — Full event history, delivery photos, SMS/email notifications

---

## AI Agents

| # | Agent | Purpose | Auto-triggered |
|---|-------|---------|---------------|
| 1 | Customer Service | Real-time parcel tracking and customer queries | On chat |
| 2 | Fraud Detection | Multi-category threat analysis, risk scoring 0–100% | On fraud report |
| 3 | Identity Verification | Customer identity checks for high-risk cases | Risk ≥ 85% |
| 4 | Dispatcher | Intelligent parcel-to-driver assignment | Admin manifests |
| 5 | Parcel Intake | Validation, service recommendations | On registration |
| 6 | Sorting Facility | Capacity monitoring, routing decisions | AI Insights refresh |
| 7 | Delivery Coordination | Multi-stop sequencing, notifications | AI Insights refresh |
| 8 | Optimisation | Network performance and cost analysis | AI Insights refresh |

Agent system prompts: `src/infrastructure/agents/skills/` — edit the `system-prompt.md` files directly; changes load dynamically.

---

## Quick Start (Local)

```powershell
# Install dependencies
pip install -e ".[dev]"
# or
pip install -r requirements.txt

# Configure environment
Copy-Item .env.example .env   # Edit with your Azure credentials

# Initialize database containers
python scripts/initialize_all_containers.py

# Generate demo data
python utils/generators/generate_fresh_test_data.py

# Start the app
$env:FLASK_ENV='development'; py app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) — login: `admin` / `admin123`

### Required environment variables

```env
# Azure AI Foundry
AZURE_AI_PROJECT_ENDPOINT=https://your-project.services.ai.azure.com
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o

# Azure Cosmos DB
COSMOS_DB_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_DB_DATABASE_NAME=logisticstracking
COSMOS_CONNECTION_STRING=AccountEndpoint=...   # local dev only

# Flask
FLASK_SECRET_KEY=<random-32-char-string>

# Optional
AZURE_MAPS_SUBSCRIPTION_KEY=your-key
AZURE_SPEECH_KEY=your-key
AZURE_SPEECH_REGION=australiaeast
AZURE_VISION_ENDPOINT=https://...
AZURE_VISION_KEY=your-key

# Agent IDs (all required)
CUSTOMER_SERVICE_AGENT_ID=asst_XXX
FRAUD_RISK_AGENT_ID=asst_XXX
IDENTITY_AGENT_ID=asst_XXX
DISPATCHER_AGENT_ID=asst_XXX
PARCEL_INTAKE_AGENT_ID=asst_XXX
SORTING_FACILITY_AGENT_ID=asst_XXX
DELIVERY_COORDINATION_AGENT_ID=asst_XXX
OPTIMIZATION_AGENT_ID=asst_XXX
```

---

## Azure Deployment

```powershell
# First deployment — creates all Azure resources
az login
az account set --subscription "<your-subscription>"
.\deploy_to_azure.ps1

# Code-only redeploy (skips infrastructure)
.\deploy_to_azure.ps1 -CodeOnly
```

The deployment script automatically provisions: Cosmos DB, AI Hub & Project, Azure OpenAI (GPT-4o), Azure Maps, Speech, Vision, App Service, all RBAC assignments, creates all 8 agents, registers Cosmos DB tools with the Customer Service agent, initialises default users, and generates demo data.

**Default accounts after deployment:**

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Admin |
| depot_mgr | depot123 | Depot Manager |
| driver001–003 | driver123 | Driver |
| support | support123 | Customer Service |

---

## Project Structure

```
app.py                          # Entry point (thin wrapper)
src/
├── interfaces/web/
│   ├── routes/                 # Flask blueprints (admin, chatbot, api, …)
│   └── templates/              # Jinja2 templates
├── application/
│   ├── commands/               # Write operations (CQRS)
│   └── queries/                # Read operations (CQRS)
├── domain/
│   ├── models/                 # Business entities
│   └── services/               # Business logic
└── infrastructure/
    ├── agents/
    │   ├── core/               # Agent implementations
    │   ├── skills/             # system-prompt.md per agent
    │   └── tools/              # Cosmos DB function tools
    ├── database/               # Cosmos DB client + repositories
    └── external_services/      # Azure Maps, Speech, Vision
workflows/                      # Multi-agent orchestration
utils/generators/               # Demo and test data generators
scripts/                        # Deployment and maintenance scripts
tests/
├── unit/
├── integration/
└── e2e/
```

---

## Demo Data

```powershell
# 2,000 realistic parcels across all 8 Australian states
python utils/generators/generate_bulk_realistic_data.py

# AI approval demo parcels (auto-approve / auto-deny / manual review)
cd utils/generators
python generate_sample_parcels.py   # select option 3

# Driver manifests
python utils/generators/generate_demo_manifests.py
```

**Voice & chatbot test queries:**
- `"Track parcel RG857954"` — Dr. Emma Wilson, Sydney NSW
- `"Photo proof for parcel DT202512170037"` — Sarah Johnson, Perth WA

---

## Troubleshooting

**Cosmos DB Unauthorized after deployment:**
```powershell
.\scripts\fix_cosmos_auth.ps1          # standard fix
.\scripts\force_fix_auth.ps1           # aggressive reset (stop/start + 90s wait)
```

**Missing containers:**
```powershell
python scripts/diagnose_containers.py
.\scripts\fix_azure_containers.ps1
```

**Agent not responding:**
```powershell
python scripts/validate_agent_tools.py
python scripts/register_agent_tools_openai.py
```

**Run tests:**
```powershell
pytest tests/ -v
pytest tests/unit/          # fast
pytest tests/integration/   # requires Azure credentials
```

---

## Documentation

- [AGENTS.md](AGENTS.md) — AI agent technical reference
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Clean Architecture + DDD overview
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — Developer setup and conventions
- [docs/TESTING.md](docs/TESTING.md) — Testing strategy
- [docs/AZURE_DEPLOYMENT.md](docs/AZURE_DEPLOYMENT.md) — Deployment details
- [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) — Feature walkthrough
- [docs/APPROVAL_DEMO_GUIDE.md](docs/APPROVAL_DEMO_GUIDE.md) — AI approval workflow demo

---

## License

Non-Commercial Open Source License — see [LICENSE](LICENSE).

**Maintained by:** Darren Turchiarelli - Microsoft Australia
