use async_trait::async_trait;
use serde::{Deserialize, Serialize};

use crate::error::AppError;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum MessageRole {
    System,
    User,
    Assistant,
    Tool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub role: MessageRole,
    pub content: String,
    #[serde(default)]
    pub name: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenUsage {
    pub input_tokens: u32,
    pub output_tokens: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LLMResponse {
    pub content: String,
    pub usage: TokenUsage,
    pub model: String,
    #[serde(default)]
    pub finish_reason: Option<String>,
}

#[async_trait]
pub trait LLMProvider: Send + Sync {
    fn provider_name(&self) -> &'static str;
    fn model_id(&self) -> &str;

    async fn chat(
        &self,
        messages: Vec<Message>,
        temperature: f64,
        max_tokens: u32,
    ) -> Result<LLMResponse, AppError>;
}

