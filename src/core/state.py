"""State Machine for project lifecycle management"""

from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


class ProjectState(str, Enum):
    """Valid project states"""
    CREATED = "CREATED"
    RESEARCH = "RESEARCH"
    STRATEGY = "STRATEGY"
    CONTENT = "CONTENT"
    DESIGN = "DESIGN"
    PDF = "PDF"
    VISUALS = "VISUALS"
    QUALITY_CHECK = "QUALITY_CHECK"
    CORRECTION = "CORRECTION"
    SEO = "SEO"
    PRICING = "PRICING"
    IP_CHECK = "IP_CHECK"
    FINALIZATION = "FINALIZATION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted"""
    pass


@dataclass
class StateTransition:
    """Record of a state change"""
    from_state: ProjectState
    to_state: ProjectState
    timestamp: datetime
    attempt: int
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateMachine:
    """Manages project state transitions"""
    
    # Valid transitions
    VALID_TRANSITIONS = {
        ProjectState.CREATED: [ProjectState.RESEARCH, ProjectState.FAILED],
        ProjectState.RESEARCH: [ProjectState.STRATEGY, ProjectState.FAILED],
        ProjectState.STRATEGY: [ProjectState.CONTENT, ProjectState.FAILED],
        ProjectState.CONTENT: [ProjectState.DESIGN, ProjectState.FAILED],
        ProjectState.DESIGN: [ProjectState.PDF, ProjectState.FAILED],
        ProjectState.PDF: [ProjectState.VISUALS, ProjectState.QUALITY_CHECK, ProjectState.FAILED],
        ProjectState.VISUALS: [ProjectState.QUALITY_CHECK, ProjectState.FAILED],
        ProjectState.QUALITY_CHECK: [ProjectState.CORRECTION, ProjectState.SEO, ProjectState.FAILED, ProjectState.NEEDS_REVIEW],
        ProjectState.CORRECTION: [ProjectState.PDF, ProjectState.FAILED],
        ProjectState.SEO: [ProjectState.PRICING, ProjectState.FAILED],
        ProjectState.PRICING: [ProjectState.IP_CHECK, ProjectState.FAILED],
        ProjectState.IP_CHECK: [ProjectState.FINALIZATION, ProjectState.FAILED, ProjectState.NEEDS_REVIEW],
        ProjectState.FINALIZATION: [ProjectState.COMPLETED, ProjectState.FAILED],
        ProjectState.COMPLETED: [],
        ProjectState.FAILED: [ProjectState.RESEARCH],
        ProjectState.NEEDS_REVIEW: [ProjectState.RESEARCH, ProjectState.COMPLETED],
    }
    
    def __init__(self, initial_state: ProjectState = ProjectState.CREATED):
        self.current_state = initial_state
        self.history: List[StateTransition] = []
        self.attempt = 0
    
    def transition(
        self, 
        new_state: ProjectState, 
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StateTransition:
        """
        Transition to a new state.
        
        Args:
            new_state: Target state
            reason: Reason for transition
            metadata: Additional context
            
        Returns:
            StateTransition record
            
        Raises:
            StateTransitionError: If transition is invalid
        """
        if new_state not in self.VALID_TRANSITIONS.get(self.current_state, []):
            raise StateTransitionError(
                f"Invalid transition from {self.current_state} to {new_state}"
            )
        
        self.attempt += 1
        transition = StateTransition(
            from_state=self.current_state,
            to_state=new_state,
            timestamp=datetime.utcnow(),
            attempt=self.attempt,
            reason=reason,
            metadata=metadata or {}
        )
        
        self.history.append(transition)
        self.current_state = new_state
        return transition
    
    def can_transition(self, new_state: ProjectState) -> bool:
        """Check if transition is valid without executing it"""
        return new_state in self.VALID_TRANSITIONS.get(self.current_state, [])
    
    def get_valid_next_states(self) -> List[ProjectState]:
        """Get list of valid next states"""
        return self.VALID_TRANSITIONS.get(self.current_state, [])
    
    def reset(self):
        """Reset to initial state (for testing)"""
        self.current_state = ProjectState.CREATED
        self.history = []
        self.attempt = 0
