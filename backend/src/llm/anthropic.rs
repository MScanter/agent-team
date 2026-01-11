use async_trait::async_trait;
use reqwest::header::{HeaderMap, HeaderValue, CONTENT_TYPE, USER_AGENT};
use serde::Deserialize;

use crate::error::AppError;
use crate::llm::provider::{
    estimate_tokens, LLMProvider, LLMResponse, Message, MessageRole, TokenUsage,
};
use crate::tools::definition::{ToolCall, ToolDefinition};

#[derive(Clone)]
pub struct AnthropicProvider {
    client: reqwest::Client,
    model: String,
    base_url: String,
}

impl AnthropicProvider {
    pub fn new(api_key: String, model: String, base_url: Option<String>) -> Result<Self, AppError> {
        let base_url = base_url
            .unwrap_or_else(|| "https://api.anthropic.com".to_string())
            .trim_end_matches('/')
            .to_string();

        let mut headers = HeaderMap::new();
        headers.insert(
            "x-api-key",
            HeaderValue::from_str(&api_key).map_err(|e| AppError::Message(e.to_string()))?,
        );
        headers.insert("anthropic-version", HeaderValue::from_static("2023-06-01"));
        headers.insert(CONTENT_TYPE, HeaderValue::from_static("application/json"));
        headers.insert(
            USER_AGENT,
            HeaderValue::from_static(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            ),
        );

        let client = reqwest::Client::builder()
            .default_headers(headers)
            .timeout(std::time::Duration::from_secs(60))
            .build()
            .map_err(|e| AppError::Message(e.to_string()))?;

        Ok(Self {
            client,
            model,
            base_url,
        })
    }

    fn endpoint(&self) -> String {
        format!("{}/v1/messages", self.base_url.trim_end_matches('/'))
    }

    fn convert_messages(&self, messages: Vec<Message>) -> (Option<String>, Vec<serde_json::Value>) {
        let mut system: Option<String> = None;
        let mut out = Vec::new();
        for msg in messages {
            match msg.role {
                MessageRole::System => system = msg.content,
                MessageRole::User => out.push(serde_json::json!({"role": "user", "content": msg.content.unwrap_or_default()})),
                MessageRole::Assistant => out.push(serde_json::json!({"role": "assistant", "content": msg.content.unwrap_or_default()})),
                MessageRole::Tool => {
                    // Tool messages are not supported in this minimal implementation; treat as user text.
                    out.push(serde_json::json!({"role": "user", "content": msg.content.unwrap_or_default()}))
                }
            }
        }
        (system, out)
    }

    fn convert_messages_with_tools(
        &self,
        messages: Vec<Message>,
    ) -> (Option<String>, Vec<serde_json::Value>) {
        let mut system_parts: Vec<String> = Vec::new();
        let mut out = Vec::new();

        for msg in messages {
            match msg.role {
                MessageRole::System => {
                    if let Some(text) = msg.content {
                        if !text.trim().is_empty() {
                            system_parts.push(text);
                        }
                    }
                }
                MessageRole::User => {
                    out.push(serde_json::json!({
                        "role": "user",
                        "content": [{ "type": "text", "text": msg.content.unwrap_or_default() }]
                    }));
                }
                MessageRole::Assistant => {
                    let mut blocks = Vec::new();
                    if let Some(text) = msg.content {
                        if !text.trim().is_empty() {
                            blocks.push(serde_json::json!({ "type": "text", "text": text }));
                        }
                    }
                    if let Some(tool_calls) = msg.tool_calls {
                        for tc in tool_calls {
                            blocks.push(serde_json::json!({
                                "type": "tool_use",
                                "id": tc.id,
                                "name": tc.name,
                                "input": tc.arguments
                            }));
                        }
                    }
                    if blocks.is_empty() {
                        blocks.push(serde_json::json!({ "type": "text", "text": "" }));
                    }
                    out.push(serde_json::json!({ "role": "assistant", "content": blocks }));
                }
                MessageRole::Tool => {
                    let tool_use_id = msg.tool_call_id.unwrap_or_default();
                    out.push(serde_json::json!({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": msg.content.unwrap_or_default()
                        }]
                    }));
                }
            }
        }

        let system = if system_parts.is_empty() {
            None
        } else {
            Some(system_parts.join("\n\n"))
        };
        (system, out)
    }
}

