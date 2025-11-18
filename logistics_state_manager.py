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
