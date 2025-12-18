"""
DT Logistics - State Manager Module
Manages workflow state, agent context, and process coordination
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class WorkflowState(Enum):
    """Workflow states for parcel processing"""
    REGISTERED = "Registered"
    IN_TRANSIT = "In Transit"
    AT_SORTING_FACILITY = "At Sorting Facility"
    AWAITING_APPROVAL = "Awaiting Approval"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    OUT_FOR_DELIVERY = "Out for Delivery"
    DELIVERED = "Delivered"
    FAILED_DELIVERY = "Failed Delivery"
    RETURNED = "Returned to Sender"

@dataclass
class AgentContext:
    """Context information passed between AI agents"""
    agent_name: str
    tracking_number: str
    current_state: WorkflowState
    metadata: Dict[str, Any] = field(default_factory=dict)
    messages: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class AgentDecision:
    """Record of an AI agent decision for audit trail"""
    decision_id: str
    agent_name: str
    agent_type: str  # fraud_detection, route_optimization, exception_resolution, etc.
    tracking_number: Optional[str]
    decision_type: str  # approve, reject, optimize, notify, resolve
    decision_action: str  # Specific action taken
    confidence_score: float  # 0-1
    reasoning: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time_ms: float = 0.0
    
@dataclass
class AgentPerformanceMetrics:
    """Performance metrics for an AI agent"""
    agent_name: str
    agent_type: str
    total_decisions: int = 0
    successful_decisions: int = 0
    failed_decisions: int = 0
    average_confidence: float = 0.0
    average_execution_time_ms: float = 0.0
    last_execution: Optional[datetime] = None
    decisions_by_type: Dict[str, int] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_decisions == 0:
            return 0.0
        return self.successful_decisions / self.total_decisions
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate"""
        if self.total_decisions == 0:
            return 0.0
        return self.failed_decisions / self.total_decisions

@dataclass
class ApprovalRequest:
    """Approval request for human-in-the-loop workflow"""
    request_id: str
    request_type: str
    tracking_number: str
    requester_agent: str
    approval_reason: str
    context_data: Dict[str, Any]
    status: str  # Pending, Approved, Rejected
    requested_at: datetime
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None

