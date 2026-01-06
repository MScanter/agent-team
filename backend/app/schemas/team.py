"""
Team schemas for API request/response validation.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CoordinationRules(BaseModel):
    """Team coordination rules configuration."""

    first_speaker: str = Field(
        default="highest_priority",
        description="First speaker selection: 'highest_priority' or specific agent_id",
    )
    turn_taking: str = Field(
        default="round_robin",
        description="Turn taking mode: round_robin, priority_based, free",
    )
    max_rounds: int = Field(
        default=0,
        ge=0,
        description="Maximum discussion rounds (0 = unlimited)",
    )
    termination: dict = Field(
        default_factory=lambda: {"type": "consensus", "consensus_threshold": 0.8},
        description="Termination conditions",
    )


class OutputRules(BaseModel):
    """Team output rules configuration."""

    mode: str = Field(
        default="merged",
        pattern="^(individual|merged|summary)$",
        description="Output mode",
    )
    summary_agent_id: Optional[str] = Field(
        default=None,
        description="Agent ID for summary (if mode is 'summary')",
    )
    format: str = Field(
        default="markdown",
        pattern="^(text|markdown|json)$",
        description="Output format",
    )


class TeamMemberCreate(BaseModel):
    """Schema for adding a member to a team."""

    agent_id: str = Field(..., description="Agent ID to add")
    role_override: Optional[str] = Field(default=None, max_length=100, description="Override role")
    priority_override: Optional[int] = Field(default=None, ge=1, le=10, description="Override priority")
    config_override: dict = Field(default_factory=dict, description="Additional config overrides")
    position: Optional[int] = Field(
        default=None,
        ge=0,
        description="Position in team (for ordered modes); if omitted, appended to the end",
    )


class TeamMemberResponse(BaseModel):
    """Schema for team member response."""

    id: str
    agent_id: str
    role_override: Optional[str]
    priority_override: Optional[int]
    config_override: dict
    position: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TeamBase(BaseModel):
    """Base team schema with common fields."""

    name: str = Field(..., min_length=1, max_length=100, description="Team name")
    description: Optional[str] = Field(default=None, description="Team description")
    icon: Optional[str] = Field(default=None, max_length=500, description="Team icon URL")

    # Collaboration configuration
    collaboration_mode: str = Field(
        default="roundtable",
        pattern="^(roundtable|pipeline|debate|freeform|custom)$",
        description="Collaboration mode",
    )
    mode_config: dict = Field(
        default_factory=dict,
        description="Mode-specific configuration",
    )

    # Coordinator
    coordinator_id: Optional[str] = Field(
        default=None,
        description="Coordinator agent ID (null for system-managed)",
    )

    # Rules
    coordination_rules: CoordinationRules = Field(
        default_factory=CoordinationRules,
        description="Coordination rules",
    )
    output_rules: OutputRules = Field(
        default_factory=OutputRules,
        description="Output rules",
    )


class TeamCreate(TeamBase):
    """Schema for creating a new team."""

    members: list[TeamMemberCreate] = Field(
        default_factory=list,
        description="Initial team members",
    )
    is_template: bool = Field(default=False, description="Whether this is a template")
    is_public: bool = Field(default=False, description="Whether publicly visible")


class TeamUpdate(BaseModel):
    """Schema for updating a team. All fields are optional."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(default=None, max_length=500)

    collaboration_mode: Optional[str] = Field(
        default=None,
        pattern="^(roundtable|pipeline|debate|freeform|custom)$",
    )
    mode_config: Optional[dict] = None
    coordinator_id: Optional[str] = None

    coordination_rules: Optional[CoordinationRules] = None
    output_rules: Optional[OutputRules] = None

    is_public: Optional[bool] = None


class TeamResponse(TeamBase):
    """Schema for team response."""

    id: str
    user_id: str
    is_template: bool
    is_public: bool

    # Statistics
    usage_count: int
    rating: float
    rating_count: int

    # Members
    members: list[TeamMemberResponse]

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TeamListResponse(BaseModel):
    """Schema for team list response (simplified)."""

    id: str
    name: str
    description: Optional[str]
    icon: Optional[str]
    collaboration_mode: str
    member_count: int = Field(default=0, description="Number of members")
    is_template: bool
    is_public: bool
    usage_count: int
    rating: float
    created_at: datetime

    class Config:
        from_attributes = True
