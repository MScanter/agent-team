use serde::{Deserialize, Serialize};

use crate::llm::provider::{LLMProvider, Message, MessageRole};
use crate::models::agent::Agent;
use crate::tools::definition::{ToolDefinition, ToolTrace};
use crate::tools::executor::ToolExecutor;

#[derive(Clone)]
pub struct AgentInstance {
    pub id: String,
    pub name: String,
    pub system_prompt: String,
    pub temperature: f64,
    pub max_tokens: u32,
    pub max_tool_iterations: u32,
    llm: std::sync::Arc<dyn LLMProvider>,
    opinions: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentResponse {
    pub content: String,
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
            max_tool_iterations: agent.max_tool_iterations.unwrap_or(10).clamp(1, 50),
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
                let agent_name = op
                    .get("agent_name")
                    .and_then(|v| v.as_str())
                    .unwrap_or("unknown");
                let content = op.get("content").and_then(|v| v.as_str()).unwrap_or("");
                lines.push(format!("- **{agent_name}**: {content}"));
            }
            parts.push(format!("## 其他专家的观点\n{}", lines.join("\n")));
        }

        if !self.opinions.is_empty() {
            let start = self.opinions.len().saturating_sub(3);
            let mine: Vec<String> = self.opinions[start..]
                .iter()
                .map(|s| format!("- {s}"))
                .collect();
            parts.push(format!("## 你之前的观点\n{}", mine.join("\n")));
        }

        parts.join("\n\n")
    }

    fn system_message(&self) -> Message {
        Message {
            role: MessageRole::System,
            content: Some(self.system_prompt.clone()),
            name: None,
            tool_call_id: None,
            tool_calls: None,
        }
    }

    #[allow(dead_code)]
    pub async fn generate_opinion(
        &mut self,
        topic: &str,
        discussion_summary: &str,
        recent_opinions: &[serde_json::Value],
        phase: &str,
    ) -> Result<AgentResponse, crate::error::AppError> {
        let (resp, _traces) = self
            .generate_opinion_with_tools(
                topic,
                discussion_summary,
                recent_opinions,
                phase,
                &[],
                None,
            )
            .await?;
        Ok(resp)
    }

    pub async fn generate_opinion_with_tools(
        &mut self,
        topic: &str,
        discussion_summary: &str,
        recent_opinions: &[serde_json::Value],
        phase: &str,
        tools: &[ToolDefinition],
        executor: Option<&ToolExecutor>,
    ) -> Result<(AgentResponse, Vec<ToolTrace>), crate::error::AppError> {
        let mut messages = vec![self.system_message()];

        let context = self.build_context_message(discussion_summary, recent_opinions, topic);
        messages.push(Message {
            role: MessageRole::User,
            content: Some(context),
            name: None,
            tool_call_id: None,
            tool_calls: None,
        });

        let instruction = if phase == "initial" {
            "请就上述主题发表你的专业观点。\n\n要求：\n1. 从你的专业角度分析\n2. 给出具体、有见地的观点\n3. 如果有其他专家的观点，可以参考但要保持独立思考\n\n请直接输出你的观点，不要加前缀。"
        } else {
            "请根据其他专家的观点进行回应。\n\n你可以：\n1. 补充自己的观点\n2. 对某位专家的观点提出质疑或不同看法\n3. 表示同意某个观点并说明原因\n4. 如果没有新的内容要补充，可以简短表示\n\n请直接输出你的回应，不要加前缀。"
        };
        messages.push(Message {
            role: MessageRole::User,
            content: Some(instruction.to_string()),
            name: None,
            tool_call_id: None,
            tool_calls: None,
        });

        let tools_enabled = executor.is_some() && !tools.is_empty();
        if tools_enabled {
            messages.insert(
                1,
                Message {
                    role: MessageRole::System,
                    content: Some(
                        "你可以在需要时调用工具来读取/搜索/修改工作目录下的文件。仅在确有必要时调用工具，并在最终回答中引用工具返回的结果。".to_string(),
                    ),
                    name: None,
                    tool_call_id: None,
                    tool_calls: None,
                },
            );
        }

        let mut traces: Vec<ToolTrace> = Vec::new();
        let mut total_input_tokens: u32 = 0;
        let mut total_output_tokens: u32 = 0;
        let mut tokens_estimated: bool = false;

        let max_iters: usize = self.max_tool_iterations.max(1).min(50) as usize;
        let mut final_text = String::new();
        let mut last_text = String::new();
        for _ in 0..max_iters {
            let resp = if tools_enabled {
                self.llm
                    .chat_with_tools(messages.clone(), tools, self.temperature, self.max_tokens)
                    .await?
            } else {
                self.llm
                    .chat(messages.clone(), self.temperature, self.max_tokens)
                    .await?
            };

            total_input_tokens = total_input_tokens.saturating_add(resp.usage.input_tokens);
            total_output_tokens = total_output_tokens.saturating_add(resp.usage.output_tokens);
            tokens_estimated = tokens_estimated || resp.usage.estimated;
            last_text = resp.content.clone();

            if resp.tool_calls.is_empty() || !tools_enabled {
                final_text = resp.content;
                break;
            }

            let tool_calls = resp.tool_calls.clone();
            messages.push(Message {
                role: MessageRole::Assistant,
                content: None,
                name: None,
                tool_call_id: None,
                tool_calls: Some(tool_calls.clone()),
            });

            for call in tool_calls {
                let Some(executor) = executor else { break };
                let result = executor.execute(call.clone()).await;
                traces.push(ToolTrace {
                    call: call.clone(),
                    result: result.clone(),
                });

                let tool_payload = serde_json::json!({
                    "ok": result.ok,
                    "name": result.name,
                    "output": result.output,
                    "error": result.error
                });
                let tool_content = serde_json::to_string(&tool_payload)
                    .unwrap_or_else(|_| tool_payload.to_string());
                messages.push(Message {
                    role: MessageRole::Tool,
                    content: Some(tool_content),
                    name: None,
                    tool_call_id: Some(result.tool_call_id.clone()),
                    tool_calls: None,
                });
            }
        }

        if final_text.trim().is_empty() {
            final_text = last_text;
        }

        let content = final_text.trim().to_string();
        self.opinions.push(content.clone());
        let wants_to_continue = should_continue(&content);

        Ok((
            AgentResponse {
                content,
                wants_to_continue,
                responding_to: None,
                metadata: serde_json::json!({
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens,
                    "tokens_estimated": tokens_estimated
                }),
            },
            traces,
        ))
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

fn default_true() -> bool {
    true
}
