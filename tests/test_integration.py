"""Global integration tests for the entire pipeline"""

import pytest
from src.core.state import StateMachine, ProjectState, StateTransitionError
from src.core.orchestrator import MainOrchestrator, ProjectContext, StepResult


class TestGlobalIntegration:
    """Integration tests for the complete system"""
    
    def test_full_pipeline_flow(self):
        """Test complete pipeline from start to finish"""
        orch = MainOrchestrator()
        
        # Create project
        context = orch.create_project(
            request="Create a productivity planner",
            target_market="Working professionals",
            language="English"
        )
        
        project_id = context.project_id
        assert context.current_state == ProjectState.CREATED
        
        # Step 1: Research
        result = orch.execute_step(project_id, ProjectState.RESEARCH)
        assert result.is_success()
        assert orch.get_project(project_id).current_state == ProjectState.RESEARCH
        
        # Step 2: Strategy
        result = orch.execute_step(project_id, ProjectState.STRATEGY)
        assert result.is_success()
        assert orch.get_project(project_id).current_state == ProjectState.STRATEGY
        
        # Step 3: Content
        result = orch.execute_step(project_id, ProjectState.CONTENT)
        assert result.is_success()
        assert orch.get_project(project_id).current_state == ProjectState.CONTENT
        
        # Step 4: Design
        result = orch.execute_step(project_id, ProjectState.DESIGN)
        assert result.is_success()
        assert orch.get_project(project_id).current_state == ProjectState.DESIGN
        
        # Step 5: PDF
        result = orch.execute_step(project_id, ProjectState.PDF)
        assert result.is_success()
        assert orch.get_project(project_id).current_state == ProjectState.PDF
        
        # Step 6: Visuals
        result = orch.execute_step(project_id, ProjectState.VISUALS)
        assert result.is_success()
        assert orch.get_project(project_id).current_state == ProjectState.VISUALS
        
        # Step 7: Quality Check
        result = orch.execute_step(project_id, ProjectState.QUALITY_CHECK)
        assert result.is_success()
        assert orch.get_project(project_id).current_state == ProjectState.QUALITY_CHECK
        
        # Step 8: SEO
        result = orch.execute_step(project_id, ProjectState.SEO)
        assert result.is_success()
        assert orch.get_project(project_id).current_state == ProjectState.SEO
        
        # Step 9: Pricing
        result = orch.execute_step(project_id, ProjectState.PRICING)
        assert result.is_success()
        assert orch.get_project(project_id).current_state == ProjectState.PRICING
        
        # Step 10: IP Check
        result = orch.execute_step(project_id, ProjectState.IP_CHECK)
        assert result.is_success()
        assert orch.get_project(project_id).current_state == ProjectState.IP_CHECK
        
        # Step 11: Finalization
        result = orch.execute_step(project_id, ProjectState.FINALIZATION)
        assert result.is_success()
        assert orch.get_project(project_id).current_state == ProjectState.FINALIZATION
        
        # Step 12: Completed
        result = orch.execute_step(project_id, ProjectState.COMPLETED)
        assert result.is_success()
        assert orch.get_project(project_id).current_state == ProjectState.COMPLETED
        
        # Verify project status
        status = orch.get_project_status(project_id)
        assert status["current_state"] == ProjectState.COMPLETED.value
        assert status["errors_count"] == 0
    
    def test_pipeline_with_failure_and_retry(self):
        """Test pipeline handling failure and retry"""
        orch = MainOrchestrator()
        
        def failing_step(context):
            return StepResult(
                status="failed",
                score=0,
                errors=["Strategy validation failed"]
            )
        
        orch.register_step(ProjectState.STRATEGY, failing_step)
        
        context = orch.create_project("Test project")
        project_id = context.project_id
        
        # Move to Research
        orch.execute_step(project_id, ProjectState.RESEARCH)
        
        # Try Strategy - should fail
        result = orch.execute_step(project_id, ProjectState.STRATEGY)
        assert result.is_failed()
        assert orch.get_project(project_id).current_state == ProjectState.FAILED
        
        # Retry from RESEARCH
        result = orch.execute_step(project_id, ProjectState.RESEARCH)
        assert result.is_success()
        assert orch.get_project(project_id).current_state == ProjectState.RESEARCH
    
    def test_pipeline_with_review_needed(self):
        """Test pipeline with manual review requirement"""
        orch = MainOrchestrator()
        
        def review_required_step(context):
            return StepResult(
                status="needs_review",
                score=50,
                warnings=["Content quality needs improvement"]
            )
        
        orch.register_step(ProjectState.CONTENT, review_required_step)
        
        context = orch.create_project("Test project")
        project_id = context.project_id
        
        # Move through pipeline
        orch.execute_step(project_id, ProjectState.RESEARCH)
        orch.execute_step(project_id, ProjectState.STRATEGY)
        
        # Content review needed
        result = orch.execute_step(project_id, ProjectState.CONTENT)
        assert result.is_needs_review()
        assert orch.get_project(project_id).current_state == ProjectState.NEEDS_REVIEW
        
        # Can retry or complete
        assert orch.get_project(project_id).can_transition(ProjectState.RESEARCH)
        assert orch.get_project(project_id).can_transition(ProjectState.COMPLETED)
    
    def test_step_function_with_metadata_collection(self):
        """Test step functions collecting metadata"""
        orch = MainOrchestrator()
        
        def research_with_metadata(context):
            context.metadata["market_size"] = "Large"
            context.metadata["competitors"] = 5
            context.artifacts["research_report"] = "Report v1.0"
            return StepResult(
                status="success",
                score=95,
                metadata={"duration_minutes": 45}
            )
        
        orch.register_step(ProjectState.RESEARCH, research_with_metadata)
        
        context = orch.create_project("Test project")
        project_id = context.project_id
        
        result = orch.execute_step(project_id, ProjectState.RESEARCH)
        
        project = orch.get_project(project_id)
        assert project.metadata["market_size"] == "Large"
        assert project.metadata["competitors"] == 5
        assert project.artifacts["research_report"] == "Report v1.0"
        assert result.metadata["duration_minutes"] == 45
    
    def test_state_machine_direct_usage(self):
        """Test StateMachine directly without orchestrator"""
        sm = StateMachine()
        
        # Valid sequence
        transitions = []
        states = [
            ProjectState.RESEARCH,
            ProjectState.STRATEGY,
            ProjectState.CONTENT,
            ProjectState.DESIGN
        ]
        
        for state in states:
            t = sm.transition(state)
            transitions.append(t)
        
        assert len(transitions) == 4
        assert sm.current_state == ProjectState.DESIGN
        assert len(sm.history) == 4
        
        # All transitions should be recorded
        for i, t in enumerate(transitions):
            assert t.attempt == i + 1
            assert t.to_state == states[i]
    
    def test_error_handling_in_orchestrator(self):
        """Test comprehensive error handling"""
        orch = MainOrchestrator()
        
        context = orch.create_project("Test")
        project_id = context.project_id
        
        # Test 1: Invalid transition
        result = orch.execute_step(project_id, ProjectState.COMPLETED)
        assert result.is_failed()
        assert orch.get_project(project_id).current_state == ProjectState.CREATED
        
        # Test 2: Non-existent project
        with pytest.raises(Exception):
            orch.execute_step("non-existent", ProjectState.RESEARCH)
        
        # Test 3: Non-existent project status
        with pytest.raises(Exception):
            orch.get_project_status("non-existent")
    
    def test_multiple_concurrent_projects(self):
        """Test orchestrator handling multiple projects"""
        orch = MainOrchestrator()
        
        # Create multiple projects
        projects = []
        for i in range(3):
            ctx = orch.create_project(f"Project {i}")
            projects.append(ctx.project_id)
        
        assert len(orch.projects) == 3
        
        # Execute different steps for each
        orch.execute_step(projects[0], ProjectState.RESEARCH)
        orch.execute_step(projects[1], ProjectState.RESEARCH)
        orch.execute_step(projects[1], ProjectState.STRATEGY)
        
        # Verify states
        assert orch.get_project(projects[0]).current_state == ProjectState.RESEARCH
        assert orch.get_project(projects[1]).current_state == ProjectState.STRATEGY
        assert orch.get_project(projects[2]).current_state == ProjectState.CREATED
    
    def test_project_completion_paths(self):
        """Test different paths to project completion"""
        orch = MainOrchestrator()
        
        # Path 1: Normal completion
        ctx1 = orch.create_project("Project 1")
        ctx1.current_state = ProjectState.COMPLETED
        assert orch.can_complete_project(ctx1.project_id) is True
        
        # Path 2: Completion via review
        ctx2 = orch.create_project("Project 2")
        ctx2.current_state = ProjectState.NEEDS_REVIEW
        assert orch.can_complete_project(ctx2.project_id) is True
        
        # Path 3: In progress - not ready
        ctx3 = orch.create_project("Project 3")
        assert orch.can_complete_project(ctx3.project_id) is False
    
    def test_step_result_scoring(self):
        """Test step result scoring system"""
        results = [
            StepResult(status="success", score=100),
            StepResult(status="success", score=85),
            StepResult(status="needs_review", score=50),
            StepResult(status="failed", score=0),
        ]
        
        for result in results:
            if result.score == 100:
                assert result.is_success()
            elif result.score >= 50:
                assert not result.is_failed()
            else:
                assert result.is_failed()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
