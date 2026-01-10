use async_trait::async_trait;
use reqwest::header::{HeaderMap, HeaderValue, CONTENT_TYPE, USER_AGENT};
use serde::Deserialize;

use crate::error::AppError;
use crate::llm::provider::{LLMProvider, LLMResponse, Message, MessageRole, TokenUsage};

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
        headers.insert("x-api-key", HeaderValue::from_str(&api_key).map_err(|e| AppError::Message(e.to_string()))?);
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
                MessageRole::System => system = Some(msg.content),
                MessageRole::User => out.push(serde_json::json!({"role": "user", "content": msg.content})),
                MessageRole::Assistant => out.push(serde_json::json!({"role": "assistant", "content": msg.content})),
                MessageRole::Tool => {
                    // Tool messages are not supported in this minimal implementation; treat as user text.
                    out.push(serde_json::json!({"role": "user", "content": msg.content}))
                }
            }
        }
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
            return Err(AppError::Message(format!("Anthropic error: {status} {text}")));
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

        Ok(LLMResponse {
            content,
            usage: TokenUsage {
                input_tokens: parsed.usage.input_tokens.unwrap_or(0),
                output_tokens: parsed.usage.output_tokens.unwrap_or(0),
            },
            model: parsed.model.unwrap_or_else(|| self.model.clone()),
            finish_reason: parsed.stop_reason,
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
}

#[derive(Debug, Deserialize)]
struct AnthropicUsage {
    pub input_tokens: Option<u32>,
    pub output_tokens: Option<u32>,
}
