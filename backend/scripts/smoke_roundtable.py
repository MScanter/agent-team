import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from app.agents.base import AgentConfig, AgentInstance
from app.llm.base import LLMProvider, Message, LLMResponse, TokenUsage, TokenPricing
from app.orchestration.base import OrchestrationState
from app.orchestration.roundtable import RoundtableOrchestrator


class FakeLLMProvider(LLMProvider):
    def __init__(self, *, provider_name: str, model_id: str, responder):
        self._provider_name = provider_name
        self._model_id = model_id
        self._responder = responder
        self.calls = 0

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_id(self) -> str:
        return self._model_id

    async def chat(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[list] = None,
        **kwargs,
    ) -> LLMResponse:
        self.calls += 1
        content = self._responder(messages)
        return LLMResponse(
            content=content,
            usage=TokenUsage(input_tokens=1, output_tokens=1),
            model=self._model_id,
            finish_reason="stop",
        )

    async def stream(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> AsyncIterator[str]:
        if False:
            yield ""

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def get_pricing(self) -> TokenPricing:
        return TokenPricing(input_price_per_1k=0.0, output_price_per_1k=0.0)

    @property
    def max_context_length(self) -> int:
        return 100000


def _coordinator_responder(messages: list[Message]) -> str:
    prompt = messages[-1].content
    if "请生成更新后的讨论摘要" in prompt:
        return """{
  "key_points": ["要点1"],
  "consensus": ["共识1"],
  "disagreements": [],
  "summary_text": "简短摘要"
}"""
    if "请生成最终的讨论总结报告" in prompt:
        return "# 最终总结\\n\\n- 结论：OK\\n"
    return "[]"


def _agent_responder_factory(*, text: str):
    def _responder(messages: list[Message]) -> str:
        return text

    return _responder


async def main() -> None:
    coordinator_llm = FakeLLMProvider(provider_name="fake", model_id="fake-coordinator", responder=_coordinator_responder)

    # Agent A opts out after first opinion; Agent B keeps going.
    agent_a_llm = FakeLLMProvider(
        provider_name="fake",
        model_id="fake-agent-a",
        responder=_agent_responder_factory(text="我的观点：先这样，没有更多。"),
    )
    agent_b_llm = FakeLLMProvider(
        provider_name="fake",
        model_id="fake-agent-b",
        responder=_agent_responder_factory(text="补充观点：还有一些点可以继续讨论。"),
    )

    agent_a = AgentInstance(
        config=AgentConfig(id="a", name="A", system_prompt="A"),
        llm_provider=agent_a_llm,
    )
    agent_b = AgentInstance(
        config=AgentConfig(id="b", name="B", system_prompt="B"),
        llm_provider=agent_b_llm,
    )

    orchestrator = RoundtableOrchestrator({"max_rounds": 2}, coordinator_llm=coordinator_llm)
    state = OrchestrationState(topic="测试主题", tokens_budget=1000, cost_budget=1.0)

    events = []
    async for event in orchestrator.run([agent_a, agent_b], state):
        events.append(event)

    assert agent_a_llm.calls == 1, f"agent_a_llm.calls={agent_a_llm.calls} (expected 1)"
    assert agent_b_llm.calls == 4, f"agent_b_llm.calls={agent_b_llm.calls} (expected 4)"
    assert any(e.event_type == "done" for e in events), "missing done event"

    print("smoke_roundtable: ok")


if __name__ == "__main__":
    asyncio.run(main())

