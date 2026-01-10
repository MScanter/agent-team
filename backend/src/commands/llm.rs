use serde::Serialize;

use crate::error::AppError;
use crate::llm::factory::provider_from_runtime_config;
use crate::llm::openai_compatible::normalize_openai_compatible_base_url;
use crate::llm::provider::{Message, MessageRole};
use crate::models::llm::{LLMRuntimeConfig, ProviderKind};

#[derive(Debug, Clone, Serialize)]
pub struct TestLLMResponse {
    pub message: String,
    pub response_preview: String,
    pub tokens_used: u32,
    pub resolved_base_url: Option<String>,
}

#[tauri::command]
pub async fn test_llm(config: LLMRuntimeConfig, test_message: String) -> Result<TestLLMResponse, AppError> {
    let resolved_base_url = match &config.provider {
        ProviderKind::OpenaiCompatible => Some(normalize_openai_compatible_base_url(config.base_url.clone())),
        _ => None,
    };

    let provider = provider_from_runtime_config(&config)?;
    let messages = vec![Message {
        role: MessageRole::User,
        content: test_message,
        name: None,
    }];

    let resp = provider.chat(messages, 0.2, 64).await?;
    let preview = if resp.content.len() > 100 {
        format!("{}...", &resp.content[..100])
    } else {
        resp.content.clone()
    };

    Ok(TestLLMResponse {
        message: format!("Test successful for model {}", config.model_id),
        response_preview: preview,
        tokens_used: resp.usage.input_tokens.saturating_add(resp.usage.output_tokens),
        resolved_base_url,
    })
}
