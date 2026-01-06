"""
Custom orchestrator for user-defined workflows.
"""

import asyncio
from typing import AsyncIterator, Optional, Dict, Any

from app.agents.base import AgentInstance
from app.orchestration.base import (
    Orchestrator,
    OrchestrationState,
    OrchestrationEvent,
    OrchestrationPhase,
    Opinion,
)


class CustomOrchestrator(Orchestrator):
    """
    Custom workflow orchestrator.

    Allows users to define custom execution flows with nodes like:
    - AgentNode: Execute an agent
    - ConditionNode: Conditional branching
    - ParallelNode: Execute multiple agents in parallel
    - MergeNode: Merge parallel branches
    - LoopNode: Loop execution
    - UserInputNode: Wait for user input
    """

    def __init__(self, config: dict = None):
        super().__init__(config or {})
        self._sequence = 0
        self.workflow = self.config.get("workflow", {})
        self.node_results = {}

    @property
    def mode_name(self) -> str:
        return "custom"

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    async def run(
        self,
        agents: list[AgentInstance],
        state: OrchestrationState,
    ) -> AsyncIterator[OrchestrationEvent]:
        """Run custom workflow."""

        state.phase = OrchestrationPhase.INITIALIZING
        state.agent_ids = [a.id for a in agents]
        state.active_agent_ids = state.agent_ids.copy()

        yield OrchestrationEvent(
            event_type="status",
            data={"message": "Custom workflow started", "phase": "initializing"},
            sequence=self._next_sequence(),
        )

        # Execute the workflow
        try:
            await self._execute_workflow(agents, state)
        except Exception as e:
            state.phase = OrchestrationPhase.FAILED
            state.error = str(e)
            yield OrchestrationEvent(
                event_type="error",
                data={"message": f"Workflow execution failed: {str(e)}"},
                sequence=self._next_sequence(),
            )

        state.phase = OrchestrationPhase.COMPLETED
        yield OrchestrationEvent(
            event_type="done",
            data={
                "final_summary": state.summary,
                "tokens_used": state.tokens_used,
                "node_results": self.node_results,
            },
            sequence=self._next_sequence(),
        )

    async def _execute_workflow(
        self,
        agents: list[AgentInstance],
        state: OrchestrationState,
    ):
        """Execute the custom workflow."""
        nodes = self.workflow.get("nodes", [])
        edges = self.workflow.get("edges", [])
        
        # Find start nodes (nodes with no incoming edges)
        node_ids = [node["id"] for node in nodes]
        target_ids = [edge["target"] for edge in edges]
        start_nodes = [node_id for node_id in node_ids if node_id not in target_ids]
        
        # Execute workflow starting from start nodes
        for node_id in start_nodes:
            await self._execute_node(node_id, agents, state)

    async def _execute_node(
        self,
        node_id: str,
        agents: list[AgentInstance],
        state: OrchestrationState,
    ):
        """Execute a single node in the workflow."""
        nodes = {node["id"]: node for node in self.workflow.get("nodes", [])}
        node = nodes.get(node_id)
        
        if not node:
            raise ValueError(f"Node {node_id} not found in workflow")
        
        node_type = node.get("type")
        config = node.get("config", {})
        
        if node_type == "agent":
            await self._execute_agent_node(node, agents, state)
        elif node_type == "condition":
            await self._execute_condition_node(node, agents, state)
        elif node_type == "parallel":
            await self._execute_parallel_node(node, agents, state)
        elif node_type == "merge":
            await self._execute_merge_node(node, agents, state)
        elif node_type == "loop":
            await self._execute_loop_node(node, agents, state)
        elif node_type == "user_input":
            await self._execute_user_input_node(node, agents, state)
        else:
            raise ValueError(f"Unknown node type: {node_type}")

    async def _execute_agent_node(
        self,
        node: Dict[str, Any],
        agents: list[AgentInstance],
        state: OrchestrationState,
    ):
        """Execute an agent node."""
        config = node.get("config", {})
        agent_id = config.get("agent_id")
        prompt_template = config.get("prompt_template", "{topic}")
        
        # Find the agent
        agent = next((a for a in agents if a.id == agent_id), None)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Format the prompt
        topic = state.topic
        if "{topic}" in prompt_template:
            formatted_prompt = prompt_template.format(topic=topic)
        else:
            formatted_prompt = f"{topic}\n\n{prompt_template}"
        
        # Generate opinion
        response = await agent.generate_opinion(
            topic=formatted_prompt,
            discussion_summary=state.summary,
            recent_opinions=[],
            phase="initial",
        )
        
        opinion = Opinion(
            agent_id=agent.id,
            agent_name=agent.name,
            content=response.content,
            round=state.round,
            phase="agent_node",
            confidence=response.confidence,
            wants_to_continue=response.wants_to_continue,
            input_tokens=response.metadata.get("input_tokens", 0),
            output_tokens=response.metadata.get("output_tokens", 0),
        )
        state.add_opinion(opinion)
        
        # Store result for potential use by other nodes
        self.node_results[node["id"]] = response.content
        
        yield OrchestrationEvent(
            event_type="opinion",
            data={
                "agent_name": agent.name,
                "content": response.content,
                "confidence": response.confidence,
                "wants_to_continue": response.wants_to_continue,
                "node_id": node["id"],
            },
            agent_id=agent.id,
            sequence=self._next_sequence(),
        )
        
        # Follow outgoing edges
        await self._follow_outgoing_edges(node["id"], agents, state)

    async def _execute_condition_node(
        self,
        node: Dict[str, Any],
        agents: list[AgentInstance],
        state: OrchestrationState,
    ):
        """Execute a condition node."""
        config = node.get("config", {})
        condition = config.get("condition", "")
        
        # Evaluate condition based on state or previous results
        # This is a simplified implementation - in a real system, you'd have more complex logic
        result = self._evaluate_condition(condition, state)
        
        # Follow the appropriate edge based on condition result
        edges = [edge for edge in self.workflow.get("edges", []) if edge["source"] == node["id"]]
        for edge in edges:
            if edge.get("condition") == "true" and result:
                await self._execute_node(edge["target"], agents, state)
            elif edge.get("condition") == "false" and not result:
                await self._execute_node(edge["target"], agents, state)

    def _evaluate_condition(self, condition: str, state: OrchestrationState) -> bool:
        """Evaluate a condition based on state."""
        # Simplified condition evaluation
        # In a real implementation, this would be more sophisticated
        if condition == "has_opinions":
            return len(state.opinions) > 0
        elif condition == "tokens_remaining":
            return state.tokens_used < state.tokens_budget * 0.8
        else:
            # Default to True for unknown conditions
            return True

    async def _execute_parallel_node(
        self,
        node: Dict[str, Any],
        agents: list[AgentInstance],
        state: OrchestrationState,
    ):
        """Execute a parallel node."""
        config = node.get("config", {})
        agent_ids = config.get("agent_ids", [])
        
        # Find the agents to execute in parallel
        parallel_agents = [a for a in agents if a.id in agent_ids]
        
        # Execute all agents in parallel
        async def execute_agent(agent: AgentInstance):
            response = await agent.generate_opinion(
                topic=state.topic,
                discussion_summary=state.summary,
                recent_opinions=[],
                phase="parallel",
            )
            
            opinion = Opinion(
                agent_id=agent.id,
                agent_name=agent.name,
                content=response.content,
                round=state.round,
                phase="parallel_node",
                confidence=response.confidence,
                wants_to_continue=response.wants_to_continue,
                input_tokens=response.metadata.get("input_tokens", 0),
                output_tokens=response.metadata.get("output_tokens", 0),
            )
            state.add_opinion(opinion)
            
            return {
                "agent_id": agent.id,
                "content": response.content,
                "node_id": node["id"],
            }
        
        results = await asyncio.gather(
            *[execute_agent(agent) for agent in parallel_agents],
            return_exceptions=True
        )
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                yield OrchestrationEvent(
                    event_type="error",
                    data={"message": f"Parallel execution failed: {str(result)}"},
                    sequence=self._next_sequence(),
                )
            else:
                yield OrchestrationEvent(
                    event_type="opinion",
                    data={
                        "agent_name": next(a.name for a in parallel_agents if a.id == result["agent_id"]),
                        "content": result["content"],
                        "node_id": result["node_id"],
                    },
                    agent_id=result["agent_id"],
                    sequence=self._next_sequence(),
                )
        
        # Follow outgoing edges
        await self._follow_outgoing_edges(node["id"], agents, state)

    async def _execute_merge_node(
        self,
        node: Dict[str, Any],
        agents: list[AgentInstance],
        state: OrchestrationState,
    ):
        """Execute a merge node."""
        # A merge node simply consolidates inputs from multiple branches
        # In this simplified version, we just continue to the next nodes
        await self._follow_outgoing_edges(node["id"], agents, state)

    async def _execute_loop_node(
        self,
        node: Dict[str, Any],
        agents: list[AgentInstance],
        state: OrchestrationState,
    ):
        """Execute a loop node."""
        config = node.get("config", {})
        max_iterations = config.get("max_iterations", 5)
        condition = config.get("condition", "continue")
        
        iteration = 0
        while iteration < max_iterations:
            # Execute the loop body (connected to this node)
            await self._follow_outgoing_edges(node["id"], agents, state)
            
            # Check if we should continue
            if condition == "continue":
                should_continue = True
            elif condition == "has_opinions":
                should_continue = len(state.opinions) < 10
            else:
                should_continue = False
            
            if not should_continue:
                break
                
            iteration += 1

    async def _execute_user_input_node(
        self,
        node: Dict[str, Any],
        agents: list[AgentInstance],
        state: OrchestrationState,
    ):
        """Execute a user input node."""
        # In a real implementation, this would pause execution and wait for user input
        # For now, we'll just continue to the next nodes
        yield OrchestrationEvent(
            event_type="status",
            data={"message": "Waiting for user input", "node_id": node["id"]},
            sequence=self._next_sequence(),
        )
        
        await self._follow_outgoing_edges(node["id"], agents, state)

    async def _follow_outgoing_edges(
        self,
        node_id: str,
        agents: list[AgentInstance],
        state: OrchestrationState,
    ):
        """Follow outgoing edges from a node."""
        edges = [edge for edge in self.workflow.get("edges", []) if edge["source"] == node_id]
        for edge in edges:
            await self._execute_node(edge["target"], agents, state)

    async def handle_followup(
        self,
        followup: str,
        agents: list[AgentInstance],
        state: OrchestrationState,
        target_agent_id: Optional[str] = None,
    ) -> AsyncIterator[OrchestrationEvent]:
        """Handle follow-up question in custom workflow context."""
        # For custom workflows, we'll add a special follow-up node
        yield OrchestrationEvent(
            event_type="status",
            data={"message": "Processing follow-up in custom workflow"},
            sequence=self._next_sequence(),
        )
        
        # If a specific agent is targeted, create a simple agent node execution
        if target_agent_id:
            agent = next((a for a in agents if a.id == target_agent_id), None)
            if agent:
                response = await agent.generate_opinion(
                    topic=followup,
                    discussion_summary=state.summary,
                    recent_opinions=[],
                    phase="followup",
                )
                
                opinion = Opinion(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    content=response.content,
                    round=state.round + 1,
                    phase="followup",
                    confidence=response.confidence,
                    wants_to_continue=response.wants_to_continue,
                    input_tokens=response.metadata.get("input_tokens", 0),
                    output_tokens=response.metadata.get("output_tokens", 0),
                )
                state.add_opinion(opinion)
                
                yield OrchestrationEvent(
                    event_type="opinion",
                    data={
                        "agent_name": agent.name,
                        "content": response.content,
                        "phase": "followup",
                    },
                    agent_id=agent.id,
                    sequence=self._next_sequence(),
                )
        else:
            # For non-targeted follow-ups, we could implement a more complex workflow
            # For now, just return a status
            yield OrchestrationEvent(
                event_type="status",
                data={"message": "Follow-up processing completed"},
                sequence=self._next_sequence(),
            )