# 🎭 DT Logistics - Complete Demo Walkthrough

This guide provides a comprehensive walkthrough of the DT Logistics system, showing what each user persona can do and how to experience AI features in action.

## 👥 User Personas & Capabilities

### 1️⃣ **Admin** (System Administrator)
**Login:** `admin` / `admin123`

#### What Admin Can Do:
- ✅ **Full System Access** - View and manage all parcels, manifests, and users
- ✅ **Create Driver Manifests** - Generate optimized delivery routes
- ✅ **Approve Requests** - Handle exception approvals and special handling
- ✅ **View AI Insights** - Access analytics dashboard with AI-generated insights
- ✅ **Manage Users** - Create, update, and deactivate user accounts
- ✅ **Report Fraud** - Submit suspicious messages for AI analysis

#### AI Features for Admin:

**🤖 AI Agent: Fraud Detection Agent**
- **Service:** Azure AI Foundry GPT-4o model
- **Type:** ✅ Agentic (autonomous analysis, risk assessment, tool usage)
- **How to Experience:**
  1. Navigate to: **Report Fraud** (nav menu)
  2. Enter a suspicious message like: "Your parcel is delayed. Pay $50 fee to: http://fake-site.com"
  3. Click **Analyze with AI**
  4. Watch the AI agent analyze the message and provide:
     - Risk score (0-100%)
     - Risk factors identified
     - Recommended actions
     - Customer communication suggestions

**📊 Azure Maps Route Optimization**
- **Service:** Azure Maps Distance Matrix API
- **Type:** ❌ NOT Agentic (AI-enhanced service, deterministic routing)
- **How to Experience:**
  1. Navigate to: **Admin** → **Manifests**
  2. Click **Create New Manifest**
  3. Enter driver ID: `driver-001`
  4. Enter driver name: `John Smith`
  5. Paste barcodes (comma or newline separated)
  6. Click **Create Manifest**
  7. View Azure Maps optimization:
     - Traffic-aware routing calculations
     - Distance and time estimates
     - Interactive map visualization
     - ML-powered but not autonomous decision-making

---

### 2️⃣ **Support** (Customer Service)
**Login:** `support` / `support123`

#### What Support Can Do:
- ✅ **Track Parcels** - Search and view parcel details and history
- ✅ **AI Chatbot** - Use voice-enabled AI assistant for customer queries
- ✅ **View All Parcels** - Filter and search parcel database
- ✅ **Handle Approvals** - Process customer requests and exceptions
- ✅ **Report Fraud** - Analyze suspicious customer communications

#### AI Features for Support:

**🤖 AI Agent: Customer Service Agent "Alex"**
- **Service:** Azure AI Foundry GPT-4o + Azure Speech Services
- **Type:** Agentic (conversational, uses tools to fetch data)
- **How to Experience:**
  1. Click the **💬 Chat** button (bottom right, any page)
  2. **Text Option:**
     - Type: "Where is my parcel LP12345678AB?"
     - Watch Alex use tools to query the database
     - Receive conversational, natural language response
  3. **Voice Option:**
     - Click the microphone icon 🎤
     - Select voice: "Ken (Male Australian)" or any persona
     - Speak: "Track my parcel"
     - Hear AI response in selected voice
     - Experience Azure Speech Services (speech-to-text + text-to-speech)

**🤖 AI Workflow: Fraud → Customer Service Escalation**
- **Services:** Azure AI Foundry (multi-agent orchestration)
- **Type:** Agentic Workflow (automated agent-to-agent communication)
- **How to Experience:**
  1. Navigate to: **Report Fraud**
  2. Enter high-risk message: "URGENT: Your parcel is held. Pay $200 customs fee to unlock: http://scam-site.com/pay"
  3. Enter customer details:
     - Name: "John Doe"
     - Email: "john@example.com"
     - Phone: "+61 2 1234 5678"
  4. Click **Analyze with AI**
  5. Watch the automated workflow:
     - **Step 1:** Fraud Agent detects risk (score ≥70%)
     - **Step 2:** Auto-triggers Customer Service Agent
     - **Step 3:** Generates personalized warning message
     - **Step 4:** Simulates sending email/SMS notification
     - **Step 5:** For very high risk (≥85%): suggests identity verification
     - **Step 6:** For critical risk (≥90%): recommends parcel hold
  6. View workflow results showing agent collaboration

