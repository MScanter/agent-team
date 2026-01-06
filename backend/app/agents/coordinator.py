"""
Coordinator agent for managing discussions.
"""

from dataclasses import dataclass, field
from typing import Optional

from app.llm import LLMProvider, Message, MessageRole


@dataclass
class DiscussionSummary:
    """Summary of discussion state."""

    topic: str
    round: int
    key_points: list[str] = field(default_factory=list)
    consensus: list[str] = field(default_factory=list)
    disagreements: list[dict] = field(default_factory=list)
    summary_text: str = ""


class Coordinator:
    """
    Coordinator manages the discussion flow.

    Responsibilities:
    - Analyze user questions and select relevant agents
    - Maintain discussion summary
    - Track token usage and budget
    - Determine when to end discussion
    """

    SYSTEM_PROMPT = """你是一个讨论协调者，负责管理多个专家之间的讨论。

你的职责：
1. 分析用户的问题，判断需要哪些专业领域的专家参与
2. 维护讨论摘要，提取关键观点和分歧
3. 在适当的时候总结讨论结果
4. 确保讨论有序进行

你不直接参与讨论内容，而是负责组织和协调。"""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        if llm_provider is None:
            raise ValueError("Coordinator requires an LLM provider (configure via ExecutionCreate.llm).")
        self.llm = llm_provider
        self._summary = DiscussionSummary(topic="", round=0)

    async def analyze_question(
        self,
        question: str,
        available_agents: list[dict],
    ) -> list[str]:
        """
        Analyze user question and select relevant agents.

        Args:
            question: User's question
            available_agents: List of available agents with their domains

        Returns:
            List of agent IDs that should participate
        """
        agents_info = "\n".join(
            f"- {a['name']} (ID: {a['id']}): {a.get('domain', '通用')} - {a.get('description', '')}"
            for a in available_agents
        )

        messages = [
            Message(role=MessageRole.SYSTEM, content=self.SYSTEM_PROMPT),
            Message(
                role=MessageRole.USER,
                content=f"""用户问题：{question}

可用专家：
{agents_info}

请分析这个问题需要哪些专家参与讨论。
返回格式：只返回专家ID列表，用逗号分隔，不要其他内容。
例如：agent_id_1,agent_id_2,agent_id_3""",
            ),
        ]

        response = await self.llm.chat(messages=messages, temperature=0.3, max_tokens=500)

        # Parse response to get agent IDs
        agent_ids = [
            aid.strip()
            for aid in response.content.strip().split(",")
            if aid.strip()
        ]

        # Validate IDs exist
        valid_ids = {a["id"] for a in available_agents}
        return [aid for aid in agent_ids if aid in valid_ids]

    async def generate_summary(
        self,
        topic: str,
        opinions: list[dict],
        previous_summary: str = "",
    ) -> DiscussionSummary:
        """
        Generate updated discussion summary.

        Args:
            topic: Discussion topic
            opinions: List of opinions from agents
            previous_summary: Previous summary to build upon

        Returns:
            Updated DiscussionSummary
        """
        opinions_text = "\n".join(
            f"**{op['agent_name']}**: {op['content']}"
            for op in opinions
        )

        messages = [
            Message(role=MessageRole.SYSTEM, content=self.SYSTEM_PROMPT),
            Message(
                role=MessageRole.USER,
                content=f"""讨论主题：{topic}

之前的摘要：
{previous_summary if previous_summary else "（无）"}

最新的专家观点：
{opinions_text}

请生成更新后的讨论摘要，包括：
1. 关键要点（3-5个）
2. 已达成的共识
3. 仍存在的分歧
4. 简短的总结文字（不超过200字）

请用JSON格式返回：
{{
  "key_points": ["要点1", "要点2"],
  "consensus": ["共识1", "共识2"],
  "disagreements": [{{"point": "分歧点", "parties": ["专家A", "专家B"]}}],
  "summary_text": "总结文字"
}}""",
            ),
        ]

        response = await self.llm.chat(messages=messages, temperature=0.3, max_tokens=1000)

        # Parse JSON response
        import json

        try:
            data = json.loads(response.content)
            self._summary = DiscussionSummary(
                topic=topic,
                round=self._summary.round + 1,
                key_points=data.get("key_points", []),
                consensus=data.get("consensus", []),
                disagreements=data.get("disagreements", []),
                summary_text=data.get("summary_text", ""),
            )
        except json.JSONDecodeError:
            # Fallback: use raw text as summary
            self._summary = DiscussionSummary(
                topic=topic,
                round=self._summary.round + 1,
                summary_text=response.content,
            )

        return self._summary

    async def route_followup(
        self,
        followup: str,
        available_agents: list[dict],
        current_summary: DiscussionSummary,
    ) -> dict:
        """
        Route a follow-up question to appropriate agents.

        Args:
            followup: User's follow-up question
            available_agents: List of available agents
            current_summary: Current discussion summary

        Returns:
            Dict with routing decision:
            {
                "type": "specific" | "all" | "summary",
                "agent_ids": [...],
                "instruction": "..."
            }
        """
        agents_info = "\n".join(
            f"- {a['name']} (ID: {a['id']}): {a.get('domain', '通用')}"
            for a in available_agents
        )

        messages = [
            Message(role=MessageRole.SYSTEM, content=self.SYSTEM_PROMPT),
            Message(
                role=MessageRole.USER,
                content=f"""当前讨论摘要：
{current_summary.summary_text}

参与的专家：
{agents_info}

用户追问：{followup}

请分析这个追问应该如何路由：
1. 如果是针对某个专家的追问，返回该专家ID
2. 如果是新问题，返回所有相关专家ID
3. 如果是要求总结，返回 "summary"

返回JSON格式：
{{
  "type": "specific" | "all" | "summary",
  "agent_ids": ["id1", "id2"],
  "instruction": "给专家的指令"
}}""",
            ),
        ]

        response = await self.llm.chat(messages=messages, temperature=0.3, max_tokens=500)

        import json

        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            # Default to all agents
            return {
                "type": "all",
                "agent_ids": [a["id"] for a in available_agents],
                "instruction": followup,
            }

    async def generate_final_summary(
        self,
        topic: str,
        all_opinions: list[dict],
        summary: DiscussionSummary,
    ) -> str:
        """
        Generate final discussion summary.

        Args:
            topic: Discussion topic
            all_opinions: All opinions from the discussion
            summary: Current summary state

        Returns:
            Final summary text
        """
        opinions_text = "\n".join(
            f"**{op['agent_name']}** (第{op.get('round', '?')}轮): {op['content']}"
            for op in all_opinions
        )

        messages = [
            Message(role=MessageRole.SYSTEM, content=self.SYSTEM_PROMPT),
            Message(
                role=MessageRole.USER,
                content=f"""讨论主题：{topic}

所有专家观点：
{opinions_text}

当前摘要：
- 关键要点：{', '.join(summary.key_points)}
- 共识：{', '.join(summary.consensus)}
- 分歧：{summary.disagreements}

请生成最终的讨论总结报告，包括：
1. 主要结论
2. 专家们的核心观点
3. 达成的共识
4. 仍有分歧的地方
5. 建议的下一步行动

请用清晰的Markdown格式输出。""",
            ),
        ]

        response = await self.llm.chat(messages=messages, temperature=0.5, max_tokens=2000)
        return response.content

    def reset(self):
        """Reset coordinator state."""
        self._summary = DiscussionSummary(topic="", round=0)
