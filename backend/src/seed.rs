use chrono::Utc;
use serde::Deserialize;
use std::collections::HashSet;

use crate::error::AppError;
use crate::models::agent::{Agent, InteractionRules};
use crate::models::team::{CoordinationRules, OutputRules, Team, TeamMember};
use crate::store::sqlite::SqliteStore;

const DEFAULTS_JSON: &str = include_str!("../assets/defaults.json");
const LOCAL_USER_ID: &str = "local";

#[derive(Debug, Deserialize)]
struct SeedDefaults {
    agents: Vec<SeedAgent>,
    teams: Vec<SeedTeam>,
}

#[derive(Debug, Deserialize)]
struct SeedAgent {
    id: String,
    name: String,
    #[serde(default)]
    avatar: Option<String>,
    #[serde(default)]
    description: Option<String>,
    collaboration_style: String,
    speaking_priority: i32,
    system_prompt: String,
    #[serde(default)]
    temperature: Option<f64>,
    #[serde(default)]
    max_tokens: Option<u32>,
    #[serde(default)]
    max_tool_iterations: Option<u32>,
}

#[derive(Debug, Deserialize)]
struct SeedTeam {
    id: String,
    name: String,
    #[serde(default)]
    description: Option<String>,
    #[serde(default)]
    icon: Option<String>,
    collaboration_mode: String,
    members: Vec<String>,
}

pub fn seed_if_empty(store: &SqliteStore) -> Result<bool, AppError> {
    if !store.is_empty()? {
        return Ok(false);
    }

    let parsed: SeedDefaults = serde_json::from_str(DEFAULTS_JSON)
        .map_err(|e| AppError::Message(format!("Invalid defaults.json: {e}")))?;

    let agent_ids: HashSet<String> = parsed.agents.iter().map(|a| a.id.clone()).collect();
    if agent_ids.len() != parsed.agents.len() {
        return Err(AppError::Message(
            "defaults.json contains duplicate agent ids".to_string(),
        ));
    }
    let team_ids: HashSet<String> = parsed.teams.iter().map(|t| t.id.clone()).collect();
    if team_ids.len() != parsed.teams.len() {
        return Err(AppError::Message(
            "defaults.json contains duplicate team ids".to_string(),
        ));
    }
    for t in parsed.teams.iter() {
        for member_id in t.members.iter() {
            if !agent_ids.contains(member_id) {
                return Err(AppError::Message(format!(
                    "defaults.json team '{}' references unknown agent id '{}'",
                    t.id, member_id
                )));
            }
        }
    }

    let now = Utc::now();

    for a in parsed.agents {
        let record = Agent {
            id: a.id,
            user_id: LOCAL_USER_ID.to_string(),
            name: a.name,
            avatar: a.avatar,
            description: a.description,
            tags: Vec::new(),
            system_prompt: a.system_prompt,
            model_id: None,
            temperature: a.temperature.unwrap_or(0.7),
            max_tokens: a.max_tokens.unwrap_or(2000),
            max_tool_iterations: a.max_tool_iterations.or(Some(10)),
            tools: Vec::new(),
            knowledge_base_id: None,
            memory_enabled: false,
            domain: None,
            collaboration_style: a.collaboration_style,
            speaking_priority: a.speaking_priority,
            interaction_rules: InteractionRules::default(),
            version: 1,
            is_template: true,
            is_public: false,
            parent_id: None,
            usage_count: 0,
            rating: 0.0,
            rating_count: 0,
            created_at: now,
            updated_at: now,
        };
        store.agents_upsert(&record)?;
    }

    for t in parsed.teams {
        let members = t
            .members
            .iter()
            .enumerate()
            .map(|(idx, agent_id)| TeamMember {
                id: format!("{}-member-{}", t.id, idx + 1),
                agent_id: agent_id.clone(),
                role_override: None,
                priority_override: None,
                config_override: serde_json::json!({}),
                position: (idx + 1) as i32,
                is_active: true,
                created_at: now,
                updated_at: now,
            })
            .collect();

        let record = Team {
            id: t.id,
            user_id: LOCAL_USER_ID.to_string(),
            name: t.name,
            description: t.description,
            icon: t.icon,
            collaboration_mode: t.collaboration_mode,
            mode_config: serde_json::json!({}),
            coordinator_id: None,
            coordination_rules: CoordinationRules::default(),
            output_rules: OutputRules::default(),
            is_template: true,
            is_public: false,
            usage_count: 0,
            rating: 0.0,
            rating_count: 0,
            members,
            created_at: now,
            updated_at: now,
        };
        store.teams_upsert(&record)?;
    }

    Ok(true)
}
