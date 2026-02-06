"""Planner Agent implementing Plan-and-Execute pattern."""
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from models.schemas import Constraints, ModelInfo, CostEstimate, AdvisorResponse
from tools import (
    HuggingFaceAPI,
    CostEstimator,
    ModelCardAggregator,
    CodeGenerator,
    LLMWriter
)
from logger import logger
from metrics import metrics


class ToolAction(str, Enum):
    SEARCH_MODELS = "search_models"
    FILTER_BY_VRAM = "filter_by_vram"
    GET_MODEL_CARDS = "get_model_cards"
    ESTIMATE_COSTS = "estimate_costs"
    GENERATE_CODE = "generate_code"
    WRITE_TRADEOFFS = "write_tradeoffs"
    WRITE_TIPS = "write_tips"


@dataclass
class PlanStep:
    action: ToolAction
    params: Dict[str, Any]
    description: str


class Planner:
    """Plan-and-Execute agent for model recommendation workflow."""
    
    def __init__(self):
        self.hf_api = HuggingFaceAPI()
        self.cost_estimator = CostEstimator()
        self.model_card_aggregator = ModelCardAggregator()
        self.code_generator = CodeGenerator()
        self.llm_writer = LLMWriter()
    
    def create_plan(self, constraints: Constraints) -> List[PlanStep]:
        """
        Create execution plan based on constraints.
        
        Args:
            constraints: Extracted user constraints
            
        Returns:
            List of plan steps to execute
        """
        steps = []
        
        # Step 1: Always search for models
        steps.append(PlanStep(
            action=ToolAction.SEARCH_MODELS,
            params={
                "task": constraints.primary_task or "text-generation",
                "license_filter": constraints.license_requirement,
            },
            description="Search Hugging Face for matching models"
        ))
        
        # Step 2: Filter by VRAM if hardware constraint exists
        if constraints.hardware_constraint:
            steps.append(PlanStep(
                action=ToolAction.FILTER_BY_VRAM,
                params={"constraint": constraints.hardware_constraint},
                description=f"Filter models for {constraints.hardware_constraint}"
            ))
        
        # Step 3: Get detailed model cards
        steps.append(PlanStep(
            action=ToolAction.GET_MODEL_CARDS,
            params={"limit": 5},
            description="Fetch detailed model information"
        ))
        
        # Step 4: Estimate costs
        steps.append(PlanStep(
            action=ToolAction.ESTIMATE_COSTS,
            params={
                "deployment": constraints.deployment_environment,
                "priority": constraints.performance_priority,
            },
            description="Calculate deployment costs"
        ))
        
        # Step 5: Generate deployment code
        steps.append(PlanStep(
            action=ToolAction.GENERATE_CODE,
            params={"deployment_type": constraints.deployment_environment},
            description="Generate Python deployment code"
        ))
        
        # Step 6: Write trade-offs and recommendations
        steps.append(PlanStep(
            action=ToolAction.WRITE_TRADEOFFS,
            params={},
            description="Generate trade-off analysis"
        ))
        
        steps.append(PlanStep(
            action=ToolAction.WRITE_TIPS,
            params={},
            description="Generate pro tips and next steps"
        ))
        
        return steps
    
    async def execute(self, constraints: Constraints, session_id: str) -> AdvisorResponse:
        """
        Execute the full recommendation workflow.
        
        Args:
            constraints: User constraints
            session_id: Session ID for tracking
            
        Returns:
            Complete advisor response
        """
        workflow_start = time.time()
        logger.log_agent_step(
            agent="Planner",
            step="workflow_start",
            success=True,
            details={"session_id": session_id, "task": constraints.primary_task}
        )
        
        plan = self.create_plan(constraints)
        
        # Execute each step
        models = []
        filtered_models = []
        model_cards = []
        best_model = None
        cost_estimate = None
        deployment_code = ""
        trade_offs = []
        use_case_fit = ""
        pro_tips = []
        next_steps = []
        reality_check = {}
        
        for step in plan:
            step_start = time.time()
            try:
                if step.action == ToolAction.SEARCH_MODELS:
                    models = await self.hf_api.search_models(
                        task=step.params["task"],
                        license_filter=step.params.get("license_filter"),
                        limit=20
                    )
                    filtered_models = models
                    logger.log_tool_call(
                        tool="HuggingFaceAPI",
                        operation="search_models",
                        duration_ms=(time.time() - step_start) * 1000,
                        success=True,
                        output_size=len(models)
                    )
                
                elif step.action == ToolAction.FILTER_BY_VRAM:
                    if models:
                        vram_limit = self.hf_api.parse_vram_constraint(
                            step.params["constraint"]
                        )
                        if vram_limit:
                            filtered_models = self.hf_api.filter_by_vram(
                                models, vram_limit
                            )
                        if not filtered_models:
                            filtered_models = models[:10]  # Fallback
                
                elif step.action == ToolAction.GET_MODEL_CARDS:
                    top_models = filtered_models[:step.params.get("limit", 5)]
                    model_ids = [m.get("modelId", m.get("id", "")) for m in top_models]
                    model_cards = await self.model_card_aggregator.get_multiple_cards(model_ids)
                    
                    if model_cards:
                        best_model = model_cards[0]
                        # Add VRAM estimation
                        best_model["vram_required"] = self.model_card_aggregator.estimate_vram_requirement(best_model)
                
                elif step.action == ToolAction.ESTIMATE_COSTS:
                    if best_model:
                        size_gb = (best_model.get("size_mb") or 1000) / 1024
                        recommendation = self.cost_estimator.get_recommendation(
                            model_size_gb=size_gb,
                            monthly_requests=100000,
                            budget_priority=step.params.get("priority", "balanced")
                        )
                        cost_estimate = recommendation["recommended"]
                
                elif step.action == ToolAction.GENERATE_CODE:
                    if best_model:
                        deployment_code = self.code_generator.generate(
                            model_id=best_model["model_id"],
                            task=best_model.get("task", ""),
                            deployment_type=step.params.get("deployment_type", "local"),
                            library=best_model.get("library")
                        )
                
                elif step.action == ToolAction.WRITE_TRADEOFFS:
                    if best_model:
                        trade_offs = await self.llm_writer.generate_tradeoffs(
                            best_model, constraints.model_dump()
                        )
                        use_case_fit = await self.llm_writer.generate_use_case_fit(
                            best_model, constraints.model_dump()
                        )
                        reality_check = await self.llm_writer.generate_reality_check(
                            best_model, constraints.model_dump()
                        )
                
                elif step.action == ToolAction.WRITE_TIPS:
                    if best_model:
                        pro_tips = await self.llm_writer.generate_pro_tips(
                            best_model, constraints.model_dump()
                        )
                        next_steps = await self.llm_writer.generate_next_steps(
                            best_model, constraints.model_dump()
                        )
                        
            except Exception as e:
                logger.log_agent_step(
                    agent="Planner",
                    step=step.action.value,
                    duration_ms=(time.time() - step_start) * 1000,
                    success=False,
                    error=str(e)
                )
                metrics.record_error(
                    category="agent",
                    error_type=type(e).__name__,
                    message=f"Error in {step.action.value}: {str(e)}",
                    details={"step": step.action.value}
                )
                continue
        
        # Log workflow completion
        workflow_duration = (time.time() - workflow_start) * 1000
        logger.log_agent_step(
            agent="Planner",
            step="workflow_complete",
            duration_ms=workflow_duration,
            success=True,
            details={"steps_executed": len(plan), "models_found": len(model_cards)}
        )
        metrics.record_agent_execution(
            agent="Planner",
            step="execute",
            duration_ms=workflow_duration,
            success=True
        )
        
        # Build response
        best_match = self._build_model_info(best_model) if best_model else ModelInfo(
            model_id="unknown",
            name="No matching model found",
            task=constraints.primary_task or "unknown"
        )
        
        also_considered = [
            self._build_model_info(card) 
            for card in model_cards[1:4] if card
        ]
        
        return AdvisorResponse(
            session_id=session_id,
            constraints=constraints,
            best_match=best_match,
            reality_check=reality_check,
            trade_offs=[
                {"aspect": t.get("aspect", ""), "pros": t.get("pros", []), "cons": t.get("cons", [])}
                for t in trade_offs
            ] if trade_offs else [],
            use_case_fit=use_case_fit or "Evaluate based on your specific requirements.",
            pro_tips=pro_tips or ["Review the model card for detailed information."],
            next_steps=next_steps or ["Install the required dependencies and run the code snippet."],
            cost_breakdown=CostEstimate(
                deployment_type=cost_estimate.get("deployment_type", "unknown") if cost_estimate else "unknown",
                monthly_cost_low=cost_estimate.get("monthly_cost_low", 0) if cost_estimate else 0,
                monthly_cost_high=cost_estimate.get("monthly_cost_high", 0) if cost_estimate else 0,
                notes=cost_estimate.get("notes", []) if cost_estimate else []
            ),
            deployment_code=deployment_code,
            also_considered=also_considered
        )
    
    def _build_model_info(self, card: Dict[str, Any]) -> ModelInfo:
        """Convert model card dict to ModelInfo object."""
        return ModelInfo(
            model_id=card.get("model_id", ""),
            name=card.get("name", ""),
            task=card.get("task", ""),
            downloads=card.get("downloads", 0),
            likes=card.get("likes", 0),
            license=card.get("license", ""),
            size_mb=card.get("size_mb"),
            vram_required=card.get("vram_required", "Unknown"),
            languages=card.get("languages", ["en"]),
            tags=card.get("tags", []),
            description=card.get("description", ""),
            model_card_url=card.get("model_card_url", "")
        )