---

### 3️⃣ **Driver** (Delivery Driver)
**Login:** `driver001` / `driver123` (or `driver002`, `driver003`)

#### What Driver Can Do:
- ✅ **View My Manifest** - See today's assigned deliveries
- ✅ **Optimized Route** - Follow AI-optimized delivery sequence
- ✅ **Interactive Map** - View route on Azure Maps
- ✅ **Mark Complete** - Update delivery status in real-time
- ✅ **Proof of Delivery** - Mobile-friendly completion interface

#### AI Features for Driver:

**📊 Azure Maps Route Visualization**
- **Service:** Azure Maps (Distance Matrix, Geocoding, Rendering)
- **Type:** ❌ NOT Agentic (AI-enhanced ML service for routing)
- **How to Experience:**
  1. Login as: `driver001` / `driver123`
  2. Navigate to: **Driver Manifest**
  3. View the optimized route with:
     - **Delivery Sequence:** Parcels ordered for efficiency
     - **Distance Calculations:** Real-time distance between stops
     - **Time Estimates:** Traffic-aware delivery windows
     - **Map Visualization:** Interactive Azure Maps with pins
  4. Click **Complete** on any delivery
  5. Watch the system update in real-time

**Why Azure Maps is NOT Agentic:**
- Uses deterministic routing algorithms (not autonomous reasoning)
- Provides ML-powered traffic predictions (but no decision-making)
- Acts as a tool/service (not an independent agent)
- No tool usage or multi-turn reasoning capabilities

---

### 4️⃣ **Depot Manager**
**Login:** `depot_mgr` / `depot123`

#### What Depot Manager Can Do:
- ✅ **View All Manifests** - Monitor all driver manifests
- ✅ **Create Manifests** - Generate new driver assignments
- ✅ **Track Performance** - Monitor delivery progress
- ✅ **Approve Exceptions** - Handle special requests
- ✅ **Register Parcels** - Add new parcels to system

#### AI Features for Depot Manager:

**📊 Manifest Management Dashboard**
- **Service:** Database-driven with Azure Maps integration
- **Type:** ❌ NOT Agentic (CRUD operations with route calculations)
- **How to Experience:**
  1. Login as: `depot_mgr` / `depot123`
  2. Navigate to: **Admin** → **Manifests**
  3. View all active manifests:
     - Parcel distribution across drivers
     - Completion percentage tracking
     - Azure Maps route visualization
  4. Create new manifest (database operation):
     - Manually select parcels or paste barcodes
     - System creates manifest record
     - Azure Maps calculates optimal route

**Note:** While manifest creation could use an agentic AI agent for intelligent parcel assignment and workload balancing, the current implementation uses direct database operations with Azure Maps API for routing.

---

## 🤖 Complete AI Architecture

### **✅ Truly Agentic AI Systems** (Autonomous Reasoning, Tool Usage, Decision Making)

#### 1. **Customer Service Agent "Alex"**
- **Framework:** Azure AI Foundry Agent SDK
- **Model:** GPT-4o
- **Agent ID:** `CUSTOMER_SERVICE_AGENT_ID` (configured in .env)
- **Tools (Autonomous Selection):**
  - `track_parcel_tool()` - Queries Cosmos DB for parcel tracking
  - `get_parcel_data_tool()` - Retrieves comprehensive parcel info
  - `check_frauds_tool()` - Searches fraud detection database
- **Why Agentic:**
  - ✅ Autonomously decides which tool to use based on query
  - ✅ Multi-turn conversation with dynamic tool calling
  - ✅ Context-aware reasoning (not hardcoded logic)
  - ✅ Goal-oriented (answers questions without step-by-step instructions)
- **Capabilities:**
  - Natural conversation processing
  - Real-time database queries via tools
  - Context retention across conversation
  - Voice input/output integration (Azure Speech)

