"""Pydantic schemas for request/response validation."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Constraints(BaseModel):
    """Extracted constraints from user query."""
    primary_task: str = Field(default="", description="Main task type (text-generation, embedding, etc)")
    sub_task: str = Field(default="", description="Specific sub-task")
    deployment_environment: str = Field(default="cloud", description="local, cloud, edge, mobile")
    hardware_constraint: str = Field(default="", description="VRAM, RAM constraints")
    license_requirement: str = Field(default="any", description="open-source, commercial, any")
    performance_priority: str = Field(default="balanced", description="speed, quality, balanced, cost")
    language_requirement: str = Field(default="en", description="Language requirements")
    domain_specificity: str = Field(default="", description="Specific domain focus")
    use_case_context: str = Field(default="", description="Broader context of the use case")
    budget_constraint: str = Field(default="", description="Budget limitations")
    batch_size: str = Field(default="", description="Expected batch/volume size")


class ModelInfo(BaseModel):
    """Information about a recommended model."""
    model_id: str
    name: str
    task: str
    downloads: int = 0
    likes: int = 0
    license: str = ""
    size_mb: Optional[float] = None
    vram_required: Optional[str] = None
    languages: List[str] = []
    tags: List[str] = []
    description: str = ""
    model_card_url: str = ""


class CostEstimate(BaseModel):
    """Cost estimation breakdown."""
    deployment_type: str  # self-hosted, api, cloud
    monthly_cost_low: float
    monthly_cost_high: float
    setup_cost: float = 0
    notes: List[str] = []


class TradeOff(BaseModel):
    """Trade-off analysis item."""
    aspect: str
    pros: List[str]
    cons: List[str]


class AdvisorQuery(BaseModel):
    """User query to the advisor."""
    query: str
    session_id: Optional[str] = None


class AdvisorResponse(BaseModel):
    """Full response from the advisor."""
    session_id: str
    constraints: Constraints
    best_match: ModelInfo
    reality_check: Dict[str, Any]
    trade_offs: List[TradeOff]
    use_case_fit: str
    pro_tips: List[str]
    next_steps: List[str]
    cost_breakdown: CostEstimate
    deployment_code: str
    also_considered: List[ModelInfo]
    raw_response: Optional[str] = None


class FollowUpQuery(BaseModel):
    """Follow-up query with session context."""
    query: str
    session_id: str


class SystemDesignQuery(BaseModel):
    """Query to the system design expert."""
    question: str
    session_id: str
    hardware_specs: Optional[Dict[str, Any]] = None  # Override session hardware


class CodeSample(BaseModel):
    """Code sample with metadata."""
    language: str
    code: str
    filename: Optional[str] = None
    description: str


class SystemDesignResponse(BaseModel):
    """Response from the system design expert."""
    answer: str
    code_samples: List[CodeSample] = []
    tradeoffs: List[Dict[str, Any]] = []
    alternatives: List[str] = []
    resources: List[Dict[str, str]] = []  # {title, url}
    suggested_followups: List[str] = []
    context_summary: str  # What model/constraints the advice is based on

