use std::collections::HashMap;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
#[derive(Default)]
pub enum OrchestrationPhase {
    #[default]
    Initializing,
    Parallel,
    Responding,
    Sequential,
    Summarizing,
    Completed,
    Paused,
    Failed,
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

#[cfg(test)]
mod tests {
    use super::*;

    fn opinion(id: &str, name: &str, input: u32, output: u32, wants: bool) -> Opinion {
        Opinion {
            agent_id: id.to_string(),
            agent_name: name.to_string(),
            content: format!("{name} speaks"),
            round: 1,
            phase: "initial".to_string(),
            wants_to_continue: wants,
            responding_to: None,
            input_tokens: input,
            output_tokens: output,
        }
    }

    #[test]
    fn add_opinion_accumulates_tokens_and_tracks_continuation() {
        let mut state = OrchestrationState::default();
        state.add_opinion(opinion("a1", "Alice", 100, 50, true));
        state.add_opinion(opinion("a2", "Bob", 30, 20, false));

        assert_eq!(state.tokens_used, 200);
        assert_eq!(state.opinions.len(), 2);
        assert_eq!(state.agent_wants_continue.get("a1"), Some(&true));
        assert_eq!(state.agent_wants_continue.get("a2"), Some(&false));
    }

    #[test]
    fn add_opinion_latest_continuation_wins_for_same_agent() {
        let mut state = OrchestrationState::default();
        state.add_opinion(opinion("a1", "Alice", 0, 0, true));
        state.add_opinion(opinion("a1", "Alice", 0, 0, false));

        assert_eq!(state.agent_wants_continue.get("a1"), Some(&false));
        assert_eq!(state.opinions.len(), 2);
    }

    #[test]
    fn add_opinion_saturates_token_counter() {
        let mut state = OrchestrationState::default();
        state.add_opinion(opinion("a1", "Alice", u32::MAX, 10, true));
        assert_eq!(state.tokens_used, u32::MAX);
    }

    #[test]
    fn recent_opinions_json_returns_trailing_window() {
        let mut state = OrchestrationState::default();
        for i in 0..5 {
            state.add_opinion(opinion(&format!("a{i}"), &format!("Agent{i}"), 0, 0, true));
        }
        let recent = state.recent_opinions_json(2);
        assert_eq!(recent.len(), 2);
        assert_eq!(recent[0]["agent_name"], "Agent3");
        assert_eq!(recent[1]["agent_name"], "Agent4");
    }

    #[test]
    fn recent_opinions_json_clamps_to_available() {
        let mut state = OrchestrationState::default();
        state.add_opinion(opinion("a0", "Solo", 0, 0, true));
        assert_eq!(state.recent_opinions_json(10).len(), 1);
    }

    #[test]
    fn start_new_round_increments_round() {
        let mut state = OrchestrationState::default();
        assert_eq!(state.round, 0);
        state.start_new_round();
        state.start_new_round();
        assert_eq!(state.round, 2);
    }
}
