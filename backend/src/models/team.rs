use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoordinationRules {
    #[serde(default = "default_first_speaker")]
    pub first_speaker: String,
    #[serde(default = "default_turn_taking")]
    pub turn_taking: String,
    #[serde(default)]
    pub max_rounds: i32,
    #[serde(default = "default_termination")]
    pub termination: Value,
}

impl Default for CoordinationRules {
    fn default() -> Self {
        Self {
            first_speaker: default_first_speaker(),
            turn_taking: default_turn_taking(),
            max_rounds: 0,
            termination: default_termination(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OutputRules {
    #[serde(default = "default_output_mode")]
    pub mode: String,
    #[serde(default)]
    pub summary_agent_id: Option<String>,
    #[serde(default = "default_output_format")]
    pub format: String,
}

impl Default for OutputRules {
    fn default() -> Self {
        Self {
            mode: default_output_mode(),
            summary_agent_id: None,
            format: default_output_format(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TeamMember {
    pub id: String,
    pub agent_id: String,
    pub role_override: Option<String>,
    pub priority_override: Option<i32>,
    #[serde(default)]
    pub config_override: Value,
    pub position: i32,
    pub is_active: bool,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Team {
    pub id: String,
    pub user_id: String,
    pub name: String,
    pub description: Option<String>,
    pub icon: Option<String>,
    pub collaboration_mode: String,
    #[serde(default)]
    pub mode_config: Value,
    pub coordinator_id: Option<String>,
    #[serde(default)]
    pub coordination_rules: CoordinationRules,
    #[serde(default)]
    pub output_rules: OutputRules,
    pub is_template: bool,
    pub is_public: bool,
    pub usage_count: u32,
    pub rating: f64,
    pub rating_count: u32,
    #[serde(default)]
    pub members: Vec<TeamMember>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TeamListItem {
    pub id: String,
    pub name: String,
    pub description: Option<String>,
    pub icon: Option<String>,
    pub collaboration_mode: String,
    pub member_count: usize,
    pub is_template: bool,
    pub is_public: bool,
    pub usage_count: u32,
    pub rating: f64,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TeamMemberCreate {
    pub agent_id: String,
    #[serde(default)]
    pub role_override: Option<String>,
    #[serde(default)]
    pub priority_override: Option<i32>,
    #[serde(default)]
    pub config_override: Value,
    #[serde(default)]
    pub position: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TeamCreate {
    pub name: String,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub icon: Option<String>,
    #[serde(default = "default_collaboration_mode")]
    pub collaboration_mode: String,
    #[serde(default)]
    pub mode_config: Value,
    #[serde(default)]
    pub coordinator_id: Option<String>,
    #[serde(default)]
    pub coordination_rules: CoordinationRules,
    #[serde(default)]
    pub output_rules: OutputRules,
    #[serde(default)]
    pub members: Vec<TeamMemberCreate>,
    #[serde(default)]
    pub is_template: bool,
    #[serde(default)]
    pub is_public: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct TeamUpdate {
    pub name: Option<String>,
    pub description: Option<String>,
    pub icon: Option<String>,
    pub collaboration_mode: Option<String>,
    pub mode_config: Option<Value>,
    pub coordinator_id: Option<String>,
    pub coordination_rules: Option<CoordinationRules>,
    pub output_rules: Option<OutputRules>,
    pub members: Option<Vec<TeamMemberCreate>>,
    pub is_public: Option<bool>,
}

fn default_first_speaker() -> String {
    "highest_priority".to_string()
}

fn default_turn_taking() -> String {
    "round_robin".to_string()
}

fn default_termination() -> Value {
    serde_json::json!({"type": "consensus", "consensus_threshold": 0.8})
}

fn default_output_mode() -> String {
    "merged".to_string()
}

fn default_output_format() -> String {
    "markdown".to_string()
}

fn default_collaboration_mode() -> String {
    "roundtable".to_string()
}

