use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrchestrationEvent {
    pub event_type: String,
    pub data: Value,
    #[serde(default)]
    pub agent_id: Option<String>,
}