class StateManager:
    """
    Manages workflow state transitions and agent coordination
    """
    
    def __init__(self):
        """Initialize state manager"""
        self.parcel_states: Dict[str, WorkflowState] = {}
        self.agent_contexts: Dict[str, List[AgentContext]] = {}
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        self.state_history: Dict[str, List[tuple[WorkflowState, datetime]]] = {}
        self.agent_decisions: List[AgentDecision] = []
        self.agent_metrics: Dict[str, AgentPerformanceMetrics] = {}
    
    def record_agent_decision(
        self,
        decision: AgentDecision,
        success: bool = True
    ) -> None:
        """
        Record an agent decision for audit trail and performance tracking
        
        Args:
            decision: AgentDecision object
            success: Whether the decision execution was successful
        """
        # Add to decision log
        self.agent_decisions.append(decision)
        
        # Update agent metrics
        agent_key = f"{decision.agent_type}:{decision.agent_name}"
        
        if agent_key not in self.agent_metrics:
            self.agent_metrics[agent_key] = AgentPerformanceMetrics(
                agent_name=decision.agent_name,
                agent_type=decision.agent_type
            )
        
        metrics = self.agent_metrics[agent_key]
        metrics.total_decisions += 1
        
        if success:
            metrics.successful_decisions += 1
        else:
            metrics.failed_decisions += 1
        
        # Update average confidence
        prev_avg = metrics.average_confidence
        total = metrics.total_decisions
        metrics.average_confidence = (prev_avg * (total - 1) + decision.confidence_score) / total
        
        # Update average execution time
        prev_avg_time = metrics.average_execution_time_ms
        metrics.average_execution_time_ms = (prev_avg_time * (total - 1) + decision.execution_time_ms) / total
        
        # Update decision type counts
        if decision.decision_type not in metrics.decisions_by_type:
            metrics.decisions_by_type[decision.decision_type] = 0
        metrics.decisions_by_type[decision.decision_type] += 1
        
        metrics.last_execution = decision.timestamp
    
    def get_agent_decisions(
        self,
        agent_name: Optional[str] = None,
        agent_type: Optional[str] = None,
        tracking_number: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentDecision]:
        """
        Get agent decisions with optional filtering
        
        Args:
            agent_name: Filter by agent name
            agent_type: Filter by agent type
            tracking_number: Filter by tracking number
            limit: Maximum number of results
        
        Returns:
            List of AgentDecision objects
        """
        decisions = self.agent_decisions
        
        if agent_name:
            decisions = [d for d in decisions if d.agent_name == agent_name]
        
        if agent_type:
            decisions = [d for d in decisions if d.agent_type == agent_type]
        
        if tracking_number:
            decisions = [d for d in decisions if d.tracking_number == tracking_number]
        
        # Sort by timestamp descending (most recent first)
        decisions = sorted(decisions, key=lambda d: d.timestamp, reverse=True)
        
        return decisions[:limit]
    
    def get_agent_performance(
        self,
        agent_name: Optional[str] = None,
        agent_type: Optional[str] = None
    ) -> List[AgentPerformanceMetrics]:
        """
        Get performance metrics for agents
        
        Args:
            agent_name: Filter by agent name
            agent_type: Filter by agent type
        
        Returns:
            List of AgentPerformanceMetrics objects
        """
        metrics = list(self.agent_metrics.values())
        
        if agent_name:
            metrics = [m for m in metrics if m.agent_name == agent_name]
        
        if agent_type:
            metrics = [m for m in metrics if m.agent_type == agent_type]
        
        return metrics
    
    def get_agent_dashboard_data(self) -> Dict[str, Any]:
        """
        Get comprehensive agent performance data for dashboard
        
        Returns:
            Dictionary with agent performance summary
        """
        total_decisions = len(self.agent_decisions)
        
        if total_decisions == 0:
            return {
                "total_decisions": 0,
                "overall_avg_confidence": 0,
                "overall_avg_execution_ms": 0,
                "agents": [],
                "decision_types": {},
                "recent_decisions": [],
                "configured_active_agents": 8
            }
        
        # Calculate overall metrics
        successful = sum(1 for d in self.agent_decisions if any(
            m.successful_decisions > 0 and m.agent_name == d.agent_name
            for m in self.agent_metrics.values()
        ))
        
        avg_confidence = sum(d.confidence_score for d in self.agent_decisions) / total_decisions
        avg_execution = sum(d.execution_time_ms for d in self.agent_decisions) / total_decisions
        
        # Decision types breakdown
        decision_types = {}
        for decision in self.agent_decisions:
            dt = decision.decision_type
            if dt not in decision_types:
                decision_types[dt] = 0
            decision_types[dt] += 1
        
        # Agent summaries
        agents = []
        for metrics in self.agent_metrics.values():
            agents.append({
                "name": metrics.agent_name,
                "type": metrics.agent_type,
                "total_decisions": metrics.total_decisions,
                "success_rate": metrics.success_rate,
                "avg_confidence": metrics.average_confidence,
                "avg_execution_ms": metrics.average_execution_time_ms,
                "last_execution": metrics.last_execution.isoformat() if metrics.last_execution else None
            })
        
        # Recent decisions (last 10)
        recent = self.get_agent_decisions(limit=10)
        recent_decisions = [
            {
                "decision_id": d.decision_id,
                "agent": d.agent_name,
                "type": d.decision_type,
                "action": d.decision_action,
                "confidence": d.confidence_score,
                "timestamp": d.timestamp.isoformat()
            }
            for d in recent
        ]
        
        return {
            "total_decisions": total_decisions,
            "overall_avg_confidence": avg_confidence,
            "overall_avg_execution_ms": avg_execution,
            "agents": agents,
            "decision_types": decision_types,
            "recent_decisions": recent_decisions,
            "configured_active_agents": 8
        }
    
    def register_parcel(self, tracking_number: str) -> None:
        """Register a new parcel in the system"""
        self.parcel_states[tracking_number] = WorkflowState.REGISTERED
        self.state_history[tracking_number] = [(WorkflowState.REGISTERED, datetime.now())]
        self.agent_contexts[tracking_number] = []
    
    def get_current_state(self, tracking_number: str) -> Optional[WorkflowState]:
        """Get current workflow state for a parcel"""
        return self.parcel_states.get(tracking_number)
    
    def transition_state(
        self,
        tracking_number: str,
        new_state: WorkflowState,
        agent_name: str = "System",
        notes: Optional[str] = None
    ) -> bool:
        """
        Transition parcel to a new workflow state
        
        Args:
            tracking_number: Parcel tracking number
            new_state: Target workflow state
            agent_name: Name of agent requesting transition
            notes: Optional transition notes
        
        Returns:
            True if transition successful, False otherwise
        """
        current_state = self.parcel_states.get(tracking_number)
        
        if not current_state:
            print(f"Error: Parcel {tracking_number} not found in state manager")
            return False
        
        # Validate state transition
        if not self._is_valid_transition(current_state, new_state):
            print(f"Error: Invalid state transition from {current_state.value} to {new_state.value}")
            return False
        
        # Update state
        self.parcel_states[tracking_number] = new_state
        
        # Record history
        if tracking_number not in self.state_history:
            self.state_history[tracking_number] = []
        self.state_history[tracking_number].append((new_state, datetime.now()))
        
        # Create agent context
        context = AgentContext(
            agent_name=agent_name,
            tracking_number=tracking_number,
            current_state=new_state,
            metadata={"notes": notes} if notes else {},
            messages=[f"State transitioned to {new_state.value}"]
        )
        
        if tracking_number not in self.agent_contexts:
            self.agent_contexts[tracking_number] = []
        self.agent_contexts[tracking_number].append(context)
        
        return True
    
    def _is_valid_transition(self, current: WorkflowState, target: WorkflowState) -> bool:
        """
        Validate if state transition is allowed
        
        Valid transitions:
        - REGISTERED → IN_TRANSIT, AT_SORTING_FACILITY
        - IN_TRANSIT → AT_SORTING_FACILITY, OUT_FOR_DELIVERY
        - AT_SORTING_FACILITY → AWAITING_APPROVAL, OUT_FOR_DELIVERY
        - AWAITING_APPROVAL → APPROVED, REJECTED
        - APPROVED → OUT_FOR_DELIVERY
        - OUT_FOR_DELIVERY → DELIVERED, FAILED_DELIVERY
        - FAILED_DELIVERY → OUT_FOR_DELIVERY, RETURNED
        - Any state → RETURNED (exception handling)
        """
        valid_transitions = {
            WorkflowState.REGISTERED: [
                WorkflowState.IN_TRANSIT,
                WorkflowState.AT_SORTING_FACILITY,
                WorkflowState.RETURNED
            ],
            WorkflowState.IN_TRANSIT: [
                WorkflowState.AT_SORTING_FACILITY,
                WorkflowState.OUT_FOR_DELIVERY,
                WorkflowState.RETURNED
            ],
            WorkflowState.AT_SORTING_FACILITY: [
                WorkflowState.AWAITING_APPROVAL,
                WorkflowState.OUT_FOR_DELIVERY,
                WorkflowState.RETURNED
            ],
            WorkflowState.AWAITING_APPROVAL: [
                WorkflowState.APPROVED,
                WorkflowState.REJECTED,
                WorkflowState.RETURNED
            ],
            WorkflowState.APPROVED: [
                WorkflowState.OUT_FOR_DELIVERY,
                WorkflowState.RETURNED
            ],
            WorkflowState.REJECTED: [
                WorkflowState.AT_SORTING_FACILITY,
                WorkflowState.RETURNED
            ],
            WorkflowState.OUT_FOR_DELIVERY: [
                WorkflowState.DELIVERED,
                WorkflowState.FAILED_DELIVERY,
                WorkflowState.RETURNED
            ],
            WorkflowState.FAILED_DELIVERY: [
                WorkflowState.OUT_FOR_DELIVERY,
                WorkflowState.RETURNED
            ],
            WorkflowState.DELIVERED: [],  # Terminal state
            WorkflowState.RETURNED: []  # Terminal state
        }
        
        return target in valid_transitions.get(current, [])
    
    def create_approval_request(
        self,
        request_id: str,
        request_type: str,
        tracking_number: str,
        requester_agent: str,
        approval_reason: str,
        context_data: Dict[str, Any]
    ) -> ApprovalRequest:
        """
        Create a new approval request for human review
        
        Args:
            request_id: Unique request identifier
            request_type: Type of approval (delivery_exception, address_change, etc.)
            tracking_number: Related parcel tracking number
            requester_agent: Agent requesting approval
            approval_reason: Reason for approval request
            context_data: Additional context information
        
        Returns:
            ApprovalRequest object
        """
        approval = ApprovalRequest(
            request_id=request_id,
            request_type=request_type,
            tracking_number=tracking_number,
            requester_agent=requester_agent,
            approval_reason=approval_reason,
            context_data=context_data,
            status="Pending",
            requested_at=datetime.now()
        )
        
        self.pending_approvals[request_id] = approval
        
        # Transition parcel to awaiting approval state
        self.transition_state(tracking_number, WorkflowState.AWAITING_APPROVAL, requester_agent)
        
        return approval
    
    def process_approval(
        self,
        request_id: str,
        approved: bool,
        reviewer: str,
        review_notes: Optional[str] = None
    ) -> bool:
        """
        Process an approval request
        
        Args:
            request_id: Approval request ID
            approved: True if approved, False if rejected
            reviewer: Name of person reviewing
            review_notes: Optional review notes
        
        Returns:
            True if processed successfully
        """
        approval = self.pending_approvals.get(request_id)
        
        if not approval:
            print(f"Error: Approval request {request_id} not found")
            return False
        
        if approval.status != "Pending":
            print(f"Error: Approval request {request_id} already processed")
            return False
        
        # Update approval
        approval.status = "Approved" if approved else "Rejected"
        approval.reviewed_by = reviewer
        approval.reviewed_at = datetime.now()
        approval.review_notes = review_notes
        
        # Transition parcel state
        tracking_number = approval.tracking_number
        if approved:
            self.transition_state(tracking_number, WorkflowState.APPROVED, f"Supervisor:{reviewer}")
        else:
            self.transition_state(tracking_number, WorkflowState.REJECTED, f"Supervisor:{reviewer}")
        
        return True
    
    def get_pending_approvals(self) -> List[ApprovalRequest]:
        """Get all pending approval requests"""
        return [
            approval for approval in self.pending_approvals.values()
            if approval.status == "Pending"
        ]
    
    def get_parcel_history(self, tracking_number: str) -> List[tuple[WorkflowState, datetime]]:
        """Get state transition history for a parcel"""
        return self.state_history.get(tracking_number, [])
    
    def get_agent_context(self, tracking_number: str) -> List[AgentContext]:
        """Get agent context history for a parcel"""
        return self.agent_contexts.get(tracking_number, [])
    
    def add_agent_message(self, tracking_number: str, agent_name: str, message: str) -> None:
        """Add a message to agent context"""
        current_state = self.parcel_states.get(tracking_number, WorkflowState.REGISTERED)
        
        context = AgentContext(
            agent_name=agent_name,
            tracking_number=tracking_number,
            current_state=current_state,
            messages=[message]
        )
        
        if tracking_number not in self.agent_contexts:
            self.agent_contexts[tracking_number] = []
        self.agent_contexts[tracking_number].append(context)
    
    def get_state_summary(self) -> Dict[str, int]:
        """Get count of parcels in each state"""
        summary = {}
        for state in WorkflowState:
            count = sum(1 for s in self.parcel_states.values() if s == state)
            if count > 0:
                summary[state.value] = count
        return summary

