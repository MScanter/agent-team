use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ProviderKind {
    OpenaiCompatible,
    Anthropic,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LLMRuntimeConfig {
    #[serde(default = "default_provider")]
    pub provider: ProviderKind,
    pub model_id: String,
    pub api_key: String,
    #[serde(default)]
    pub base_url: Option<String>,
    #[serde(default = "default_max_context_length")]
    pub max_context_length: u32,
    #[serde(default = "default_supports_tools")]
    pub supports_tools: bool,
    #[serde(default)]
    pub supports_vision: bool,
    #[serde(default)]
    pub input_price_per_1k: f64,
    #[serde(default)]
    pub output_price_per_1k: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionLLMConfig {
    pub default: LLMRuntimeConfig,
    #[serde(default)]
    pub models: HashMap<String, LLMRuntimeConfig>,
}

fn default_provider() -> ProviderKind {
    ProviderKind::OpenaiCompatible
}

fn default_max_context_length() -> u32 {
    8192
}

fn default_supports_tools() -> bool {
    true
}

