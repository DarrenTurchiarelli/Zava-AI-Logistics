# Zava — AI-Powered Last Mile Delivery Platform

Parcel tracking and logistics management platform powered by **8 Azure AI Foundry agents** with end-to-end intelligent automation. Built with Python/Flask, Azure Cosmos DB, Azure Maps, Azure Speech Services, and the Microsoft Agent Framework.

---

## Features

- **8 AI Foundry Agents** — Customer service, fraud detection, identity verification, dispatcher, parcel intake, sorting facility, delivery coordination, optimisation
- **AI Insights Dashboard** — Live agent analysis with 15-second timeout fallback, dynamic peak demand forecasting, health monitoring
- **Demand & Capacity Planner** — Read-only synthetic processing-centre scenarios, hourly stage queues, dispatch-cutoff risk, and staffing/transfer comparisons; no operational writes
- **Multi-agent Fraud Workflow** — Fraud Detection → Customer Service → Identity Verification chain, auto-triggered at configurable risk thresholds
- **AI Approval Engine** — Automated parcel approval/denial with configurable risk thresholds and audit trail
- **Customer Service Chatbot** — Azure AI Foundry persistent threads, tool-trace panel, GPT-4o attribution badge
- **Driver Manifests** — Auto-assigned routes with Azure Maps optimisation
- **Voice Interface** — Azure Speech Services (speech-to-text + text-to-speech)
- **Address Validation** — Azure Maps geocoding with graceful degradation on timeout
- **Parcel Registration** — OCR via Azure Vision, lodgement photo capture
- **Real-time Tracking** — Full event history, delivery photos, SMS/email notifications

---

## Demand & Capacity Planning

Open the home page's **Demand & Capacity Planner** tile,
**AI Insights > Open Demand Planner**, or the **Demand Planner** navigation
link (`/ai/demand-planning`, login required). Select any of the application's
40 distribution centres and a rest-of-day, next-24-hour or next-7-day horizon.
AI Insights, the planner and the Approvals dropdown share one catalogue of centre
codes, names and states. The planning preview and return link preserve the selected
centre. Planning clocks use the centre's local timezone, including half-hour
offsets and daylight saving where applicable.

Use **Demo: surge + late truck + lane outage**, then **Demo response: restore
lane + staff + hours** to compare the disruption and response. Numeric controls
also support absence, parcel handling mix and constrained transfer reservations.
Changing the distribution centre automatically refreshes its workload, hourly chart,
stage queues, cutoff misses, response options and chat context, retaining the current
scenario controls. Other input changes recalculate on **Compare scenario**.
Three response options are ranked by cutoff misses, then incremental
cost; each retains the selected disruption but replaces mitigation controls.
Baseline always means normal operations, not the previous scenario.

### Hybrid application snapshot and synthetic forecast

For admin and depot-manager users, the planner reads bounded, non-personal
projections from the existing `parcels`, `delivery_attempts`, `driver_manifests`
and `users` Cosmos containers. It uses existing Cosmos connection settings and
managed identity/key/CLI authentication; it never creates databases, containers,
or operational records. Each feed is capped at 20,000 records. A failed or
over-limit feed is visibly **unavailable**, not an empty or partially complete total.

When both parcel and approval feeds are complete, distinct eligible parcel records
replace the synthetic starting backlog. Exact current centre codes/names are
mapped to the shared catalogue; lodgement/origin locations, destinations and
states are not used to invent current occupancy. Tracking/barcode aliases deduplicate
parcels; conflicting identities/locations and unmapped records are excluded and
reported. At-depot parcels start at unload and sorting parcels start at sort.
Terminal, outbound and pre-arrival parcels are not added to processing queues.
Explicit holds and unresolved required release are excluded. Otherwise-processable
parcels linked to pending approvals are conservatively excluded as **awaiting review**,
not asserted to be confirmed physical holds. Several requests for one parcel
never create several parcels. The planner cannot approve or release anything.

Today's active delivery manifests are linked through parcel identities to provide
outbound context, never confirmed inbound demand. Differently dated manifests are
excluded and flagged. Driver accounts are shown only as directory context:
state-wide accounts and assigned delivery drivers are not available drivers,
trained sorters or measured facility capacity. Missing state assignments are flagged.
The source panel shows read time, last stored update, missing feeds and reconciliation
warnings. Stored update times are not interpreted as arrival/processing events.
Records may themselves be seeded demo data, not real-world operating measurements.

Future arrivals, staffing, equipment, deadlines, costs and receiving reservations
remain explicitly **synthetic**. Each centre retains its reproducible future daily
volume and hourly arrival pattern. Future arrivals are additional simulated demand,
not a second count of starting application parcels. There is no confirmed inbound
booking feed or invented 70/30 manifest-confirmed split. Processing-capacity
assumptions remain shared across centres. If current parcel/approval eligibility
cannot be established, the projection uses a clearly labelled synthetic starting
backlog, never a synthetic number labelled as an application count.