# Example usage and testing
if __name__ == "__main__":
    print("DT Logistics - State Manager Module")
    print("=" * 50)
    
    # Create state manager
    manager = StateManager()
    
    # Register parcel
    tracking_num = "DTVIC12345678"
    print(f"\nRegistering parcel: {tracking_num}")
    manager.register_parcel(tracking_num)
    print(f"Current state: {manager.get_current_state(tracking_num).value}")
    
    # Transition through workflow
    print("\nTransitioning through workflow...")
    transitions = [
        (WorkflowState.IN_TRANSIT, "Parcel Intake Agent", "Parcel accepted at intake"),
        (WorkflowState.AT_SORTING_FACILITY, "Sorting Agent", "Arrived at sorting facility"),
        (WorkflowState.AWAITING_APPROVAL, "Sorting Agent", "Requires supervisor approval"),
    ]
    
    for new_state, agent, notes in transitions:
        success = manager.transition_state(tracking_num, new_state, agent, notes)
        if success:
            print(f"  ✓ {agent}: {new_state.value}")
        else:
            print(f"  ✗ Failed: {new_state.value}")
    
    # Create approval request
    print("\nCreating approval request...")
    approval = manager.create_approval_request(
        request_id="APPR_001",
        request_type="delivery_exception",
        tracking_number=tracking_num,
        requester_agent="Sorting Agent",
        approval_reason="Weekend delivery required",
        context_data={"customer_priority": "high", "delivery_date": "2024-01-20"}
    )
    print(f"  Request ID: {approval.request_id}")
    print(f"  Status: {approval.status}")
    
    # Process approval
    print("\nProcessing approval...")
    manager.process_approval("APPR_001", True, "Supervisor Mike", "Approved for weekend delivery")
    
    # Show history
    print(f"\nState History for {tracking_num}:")
    for state, timestamp in manager.get_parcel_history(tracking_num):
        print(f"  {timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {state.value}")
    
    # Show summary
    print("\nState Summary:")
    for state, count in manager.get_state_summary().items():
        print(f"  {state}: {count}")
