use std::collections::HashMap;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrchestrationPhase {
    Initializing,
    Parallel,
    Responding,
    Sequential,
    Summarizing,
    Completed,
    Paused,
    Failed,
}

impl Default for OrchestrationPhase {
    fn default() -> Self {
        OrchestrationPhase::Initializing
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Opinion {
    pub agent_id: String,
    pub agent_name: String,
    pub content: String,
    pub round: i32,
    pub phase: String,
    #[serde(default = "default_true")]
    pub wants_to_continue: bool,
    #[serde(default)]
    pub responding_to: Option<String>,
    #[serde(default)]
    pub input_tokens: u32,
    #[serde(default)]
    pub output_tokens: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct OrchestrationState {
    #[serde(default)]
    pub topic: String,
    #[serde(default)]
    pub round: i32,
    #[serde(default)]
    pub phase: OrchestrationPhase,

    #[serde(default)]
    pub agent_ids: Vec<String>,
    #[serde(default)]
    pub active_agent_ids: Vec<String>,

    #[serde(default)]
    pub opinions: Vec<Opinion>,

    #[serde(default)]
    pub summary: String,

    #[serde(default)]
    pub agent_wants_continue: HashMap<String, bool>,

    #[serde(default)]
    pub tokens_used: u32,
    #[serde(default = "default_tokens_budget")]
    pub tokens_budget: u32,
    #[serde(default)]
    pub cost: f64,
    #[serde(default = "default_cost_budget")]
    pub cost_budget: f64,
}

impl OrchestrationState {
    pub fn start_new_round(&mut self) {
        self.round += 1;
    }

    pub fn add_opinion(&mut self, opinion: Opinion) {
        self.tokens_used = self
            .tokens_used
            .saturating_add(opinion.input_tokens.saturating_add(opinion.output_tokens));
        self.agent_wants_continue
            .insert(opinion.agent_id.clone(), opinion.wants_to_continue);
        self.opinions.push(opinion);
    }

    pub fn recent_opinions_json(&self, limit: usize) -> Vec<serde_json::Value> {
        let start = self.opinions.len().saturating_sub(limit);
        self.opinions[start..]
            .iter()
            .map(|op| serde_json::json!({"agent_name": op.agent_name.clone(), "content": op.content.clone(), "agent_id": op.agent_id.clone()}))
            .collect()
    }
}

fn default_true() -> bool {
    true
}

fn default_tokens_budget() -> u32 {
    200_000
}

fn default_cost_budget() -> f64 {
    10.0
}
