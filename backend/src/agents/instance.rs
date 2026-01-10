use serde::{Deserialize, Serialize};

use crate::models::agent::Agent;
use crate::llm::provider::{LLMProvider, Message, MessageRole};

#[derive(Clone)]
pub struct AgentInstance {
    pub id: String,
    pub name: String,
    pub system_prompt: String,
    pub temperature: f64,
    pub max_tokens: u32,
    pub domain: Option<String>,
    pub collaboration_style: String,
    pub speaking_priority: i32,
    llm: std::sync::Arc<dyn LLMProvider>,
    opinions: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentResponse {
    pub content: String,
    #[serde(default = "default_confidence")]
    pub confidence: f64,
    #[serde(default = "default_true")]
    pub wants_to_continue: bool,
    #[serde(default)]
    pub responding_to: Option<String>,
    #[serde(default)]
    pub metadata: serde_json::Value,
}

impl AgentInstance {
    pub fn from_agent(agent: &Agent, llm: std::sync::Arc<dyn LLMProvider>) -> Self {
        Self {
            id: agent.id.clone(),
            name: agent.name.clone(),
            system_prompt: agent.system_prompt.clone(),
            temperature: agent.temperature,
            max_tokens: agent.max_tokens,
            domain: agent.domain.clone(),
            collaboration_style: agent.collaboration_style.clone(),
            speaking_priority: agent.speaking_priority,
            llm,
            opinions: Vec::new(),
        }
    }

    fn build_context_message(
        &self,
        discussion_summary: &str,
        recent_opinions: &[serde_json::Value],
        current_topic: &str,
    ) -> String {
        let mut parts = vec![format!("## 当前讨论主题\n{current_topic}")];
        if !discussion_summary.trim().is_empty() {
            parts.push(format!("## 讨论摘要\n{discussion_summary}"));
        }

        if !recent_opinions.is_empty() {
            let mut lines = Vec::new();
            for op in recent_opinions {
                let agent_name = op.get("agent_name").and_then(|v| v.as_str()).unwrap_or("unknown");
                let content = op.get("content").and_then(|v| v.as_str()).unwrap_or("");
                lines.push(format!("- **{agent_name}**: {content}"));
            }
            parts.push(format!("## 其他专家的观点\n{}", lines.join("\n")));
        }

        if !self.opinions.is_empty() {
            let start = self.opinions.len().saturating_sub(3);
            let mine: Vec<String> = self.opinions[start..].iter().map(|s| format!("- {s}")).collect();
            parts.push(format!("## 你之前的观点\n{}", mine.join("\n")));
        }

        parts.join("\n\n")
    }

    fn system_message(&self) -> Message {
        Message {
            role: MessageRole::System,
            content: self.system_prompt.clone(),
            name: None,
        }
    }

    pub async fn generate_opinion(
        &mut self,
        topic: &str,
        discussion_summary: &str,
        recent_opinions: &[serde_json::Value],
        phase: &str,
    ) -> Result<AgentResponse, crate::error::AppError> {
        let mut messages = vec![self.system_message()];

        let context = self.build_context_message(discussion_summary, recent_opinions, topic);
        messages.push(Message {
            role: MessageRole::User,
            content: context,
            name: None,
        });

        let instruction = if phase == "initial" {
            "请就上述主题发表你的专业观点。\n\n要求：\n1. 从你的专业角度分析\n2. 给出具体、有见地的观点\n3. 如果有其他专家的观点，可以参考但要保持独立思考\n\n请直接输出你的观点，不要加前缀。"
        } else {
            "请根据其他专家的观点进行回应。\n\n你可以：\n1. 补充自己的观点\n2. 对某位专家的观点提出质疑或不同看法\n3. 表示同意某个观点并说明原因\n4. 如果没有新的内容要补充，可以简短表示\n\n请直接输出你的回应，不要加前缀。"
        };
        messages.push(Message {
            role: MessageRole::User,
            content: instruction.to_string(),
            name: None,
        });

        let resp = self
            .llm
            .chat(messages, self.temperature, self.max_tokens)
            .await?;

        let content = resp.content.trim().to_string();
        self.opinions.push(content.clone());
        let wants_to_continue = should_continue(&content);

        Ok(AgentResponse {
            content,
            confidence: 0.8,
            wants_to_continue,
            responding_to: None,
            metadata: serde_json::json!({
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens
            }),
        })
    }
}

fn should_continue(content: &str) -> bool {
    let completion_phrases = [
        "没有补充",
        "没有更多",
        "我同意",
        "我赞同",
        "没有异议",
        "就这些",
    ];
    let lowered = content.to_lowercase();
    for p in completion_phrases {
        if lowered.contains(p) {
            return false;
        }
    }
    true
}

fn default_confidence() -> f64 {
    0.8
}

fn default_true() -> bool {
    true
}
