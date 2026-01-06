"""
Agent factory for creating agent instances from configurations.
"""

from typing import Optional

from typing import Any

from app.agents.base import AgentConfig, AgentInstance
from app.llm import LLMProvider, ModelRouter, get_model_router


class AgentFactory:
    """
    Factory for creating agent instances.

    Handles conversion from database models to runtime instances.
    """

    def __init__(self, model_router: Optional[ModelRouter] = None):
        self._router = model_router or get_model_router()
        self._instances: dict[str, AgentInstance] = {}

    def create_config(self, agent_model: dict[str, Any]) -> AgentConfig:
        """Create AgentConfig from a stored agent record."""
        interaction_rules = agent_model.get("interaction_rules") or {}

        return AgentConfig(
            id=agent_model["id"],
            name=agent_model["name"],
            system_prompt=agent_model["system_prompt"],
            model_id=agent_model.get("model_id"),
            temperature=agent_model.get("temperature", 0.7),
            max_tokens=agent_model.get("max_tokens", 2048),
            domain=agent_model.get("domain"),
            collaboration_style=agent_model.get("collaboration_style", "supportive"),
            speaking_priority=agent_model.get("speaking_priority", 5),
            can_challenge=interaction_rules.get("can_challenge", True),
            can_be_challenged=interaction_rules.get("can_be_challenged", True),
            defer_to=interaction_rules.get("defer_to", []),
            tools=agent_model.get("tools") or [],
            memory_enabled=bool(agent_model.get("memory_enabled")),
            avatar=agent_model.get("avatar"),
            description=agent_model.get("description"),
        )

    def create_instance(
        self,
        config: AgentConfig,
        llm_provider: Optional[LLMProvider] = None,
    ) -> AgentInstance:
        """
        Create an agent instance from configuration.

        Args:
            config: Agent configuration
            llm_provider: Optional specific LLM provider

        Returns:
            AgentInstance ready for use
        """
        if llm_provider is None:
            raise ValueError("AgentFactory requires an LLM provider (configure via ExecutionCreate.llm).")

        instance = AgentInstance(config=config, llm_provider=llm_provider)
        self._instances[config.id] = instance
        return instance

    def create_from_model(
        self,
        agent_model: dict[str, Any],
        llm_provider: Optional[LLMProvider] = None,
    ) -> AgentInstance:
        """
        Create an agent instance directly from database model.

        Args:
            agent_model: Database agent model
            llm_provider: Optional specific LLM provider (e.g., from user's model config)

        Returns:
            AgentInstance ready for use
        """
        config = self.create_config(agent_model)
        return self.create_instance(config, llm_provider)

    def get_instance(self, agent_id: str) -> Optional[AgentInstance]:
        """Get a cached agent instance by ID."""
        return self._instances.get(agent_id)

    def clear_cache(self):
        """Clear all cached instances."""
        self._instances.clear()

    def remove_instance(self, agent_id: str):
        """Remove a specific instance from cache."""
        self._instances.pop(agent_id, None)


# Global factory instance
_factory: Optional[AgentFactory] = None


def get_agent_factory() -> AgentFactory:
    """Get the global agent factory instance."""
    global _factory
    if _factory is None:
        _factory = AgentFactory()
    return _factory
