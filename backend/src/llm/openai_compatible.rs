use crate::error::AppError;
use crate::llm::provider::{estimate_tokens, LLMProvider, LLMResponse, Message, TokenUsage};
use crate::tools::definition::{ToolCall, ToolDefinition};
use async_trait::async_trait;
use reqwest::header::{HeaderMap, HeaderValue, AUTHORIZATION, CONTENT_TYPE, USER_AGENT};
use serde::Deserialize;

#[derive(Clone)]
pub struct OpenAICompatibleProvider {
    client: reqwest::Client,
    model: String,
    base_url: String,
}

impl OpenAICompatibleProvider {
    pub fn new(api_key: String, model: String, base_url: Option<String>) -> Result<Self, AppError> {
        let base_url = normalize_openai_compatible_base_url(base_url);
        let mut headers = HeaderMap::new();
        headers.insert(
            AUTHORIZATION,
            HeaderValue::from_str(&format!("Bearer {}", api_key))
                .map_err(|e| AppError::Message(e.to_string()))?,
        );
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
        format!("{}/chat/completions", self.base_url.trim_end_matches('/'))
    }
}

#[async_trait]
impl LLMProvider for OpenAICompatibleProvider {
    fn provider_name(&self) -> &'static str {
        "openai_compatible"
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
        let body = serde_json::json!({
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        });

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
                "OpenAI-compatible error: {status} {text}"
            )));
        }

        let parsed: ChatResponse = resp
            .json()
            .await
            .map_err(|e| AppError::Message(e.to_string()))?;

        let choice = parsed
            .choices
            .get(0)
            .ok_or_else(|| AppError::Message("No choices".to_string()))?;
        let content = choice.message.content.clone().unwrap_or_default();

        let prompt_tokens = parsed.usage.as_ref().and_then(|u| u.prompt_tokens);
        let completion_tokens = parsed.usage.as_ref().and_then(|u| u.completion_tokens);
        let estimated = prompt_tokens.is_none() || completion_tokens.is_none();

        Ok(LLMResponse {
            content,
            usage: TokenUsage {
                input_tokens: prompt_tokens.unwrap_or_else(|| estimate_tokens(&body.to_string())),
                output_tokens: completion_tokens.unwrap_or_else(|| {
                    estimate_tokens(&choice.message.content.clone().unwrap_or_default())
                }),
                estimated,
            },
            model: parsed.model.unwrap_or_else(|| self.model.clone()),
            finish_reason: choice.finish_reason.clone(),
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
        let tool_defs = tools
            .iter()
            .map(|t| {
                serde_json::json!({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters
                    }
                })
            })
            .collect::<Vec<_>>();

        let openai_messages = messages
            .into_iter()
            .map(to_openai_message)
            .collect::<Result<Vec<_>, AppError>>()?;

        let body = serde_json::json!({
            "model": self.model,
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "tools": tool_defs,
            "tool_choice": "auto"
        });

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
                "OpenAI-compatible error: {status} {text}"
            )));
        }

        let parsed: ChatResponse = resp
            .json()
            .await
            .map_err(|e| AppError::Message(e.to_string()))?;

        let choice = parsed
            .choices
            .get(0)
            .ok_or_else(|| AppError::Message("No choices".to_string()))?;

        let content = choice.message.content.clone().unwrap_or_default();
        let tool_calls: Vec<ToolCall> = choice
            .message
            .tool_calls
            .clone()
            .unwrap_or_default()
            .into_iter()
            .map(|tc| {
                let args_value = serde_json::from_str(&tc.function.arguments)
                    .unwrap_or_else(|_| serde_json::Value::String(tc.function.arguments));
                ToolCall {
                    id: tc.id,
                    name: tc.function.name,
                    arguments: args_value,
                }
            })
            .collect();

        let prompt_tokens = parsed.usage.as_ref().and_then(|u| u.prompt_tokens);
        let completion_tokens = parsed.usage.as_ref().and_then(|u| u.completion_tokens);
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
            finish_reason: choice.finish_reason.clone(),
            tool_calls,
        })
    }
}

#[derive(Debug, Deserialize)]
struct ChatResponse {
    pub choices: Vec<ChatChoice>,
    pub model: Option<String>,
    pub usage: Option<ChatUsage>,
}

#[derive(Debug, Deserialize)]
struct ChatChoice {
    pub message: ChatMessage,
    pub finish_reason: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ChatMessage {
    pub content: Option<String>,
    pub tool_calls: Option<Vec<OpenAIToolCall>>,
}

#[derive(Debug, Deserialize)]
struct ChatUsage {
    pub prompt_tokens: Option<u32>,
    pub completion_tokens: Option<u32>,
}

#[derive(Debug, Clone, Deserialize)]
struct OpenAIToolCall {
    pub id: String,
    #[allow(dead_code)]
    #[serde(rename = "type")]
    pub r#type: String,
    pub function: OpenAIFunctionCall,
}

#[derive(Debug, Clone, Deserialize)]
struct OpenAIFunctionCall {
    pub name: String,
    pub arguments: String,
}

fn to_openai_message(msg: Message) -> Result<serde_json::Value, AppError> {
    let role = match msg.role {
        crate::llm::provider::MessageRole::System => "system",
        crate::llm::provider::MessageRole::User => "user",
        crate::llm::provider::MessageRole::Assistant => "assistant",
        crate::llm::provider::MessageRole::Tool => "tool",
    };

    let mut out = serde_json::Map::new();
    out.insert(
        "role".to_string(),
        serde_json::Value::String(role.to_string()),
    );
    out.insert(
        "content".to_string(),
        msg.content
            .map(serde_json::Value::String)
            .unwrap_or(serde_json::Value::Null),
    );

    if let Some(name) = msg.name {
        out.insert("name".to_string(), serde_json::Value::String(name));
    }

    if let Some(tool_call_id) = msg.tool_call_id {
        out.insert(
            "tool_call_id".to_string(),
            serde_json::Value::String(tool_call_id),
        );
    }

    if let Some(tool_calls) = msg.tool_calls {
        let mapped = tool_calls
            .into_iter()
            .map(|tc| {
                let args = serde_json::to_string(&tc.arguments)
                    .map_err(|e| AppError::Message(e.to_string()))?;
                Ok(serde_json::json!({
                    "id": tc.id,
                    "type": "function",
                    "function": { "name": tc.name, "arguments": args }
                }))
            })
            .collect::<Result<Vec<_>, AppError>>()?;
        out.insert("tool_calls".to_string(), serde_json::Value::Array(mapped));
    }

    Ok(serde_json::Value::Object(out))
}

pub fn normalize_openai_compatible_base_url(base_url: Option<String>) -> String {
    let default_url = "https://api.openai.com/v1".to_string();
    let Some(mut base) = base_url else {
        return default_url;
    };
    base = base.trim().to_string();
    if base.is_empty() {
        return default_url;
    }

    // Users sometimes paste full endpoint.
    let trimmed = base.trim_end_matches('/');
    if trimmed.ends_with("/chat/completions") {
        base = trimmed
            .strip_suffix("/chat/completions")
            .unwrap_or(trimmed)
            .to_string();
    }

    // Only append /v1 when no path provided.
    match url::Url::parse(&base) {
        Ok(url) => {
            let path = url.path();
            if path.is_empty() || path == "/" {
                return format!("{}/v1", base.trim_end_matches('/'));
            }
            if base.ends_with("/v1/") {
                return base[..base.len() - 1].to_string();
            }
            base.trim_end_matches('/').to_string()
        }
        Err(_) => base.trim_end_matches('/').to_string(),
    }
}
