use std::sync::Arc;

use crate::error::AppError;
use crate::llm::anthropic::AnthropicProvider;
use crate::llm::openai_compatible::OpenAICompatibleProvider;
use crate::llm::provider::LLMProvider;
use crate::models::llm::{ExecutionLLMConfig, LLMRuntimeConfig, ProviderKind};

pub fn provider_from_runtime_config(cfg: &LLMRuntimeConfig) -> Result<Arc<dyn LLMProvider>, AppError> {
    if cfg.api_key.trim().is_empty() {
        return Err(AppError::Message("Model config is missing api_key".to_string()));
    }

    let provider: Arc<dyn LLMProvider> = match &cfg.provider {
        ProviderKind::OpenaiCompatible => Arc::new(OpenAICompatibleProvider::new(
            cfg.api_key.clone(),
            cfg.model_id.clone(),
            cfg.base_url.clone(),
        )?),
        ProviderKind::Anthropic => Arc::new(AnthropicProvider::new(
            cfg.api_key.clone(),
            cfg.model_id.clone(),
            cfg.base_url.clone(),
        )?),
    };

    Ok(provider)
}

pub fn resolve_runtime_config_for_agent(
    agent_model_id: Option<&str>,
    llm: &ExecutionLLMConfig,
) -> Result<LLMRuntimeConfig, AppError> {
    let model_ref = agent_model_id.map(|s| s.trim()).filter(|s| !s.is_empty());

    if let Some(model_ref) = model_ref {
        if let Some(cfg) = llm.models.get(model_ref) {
            return Ok(cfg.clone());
        }

        if looks_like_client_config_id(model_ref) {
            return Err(AppError::Message(format!(
                "Agent model_id '{model_ref}' refers to a client-side model config, but it is not available in this execution's llm bundle."
            )));
        }
    }

    let mut cfg = llm.default.clone();
    if let Some(model_ref) = model_ref {
        cfg.model_id = model_ref.to_string();
    }
    Ok(cfg)
}

fn looks_like_client_config_id(value: &str) -> bool {
    if value.starts_with("mc_") {
        return true;
    }
    let parts: Vec<&str> = value.split('-').collect();
    if parts.len() != 5 {
        return false;
    }
    let expected = [8, 4, 4, 4, 12];
    for (p, &len) in parts.iter().zip(expected.iter()) {
        if p.len() != len {
            return false;
        }
    }
    true
}
