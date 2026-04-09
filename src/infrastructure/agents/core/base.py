"""
Azure AI Foundry Agent Integration Layer
Provides unified interface to call all 9 Azure AI Foundry persistent agents
This module replaces local Python agent implementations with real Azure AI agents

Required Azure RBAC Permissions for Managed Identity:
- Cognitive Services OpenAI Contributor (for OpenAI operations)
- Azure AI Developer (for agents/write permissions)
- Cognitive Services User (for agents/read permissions)

Setup Instructions:
1. Enable managed identity on App Service
2. Run Scripts/setup_rbac_permissions.ps1 to grant roles
3. See Guides/DEPLOYMENT.md#rbac-permissions for details
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

from openai import AzureOpenAI
from azure.identity import AzureCliCredential, DefaultAzureCredential, ManagedIdentityCredential, get_bearer_token_provider
from dotenv import load_dotenv

from src.infrastructure.agents.core.prompt_loader import get_agent_prompt
from config.company import COMPANY_EMAIL, COMPANY_NAME, COMPANY_PHONE

load_dotenv()

# Feature flag: set USE_MAF=true to route agent calls through the MAF v1.0 SDK
# instead of the raw OpenAI Assistants API.  Safe to toggle at runtime.
_USE_MAF: bool = os.getenv("USE_MAF", "false").lower() == "true"

# Azure OpenAI Configuration  
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_AI_MODEL_DEPLOYMENT_NAME = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o")

# All 9 Azure AI Foundry Agent IDs
PARCEL_INTAKE_AGENT_ID = os.getenv("PARCEL_INTAKE_AGENT_ID")
SORTING_FACILITY_AGENT_ID = os.getenv("SORTING_FACILITY_AGENT_ID")
DELIVERY_COORDINATION_AGENT_ID = os.getenv("DELIVERY_COORDINATION_AGENT_ID")
DISPATCHER_AGENT_ID = os.getenv("DISPATCHER_AGENT_ID")
DRIVER_AGENT_ID = os.getenv("DRIVER_AGENT_ID")
OPTIMIZATION_AGENT_ID = os.getenv("OPTIMIZATION_AGENT_ID")
CUSTOMER_SERVICE_AGENT_ID = os.getenv("CUSTOMER_SERVICE_AGENT_ID")
FRAUD_RISK_AGENT_ID = os.getenv("FRAUD_RISK_AGENT_ID")
IDENTITY_AGENT_ID = os.getenv("IDENTITY_AGENT_ID")

# Reverse-lookup: asst_XXX → MAF agent key (used by call_azure_agent when USE_MAF=true)
_AGENT_ID_TO_KEY: dict[str, str] = {}


def _build_agent_id_map() -> None:
    """Populate _AGENT_ID_TO_KEY lazily after env vars are loaded."""
    mapping = {
        CUSTOMER_SERVICE_AGENT_ID: "customer_service",
        FRAUD_RISK_AGENT_ID: "fraud_risk",
        IDENTITY_AGENT_ID: "identity",
        DISPATCHER_AGENT_ID: "dispatcher",
        PARCEL_INTAKE_AGENT_ID: "parcel_intake",
        SORTING_FACILITY_AGENT_ID: "sorting_facility",
        DELIVERY_COORDINATION_AGENT_ID: "delivery_coordination",
        OPTIMIZATION_AGENT_ID: "optimization",
        DRIVER_AGENT_ID: "driver",
    }
    for agent_id, key in mapping.items():
        if agent_id:
            _AGENT_ID_TO_KEY[agent_id] = key


class AzureOpenAIAgentClient:
    """Singleton client for Azure OpenAI Assistants (used as agents)"""

    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_client(self) -> AzureOpenAI:
        """Get or create Azure Open AI client for Assistants API  
        
        This uses the Azure OpenAI Assistants API directly, which is compatible
        with Azure AI Foundry agents created via the Assistants API.
        """
        if self._client is None:
            api_version = "2024-05-01-preview"  # Assistants API version
            
            # Use Managed Identity when explicitly enabled (Azure deployment)  
            if os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true":
                # Running in Azure with managed identity
                credential = ManagedIdentityCredential()
                token_provider = get_bearer_token_provider(
                    credential, 
                    "https://cognitiveservices.azure.com/.default"
                )
                self._client = AzureOpenAI(
                    azure_endpoint=AZURE_OPENAI_ENDPOINT,
                    azure_ad_token_provider=token_provider,
                    api_version=api_version
                )
            else:
                # Running locally - use DefaultAzureCredential  
                credential = DefaultAzureCredential(
                    exclude_managed_identity_credential=True,
                    exclude_visual_studio_code_credential=True,
                    additionally_allowed_tenants=["*"],
                )
                token_provider = get_bearer_token_provider(
                    credential,
                    "https://cognitiveservices.azure.com/.default"
                )
                self._client = AzureOpenAI(
                    azure_endpoint=AZURE_OPENAI_ENDPOINT,
                    azure_ad_token_provider=token_provider,
                    api_version=api_version
                )
        
        return self._client


async def call_azure_agent(
    agent_id: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    thread_id: Optional[str] = None,
    event_queue: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Universal function to call any Azure OpenAI Assistant (agent)

    Args:
        agent_id: The Azure OpenAI Assistant ID (asst_XXX)
        message: The user message to send to the agent
        context: Optional context dictionary for additional information
        thread_id: Optional existing thread ID to continue a conversation

    Returns:
        Dictionary with agent response and metadata
    """
    print(f"\n🤖 Calling Azure OpenAI Assistant: {agent_id}")
    print(f"📍 Endpoint: {AZURE_OPENAI_ENDPOINT}")
    print(f"📝 Message length: {len(message)} chars")

    # ------------------------------------------------------------------
    # MAF v1.0 fast-path (feature flag: USE_MAF=true)
    # ------------------------------------------------------------------
    if _USE_MAF:
        if not _AGENT_ID_TO_KEY:
            _build_agent_id_map()
        agent_key = _AGENT_ID_TO_KEY.get(agent_id or "", "")
        if agent_key:
            print(f"🚀 Routing to MAF SDK  (agent_key={agent_key})")
            try:
                from src.infrastructure.agents.maf.client import call_maf_agent

                maf_result = await call_maf_agent(
                    agent_key,
                    message,
                    context=context,
                    event_queue=event_queue,
                )
                # Normalise return shape to match legacy callers
                maf_result["agent_id"] = agent_id
                maf_result.setdefault("thread_id", None)
                return maf_result
            except Exception as maf_exc:
                print(f"⚠️  MAF call failed ({maf_exc}), falling back to legacy path")
        else:
            print(f"⚠️  No MAF key for agent_id={agent_id!r}, using legacy path")
    # ------------------------------------------------------------------

    if not AZURE_OPENAI_ENDPOINT:
        error_msg = "AZURE_OPENAI_ENDPOINT not configured in environment variables"
        print(f"❌ {error_msg}")
        return {"success": False, "agent_id": agent_id, "error": error_msg, "response": None}

    if not agent_id:
        error_msg = "Agent ID not provided or not configured"
        print(f"❌ {error_msg}")
        return {"success": False, "agent_id": agent_id, "error": error_msg, "response": None}

    try:
        client = AzureOpenAIAgentClient().get_client()
        print("✅ Azure OpenAI client initialized")

        # Add context to message if provided
        if context:
            context_str = f"\n\nContext:\n{json.dumps(context, indent=2)}"
            full_message = message + context_str
        else:
            full_message = message

        # Create thread and run assistant with tool support
        print(f"🔄 Creating thread and processing run...")

        # Import tool handlers if available
        try:
            from src.infrastructure.agents.tools.cosmos_tools import TOOL_FUNCTIONS
            has_tools = True
            print(f"✅ Agent tools loaded: {list(TOOL_FUNCTIONS.keys())}")
        except ImportError:
            try:
                from agent_tools import TOOL_FUNCTIONS  # legacy root-level fallback
                has_tools = True
                print(f"✅ Agent tools loaded (fallback): {list(TOOL_FUNCTIONS.keys())}")
            except ImportError:
                has_tools = False
                TOOL_FUNCTIONS = {}
                print("⚠️ Agent tools not available")

        # Create or reuse thread
        if thread_id:
            print(f"🧵 Reusing existing thread: {thread_id}")
            thread = type("Thread", (), {"id": thread_id})()
        else:
            print(f"🧵 Creating new thread...")
            thread = client.beta.threads.create()
        print(f"   Thread ID: {thread.id}")

        print(f"📝 Adding message to thread...")
        client.beta.threads.messages.create(thread_id=thread.id, role="user", content=full_message)

        print(f"▶️ Creating run...")
        run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=agent_id)

        print(f"⏳ Polling run status...")
        import time

        max_iterations = 30
        iteration = 0
        tools_used = []  # Track tool calls for UI trace panel

        while iteration < max_iterations:
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            print(f"   Status: {run.status} (iteration {iteration + 1}/{max_iterations})")

            if run.status == "requires_action":
                print(f"🔧 Agent requested tool calls!")

                # Process tool calls
                tool_outputs = []
                if has_tools and hasattr(run, "required_action") and run.required_action:
                    submit_tool_outputs = run.required_action.submit_tool_outputs

                    for tool_call in submit_tool_outputs.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)

                        print(f"   🔨 Calling tool: {function_name}")
                        print(f"      Arguments: {function_args}")

                        # Record for UI trace panel
                        tools_used.append({
                            "tool": function_name,
                            "args": function_args,
                        })

                        # Emit tool_start event to SSE stream if a queue was provided
                        if event_queue is not None:
                            try:
                                event_queue.put_nowait({
                                    "type": "tool_start",
                                    "tool": function_name,
                                    "args_preview": str(function_args)[:300],
                                })
                            except Exception:
                                pass

                        # Execute the tool function (sync — no event-loop dance needed)
                        if function_name in TOOL_FUNCTIONS:
                            tool_function = TOOL_FUNCTIONS[function_name]
                            print(f"      🚀 Executing tool in thread pool...")
                            import concurrent.futures

                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(tool_function, **function_args)
                                output = future.result(timeout=30)

                            tool_outputs.append({"tool_call_id": tool_call.id, "output": output})
                            print(f"      ✅ Tool output: {output[:200]}...")

                            # Emit tool_done event
                            if event_queue is not None:
                                try:
                                    event_queue.put_nowait({
                                        "type": "tool_done",
                                        "tool": function_name,
                                        "preview": output[:400],
                                    })
                                except Exception:
                                    pass
                        else:
                            print(f"      ❌ Tool function not found: {function_name}")
                            tool_outputs.append(
                                {
                                    "tool_call_id": tool_call.id,
                                    "output": json.dumps({"error": f"Tool {function_name} not implemented"}),
                                }
                            )

                    # Submit tool outputs
                    if tool_outputs:
                        print(f"   📤 Submitting {len(tool_outputs)} tool outputs...")
                        run = client.beta.threads.runs.submit_tool_outputs(
                            thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs
                        )
                        print(f"   ✅ Tool outputs submitted, continuing run...")

            elif run.status == "completed":
                print(f"✅ Run completed successfully!")
                break
            elif run.status in ["failed", "cancelled", "expired"]:
                error_detail = getattr(run, 'last_error', None)
                error_msg = str(error_detail) if error_detail else f"Run ended with status: {run.status}"
                print(f"❌ {error_msg}")
                return {
                    "success": False,
                    "agent_id": agent_id,
                    "error": error_msg,
                    "response": None,
                }

            iteration += 1
            time.sleep(1)

        if iteration >= max_iterations:
            print(f"⚠️ Max iterations reached, run may still be processing")

        run_result = run

        print(f"✅ Run completed - Thread ID: {thread.id}, Run ID: {run_result.id}, Status: {run_result.status}")
        print(f"🔍 Run status type: {type(run_result.status)}")
        print(f"🔍 Run status value: {run_result.status}")

        # List all messages in thread
        print(f"🔍 Listing all messages in thread...")
        all_messages = client.beta.threads.messages.list(thread_id=thread.id)
        print(f"🔍 Total messages in thread: {len(all_messages.data) if hasattr(all_messages, 'data') else 'unknown'}")

        # Get the last assistant message
        response_text = None
        for msg in all_messages.data:
            if msg.role == "assistant":
                # Get the first text content from the message
                for content in msg.content:
                    if content.type == "text":
                        response_text = content.text.value
                        break
                if response_text:
                    break
        
        if not response_text:
            response_text = "No response from assistant"

        print(f"✅ Extracted response text ({len(response_text)} chars): {response_text[:200]}...")

        # Emit completion event
        if event_queue is not None:
            try:
                event_queue.put_nowait({"type": "complete", "summary": response_text[:600]})
            except Exception:
                pass

        return {
            "success": True,
            "agent_id": agent_id,
            "thread_id": thread.id,
            "response": response_text,
            "tools_used": tools_used,
            "metadata": {"run_id": run_result.id, "status": run_result.status},
        }

    except Exception as e:
        print(f"❌ Error calling Azure OpenAI assistant: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "agent_id": agent_id, "error": str(e), "response": None}


# ============================================================================
# AGENT-SPECIFIC FUNCTIONS
# ============================================================================


async def parcel_intake_agent(parcel_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Parcel Intake Agent to validate new parcel registrations

    Performs comprehensive validation including:
    - Service type recommendations based on parcel characteristics
    - Address validation and completeness checks
    - Delivery complication predictions
    - Weight/dimension verification
    - Special handling requirements detection

    Args:
        parcel_data: Dictionary with parcel information (tracking_number, sender, recipient, etc.)

    Returns:
        Validation results with recommendations, warnings, and insights
    """
    # Load base system prompt from Agent-Skills folder
    base_prompt = get_agent_prompt("parcel-intake")
    
    message = f"""{base_prompt}

## New Parcel Registration

**Parcel Information:**
- Tracking Number: {parcel_data.get('tracking_number')}
- Service Type: {parcel_data.get('service_type', 'standard')}
- Weight: {parcel_data.get('weight_kg', 'Unknown')} kg
- Dimensions: {parcel_data.get('dimensions', 'Unknown')}
- Declared Value: ${parcel_data.get('declared_value', 0)}

**Sender:**
- Name: {parcel_data.get('sender_name')}
- Address: {parcel_data.get('sender_address')}

**Recipient:**
- Name: {parcel_data.get('recipient_name')}
- Address: {parcel_data.get('recipient_address')}
- Postcode: {parcel_data.get('destination_postcode')}
- State: {parcel_data.get('destination_state', 'Unknown')}

**Special Instructions:** {parcel_data.get('special_instructions', 'None')}

## Analysis Required

Please validate this parcel registration and provide:
1. Service type recommendation (is '{parcel_data.get('service_type')}' optimal?)
2. Address validation and completeness check
3. Potential delivery complications
4. Data quality assessment

Provide concise, actionable feedback in a friendly tone.
"""

    return await call_azure_agent(PARCEL_INTAKE_AGENT_ID, message, parcel_data)


async def address_intelligence_agent(address: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Call Parcel Intake Agent to provide intelligent address validation and analysis

    Uses AI to:
    - Detect common typos and suggest corrections
    - Identify missing address components
    - Predict delivery complications (rural, multi-tenant, restricted access)
    - Recommend alternative delivery points
    - Flag addresses with poor delivery history
    - Provide delivery time estimates

    Args:
        address: The address string to validate and analyze
        context: Optional context including recipient name, postcode, service type

    Returns:
        Dictionary with validation status, recommendations, warnings, and suggestions
        {
            'success': bool,
            'response': str,  # Full AI analysis
            'is_valid': bool,  # Overall validation status
            'confidence': float,  # Confidence score 0-1
            'typo_detected': bool,  # Whether typos were found
            'suggested_correction': str,  # Corrected address if typo detected
            'complications': List[str],  # List of delivery complications
            'warnings': List[str],  # Warnings to show user
            'recommendations': List[str]  # Recommendations for better delivery
        }
    """
    context = context or {}

    message = f"""
    Analyze this delivery address for validation and potential issues:

    ADDRESS TO VALIDATE: {address}

    CONTEXT:
    Recipient Name: {context.get('recipient_name', 'Unknown')}
    Expected Postcode: {context.get('postcode', 'Unknown')}
    Service Type: {context.get('service_type', 'standard')}
    Declared Value: ${context.get('declared_value', 0)}

    PLEASE ANALYZE AND PROVIDE:

    1. ADDRESS QUALITY (Score 1-10):
       - Is the address complete with street number, street name, suburb, state, and postcode?
       - Are there any obvious typos or misspellings (e.g., "Mellbourne" vs "Melbourne")?
       - Does the postcode match the suburb?
       - Is the format correct for Australian addresses?

    2. TYPO DETECTION:
       - Check for common spelling mistakes in suburb names
       - Check for swapped/transposed numbers in street addresses
       - Detect missing punctuation or spacing issues
       - If typo detected, provide CORRECTED ADDRESS

    3. DELIVERY COMPLICATIONS:
       - Remote/rural area (outside metro delivery zones)
       - Multi-tenant building (requires unit/apartment number)
       - Restricted access area (gated community, secure building)
       - Business address (delivery hours restricted)
       - PO Box (requires special handling)
       - Construction site or temporary location
       - Known difficult delivery location

    4. RECOMMENDATIONS:
       - Suggest adding missing components (unit number, building name)
       - Recommend alternative delivery points if problematic
       - Suggest delivery time windows based on location type
       - Flag if signature required for this address type

    5. CONFIDENCE ASSESSMENT:
       - Overall confidence in successful delivery (0-100%)
       - Risk level: LOW, MEDIUM, HIGH

    FORMAT YOUR RESPONSE:
    [Valid: YES/NO]
    [Confidence: XX%]
    [Typo Detected: YES/NO]
    [Suggested Correction: corrected address if applicable]
    [Complications: comma-separated list]
    [Warnings: comma-separated list]
    [Recommendations: comma-separated list]
    [Risk Level: LOW/MEDIUM/HIGH]

    Then provide a brief friendly explanation for the customer.
    """

    result = await call_azure_agent(PARCEL_INTAKE_AGENT_ID, message, {"address": address, **context})

    # Parse structured response
    if result.get("success"):
        response_text = result.get("response", "")

        # Extract structured data using regex patterns
        import re

        # Helper function to extract bracketed values
        def extract_value(pattern, text, default=""):
            match = re.search(pattern, text, re.IGNORECASE)
            return match.group(1).strip() if match else default

        is_valid = extract_value(r"\[Valid:\s*(YES|NO)\]", response_text, "NO").upper() == "YES"
        confidence_str = extract_value(r"\[Confidence:\s*(\d+)%?\]", response_text, "50")
        confidence = int(confidence_str.replace("%", "")) / 100.0
        typo_detected = extract_value(r"\[Typo Detected:\s*(YES|NO)\]", response_text, "NO").upper() == "YES"
        suggested_correction = extract_value(r"\[Suggested Correction:\s*([^\]]+)\]", response_text, "")
        complications_str = extract_value(r"\[Complications:\s*([^\]]+)\]", response_text, "")
        warnings_str = extract_value(r"\[Warnings:\s*([^\]]+)\]", response_text, "")
        recommendations_str = extract_value(r"\[Recommendations:\s*([^\]]+)\]", response_text, "")
        risk_level = extract_value(r"\[Risk Level:\s*(LOW|MEDIUM|HIGH)\]", response_text, "MEDIUM")

        # Parse comma-separated lists
        complications = [c.strip() for c in complications_str.split(",") if c.strip() and c.strip().lower() != "none"]
        warnings = [w.strip() for w in warnings_str.split(",") if w.strip() and w.strip().lower() != "none"]
        recommendations = [
            r.strip() for r in recommendations_str.split(",") if r.strip() and r.strip().lower() != "none"
        ]

        result["is_valid"] = is_valid
        result["confidence"] = confidence
        result["typo_detected"] = typo_detected
        result["suggested_correction"] = suggested_correction if typo_detected else None
        result["complications"] = complications
        result["warnings"] = warnings
        result["recommendations"] = recommendations
        result["risk_level"] = risk_level

    return result


async def sorting_facility_agent(parcel_info: Dict[str, Any], intake_results: Optional[str] = None) -> Dict[str, Any]:
    """
    Call Sorting Facility Agent to determine parcel routing

    Args:
        parcel_info: Parcel information including destination
        intake_results: Optional results from parcel intake agent

    Returns:
        Routing decision and any exceptions
    """
    # Load base system prompt from Agent-Skills folder
    base_prompt = get_agent_prompt("sorting-facility")
    
    message = f"""{base_prompt}

## Parcel Sorting Task

**Parcel Details:**
- Tracking Number: {parcel_info.get('tracking_number')}
- Destination: {parcel_info.get('destination_address')}
- Destination Postcode: {parcel_info.get('destination_postcode')}
- Service Type: {parcel_info.get('service_type', 'standard')}
- Special Handling: {parcel_info.get('special_handling', 'None')}

{f"**Intake Results:** {intake_results}" if intake_results else ""}

Determine routing decision and identify any exceptions.
"""

    return await call_azure_agent(SORTING_FACILITY_AGENT_ID, message, parcel_info)


async def delivery_coordination_agent(
    routing_info: Dict[str, Any], sorting_results: Optional[str] = None
) -> Dict[str, Any]:
    """
    Call Delivery Coordination Agent to assign delivery

    Args:
        routing_info: Routing information from sorting
        sorting_results: Optional results from sorting facility agent

    Returns:
        Delivery assignment and coordination details
    """
    # Load base system prompt from Agent-Skills folder
    base_prompt = get_agent_prompt("delivery-coordination")
    
    message = f"""{base_prompt}

## Delivery Coordination Task

**Delivery Details:**
- Tracking Number: {routing_info.get('tracking_number')}
- Route: {routing_info.get('route', 'Unknown')}
- Priority: {routing_info.get('priority', 'normal')}
- Special Instructions: {routing_info.get('special_instructions', 'None')}

{f"**Sorting Results:** {sorting_results}" if sorting_results else ""}

Assign to appropriate driver and confirm delivery plan.
"""

    return await call_azure_agent(DELIVERY_COORDINATION_AGENT_ID, message, routing_info)


async def dispatcher_agent(route_data: Dict[str, Any], event_queue: Optional[Any] = None) -> Dict[str, Any]:
    """
    Call Dispatcher Agent for route optimization and driver assignment

    Args:
        route_data: Dictionary with parcels, drivers, capacity, SLAs
        event_queue: Optional queue.Queue for streaming SSE events

    Returns:
        Optimized route assignments and driver allocations
    """
    # Load base system prompt from Agent-Skills folder
    base_prompt = get_agent_prompt("dispatcher")
    
    message = f"""{base_prompt}

## Current Route Assignment Task

**Overview:**
- Number of Parcels: {route_data.get('parcel_count', 0)}
- Available Drivers: {route_data.get('available_drivers', [])}
- Service Level: {route_data.get('service_level', 'standard')}
- Delivery Window: {route_data.get('delivery_window', 'standard')}
- Geographic Zone: {route_data.get('zone', 'Unknown')}

**Parcels Summary:**
{json.dumps(route_data.get('parcels', []), indent=2)}

Provide optimized route manifest with driver assignments and capacity utilization.
"""

    return await call_azure_agent(DISPATCHER_AGENT_ID, message, route_data, event_queue=event_queue)


async def driver_agent(delivery_action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Driver Agent for delivery execution and proof of delivery

    Args:
        delivery_action: Dictionary with scan type, location, parcel details

    Returns:
        Delivery status and next action required
    """
    # Load base system prompt from Agent-Skills folder
    base_prompt = get_agent_prompt("driver")
    
    message = f"""{base_prompt}

## Current Delivery Action

**Action Details:**
- Action Type: {delivery_action.get('action_type', 'scan')}
- Tracking Number: {delivery_action.get('tracking_number')}
- Location: {delivery_action.get('location', 'Unknown')}
- Scan Type: {delivery_action.get('scan_type', 'Unknown')}
- Driver ID: {delivery_action.get('driver_id', 'Unknown')}

{f"**Delivery Note:** {delivery_action.get('note', '')}" if delivery_action.get('note') else ""}
{f"**Exception:** {delivery_action.get('exception', '')}" if delivery_action.get('exception') else ""}

Process scan and provide next action required.
"""

    return await call_azure_agent(DRIVER_AGENT_ID, message, delivery_action)


async def optimization_agent(route_conditions: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Optimization Agent for ETA prediction and route intelligence

    Args:
        route_conditions: Current route state, traffic, weather, disruptions

    Returns:
        Updated ETAs, route changes, optimization recommendations
    """
    # Load base system prompt from Agent-Skills folder
    base_prompt = get_agent_prompt("optimization")
    
    message = f"""{base_prompt}

## Current Route Analysis Task

**Route Information:**
- Route ID: {route_conditions.get('route_id', 'Unknown')}
- Current Location: {route_conditions.get('current_location', 'Unknown')}
- Remaining Stops: {route_conditions.get('remaining_stops', 0)}
- Traffic Conditions: {route_conditions.get('traffic', 'normal')}
- Weather: {route_conditions.get('weather', 'clear')}

{f"**Disruptions:** {route_conditions.get('disruptions', '')}" if route_conditions.get('disruptions') else ""}

**Stops:**
{json.dumps(route_conditions.get('stops', []), indent=2)}

Provide updated ETAs and optimization recommendations.
"""

    return await call_azure_agent(OPTIMIZATION_AGENT_ID, message, route_conditions)


async def customer_service_agent(customer_request: Dict[str, Any], thread_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Call Customer Service Agent for exception handling and communications.
    The agent queries Cosmos DB in real-time via registered function tools.

    Args:
        customer_request: Customer issue, delivery preferences, or inquiry
        thread_id: Optional existing thread ID to continue a conversation

    Returns:
        Dictionary with agent response and metadata
    """
    base_prompt = get_agent_prompt("customer-service")
    is_public = bool(customer_request.get("public_mode"))
    question = customer_request.get("details", "No details provided")

    if is_public:
        message = f"""{base_prompt}

## Customer's Question

{question}

## Company Information
- Phone: {COMPANY_PHONE}
- Email: {COMPANY_EMAIL}

Use your tools to look up any parcel data in real time. If a lookup fails, say you are unable to retrieve that information right now."""
    else:
        message = f"""{base_prompt}

## Internal Customer Service Request

**Customer:** {customer_request.get('customer_name', 'Unknown')}
**Issue Type:** {customer_request.get('issue_type', 'inquiry')}
**Tracking Number:** {customer_request.get('tracking_number', 'N/A')}

**Question / Details:**
{question}

**Company:** {COMPANY_NAME} | Phone: {COMPANY_PHONE} | Email: {COMPANY_EMAIL}

Use your tools to look up any parcel data in real time. When tracking data includes photos, acknowledge them naturally."""

    return await call_azure_agent(CUSTOMER_SERVICE_AGENT_ID, message, customer_request, thread_id=thread_id)


async def fraud_risk_agent(suspicious_activity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Fraud & Risk Agent for security and scam detection

    Args:
        suspicious_activity: Message, sender info, or activity pattern to analyze

    Returns:
        Risk assessment and recommended actions
    """
    # Load base system prompt from Agent-Skills folder
    base_prompt = get_agent_prompt("fraud-detection")
    
    # Build message content dynamically
    message_parts = [base_prompt, "", "## Current Security Analysis Task", ""]
    
    message_parts.append(f"**Activity Type:** {suspicious_activity.get('activity_type', 'message')}")
    message_parts.append(f"**Source:** {suspicious_activity.get('source', 'Unknown')}")
    message_parts.append("")

    if suspicious_activity.get("message"):
        message_parts.append("**Message Content:**")
        message_parts.append(suspicious_activity.get("message", ""))
        message_parts.append("")

    if suspicious_activity.get("pattern"):
        message_parts.append("**Activity Pattern:**")
        message_parts.append(suspicious_activity.get("pattern", ""))
        message_parts.append("")

    message_parts.append("**Sender Information:**")
    message_parts.append(json.dumps(suspicious_activity.get("sender_info", {}), indent=2))
    message_parts.append("")
    message_parts.append("Assess risk level and provide recommended actions.")

    message = "\n".join(message_parts)

    return await call_azure_agent(FRAUD_RISK_AGENT_ID, message, suspicious_activity)


async def identity_agent(verification_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Identity Agent for courier verification and authentication

    Args:
        verification_request: Courier credentials and verification details

    Returns:
        Verification status and compliance assessment
    """
    # Load base system prompt from Agent-Skills folder
    base_prompt = get_agent_prompt("identity-verification")
    
    message = f"""{base_prompt}

## Current Verification Request

**Courier Information:**
- Courier ID: {verification_request.get('courier_id', 'Unknown')}
- Name: {verification_request.get('name', 'Unknown')}
- Role: {verification_request.get('role', 'driver')}
- Employment Status: {verification_request.get('employment_status', 'Unknown')}
- Authorized Zone: {verification_request.get('authorized_zone', 'Unknown')}

{f"**Credentials:** {str(verification_request.get('credentials', ''))}" if verification_request.get('credentials') else ""}
{f"**Verification Method:** {verification_request.get('verification_method', 'standard')}" if verification_request.get('verification_method') else ""}

Verify identity and provide authentication status.
"""

    try:
        # Add timeout for agent call - don't block login if agent is slow
        result = await asyncio.wait_for(
            call_azure_agent(IDENTITY_AGENT_ID, message, verification_request), timeout=10.0  # 10 second timeout
        )
        return result
    except asyncio.TimeoutError:
        print(f"⚠️ Identity Agent timeout - proceeding with login")
        return {"success": False, "error": "Agent call timeout", "agent_id": IDENTITY_AGENT_ID, "response": None}
    except Exception as e:
        print(f"⚠️ Identity Agent error: {e}")
        return {"success": False, "error": str(e), "agent_id": IDENTITY_AGENT_ID, "response": None}


# ============================================================================
# BATCH OPERATIONS
# ============================================================================


async def call_multiple_agents(agent_calls: List[tuple]) -> List[Dict[str, Any]]:
    """
    Call multiple agents in parallel for efficiency

    Args:
        agent_calls: List of (agent_function, args_dict) tuples

    Returns:
        List of results from all agent calls
    """
    tasks = [agent_func(**args) for agent_func, args in agent_calls]
    return await asyncio.gather(*tasks, return_exceptions=True)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def parse_agent_response(response: Dict[str, Any], expected_format: Optional[str] = None) -> Dict[str, Any]:
    """
    Parse and structure agent response text

    Args:
        response: Raw agent response dictionary
        expected_format: Optional hint about expected response format

    Returns:
        Structured response data
    """
    if not response.get("success"):
        return {"success": False, "error": response.get("error", "Unknown error"), "parsed_data": None}

    response_text = response.get("response", "")

    # Try to extract structured data from response
    # Look for [Key: Value] patterns
    structured_data = {}

    import re

    pattern = r"\[([^:]+):\s*([^\]]+)\]"
    matches = re.findall(pattern, response_text)

    for key, value in matches:
        structured_data[key.strip()] = value.strip()

    return {
        "success": True,
        "raw_response": response_text,
        "parsed_data": structured_data if structured_data else None,
        "thread_id": response.get("thread_id"),
        "agent_id": response.get("agent_id"),
    }


# Synchronous wrapper for use in non-async contexts
def call_agent_sync(agent_function, **kwargs) -> Dict[str, Any]:
    """
    Synchronous wrapper to call async agent functions

    Args:
        agent_function: The async agent function to call
        **kwargs: Arguments to pass to the agent function

    Returns:
        Agent response dictionary
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(agent_function(**kwargs))


if __name__ == "__main__":
    # Test agent connectivity
    async def test_agents():
        print("Testing Azure AI Foundry Agent Connectivity...")
        print("=" * 70)

        # Test Parcel Intake Agent
        test_parcel = {
            "tracking_number": "TEST12345",
            "sender_name": "Test Sender",
            "sender_address": "123 Test St, Sydney NSW 2000",
            "recipient_name": "Test Recipient",
            "recipient_address": "456 Demo Ave, Melbourne VIC 3000",
            "service_type": "express",
            "weight_kg": 2.5,
        }

        print("\n1. Testing Parcel Intake Agent...")
        result = await parcel_intake_agent(test_parcel)
        print(f"   Success: {result['success']}")
        if result["success"]:
            print(f"   Response: {result['response'][:100]}...")
        else:
            print(f"   Error: {result['error']}")

        print("\n✅ Agent connectivity test complete!")
        print("All 9 agents are now available for use.")

    asyncio.run(test_agents())
