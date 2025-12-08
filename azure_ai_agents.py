"""
Azure AI Foundry Agent Integration Layer
Provides unified interface to call all 9 Azure AI Foundry persistent agents
This module replaces local Python agent implementations with real Azure AI agents
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

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
            credential = DefaultAzureCredential()
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
    try:
        client = AzureAIAgentClient().get_client()
        
        # Add context to message if provided
        if context:
            context_str = f"\n\nContext:\n{json.dumps(context, indent=2)}"
            full_message = message + context_str
        else:
            full_message = message
        
        # Create thread and run agent
        run_result = client.agents.create_thread_and_process_run(
            agent_id=agent_id,
            thread={
                "messages": [{"role": "user", "content": full_message}]
            }
        )
        
        # Get agent response
        response_obj = client.agents.messages.get_last_message_text_by_role(
            thread_id=run_result.thread_id,
            role="assistant"
        )
        
        # Extract text from MessageTextContent object (nested structure)
        if isinstance(response_obj, dict):
            # Handle {'type': 'text', 'text': {'value': '...'}} structure
            if 'text' in response_obj and isinstance(response_obj['text'], dict):
                response_text = response_obj['text'].get('value', str(response_obj))
            else:
                response_text = response_obj.get('value', str(response_obj))
        elif hasattr(response_obj, 'value'):
            response_text = response_obj.value
        elif isinstance(response_obj, str):
            response_text = response_obj
        else:
            response_text = str(response_obj)
        
        return {
            "success": True,
            "agent_id": agent_id,
            "thread_id": run_result.thread_id,
            "response": response_text,
            "metadata": {
                "run_id": run_result.id,
                "status": run_result.status
            }
        }
        
    except Exception as e:
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
    
    Args:
        parcel_data: Dictionary with parcel information (tracking_number, sender, recipient, etc.)
        
    Returns:
        Validation results with status and any issues found
    """
    message = f"""
    Process new parcel registration:
    
    Tracking Number: {parcel_data.get('tracking_number')}
    Sender: {parcel_data.get('sender_name')} ({parcel_data.get('sender_address')})
    Recipient: {parcel_data.get('recipient_name')} ({parcel_data.get('recipient_address')})
    Service Type: {parcel_data.get('service_type', 'standard')}
    Weight: {parcel_data.get('weight_kg', 'Unknown')} kg
    Dimensions: {parcel_data.get('dimensions', 'Unknown')}
    Special Instructions: {parcel_data.get('special_instructions', 'None')}
    
    Validate all fields and identify any issues or missing information.
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
    
    return await call_azure_agent(IDENTITY_AGENT_ID, message, verification_request)


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
