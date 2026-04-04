"""
State Management Infrastructure

Manages workflow state, agent context, and process coordination.
"""

from .state_manager import (
    StateManager,
    AgentDecision,
    AgentContext,
    AgentPerformanceMetrics,
    ApprovalRequest,
    WorkflowState,
)

__all__ = [
    "StateManager",
    "AgentDecision",
    "AgentContext",
    "AgentPerformanceMetrics",
    "ApprovalRequest",
    "WorkflowState",
]
