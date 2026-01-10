use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InteractionRules {
    #[serde(default = "default_true")]
    pub can_challenge: bool,
    #[serde(default = "default_true")]
    pub can_be_challenged: bool,
    #[serde(default)]
    pub defer_to: Vec<String>,
}

impl Default for InteractionRules {
    fn default() -> Self {
        Self {
            can_challenge: true,
            can_be_challenged: true,
            defer_to: Vec::new(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Agent {
    pub id: String,
    pub user_id: String,
    pub name: String,
    pub avatar: Option<String>,
    pub description: Option<String>,
    #[serde(default)]
    pub tags: Vec<String>,
    pub system_prompt: String,
    pub model_id: Option<String>,
    pub temperature: f64,
    pub max_tokens: u32,
    #[serde(default)]
    pub tools: Vec<String>,
    pub knowledge_base_id: Option<String>,
    pub memory_enabled: bool,
    pub domain: Option<String>,
    pub collaboration_style: String,
    pub speaking_priority: i32,
    #[serde(default)]
    pub interaction_rules: InteractionRules,
    pub version: u32,
    pub is_template: bool,
    pub is_public: bool,
    pub parent_id: Option<String>,
    pub usage_count: u32,
    pub rating: f64,
    pub rating_count: u32,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentListItem {
    pub id: String,
    pub name: String,
    pub avatar: Option<String>,
    pub description: Option<String>,
    #[serde(default)]
    pub tags: Vec<String>,
    pub domain: Option<String>,
    pub collaboration_style: String,
    pub is_template: bool,
    pub is_public: bool,
    pub usage_count: u32,
    pub rating: f64,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentCreate {
    pub name: String,
    #[serde(default)]
    pub avatar: Option<String>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub tags: Vec<String>,
    pub system_prompt: String,
    #[serde(default)]
    pub model_id: Option<String>,
    #[serde(default = "default_temperature")]
    pub temperature: f64,
    #[serde(default = "default_max_tokens")]
    pub max_tokens: u32,
    #[serde(default)]
    pub tools: Vec<String>,
    #[serde(default)]
    pub knowledge_base_id: Option<String>,
    #[serde(default)]
    pub memory_enabled: bool,
    #[serde(default)]
    pub domain: Option<String>,
    #[serde(default = "default_collaboration_style")]
    pub collaboration_style: String,
    #[serde(default = "default_speaking_priority")]
    pub speaking_priority: i32,
    #[serde(default)]
    pub interaction_rules: InteractionRules,
    #[serde(default)]
    pub is_template: bool,
    #[serde(default)]
    pub is_public: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AgentUpdate {
    pub name: Option<String>,
    pub avatar: Option<String>,
    pub description: Option<String>,
    pub tags: Option<Vec<String>>,
    pub system_prompt: Option<String>,
    pub model_id: Option<String>,
    pub temperature: Option<f64>,
    pub max_tokens: Option<u32>,
    pub tools: Option<Vec<String>>,
    pub knowledge_base_id: Option<String>,
    pub memory_enabled: Option<bool>,
    pub domain: Option<String>,
    pub collaboration_style: Option<String>,
    pub speaking_priority: Option<i32>,
    pub interaction_rules: Option<InteractionRules>,
    pub is_public: Option<bool>,
}

fn default_true() -> bool {
    true
}

fn default_temperature() -> f64 {
    0.7
}

fn default_max_tokens() -> u32 {
    2048
}

fn default_speaking_priority() -> i32 {
    5
}

fn default_collaboration_style() -> String {
    "supportive".to_string()
}

