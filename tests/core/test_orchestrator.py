"""Tests for MainOrchestrator"""

import pytest
from datetime import datetime
from src.core.orchestrator import (
    MainOrchestrator, 
    ProjectContext, 
    StepResult,
    OrchestratorError
)
from src.core.state import ProjectState


class TestProjectContext:
    """Test ProjectContext dataclass"""
    
    def test_create_project_context(self):
        """Test creating a project context"""
        context = ProjectContext(
            project_id="test-123",
            request="Create a planner",
            target_market="English speakers",
            language="English"
        )
        
        assert context.project_id == "test-123"
        assert context.request == "Create a planner"
        assert context.target_market == "English speakers"
        assert context.language == "English"
        assert context.current_state == ProjectState.CREATED
        assert len(context.artifacts) == 0
        assert len(context.results) == 0
        assert len(context.errors) == 0


class TestStepResult:
    """Test StepResult dataclass"""
    
    def test_success_result(self):
        """Test creating a success result"""
        result = StepResult(status="success", score=95)
        
        assert result.is_success() is True
        assert result.is_failed() is False
        assert result.is_needs_review() is False
    
    def test_failed_result(self):
        """Test creating a failed result"""
        result = StepResult(status="failed", score=0, errors=["Error occurred"])
        
        assert result.is_failed() is True
        assert result.is_success() is False
        assert len(result.errors) == 1
    
    def test_needs_review_result(self):
        """Test creating a needs_review result"""
        result = StepResult(
            status="needs_review", 
            score=50,
            warnings=["Manual review required"]
        )
        
        assert result.is_needs_review() is True
        assert len(result.warnings) == 1