#### 2. **Fraud Detection Agent**
- **Framework:** Azure AI Foundry Agent SDK
- **Model:** GPT-4o
- **Agent ID:** `FRAUD_RISK_AGENT_ID` (configured in .env)
- **Why Agentic:**
  - ✅ Autonomous pattern recognition and risk assessment
  - ✅ Dynamic decision-making for recommended actions
  - ✅ Escalation logic based on autonomous reasoning
  - ✅ Generates personalized responses (not templates)
- **Capabilities:**
  - Scam and phishing detection
  - Risk scoring (0-100%) with reasoning
  - Context-aware threat assessment
  - Automated escalation workflows

#### 3. **Multi-Agent Workflow: Fraud → Customer Service**
- **Framework:** Azure AI Foundry multi-agent orchestration
- **Agents Involved:** Fraud Agent → Customer Service Agent → Identity Agent
- **File:** `workflows/fraud_to_customer_service.py`
- **Why Agentic:**
  - ✅ Agent-to-agent communication (not hardcoded pipeline)
  - ✅ Conditional branching based on agent decisions
  - ✅ Each agent reasons autonomously at their stage
  - ✅ Dynamic workflow execution (not fixed script)
- **Workflow:**
  1. Fraud Agent analyzes message → generates risk score
  2. If risk ≥70%: Customer Service Agent auto-triggered
  3. Customer Service Agent generates personalized warning
  4. If risk ≥85%: Identity Agent suggests verification
  5. If risk ≥90%: Recommends parcel hold

#### 4. **Identity Verification Agent**
- **Framework:** Azure AI Foundry Agent SDK
- **Model:** GPT-4o
- **Agent ID:** `IDENTITY_AGENT_ID` (configured in .env)
- **Why Agentic:**
  - ✅ Autonomous verification decision-making
  - ✅ Can use tools for document analysis
  - ✅ Context-aware identity confirmation
- **Capabilities:**
  - Customer identity verification
  - Document validation (with Azure Vision OCR)
  - Fraud prevention logic

### **📊 Additional Configured Agents** (Not Currently Used in UI)

The system has 9 Azure AI Foundry agents configured via environment variables:
- `PARCEL_INTAKE_AGENT_ID`
- `SORTING_FACILITY_AGENT_ID`
- `DELIVERY_COORDINATION_AGENT_ID`
- `DISPATCHER_AGENT_ID`
- `DRIVER_AGENT_ID`
- `OPTIMIZATION_AGENT_ID`

**Note:** These agents are configured but not actively integrated into the current UI workflow. They represent potential expansion points for agentic automation.

### **❌ AI-Enhanced Services** (ML-Powered, BUT NOT Agentic)

These are intelligent AI services used BY agents as tools, but they don't make autonomous decisions themselves.

#### 5. **Azure Speech Services**
- **Service:** Azure Cognitive Services Speech
- **Why NOT Agentic:** Deterministic speech processing (input → output, no reasoning)
- **Capabilities:**
  - Speech-to-text (ASR - Automatic Speech Recognition)
  - Text-to-speech (Neural TTS with 13 voice personas)
  - Real-time synthesis
- **Used By:** Customer Service Agent for voice I/O

#### 6. **Azure Maps**
- **Service:** Azure Maps Distance Matrix API + Routing
- **Why NOT Agentic:** API-based routing calculations (no autonomous decision-making)
- **Capabilities:**
  - Traffic-aware routing (ML-powered predictions)
  - Distance and time calculations
  - Geocoding and reverse geocoding
  - Interactive map rendering
- **Used By:** Manifest creation and driver route visualization

#### 7. **Azure AI Vision** (OCR)
- **Service:** Azure Cognitive Services Vision
- **Why NOT Agentic:** Text extraction only (no reasoning or decisions)
- **Capabilities:**
  - OCR text extraction from images
  - Screenshot analysis for fraud detection
  - Layout and structure recognition
- **Used By:** Fraud Detection Agent for analyzing screenshot submissions

---

## 🎯 Agentic vs AI-Enhanced: Key Differences

| Feature | Agentic AI | AI-Enhanced Service |
|---------|------------|---------------------|
| **Decision Making** | ✅ Autonomous | ❌ Deterministic |
| **Tool Usage** | ✅ Decides which tools to use | ❌ Fixed API calls |
| **Reasoning** | ✅ Multi-turn, context-aware | ❌ Single input → output |
| **Goal-Oriented** | ✅ Works toward objectives | ❌ Executes specific function |
| **Adaptability** | ✅ Handles variations | ❌ Fixed logic |
| **Examples in App** | Customer Service, Fraud Detection | Azure Maps, Speech, Vision |

