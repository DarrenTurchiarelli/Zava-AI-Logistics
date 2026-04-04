"""
Infrastructure: Agents
Azure AI Foundry agent integration and orchestration
"""

# Import core agent functions from the core module
from .core.base import (
    call_agent_sync,
    customer_service_agent,
    delivery_coordination_agent,
    dispatcher_agent,
    driver_agent,
    identity_agent,
    optimization_agent,
    parcel_intake_agent,
    sorting_facility_agent,
)
from .core.fraud import analyze_with_fraud_agent, fraud_risk_agent
from .core.manifest import ManifestGenerationAgent
from .core.prompt_loader import get_agent_prompt, get_agent_skills, list_available_agents

__all__ = [
    # Core agent functions
    "call_agent_sync",
    "customer_service_agent",
    "delivery_coordination_agent",
    "dispatcher_agent",
    "driver_agent",
    "identity_agent",
    "optimization_agent",
    "parcel_intake_agent",
    "sorting_facility_agent",
    # Fraud detection
    "fraud_risk_agent",
    "analyze_with_fraud_agent",
    # Manifest generation
    "ManifestGenerationAgent",
    # Utilities
    "get_agent_prompt",
    "get_agent_skills",
    "list_available_agents",
]
