"""Main Orchestrator for coordinating the autonomous agent pipeline"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import uuid4

from src.core.state import StateMachine, ProjectState, StateTransitionError


@dataclass
class ProjectContext:
    """Context containing all project information"""
    project_id: str
    request: str
    target_market: Optional[str] = None
    language: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    current_state: ProjectState = ProjectState.CREATED
    artifacts: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StepResult:
    """Result of a pipeline step"""
    status: str  # "success", "failed", "needs_review"
    score: int  # 0-100
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    output: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_success(self) -> bool:
        return self.status == "success"
    
    def is_failed(self) -> bool:
        return self.status == "failed"
    
    def is_needs_review(self) -> bool:
        return self.status == "needs_review"


class OrchestratorError(Exception):
    """Orchestrator-specific errors"""
    pass


class MainOrchestrator:
    """
    Central orchestrator managing the entire autonomous agent pipeline.
    Coordinates state transitions, step execution, and result tracking.
    """
    
    def __init__(self):
        self.state_machine = StateMachine()
        self.projects: Dict[str, ProjectContext] = {}
        self.step_registry: Dict[str, callable] = {}
    
    def register_step(self, state: ProjectState, step_func: callable) -> None:
        """Register a step function for a given state"""
        self.step_registry[state.value] = step_func
    
    def create_project(
        self,
        request: str,
        target_market: Optional[str] = None,
        language: Optional[str] = None
    ) -> ProjectContext:
        """
        Create a new project context.
        
        Args:
            request: User's product request
            target_market: Optional target market specification
            language: Optional language specification
            
        Returns:
            ProjectContext instance
        """
        project_id = str(uuid4())
        
        context = ProjectContext(
            project_id=project_id,
            request=request,
            target_market=target_market,
            language=language
        )
        
        self.projects[project_id] = context
        return context
    
    def get_project(self, project_id: str) -> Optional[ProjectContext]:
        """Retrieve a project by ID"""
        return self.projects.get(project_id)
    
    def execute_step(
        self,
        project_id: str,
        target_state: ProjectState
    ) -> StepResult:
        """
        Execute a pipeline step and transition state.
        
        Args:
            project_id: ID of the project
            target_state: Target state to transition to
            
        Returns:
            StepResult with execution details
        """
        context = self.get_project(project_id)
        if not context:
            raise OrchestratorError(f"Project {project_id} not found")
        
        # Check if transition is valid
        if not self.state_machine.can_transition(target_state):
            return StepResult(
                status="failed",
                score=0,
                errors=[f"Cannot transition from {self.state_machine.current_state} to {target_state}"]
            )
        
        # Get the step function
        step_func = self.step_registry.get(target_state.value)
        
        if not step_func:
            # If no step is registered, just transition state
            self.state_machine.transition(target_state)
            context.current_state = target_state
            
            return StepResult(
                status="success",
                score=100,
                output=f"Transitioned to {target_state.value}"
            )
        
        # Execute the step function
        try:
            result = step_func(context)
            
            # Validate result
            if not isinstance(result, StepResult):
                raise OrchestratorError(
                    f"Step function for {target_state} did not return StepResult"
                )
            
            # Transition state based on result
            if result.is_success():
                self.state_machine.transition(target_state)
                context.current_state = target_state
            elif result.is_failed():
                self.state_machine.transition(ProjectState.FAILED)
                context.current_state = ProjectState.FAILED
            elif result.is_needs_review():
                self.state_machine.transition(ProjectState.NEEDS_REVIEW)
                context.current_state = ProjectState.NEEDS_REVIEW
            
            # Record results
            context.results[target_state.value] = result
            if result.errors:
                context.errors.extend(result.errors)
            if result.warnings:
                context.warnings.extend(result.warnings)
            
            return result
            
        except Exception as e:
            context.errors.append(str(e))
            self.state_machine.transition(ProjectState.FAILED)
            context.current_state = ProjectState.FAILED
            
            return StepResult(
                status="failed",
                score=0,
                errors=[str(e)]
            )
    
    def get_project_status(self, project_id: str) -> Dict[str, Any]:
        """Get comprehensive status of a project"""
        context = self.get_project(project_id)
        if not context:
            raise OrchestratorError(f"Project {project_id} not found")
        
        return {
            "project_id": context.project_id,
            "request": context.request,
            "current_state": context.current_state.value,
            "created_at": context.created_at.isoformat(),
            "errors_count": len(context.errors),
            "warnings_count": len(context.warnings),
            "completed_steps": list(context.results.keys()),
            "errors": context.errors,
            "warnings": context.warnings
        }
    
    def can_complete_project(self, project_id: str) -> bool:
        """Check if project can transition to COMPLETED"""
        context = self.get_project(project_id)
        if not context:
            return False
        
        # Project can complete only if it's in a final state
        return context.current_state in [
            ProjectState.COMPLETED,
            ProjectState.NEEDS_REVIEW
        ]
