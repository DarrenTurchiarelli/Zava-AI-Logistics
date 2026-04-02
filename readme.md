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
# Install
pip install -r requirements.txt

# Configure
cp .env.example .env  # Edit with Azure credentials

# Initialize
python parcel_tracking_db.py

# Run
py app.py
```

**Environment (.env):**
```env
AZURE_AI_PROJECT_ENDPOINT="your-endpoint"
AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-4o"
COSMOS_DB_ENDPOINT="your-endpoint"
COSMOS_DB_DATABASE_NAME="logisticstracking"
AZURE_MAPS_SUBSCRIPTION_KEY="your-key"
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

---

## 🔧 Troubleshooting

**Access Denied:**
```powershell
az webapp restart --name <name> --resource-group RG-Zava-Frontend-dev
```

**Database Connection:**
```bash
python parcel_tracking_db.py  # Test connectivity
```

**Agent Issues:**
```bash
az login  # Verify credentials
```

---

## 📚 Documentation

- [AGENTS.md](AGENTS.md) - Technical agent documentation
- [Guides/DEPLOYMENT.md](Guides/DEPLOYMENT.md) - Deployment guide
- [Agent-Skills/README.md](Agent-Skills/README.md) - System prompts

Telemetry: https://ai.azure.com → Tracing / Monitoring

---

## 📄 License

Non-Commercial Open Source License

---

**Maintained by:** Microsoft Australia