class TestMainOrchestrator:
    """Test suite for MainOrchestrator"""
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initializes correctly"""
        orch = MainOrchestrator()
        
        assert len(orch.projects) == 0
        assert len(orch.step_registry) == 0
        assert orch.state_machine is not None
    
    def test_create_project(self):
        """Test creating a project"""
        orch = MainOrchestrator()
        
        context = orch.create_project(
            request="Create a productivity planner",
            target_market="Working professionals",
            language="English"
        )
        
        assert context.project_id is not None
        assert context.request == "Create a productivity planner"
        assert context.target_market == "Working professionals"
        assert context.language == "English"
        assert context.current_state == ProjectState.CREATED
    
    def test_get_project(self):
        """Test retrieving a project"""
        orch = MainOrchestrator()
        
        context = orch.create_project("Test request")
        project_id = context.project_id
        
        retrieved = orch.get_project(project_id)
        
        assert retrieved is not None
        assert retrieved.project_id == project_id
        assert retrieved.request == "Test request"
    
    def test_get_nonexistent_project(self):
        """Test retrieving a non-existent project returns None"""
        orch = MainOrchestrator()
        
        result = orch.get_project("nonexistent-id")
        
        assert result is None
    
    def test_register_step(self):
        """Test registering a step function"""
        orch = MainOrchestrator()
        
        def test_step(context):
            return StepResult(status="success", score=100)
        
        orch.register_step(ProjectState.RESEARCH, test_step)
        
        assert ProjectState.RESEARCH.value in orch.step_registry
    
    def test_execute_step_no_step_registered(self):
        """Test executing a step with no registered function"""
        orch = MainOrchestrator()
        
        context = orch.create_project("Test")
        project_id = context.project_id
        
        result = orch.execute_step(project_id, ProjectState.RESEARCH)
        
        assert result.is_success()
        assert orch.get_project(project_id).current_state == ProjectState.RESEARCH
    
    def test_execute_step_with_registered_function(self):
        """Test executing a step with a registered function"""
        orch = MainOrchestrator()
        
        def research_step(context):
            context.metadata["research_done"] = True
            return StepResult(status="success", score=90)
        
        orch.register_step(ProjectState.RESEARCH, research_step)
        
        context = orch.create_project("Test")
        project_id = context.project_id
        
        result = orch.execute_step(project_id, ProjectState.RESEARCH)
        
        assert result.is_success()
        assert result.score == 90
        assert orch.get_project(project_id).current_state == ProjectState.RESEARCH
        assert orch.get_project(project_id).metadata.get("research_done") is True
    
    def test_execute_step_invalid_transition(self):
        """Test executing invalid state transition"""
        orch = MainOrchestrator()
        
        context = orch.create_project("Test")
        project_id = context.project_id
        
        # Try invalid transition: CREATED -> DESIGN
        result = orch.execute_step(project_id, ProjectState.DESIGN)
        
        assert result.is_failed()
        assert len(result.errors) > 0
    
    def test_execute_step_sequence(self):
        """Test executing a valid sequence of steps"""
        orch = MainOrchestrator()
        
        context = orch.create_project("Test")
        project_id = context.project_id
        
        # CREATED -> RESEARCH
        result1 = orch.execute_step(project_id, ProjectState.RESEARCH)
        assert result1.is_success()
        assert orch.get_project(project_id).current_state == ProjectState.RESEARCH
        
        # RESEARCH -> STRATEGY
        result2 = orch.execute_step(project_id, ProjectState.STRATEGY)
        assert result2.is_success()
        assert orch.get_project(project_id).current_state == ProjectState.STRATEGY
    
    def test_execute_step_step_function_returns_failed(self):
        """Test step function returning failed status"""
        orch = MainOrchestrator()
        
        def failing_step(context):
            return StepResult(
                status="failed",
                score=0,
                errors=["Step failed"]
            )
        
        orch.register_step(ProjectState.RESEARCH, failing_step)
        
        context = orch.create_project("Test")
        project_id = context.project_id
        
        result = orch.execute_step(project_id, ProjectState.RESEARCH)
        
        assert result.is_failed()
        assert orch.get_project(project_id).current_state == ProjectState.FAILED
    
    def test_execute_step_step_function_returns_needs_review(self):
        """Test step function returning needs_review status"""
        orch = MainOrchestrator()
        
        def review_step(context):
            return StepResult(
                status="needs_review",
                score=50,
                warnings=["Manual review needed"]
            )
        
        orch.register_step(ProjectState.QUALITY_CHECK, review_step)
        
        context = orch.create_project("Test")
        project_id = context.project_id
        
        # Set state to QUALITY_CHECK
        context.current_state = ProjectState.QUALITY_CHECK
        orch.state_machine.current_state = ProjectState.QUALITY_CHECK
        
        result = orch.execute_step(project_id, ProjectState.QUALITY_CHECK)
        
        # Should actually transition to NEEDS_REVIEW
        assert orch.get_project(project_id).current_state == ProjectState.NEEDS_REVIEW
    
    def test_get_project_status(self):
        """Test getting comprehensive project status"""
        orch = MainOrchestrator()
        
        context = orch.create_project(
            "Create planner",
            target_market="Professionals",
            language="English"
        )
        project_id = context.project_id
        
        orch.execute_step(project_id, ProjectState.RESEARCH)
        
        status = orch.get_project_status(project_id)
        
        assert status["project_id"] == project_id
        assert status["request"] == "Create planner"
        assert status["current_state"] == ProjectState.RESEARCH.value
        assert isinstance(status["created_at"], str)
        assert status["errors_count"] == 0
    
    def test_get_project_status_with_errors(self):
        """Test project status with errors"""
        orch = MainOrchestrator()
        
        context = orch.create_project("Test")
        project_id = context.project_id
        
        context.errors.append("Error 1")
        context.errors.append("Error 2")
        
        status = orch.get_project_status(project_id)
        
        assert status["errors_count"] == 2
        assert len(status["errors"]) == 2
    
    def test_can_complete_project_in_completed_state(self):
        """Test project completion check for COMPLETED state"""
        orch = MainOrchestrator()
        
        context = orch.create_project("Test")
        context.current_state = ProjectState.COMPLETED
        
        assert orch.can_complete_project(context.project_id) is True
    
    def test_can_complete_project_in_needs_review_state(self):
        """Test project completion check for NEEDS_REVIEW state"""
        orch = MainOrchestrator()
        
        context = orch.create_project("Test")
        context.current_state = ProjectState.NEEDS_REVIEW
        
        assert orch.can_complete_project(context.project_id) is True
    
    def test_can_complete_project_in_progress_state(self):
        """Test project completion check for non-terminal state"""
        orch = MainOrchestrator()
        
        context = orch.create_project("Test")
        context.current_state = ProjectState.RESEARCH
        
        assert orch.can_complete_project(context.project_id) is False
    
    def test_execute_step_nonexistent_project(self):
        """Test executing step on non-existent project raises error"""
        orch = MainOrchestrator()
        
        with pytest.raises(OrchestratorError) as exc_info:
            orch.execute_step("nonexistent-id", ProjectState.RESEARCH)
        
        assert "not found" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