AI Insights uses the same hybrid preview. The planner links to parcel records,
centre-filtered Approvals, and today's state manifests. Source reads are shared
per worker for up to 30 seconds (5 seconds after an unavailable feed) to avoid four
cross-partition reads on every centre selection. Independent feeds are fetched
concurrently. **Refresh application snapshot** explicitly bypasses this cache;
changing centre or submitting manual controls uses the latest cached/read snapshot.
Chat Apply and ranked response-option links instead preserve the signed source
snapshot and calculation start, so comparisons do not silently change workload.
Other authenticated roles retain synthetic planning without operational reads;
application snapshots cannot be replayed by those roles.

There are no statistical forecast-confidence claims. Cutoff misses are not confirmed
late deliveries: downstream service commitments are not connected. The assumptions
panel describes stage throughput, connection timing, cost exclusions and the
no-new-arrivals recovery estimate.

### Indicative planner costs

The expanded **Cost assumptions** panel accepts whole-AUD, GST-exclusive planning
inputs. Defaults are illustrative Australian demo assumptions, **not verified
market rates, payroll data or supplier quotes**:

| Input | Default |
|---|---:|
| Paid normal site team (all costed roles, not just sorters) | 36 people |
| Loaded normal labour | AUD 65/person-hour |
| Loaded extra sorters | AUD 95/person-hour |
| Extended-hours site team | 24 people |
| Loaded overtime | AUD 110/person-hour |
| Site overhead, including closed hours | AUD 350/elapsed hour |
| Consolidated transfer transport | AUD 650/trip |
| Transfer handling | AUD 3/parcel actually moved |
| Costed transfer load size | 400 parcels/trip |
| Restore an unavailable sorting lane | AUD 1,500 once per horizon |

**Total indicative operating cost** includes normal paid labour, site overhead and
additional response spend. **Additional response cost** includes extra sorters,
the extended-hours crew, actual transfers and lane restoration. A disruption
without a paid response can still have zero additional spend, but not zero site
operating cost. Breakdowns expose each component, paid staff-hours and assumed trips
for the selected scenario and each ranked option.

Normal site labour is paid during 06:00-22:00 hours within the horizon, without
assuming absence reduces payroll. Extra sorters work from 14:00 until closing,
including extensions; the separate overtime crew works after 22:00. Site-team
costing inputs do not change the synthetic 12-sorter processing-capacity model.
Rates are blended: no automatic award, weekend, public-holiday or night premiums.
Transport rounds actual transfers up to whole configured loads separately per
facility-local day, assuming consolidation; it does not add receiving capacity.
`restore_lane=1` restores an underlying `lane_outage=1`, charging once per horizon;
without an outage it has no effect or fee. Base fleet costs, post-horizon recovery,
claims, penalties and lost revenue remain excluded, so this is not a cost-of-inaction
or ROI model.

Rates travel with manual form updates, centre/horizon changes, scenario resets,
signed option links and chat Apply previews. They are not saved to Cosmos or as
centre budgets. Chat can explain supplied rates and costs but cannot change rates;
edit the panel instead.

Scenarios are not saved. This feature does not write to Cosmos DB, alter parcel
approvals, dispatch vehicles, change rosters or deploy infrastructure. Horizon
starts are rounded down to the current facility-local hour. A deployment is
required before local code changes appear on the hosted site.

### Ask the Planner

The open chat panel uses the existing Azure AI model deployment to interpret
questions about the displayed centre, horizon and scenario. For example:
“What if the inbound truck is two hours late and 15% of staff are absent?”
The model proposes a validated patch to supported inputs; the deterministic
planner engine calculates the preview and costs. **Apply scenario to planner**
explicitly updates the view. Chat never approves parcels or changes operations.

Configure `AZURE_OPENAI_ENDPOINT` and `AZURE_AI_MODEL_DEPLOYMENT_NAME` (default
`gpt-4o`). The existing Azure OpenAI client uses managed identity when
`USE_MANAGED_IDENTITY=true`, otherwise the local Azure credential chain. No new
agent resource, model deployment or API key is required. The identity still needs
permission to invoke the selected model. Missing configuration, model failures and
invalid AI output produce visible errors; manual scenario controls remain usable.

Each request sends the question, up to eight recent chat messages, anonymous
application counts/source warnings and synthetic engine assumptions to Azure AI;
normal model charges apply. Customer details and parcel/driver identifiers from
source feeds are not included. Chat history stays in the
browser tab's session storage, separated by centre, horizon and hybrid/synthetic mode; **Clear chat**
removes it. There is no application-side conversation database. Chat uses the
displayed snapshot, not unsaved manual edits. Context and apply links expire after
one hour; applying a preview preserves its calculation start time. Unsupported or
ambiguous requests should produce a clarification, not a fabricated forecast.

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
