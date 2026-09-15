"""Tests for State Machine"""

import pytest
from datetime import datetime
from src.core.state import StateMachine, ProjectState, StateTransitionError


class TestStateMachine:
    """Test suite for StateMachine"""
    
    def test_initial_state(self):
        """Test that state machine starts in CREATED state"""
        sm = StateMachine()
        assert sm.current_state == ProjectState.CREATED
        assert sm.attempt == 0
        assert len(sm.history) == 0
    
    def test_valid_transition_created_to_research(self):
        """Test valid transition CREATED -> RESEARCH"""
        sm = StateMachine()
        transition = sm.transition(ProjectState.RESEARCH, reason="Start market research")
        
        assert sm.current_state == ProjectState.RESEARCH
        assert transition.from_state == ProjectState.CREATED
        assert transition.to_state == ProjectState.RESEARCH
        assert transition.reason == "Start market research"
        assert transition.attempt == 1
        assert isinstance(transition.timestamp, datetime)
        assert len(sm.history) == 1
    
    def test_valid_transition_sequence(self):
        """Test a valid sequence of transitions"""
        sm = StateMachine()
        
        # CREATED -> RESEARCH
        sm.transition(ProjectState.RESEARCH)
        assert sm.current_state == ProjectState.RESEARCH
        
        # RESEARCH -> STRATEGY
        sm.transition(ProjectState.STRATEGY)
        assert sm.current_state == ProjectState.STRATEGY
        
        # STRATEGY -> CONTENT
        sm.transition(ProjectState.CONTENT)
        assert sm.current_state == ProjectState.CONTENT
        
        assert len(sm.history) == 3
    
    def test_invalid_transition_raises_error(self):
        """Test that invalid transition raises StateTransitionError"""
        sm = StateMachine()
        
        # Can't go from CREATED to DESIGN directly
        with pytest.raises(StateTransitionError) as exc_info:
            sm.transition(ProjectState.DESIGN)
        
        assert "Invalid transition" in str(exc_info.value)
        assert sm.current_state == ProjectState.CREATED  # State unchanged
    
    def test_can_transition(self):
        """Test can_transition method"""
        sm = StateMachine()
        
        # From CREATED, can transition to RESEARCH
        assert sm.can_transition(ProjectState.RESEARCH) is True
        
        # From CREATED, cannot transition to DESIGN
        assert sm.can_transition(ProjectState.DESIGN) is False
        
        # After transition, valid next states change
        sm.transition(ProjectState.RESEARCH)
        assert sm.can_transition(ProjectState.STRATEGY) is True
        assert sm.can_transition(ProjectState.CONTENT) is False
    
    def test_get_valid_next_states(self):
        """Test get_valid_next_states method"""
        sm = StateMachine()
        
        # From CREATED, valid states are RESEARCH and FAILED
        valid_states = sm.get_valid_next_states()
        assert ProjectState.RESEARCH in valid_states
        assert ProjectState.FAILED in valid_states
        assert ProjectState.STRATEGY not in valid_states
    
    def test_transition_with_metadata(self):
        """Test transition with metadata"""
        sm = StateMachine()
        metadata = {"product_type": "pdf", "category": "planners"}
        
        transition = sm.transition(
            ProjectState.RESEARCH,
            reason="Market research started",
            metadata=metadata
        )
        
        assert transition.metadata == metadata
        assert sm.history[0].metadata == metadata
    
    def test_history_tracks_all_transitions(self):
        """Test that history records all transitions"""
        sm = StateMachine()
        
        sm.transition(ProjectState.RESEARCH)
        sm.transition(ProjectState.STRATEGY)
        sm.transition(ProjectState.CONTENT)
        
        assert len(sm.history) == 3
        assert sm.history[0].from_state == ProjectState.CREATED
        assert sm.history[1].from_state == ProjectState.RESEARCH
        assert sm.history[2].from_state == ProjectState.STRATEGY
    
    def test_attempt_counter_increments(self):
        """Test that attempt counter increments with each transition"""
        sm = StateMachine()
        
        assert sm.attempt == 0
        sm.transition(ProjectState.RESEARCH)
        assert sm.attempt == 1
        
        sm.transition(ProjectState.STRATEGY)
        assert sm.attempt == 2
        
        sm.transition(ProjectState.CONTENT)
        assert sm.attempt == 3
    
    def test_reset_functionality(self):
        """Test reset method"""
        sm = StateMachine()
        
        sm.transition(ProjectState.RESEARCH)
        sm.transition(ProjectState.STRATEGY)
        
        assert sm.current_state == ProjectState.STRATEGY
        assert sm.attempt == 2
        assert len(sm.history) == 2
        
        sm.reset()
        
        assert sm.current_state == ProjectState.CREATED
        assert sm.attempt == 0
        assert len(sm.history) == 0
    
    def test_transition_to_failed_state(self):
        """Test transition to FAILED state"""
        sm = StateMachine()
        sm.transition(ProjectState.RESEARCH)
        sm.transition(ProjectState.STRATEGY)
        
        # Transition to FAILED should be valid
        assert sm.can_transition(ProjectState.FAILED) is True
        
        sm.transition(ProjectState.FAILED, reason="Error during strategy phase")
        assert sm.current_state == ProjectState.FAILED
    
    def test_retry_from_failed_state(self):
        """Test retry capability from FAILED state"""
        sm = StateMachine()
        sm.transition(ProjectState.RESEARCH)
        sm.transition(ProjectState.FAILED)
        
        # From FAILED, should be able to transition back to RESEARCH
        assert sm.can_transition(ProjectState.RESEARCH) is True
        
        sm.transition(ProjectState.RESEARCH, reason="Retrying after failure")
        assert sm.current_state == ProjectState.RESEARCH
    
    def test_completed_state_is_terminal(self):
        """Test that COMPLETED state has no valid transitions"""
        sm = StateMachine()
        
        # Manually set to COMPLETED for testing
        sm.current_state = ProjectState.COMPLETED
        
        valid_next = sm.get_valid_next_states()
        assert len(valid_next) == 0
    
    def test_needs_review_state(self):
        """Test NEEDS_REVIEW state transitions"""
        sm = StateMachine()
        sm.current_state = ProjectState.IP_CHECK
        
        # IP_CHECK can transition to NEEDS_REVIEW
        assert sm.can_transition(ProjectState.NEEDS_REVIEW) is True
        
        sm.transition(ProjectState.NEEDS_REVIEW)
        
        # From NEEDS_REVIEW, can go to RESEARCH or COMPLETED
        assert sm.can_transition(ProjectState.RESEARCH) is True
        assert sm.can_transition(ProjectState.COMPLETED) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