**Simple Test:** Can it decide HOW to solve a problem, or does it just execute a function?
- **Agentic:** "Find parcel info" → agent decides to use track_parcel_tool()
- **AI Service:** "Convert speech to text" → always same process

---

## 🎬 Complete Demo Flow (15 Minutes)

### **Act 1: Customer Service Experience (5 min)**

1. **Login:** Click "Support" quick demo button
2. **Open Chat:** Click 💬 Chat button (bottom right)
3. **Type Query:** "Where is parcel LP12345678AB?"
4. **Watch AI:** Alex agent queries database and responds naturally
5. **Try Voice:** Click 🎤 microphone icon
6. **Select Voice:** Choose "Ken (Male Australian)"
7. **Speak:** "What's the status?"
8. **Listen:** Hear AI response in Ken's voice
9. **Observe:**
   - Speech-to-text conversion
   - AI agent processing
   - Text-to-speech synthesis

### **Act 2: Fraud Detection Workflow (5 min)**

1. **Stay as Support** (or login as Admin)
2. **Navigate:** Report Fraud (nav menu)
3. **Enter Message:**
   ```
   URGENT PARCEL NOTIFICATION!
   Your delivery is held at customs. 
   Immediate payment required: $250 AUD
   Pay now: http://fake-customs-australia.tk/pay?id=12345
   Failure to pay within 24hrs = parcel destroyed
   ```
4. **Enter Details:**
   - Customer: "Sarah Johnson"
   - Email: "sarah.j@example.com"
   - Phone: "+61 2 9876 5432"
5. **Click:** Analyze with AI
6. **Watch Workflow:**
   - Fraud Agent analyzes (5 seconds)
   - Risk score appears (95% - Critical)
   - Customer Service Agent generates warning
   - Workflow log shows agent-to-agent communication
   - Recommendations displayed
7. **Observe:**
   - Multi-agent orchestration
   - Automated decision making
   - Personalized customer communication

### **Act 3: Driver Manifest & Route Optimization (5 min)**

1. **Logout:** Click profile icon → Logout
2. **Login:** Click "Driver 1" quick demo button
3. **View Manifest:** Automatically shows driver manifest
4. **Examine Route:**
   - View optimized parcel sequence
   - See Azure Maps with delivery pins
   - Check distance calculations
   - Review time estimates
5. **Complete Delivery:**
   - Click "Complete" on first parcel
   - Watch real-time status update
   - See progress percentage increase
6. **Observe:**
   - AI-optimized routing
   - Real-time updates
   - Interactive mapping

---

## 🔍 Where to See Each AI Service

| AI Feature | Location | Action | What to Observe |
|------------|----------|--------|-----------------|
| **Customer Service Agent** ✅ Agentic | Chat widget (any page) | Type or speak query | Natural conversation, autonomous tool usage, database queries |
| **Fraud Detection Agent** ✅ Agentic | Report Fraud page | Submit suspicious message | Risk analysis, autonomous pattern recognition, recommendations |
| **Fraud→Customer Workflow** ✅ Agentic | Report Fraud page | High-risk message submission | Multi-agent orchestration, automated escalation with reasoning |
| **Azure Speech** ❌ AI Service | Chat widget | Click microphone icon | Speech-to-text, text-to-speech (deterministic processing) |
| **Azure Maps** ❌ AI Service | Driver Manifest page | View manifest | Interactive map, route visualization, ML-powered traffic data |
| **Azure AI Vision** ❌ AI Service | Report Fraud page | Upload screenshot | OCR text extraction (no decision-making) |

---

## 💡 Demo Tips & Highlights

### **Best AI Demonstrations:**

1. **Voice Interaction:**
   - Use chat microphone for impressive speech demo
   - Try different voice personas (Ken, Natasha, William)
   - Speak naturally - AI handles variations

2. **Fraud Detection:**
   - Use realistic scam messages for higher risk scores
   - Include URLs, urgency, payment requests
   - Watch multi-agent workflow in action