#[async_trait]
impl LLMProvider for AnthropicProvider {
    fn provider_name(&self) -> &'static str {
        "anthropic"
    }

    fn model_id(&self) -> &str {
        &self.model
    }

    async fn chat(
        &self,
        messages: Vec<Message>,
        temperature: f64,
        max_tokens: u32,
    ) -> Result<LLMResponse, AppError> {
        let (system, converted) = self.convert_messages(messages);

        let mut body = serde_json::json!({
            "model": self.model,
            "messages": converted,
            "max_tokens": max_tokens,
            "temperature": temperature
        });
        if let Some(system) = system {
            body["system"] = serde_json::Value::String(system);
        }

        let resp = self
            .client
            .post(self.endpoint())
            .json(&body)
            .send()
            .await
            .map_err(|e| AppError::Message(e.to_string()))?;

        if !resp.status().is_success() {
            let status = resp.status();
            let text = resp.text().await.unwrap_or_else(|_| "".to_string());
            return Err(AppError::Message(format!(
                "Anthropic error: {status} {text}"
            )));
        }

        let parsed: AnthropicMessageResponse = resp
            .json()
            .await
            .map_err(|e| AppError::Message(e.to_string()))?;

        let mut content = String::new();
        for block in parsed.content {
            if block.r#type == "text" {
                content.push_str(&block.text.unwrap_or_default());
            }
        }

        let prompt_tokens = parsed.usage.input_tokens;
        let completion_tokens = parsed.usage.output_tokens;
        let estimated = prompt_tokens.is_none() || completion_tokens.is_none();
        let input_tokens = prompt_tokens.unwrap_or_else(|| estimate_tokens(&body.to_string()));
        let output_tokens = completion_tokens.unwrap_or_else(|| estimate_tokens(&content));

        Ok(LLMResponse {
            content,
            usage: TokenUsage {
                input_tokens,
                output_tokens,
                estimated,
            },
            model: parsed.model.unwrap_or_else(|| self.model.clone()),
            finish_reason: parsed.stop_reason,
            tool_calls: Vec::new(),
        })
    }

    async fn chat_with_tools(
        &self,
        messages: Vec<Message>,
        tools: &[ToolDefinition],
        temperature: f64,
        max_tokens: u32,
    ) -> Result<LLMResponse, AppError> {
        if tools.is_empty() {
            return self.chat(messages, temperature, max_tokens).await;
        }

        let (system, converted) = self.convert_messages_with_tools(messages);
        let tool_defs = tools
            .iter()
            .map(|t| {
                serde_json::json!({
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.parameters
                })
            })
            .collect::<Vec<_>>();

        let mut body = serde_json::json!({
            "model": self.model,
            "messages": converted,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "tools": tool_defs
        });
        if let Some(system) = system {
            body["system"] = serde_json::Value::String(system);
        }

        let resp = self
            .client
            .post(self.endpoint())
            .json(&body)
            .send()
            .await
            .map_err(|e| AppError::Message(e.to_string()))?;

        if !resp.status().is_success() {
            let status = resp.status();
            let text = resp.text().await.unwrap_or_else(|_| "".to_string());
            return Err(AppError::Message(format!(
                "Anthropic error: {status} {text}"
            )));
        }

        let parsed: AnthropicMessageResponse = resp
            .json()
            .await
            .map_err(|e| AppError::Message(e.to_string()))?;

        let mut content = String::new();
        let mut tool_calls: Vec<ToolCall> = Vec::new();
        for block in parsed.content {
            match block.r#type.as_str() {
                "text" => {
                    if let Some(text) = block.text {
                        content.push_str(&text);
                    }
                }
                "tool_use" => {
                    if let (Some(id), Some(name), Some(input)) = (block.id, block.name, block.input)
                    {
                        tool_calls.push(ToolCall {
                            id,
                            name,
                            arguments: input,
                        });
                    }
                }
                _ => {}
            }
        }

        let prompt_tokens = parsed.usage.input_tokens;
        let completion_tokens = parsed.usage.output_tokens;
        let estimated = prompt_tokens.is_none() || completion_tokens.is_none();

        let output_estimate_text = if tool_calls.is_empty() {
            content.clone()
        } else {
            format!(
                "{content}\n{}",
                serde_json::to_string(&tool_calls).unwrap_or_default()
            )
        };

        Ok(LLMResponse {
            content,
            usage: TokenUsage {
                input_tokens: prompt_tokens.unwrap_or_else(|| estimate_tokens(&body.to_string())),
                output_tokens: completion_tokens
                    .unwrap_or_else(|| estimate_tokens(&output_estimate_text)),
                estimated,
            },
            model: parsed.model.unwrap_or_else(|| self.model.clone()),
            finish_reason: parsed.stop_reason,
            tool_calls,
        })
    }
}

#[derive(Debug, Deserialize)]
struct AnthropicMessageResponse {
    pub model: Option<String>,
    pub content: Vec<AnthropicContentBlock>,
    pub stop_reason: Option<String>,
    pub usage: AnthropicUsage,
}

#[derive(Debug, Deserialize)]
struct AnthropicContentBlock {
    pub r#type: String,
    pub text: Option<String>,
    pub id: Option<String>,
    pub name: Option<String>,
    pub input: Option<serde_json::Value>,
}

#[derive(Debug, Deserialize)]
struct AnthropicUsage {
    pub input_tokens: Option<u32>,
    pub output_tokens: Option<u32>,
}
