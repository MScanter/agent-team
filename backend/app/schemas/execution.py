"""
Execution schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.llm import ExecutionLLMConfig


class BudgetConfig(BaseModel):
    """Budget configuration for execution."""

    max_tokens: int = Field(default=200000, ge=1000, description="Maximum tokens budget")
    max_cost: float = Field(default=10.0, ge=0, description="Maximum cost in USD")
    warning_thresholds: list[float] = Field(
        default=[0.5, 0.8, 0.95],
        description="Warning thresholds (0-1)",
    )


class ExecutionCreate(BaseModel):
    """Schema for creating a new execution."""

    team_id: str = Field(..., description="Team ID to execute")
    input: str = Field(default="", description="Initial input/question (optional)")
    title: Optional[str] = Field(default=None, max_length=200, description="Execution title")
    budget: BudgetConfig = Field(default_factory=BudgetConfig, description="Budget configuration")
    llm: Optional[ExecutionLLMConfig] = Field(
        default=None,
        description="Runtime LLM configuration (provided by the client)",
    )


class ExecutionControl(BaseModel):
    """Schema for execution control actions."""

    action: str = Field(
        ...,
        pattern="^(pause|resume|stop|extend_budget)$",
        description="Control action",
    )
    params: dict = Field(default_factory=dict, description="Action parameters")




class ExecutionMessageResponse(BaseModel):
    """Schema for execution message response."""

    id: str
    sequence: int
    round: int
    phase: str

    sender_type: str
    sender_id: Optional[str]
    sender_name: Optional[str]

    content: str
    content_type: str

    responding_to: Optional[str]
    target_agent_id: Optional[str]
    confidence: Optional[float]
    wants_to_continue: bool

    input_tokens: int
    output_tokens: int

    message_metadata: dict
    created_at: datetime

    class Config:
        from_attributes = True


class ExecutionResponse(BaseModel):
    """Schema for execution response."""

    id: str
    user_id: str
    team_id: Optional[str]

    title: Optional[str]
    initial_input: str

    status: str
    current_stage: Optional[str]
    current_round: int

    shared_state: dict
    agent_states: dict

    final_output: Optional[str]
    structured_output: Optional[dict]

    tokens_used: int
    tokens_budget: int
    cost: float
    cost_budget: float

    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    error_message: Optional[str]

    # Recent messages (for quick access)
    recent_messages: list[ExecutionMessageResponse] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExecutionListResponse(BaseModel):
    """Schema for execution list response (simplified)."""

    id: str
    team_id: Optional[str]
    title: Optional[str]
    status: str
    current_round: int
    tokens_used: int
    cost: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