3. **Route Visualization:**
   - Create manifests with 10+ parcels for visible mapping
   - View Azure Maps route calculations with traffic data
   - Explore interactive map with delivery pins

4. **Natural Conversation:**
   - Ask follow-up questions in chat
   - Use casual language like "Where's my stuff?"
   - Watch AI maintain context across messages

### **Common Demo Scenarios:**

**Scenario 1: Lost Parcel Inquiry**
- User: Support
- Action: Chat → "Customer says parcel LP12345678AB never arrived"
- AI Response: Checks status, provides tracking history, suggests next steps

**Scenario 2: Delivery Exception**
- User: Driver
- Action: View manifest, note delivery challenge
- AI Feature: Optimized alternate route suggestions

**Scenario 3: Suspected Fraud**
- User: Admin or Support
- Action: Report fraud with scam SMS
- AI Response: Multi-agent analysis, customer warning, recommended actions

**Scenario 4: Route Planning**
- User: Depot Manager
- Action: Create manifest for driver with 20 parcels
- System Response: Azure Maps calculates optimal route with traffic-aware sequencing, distance calculations, and time estimates

---

## 🎯 Key Takeaways

### **What Makes This System Truly "Agentic":**

1. **Autonomous Tool Selection:**
   - ✅ Customer Service Agent decides which tool to call (track_parcel, get_parcel_data, check_frauds)
   - ✅ Agent Framework handles tool calling loop automatically
   - ✅ No hardcoded "if query contains X, call function Y" logic

2. **Dynamic Database Queries:**
   - ✅ Agents query Cosmos DB based on reasoning, not fixed rules
   - ✅ Tools defined in `agent_tools.py` executed only when agent decides
   - ✅ Async tool execution in separate thread to avoid event loop conflicts

3. **Multi-Agent Orchestration:**
   - ✅ Fraud Agent → Customer Service Agent → Identity Agent workflow
   - ✅ Each agent reasons independently at their stage
   - ✅ Conditional branching based on agent decisions (risk score thresholds)
   - ✅ Workflow in `workflows/fraud_to_customer_service.py`

4. **Natural Language Reasoning:**
   - ✅ Handle variations in phrasing without retraining
   - ✅ Maintain conversation context across turns
   - ✅ Extract intent from casual speech ("Where's my stuff?")

### **Critical Distinction: AI Services vs Agentic AI**

**❌ AI Services (NOT Agentic - used AS TOOLS by agents):**
- **Azure Speech:** Deterministic voice I/O processing
- **Azure Maps:** API-based route calculations (ML-powered but not autonomous)
- **Azure Vision:** OCR text extraction (no reasoning)
- **Database Operations:** CRUD operations (create_manifest, track_parcel queries)

**✅ Agentic AI (Autonomous Decision-Making):**
- **Customer Service Agent:** Conversational assistant with tool usage
- **Fraud Detection Agent:** Autonomous risk analyst
- **Identity Agent:** Intelligent verification specialist
- **Multi-Agent Workflows:** Coordinated agent-to-agent communication

### **Configured But Not Yet Integrated:**
The system has 9 Azure AI Foundry agents configured (IDs in .env), but only 3 are actively used in the current UI:
- ✅ Active: Customer Service, Fraud Detection, Identity
- ⚠️ Configured: Parcel Intake, Sorting, Delivery Coordination, Dispatcher, Driver, Optimization

**Expansion Opportunity:** These additional agents could enable end-to-end agentic automation of the entire logistics workflow.

---

## 📞 Support & Resources

**Documentation:**
- [Main README](../readme.md) - Complete system overview
- [Deployment Guide](DEPLOYMENT.md) - Azure deployment
- [Demo Guide](DEMO_GUIDE.md) - Quick demo setup

**Default Credentials:**
- Admin: `admin` / `admin123`
- Support: `support` / `support123`
- Drivers: `driver001`, `driver002`, `driver003` / `driver123`
- Depot: `depot_mgr` / `depot123`

**Quick Demo Access:**
- Use quick demo buttons on login page for instant access
- No need to type credentials manually

---

**Ready to experience AI-powered logistics? Start at http://127.0.0.1:5000!** 🚀
