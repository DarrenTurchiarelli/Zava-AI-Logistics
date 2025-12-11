"""
Agents package - AI agent implementations for DT Logistics
"""

from .base import (
    AzureAIAgentClient,
    call_azure_agent,
    call_agent_sync,
    parcel_intake_agent,
    sorting_facility_agent,
    delivery_coordination_agent,
    dispatcher_agent,
    driver_agent,
    optimization_agent,
    customer_service_agent,
    fraud_risk_agent as base_fraud_risk_agent,
    identity_agent,
    parse_agent_response
)

from .fraud import analyze_with_fraud_agent, fraud_risk_agent
from .manifest import ManifestGenerationAgent

__all__ = [
    'AzureAIAgentClient',
    'call_azure_agent',
    'call_agent_sync',
    'parcel_intake_agent',
    'sorting_facility_agent',
    'delivery_coordination_agent',
    'dispatcher_agent',
    'driver_agent',
    'optimization_agent',
    'customer_service_agent',
    'fraud_risk_agent',
    'identity_agent',
    'parse_agent_response',
    'analyze_with_fraud_agent',
    'ManifestGenerationAgent'
]
