"""
Agent schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InteractionRules(BaseModel):
    """Agent interaction rules configuration."""

    can_challenge: bool = Field(default=True, description="Whether agent can challenge others")
    can_be_challenged: bool = Field(default=True, description="Whether agent accepts challenges")
    defer_to: list[str] = Field(default_factory=list, description="Agent IDs to defer to in their domain")


class AgentBase(BaseModel):
    """Base agent schema with common fields."""

    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    avatar: Optional[str] = Field(default=None, max_length=500, description="Avatar URL")
    description: Optional[str] = Field(default=None, description="Agent description")
    tags: list[str] = Field(default_factory=list, description="Searchable tags")

    # Core configuration
    system_prompt: str = Field(..., min_length=1, description="System prompt for the agent")
    model_id: Optional[str] = Field(default=None, description="Specific model to use")
    temperature: float = Field(default=0.7, ge=0, le=2, description="LLM temperature")
    max_tokens: int = Field(default=2048, ge=1, le=128000, description="Max output tokens")

    # Capabilities
    tools: list[str] = Field(default_factory=list, description="Enabled tool IDs")
    knowledge_base_id: Optional[str] = Field(default=None, description="Knowledge base ID")
    memory_enabled: bool = Field(default=False, description="Enable long-term memory")

    # Team role
    domain: Optional[str] = Field(default=None, max_length=100, description="Expertise domain")
    collaboration_style: str = Field(
        default="supportive",
        pattern="^(dominant|supportive|critical)$",
        description="Collaboration style",
    )
    speaking_priority: int = Field(default=5, ge=1, le=10, description="Speaking priority (1-10)")
    interaction_rules: InteractionRules = Field(
        default_factory=InteractionRules,
        description="Interaction rules",
    )


class AgentCreate(AgentBase):
    """Schema for creating a new agent."""

    is_template: bool = Field(default=False, description="Whether this is a template")
    is_public: bool = Field(default=False, description="Whether publicly visible")


class AgentUpdate(BaseModel):
    """Schema for updating an agent. All fields are optional."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    avatar: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = None
    tags: Optional[list[str]] = None

    system_prompt: Optional[str] = Field(default=None, min_length=1)
    model_id: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=128000)

    tools: Optional[list[str]] = None
    knowledge_base_id: Optional[str] = None
    memory_enabled: Optional[bool] = None

    domain: Optional[str] = Field(default=None, max_length=100)
    collaboration_style: Optional[str] = Field(default=None, pattern="^(dominant|supportive|critical)$")
    speaking_priority: Optional[int] = Field(default=None, ge=1, le=10)
    interaction_rules: Optional[InteractionRules] = None

    is_public: Optional[bool] = None


class AgentResponse(AgentBase):
    """Schema for agent response."""

    id: str
    user_id: str
    version: int
    is_template: bool
    is_public: bool
    parent_id: Optional[str]

    # Statistics
    usage_count: int
    rating: float
    rating_count: int

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    """Schema for agent list response (simplified)."""

    id: str
    name: str
    avatar: Optional[str]
    description: Optional[str]
    tags: list[str]
    domain: Optional[str]
    collaboration_style: str
    is_template: bool
    is_public: bool
    usage_count: int
    rating: float
    created_at: datetime

    class Config:
        from_attributes = True


class AgentFromTemplate(BaseModel):
    """Schema for creating agent from template."""

    template_id: str = Field(..., description="Template agent ID to copy from")
    name: str = Field(..., min_length=1, max_length=100, description="New agent name")
    customizations: Optional[AgentUpdate] = Field(
        default=None,
        description="Optional customizations to apply",
    )
