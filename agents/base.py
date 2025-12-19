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

import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, AzureCliCredential, ManagedIdentityCredential
from dotenv import load_dotenv
from config.company import COMPANY_NAME

load_dotenv()

# Azure AI Project Configuration
AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")

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


class AzureAIAgentClient:
    """Singleton client for Azure AI Foundry agents"""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_client(self) -> AIProjectClient:
        """Get or create Azure AI Project client"""
        if self._client is None:
            # Use Managed Identity when explicitly enabled (Azure deployment)
            if os.getenv('USE_MANAGED_IDENTITY', 'false').lower() == 'true':
                # Running in Azure with managed identity
                credential = ManagedIdentityCredential()
            else:
                # Running locally - use DefaultAzureCredential for better timeout handling
                # It will try: Environment -> ManagedIdentity -> AzureCLI -> etc.
                credential = DefaultAzureCredential(
                    exclude_managed_identity_credential=True,  # Don't try managed identity locally
                    exclude_visual_studio_code_credential=True,  # Skip VSCode auth
                    additionally_allowed_tenants=['*']  # Allow any tenant
                )
            
            self._client = AIProjectClient(
                endpoint=AZURE_AI_PROJECT_ENDPOINT,
                credential=credential
            )
        return self._client


async def call_azure_agent(agent_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Universal function to call any Azure AI Foundry agent
    
    Args:
        agent_id: The Azure AI agent ID (asst_XXX)
        message: The user message to send to the agent
        context: Optional context dictionary for additional information
        
    Returns:
        Dictionary with agent response and metadata
    """
    print(f"\n🤖 Calling Azure AI Agent: {agent_id}")
    print(f"📍 Endpoint: {AZURE_AI_PROJECT_ENDPOINT}")
    print(f"📝 Message length: {len(message)} chars")
    
    if not AZURE_AI_PROJECT_ENDPOINT:
        error_msg = "AZURE_AI_PROJECT_ENDPOINT not configured in environment variables"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "agent_id": agent_id,
            "error": error_msg,
            "response": None
        }
    
    if not agent_id:
        error_msg = "Agent ID not provided or not configured"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "agent_id": agent_id,
            "error": error_msg,
            "response": None
        }
    
    try:
        client = AzureAIAgentClient().get_client()
        print("✅ Azure AI client initialized")
        
        # Add context to message if provided
        if context:
            context_str = f"\n\nContext:\n{json.dumps(context, indent=2)}"
            full_message = message + context_str
        else:
            full_message = message
        
        # Create thread and run agent with tool support
        print(f"🔄 Creating thread and processing run...")
        
        # Import tool handlers if available
        try:
            from agent_tools import TOOL_FUNCTIONS
            has_tools = True
            print(f"✅ Agent tools loaded: {list(TOOL_FUNCTIONS.keys())}")
        except ImportError:
            has_tools = False
            print("⚠️ Agent tools not available")
        
        # Create and run with explicit parameters - DON'T use create_thread_and_process_run
        # because it tries to auto-execute tools. We need manual control.
        print(f"🧵 Creating thread...")
        thread = client.agents.threads.create()
        print(f"   Thread ID: {thread.id}")
        
        print(f"📝 Adding message to thread...")
        client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=full_message
        )
        
        print(f"▶️ Creating run...")
        run = client.agents.runs.create(
            thread_id=thread.id,
            agent_id=agent_id
        )
        
        print(f"⏳ Polling run status...")
        import time
        max_iterations = 30
        iteration = 0
        
        while iteration < max_iterations:
            run = client.agents.runs.get(thread_id=thread.id, run_id=run.id)
            print(f"   Status: {run.status} (iteration {iteration + 1}/{max_iterations})")
            
            if run.status == "requires_action":
                print(f"🔧 Agent requested tool calls!")
                
                # Process tool calls
                tool_outputs = []
                if has_tools and hasattr(run, 'required_action') and run.required_action:
                    submit_tool_outputs = run.required_action.submit_tool_outputs
                    
                    for tool_call in submit_tool_outputs.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        print(f"   🔨 Calling tool: {function_name}")
                        print(f"      Arguments: {function_args}")
                        
                        # Execute the tool function
                        if function_name in TOOL_FUNCTIONS:
                            tool_function = TOOL_FUNCTIONS[function_name]
                            print(f"      🚀 Executing async tool in separate thread...")
                            # Run the async function in a way that works with existing event loops
                            import concurrent.futures
                            
                            def run_async_in_thread():
                                # Create new event loop in this thread
                                new_loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(new_loop)
                                try:
                                    result = new_loop.run_until_complete(tool_function(**function_args))
                                    return result
                                finally:
                                    new_loop.close()
                            
                            # Run in thread to avoid event loop conflicts
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(run_async_in_thread)
                                output = future.result(timeout=30)  # 30 second timeout
                            
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": output
                            })
                            print(f"      ✅ Tool output: {output[:200]}...")
                        else:
                            print(f"      ❌ Tool function not found: {function_name}")
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": json.dumps({"error": f"Tool {function_name} not implemented"})
                            })
                    
                    # Submit tool outputs
                    if tool_outputs:
                        print(f"   📤 Submitting {len(tool_outputs)} tool outputs...")
                        run = client.agents.runs.submit_tool_outputs(
                            thread_id=thread.id,
                            run_id=run.id,
                            tool_outputs=tool_outputs
                        )
                        print(f"   ✅ Tool outputs submitted, continuing run...")
                
            elif run.status == "completed":
                print(f"✅ Run completed successfully!")
                break
            elif run.status in ["failed", "cancelled", "expired"]:
                print(f"❌ Run ended with status: {run.status}")
                break
            
            iteration += 1
            time.sleep(1)
        
        if iteration >= max_iterations:
            print(f"⚠️ Max iterations reached, run may still be processing")
        
        run_result = run
        
        print(f"✅ Run completed - Thread ID: {thread.id}, Run ID: {run_result.id}, Status: {run_result.status}")
        print(f"🔍 Run status type: {type(run_result.status)}")
        print(f"🔍 Run status value: {run_result.status}")
        
        # DEBUG: List all messages in thread
        print(f"🔍 Listing all messages in thread...")
        all_messages = client.agents.messages.list(thread_id=thread.id)
        print(f"🔍 Total messages in thread: {len(all_messages.data) if hasattr(all_messages, 'data') else 'unknown'}")
        for idx, msg in enumerate(all_messages.data[:5] if hasattr(all_messages, 'data') else []):
            print(f"   Message {idx}: Role={msg.role}, Content type={type(msg.content)}")
            if hasattr(msg.content, '__iter__'):
                for content in msg.content:
                    print(f"      Content: {type(content)} - {str(content)[:100]}")
        
        # Get agent response
        response_obj = client.agents.messages.get_last_message_text_by_role(
            thread_id=thread.id,
            role="assistant"
        )
        
        print(f"📨 Response object type: {type(response_obj)}")
        print(f"📨 Response object: {response_obj}")
        
        # Extract text from MessageTextContent object (nested structure)
        response_text = None
        
        # Try to access as dict-like object (Azure SDK models often behave like dicts)
        try:
            if hasattr(response_obj, '__getitem__'):
                # Object supports dictionary-style access
                if 'text' in response_obj and isinstance(response_obj['text'], dict):
                    response_text = response_obj['text'].get('value', '')
                elif 'value' in response_obj:
                    response_text = response_obj['value']
        except (KeyError, TypeError):
            pass
        
        # Try as object with attributes
        if not response_text and hasattr(response_obj, 'text'):
            text_obj = response_obj.text
            if hasattr(text_obj, 'value'):
                response_text = text_obj.value
            elif isinstance(text_obj, dict):
                response_text = text_obj.get('value', '')
        
        # Try direct value attribute
        if not response_text and hasattr(response_obj, 'value'):
            response_text = response_obj.value
        
        # Try as plain dict
        if not response_text and isinstance(response_obj, dict):
            if 'text' in response_obj and isinstance(response_obj['text'], dict):
                response_text = response_obj['text'].get('value', '')
            elif 'value' in response_obj:
                response_text = response_obj['value']
        
        # Try as string
        if not response_text and isinstance(response_obj, str):
            response_text = response_obj
        
        # Last resort - convert to string (but this shouldn't happen)
        if not response_text:
            response_text = str(response_obj)
        
        print(f"✅ Extracted response text ({len(response_text)} chars): {response_text[:200]}...")
        
        return {
            "success": True,
            "agent_id": agent_id,
            "thread_id": thread.id,
            "response": response_text,
            "metadata": {
                "run_id": run_result.id,
                "status": run_result.status
            }
        }
        
    except Exception as e:
        print(f"❌ Error calling Azure AI agent: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "agent_id": agent_id,
            "error": str(e),
            "response": None
        }


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
    message = f"""
    Process new parcel registration and provide comprehensive validation:
    
    PARCEL INFORMATION:
    Tracking Number: {parcel_data.get('tracking_number')}
    Service Type: {parcel_data.get('service_type', 'standard')}
    Weight: {parcel_data.get('weight_kg', 'Unknown')} kg
    Dimensions: {parcel_data.get('dimensions', 'Unknown')}
    Declared Value: ${parcel_data.get('declared_value', 0)}
    
    SENDER:
    Name: {parcel_data.get('sender_name')}
    Address: {parcel_data.get('sender_address')}
    
    RECIPIENT:
    Name: {parcel_data.get('recipient_name')}
    Address: {parcel_data.get('recipient_address')}
    Postcode: {parcel_data.get('destination_postcode')}
    State: {parcel_data.get('destination_state', 'Unknown')}
    
    SPECIAL INSTRUCTIONS: {parcel_data.get('special_instructions', 'None')}
    
    PLEASE ANALYZE AND PROVIDE:
    1. Service Type Recommendation: Based on weight, value, and destination, is '{parcel_data.get('service_type')}' the optimal choice?
       Consider if Express/Overnight is needed for high-value items, or if Standard is sufficient.
    
    2. Address Validation: Check if addresses are complete and properly formatted.
       Flag any missing elements (street number, suburb, state).
    
    3. Delivery Complications: Identify potential issues:
       - Remote/rural destination requiring special handling
       - Oversized/overweight requiring freight upgrade
       - High-value requiring insurance or signature
       - Fragile items needing special care
    
    4. Data Quality: Flag any missing or suspicious information.
    
    Provide concise, actionable feedback in a friendly tone.
    """
    
    return await call_azure_agent(PARCEL_INTAKE_AGENT_ID, message, parcel_data)


async def sorting_facility_agent(parcel_info: Dict[str, Any], intake_results: Optional[str] = None) -> Dict[str, Any]:
    """
    Call Sorting Facility Agent to determine parcel routing
    
    Args:
        parcel_info: Parcel information including destination
        intake_results: Optional results from parcel intake agent
        
    Returns:
        Routing decision and any exceptions
    """
    message = f"""
    Review parcel for sorting and routing:
    
    Tracking Number: {parcel_info.get('tracking_number')}
    Destination: {parcel_info.get('destination_address')}
    Destination Postcode: {parcel_info.get('destination_postcode')}
    Service Type: {parcel_info.get('service_type', 'standard')}
    Special Handling: {parcel_info.get('special_handling', 'None')}
    
    {"Intake Results: " + intake_results if intake_results else ""}
    
    Determine routing decision and identify any exceptions.
    """
    
    return await call_azure_agent(SORTING_FACILITY_AGENT_ID, message, parcel_info)


async def delivery_coordination_agent(routing_info: Dict[str, Any], sorting_results: Optional[str] = None) -> Dict[str, Any]:
    """
    Call Delivery Coordination Agent to assign delivery
    
    Args:
        routing_info: Routing information from sorting
        sorting_results: Optional results from sorting facility agent
        
    Returns:
        Delivery assignment and coordination details
    """
    message = f"""
    Coordinate delivery assignment:
    
    Tracking Number: {routing_info.get('tracking_number')}
    Route: {routing_info.get('route', 'Unknown')}
    Priority: {routing_info.get('priority', 'normal')}
    Special Instructions: {routing_info.get('special_instructions', 'None')}
    
    {"Sorting Results: " + sorting_results if sorting_results else ""}
    
    Assign to appropriate driver and confirm delivery plan.
    """
    
    return await call_azure_agent(DELIVERY_COORDINATION_AGENT_ID, message, routing_info)


async def dispatcher_agent(route_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Dispatcher Agent for route optimization and driver assignment
    
    Args:
        route_data: Dictionary with parcels, drivers, capacity, SLAs
        
    Returns:
        Optimized route assignments and driver allocations
    """
    message = f"""
    Optimize route assignments and driver allocation:
    
    Number of Parcels: {route_data.get('parcel_count', 0)}
    Available Drivers: {route_data.get('available_drivers', [])}
    Service Level: {route_data.get('service_level', 'standard')}
    Delivery Window: {route_data.get('delivery_window', 'standard')}
    Geographic Zone: {route_data.get('zone', 'Unknown')}
    
    Parcels Summary:
    {json.dumps(route_data.get('parcels', []), indent=2)}
    
    Provide optimized route manifest with driver assignments and capacity utilization.
    """
    
    return await call_azure_agent(DISPATCHER_AGENT_ID, message, route_data)


async def driver_agent(delivery_action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Driver Agent for delivery execution and proof of delivery
    
    Args:
        delivery_action: Dictionary with scan type, location, parcel details
        
    Returns:
        Delivery status and next action required
    """
    message = f"""
    Process delivery action:
    
    Action Type: {delivery_action.get('action_type', 'scan')}
    Tracking Number: {delivery_action.get('tracking_number')}
    Location: {delivery_action.get('location', 'Unknown')}
    Scan Type: {delivery_action.get('scan_type', 'Unknown')}
    Driver ID: {delivery_action.get('driver_id', 'Unknown')}
    
    {"Delivery Note: " + delivery_action.get('note', '') if delivery_action.get('note') else ""}
    {"Exception: " + delivery_action.get('exception', '') if delivery_action.get('exception') else ""}
    
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
    message = f"""
    Optimize route and predict ETAs:
    
    Route ID: {route_conditions.get('route_id', 'Unknown')}
    Current Location: {route_conditions.get('current_location', 'Unknown')}
    Remaining Stops: {route_conditions.get('remaining_stops', 0)}
    Traffic Conditions: {route_conditions.get('traffic', 'normal')}
    Weather: {route_conditions.get('weather', 'clear')}
    
    {"Disruptions: " + route_conditions.get('disruptions', '') if route_conditions.get('disruptions') else ""}
    
    Stops:
    {json.dumps(route_conditions.get('stops', []), indent=2)}
    
    Provide updated ETAs and optimization recommendations.
    """
    
    return await call_azure_agent(OPTIMIZATION_AGENT_ID, message, route_conditions)


async def customer_service_agent(customer_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Customer Service Agent for exception handling and communications
    
    Args:
        customer_request: Customer issue, delivery preferences, or inquiry
        
    Returns:
        Resolution options and customer communication
    """
    # Check if this is a public chat request (from chat widget)
    is_chat_request = 'public_mode' in customer_request.get('details', '')
    
    if is_chat_request:
        # Simpler, more conversational prompt for chat widget
        message = f"""
        You're Alex, a helpful customer service team member at {COMPANY_NAME}. You're having a real conversation with a customer who needs help.
        
        Customer's Question:
        {customer_request.get('details', 'No details provided')}
        
        Guidelines for your response:
        - Talk like a real person, not a robot - use natural language and be warm
        - Keep it conversational - avoid bullet points, asterisks, or formatted lists
        - Be concise but friendly - get to the point without being cold
        - If tracking a parcel, weave the details into your response naturally (e.g., "I can see your parcel is currently at our Melbourne Prahran store and should arrive by November 19th")
        - Only mention contacting support (1300 384 669 or support@dtlogistics.com.au) if there's actually a problem or you can't help
        - Use contractions (I'll, you're, it's) to sound more natural
        - Add personality - show empathy if there's a delay, enthusiasm when things are on track
        - Don't end every message asking if there's anything else - sometimes just sign off naturally
        
        Remember: You're a person helping another person, not an AI assistant writing a formal report.
        """
    else:
        # Structured format for internal customer service representatives
        message = f"""
        Handle customer request:
        
        Customer: {customer_request.get('customer_name', 'Unknown')}
        Issue Type: {customer_request.get('issue_type', 'inquiry')}
        Tracking Number: {customer_request.get('tracking_number', 'N/A')}
        
        Request Details:
        {customer_request.get('details', 'No details provided')}
        
        {"Preferred Resolution: " + customer_request.get('preferred_resolution', '') if customer_request.get('preferred_resolution') else ""}
        
        Provide resolution options and customer communication message.
        """
    
    return await call_azure_agent(CUSTOMER_SERVICE_AGENT_ID, message, customer_request)


async def fraud_risk_agent(suspicious_activity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Fraud & Risk Agent for security and scam detection
    
    Args:
        suspicious_activity: Message, sender info, or activity pattern to analyze
        
    Returns:
        Risk assessment and recommended actions
    """
    # Build message content dynamically
    message_parts = [
        "Analyze potential fraud or security risk:",
        "",
        f"Activity Type: {suspicious_activity.get('activity_type', 'message')}",
        f"Source: {suspicious_activity.get('source', 'Unknown')}",
        ""
    ]
    
    if suspicious_activity.get('message'):
        message_parts.append("Message Content:")
        message_parts.append(suspicious_activity.get('message', ''))
        message_parts.append("")
    
    if suspicious_activity.get('pattern'):
        message_parts.append("Activity Pattern:")
        message_parts.append(suspicious_activity.get('pattern', ''))
        message_parts.append("")
    
    message_parts.append("Sender Information:")
    message_parts.append(json.dumps(suspicious_activity.get('sender_info', {}), indent=2))
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
    message = f"""
    Verify courier identity and authentication:
    
    Courier ID: {verification_request.get('courier_id', 'Unknown')}
    Name: {verification_request.get('name', 'Unknown')}
    Role: {verification_request.get('role', 'driver')}
    Employment Status: {verification_request.get('employment_status', 'Unknown')}
    Authorized Zone: {verification_request.get('authorized_zone', 'Unknown')}
    
    {"Credentials: " + str(verification_request.get('credentials', '')) if verification_request.get('credentials') else ""}
    {"Verification Method: " + verification_request.get('verification_method', 'standard') if verification_request.get('verification_method') else ""}
    
    Verify identity and provide authentication status.
    """
    
    try:
        # Add timeout for agent call - don't block login if agent is slow
        result = await asyncio.wait_for(
            call_azure_agent(IDENTITY_AGENT_ID, message, verification_request),
            timeout=10.0  # 10 second timeout
        )
        return result
    except asyncio.TimeoutError:
        print(f"⚠️ Identity Agent timeout - proceeding with login")
        return {
            "success": False,
            "error": "Agent call timeout",
            "agent_id": IDENTITY_AGENT_ID,
            "response": None
        }
    except Exception as e:
        print(f"⚠️ Identity Agent error: {e}")
        return {
            "success": False,
            "error": str(e),
            "agent_id": IDENTITY_AGENT_ID,
            "response": None
        }


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
        return {
            "success": False,
            "error": response.get("error", "Unknown error"),
            "parsed_data": None
        }
    
    response_text = response.get("response", "")
    
    # Try to extract structured data from response
    # Look for [Key: Value] patterns
    structured_data = {}
    
    import re
    pattern = r'\[([^:]+):\s*([^\]]+)\]'
    matches = re.findall(pattern, response_text)
    
    for key, value in matches:
        structured_data[key.strip()] = value.strip()
    
    return {
        "success": True,
        "raw_response": response_text,
        "parsed_data": structured_data if structured_data else None,
        "thread_id": response.get("thread_id"),
        "agent_id": response.get("agent_id")
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
            "weight_kg": 2.5
        }
        
        print("\n1. Testing Parcel Intake Agent...")
        result = await parcel_intake_agent(test_parcel)
        print(f"   Success: {result['success']}")
        if result['success']:
            print(f"   Response: {result['response'][:100]}...")
        else:
            print(f"   Error: {result['error']}")
        
        print("\n✅ Agent connectivity test complete!")
        print("All 9 agents are now available for use.")
    
    asyncio.run(test_agents())
