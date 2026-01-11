use chrono::Utc;
use tauri::State;
use uuid::Uuid;

use crate::error::AppError;
use crate::models::agent::{Agent, AgentCreate, AgentListItem, AgentUpdate};
use crate::models::common::{PaginatedResponse, SuccessResponse};
use crate::state::AppState;

const LOCAL_USER_ID: &str = "local";

#[tauri::command]
pub fn list_agents(
    state: State<AppState>,
    page: Option<usize>,
    page_size: Option<usize>,
    search: Option<String>,
    tags: Option<String>,
    is_template: Option<bool>,
    collaboration_style: Option<String>,
) -> Result<PaginatedResponse<AgentListItem>, AppError> {
    let page = page.unwrap_or(1).max(1);
    let page_size = page_size.unwrap_or(20).clamp(1, 100);

    let mut agents = state.store.agents_list()?;
    agents = agents
        .into_iter()
        .filter(|a| a.user_id == LOCAL_USER_ID || a.is_public)
        .collect();

    if let Some(search) = search {
        let needle = search.to_lowercase();
        agents = agents
            .into_iter()
            .filter(|a| {
                a.name.to_lowercase().contains(&needle)
                    || a.description
                        .as_ref()
                        .map(|d| d.to_lowercase().contains(&needle))
                        .unwrap_or(false)
            })
            .collect();
    }

    if let Some(tags) = tags {
        let tag_set: std::collections::HashSet<String> = tags
            .split(',')
            .map(|s| s.trim())
            .filter(|s| !s.is_empty())
            .map(|s| s.to_string())
            .collect();
        if !tag_set.is_empty() {
            agents = agents
                .into_iter()
                .filter(|a| tag_set.iter().any(|t| a.tags.contains(t)))
                .collect();
        }
    }

    if let Some(is_template) = is_template {
        agents = agents
            .into_iter()
            .filter(|a| a.is_template == is_template)
            .collect();
    }

    if let Some(style) = collaboration_style {
        agents = agents
            .into_iter()
            .filter(|a| a.collaboration_style == style)
            .collect();
    }

    agents.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));

    let total = agents.len();
    let total_pages = if total == 0 {
        0
    } else {
        (total + page_size - 1) / page_size
    };

    let start = (page - 1) * page_size;
    let end = (start + page_size).min(total);
    let slice = if start >= total {
        &[]
    } else {
        &agents[start..end]
    };

    let items = slice
        .iter()
        .map(|a| AgentListItem {
            id: a.id.clone(),
            name: a.name.clone(),
            avatar: a.avatar.clone(),
            description: a.description.clone(),
            tags: a.tags.clone(),
            domain: a.domain.clone(),
            collaboration_style: a.collaboration_style.clone(),
            is_template: a.is_template,
            is_public: a.is_public,
            usage_count: a.usage_count,
            rating: a.rating,
            created_at: a.created_at,
        })
        .collect();

    Ok(PaginatedResponse {
        items,
        total,
        page,
        page_size,
        total_pages,
    })
}

#[tauri::command]
pub fn get_agent(state: State<AppState>, id: String) -> Result<Agent, AppError> {
    state
        .store
        .agents_get(&id)?
        .ok_or_else(|| AppError::Message(format!("Agent {id} not found")))
}

#[tauri::command]
pub fn create_agent(state: State<AppState>, agent: AgentCreate) -> Result<Agent, AppError> {
    let now = Utc::now();
    let record = Agent {
        id: Uuid::new_v4().to_string(),
        user_id: LOCAL_USER_ID.to_string(),
        name: agent.name,
        avatar: agent.avatar,
        description: agent.description,
        tags: agent.tags,
        system_prompt: agent.system_prompt,
        model_id: agent.model_id,
        temperature: agent.temperature,
        max_tokens: agent.max_tokens,
        max_tool_iterations: agent.max_tool_iterations,
        tools: agent.tools,
        knowledge_base_id: agent.knowledge_base_id,
        memory_enabled: agent.memory_enabled,
        domain: agent.domain,
        collaboration_style: agent.collaboration_style,
        speaking_priority: agent.speaking_priority,
        interaction_rules: agent.interaction_rules,
        version: 1,
        is_template: agent.is_template,
        is_public: agent.is_public,
        parent_id: None,
        usage_count: 0,
        rating: 0.0,
        rating_count: 0,
        created_at: now,
        updated_at: now,
    };
    state.store.agents_upsert(&record)?;
    Ok(record)
}

#[tauri::command]
pub fn update_agent(
    state: State<AppState>,
    id: String,
    update: AgentUpdate,
) -> Result<Agent, AppError> {
    let mut existing = state
        .store
        .agents_get(&id)?
        .ok_or_else(|| AppError::Message(format!("Agent {id} not found")))?;

    if let Some(v) = update.name {
        existing.name = v;
    }
    if let Some(v) = update.avatar {
        existing.avatar = Some(v);
    }
    if let Some(v) = update.description {
        existing.description = Some(v);
    }
    if let Some(v) = update.tags {
        existing.tags = v;
    }
    if let Some(v) = update.system_prompt {
        existing.system_prompt = v;
    }
    if let Some(v) = update.model_id {
        existing.model_id = Some(v);
    }
    if let Some(v) = update.temperature {
        existing.temperature = v;
    }
    if let Some(v) = update.max_tokens {
        existing.max_tokens = v;
    }
    if let Some(v) = update.max_tool_iterations {
        existing.max_tool_iterations = Some(v);
    }
    if let Some(v) = update.tools {
        existing.tools = v;
    }
    if let Some(v) = update.knowledge_base_id {
        existing.knowledge_base_id = Some(v);
    }
    if let Some(v) = update.memory_enabled {
        existing.memory_enabled = v;
    }
    if let Some(v) = update.domain {
        existing.domain = Some(v);
    }
    if let Some(v) = update.collaboration_style {
        existing.collaboration_style = v;
    }
    if let Some(v) = update.speaking_priority {
        existing.speaking_priority = v;
    }
    if let Some(v) = update.interaction_rules {
        existing.interaction_rules = v;
    }
    if let Some(v) = update.is_public {
        existing.is_public = v;
    }

    existing.version = existing.version.saturating_add(1);
    existing.updated_at = Utc::now();
    state.store.agents_upsert(&existing)?;
    Ok(existing)
}

#[tauri::command]
pub fn delete_agent(state: State<AppState>, id: String) -> Result<SuccessResponse, AppError> {
    state.store.agents_delete(&id)?;
    Ok(SuccessResponse {
        success: true,
        message: "Agent deleted successfully".to_string(),
    })
}

#[tauri::command]
pub fn duplicate_agent(
    state: State<AppState>,
    id: String,
    new_name: Option<String>,
) -> Result<Agent, AppError> {
    let original = state
        .store
        .agents_get(&id)?
        .ok_or_else(|| AppError::Message(format!("Agent {id} not found")))?;

    let now = Utc::now();
    let record = Agent {
        id: Uuid::new_v4().to_string(),
        user_id: LOCAL_USER_ID.to_string(),
        name: new_name.unwrap_or_else(|| format!("{} (副本)", original.name)),
        avatar: original.avatar.clone(),
        description: original.description.clone(),
        tags: original.tags.clone(),
        system_prompt: original.system_prompt.clone(),
        model_id: original.model_id.clone(),
        temperature: original.temperature,
        max_tokens: original.max_tokens,
        max_tool_iterations: original.max_tool_iterations,
        tools: original.tools.clone(),
        knowledge_base_id: original.knowledge_base_id.clone(),
        memory_enabled: original.memory_enabled,
        domain: original.domain.clone(),
        collaboration_style: original.collaboration_style.clone(),
        speaking_priority: original.speaking_priority,
        interaction_rules: original.interaction_rules.clone(),
        version: 1,
        is_template: false,
        is_public: false,
        parent_id: Some(original.id),
        usage_count: 0,
        rating: 0.0,
        rating_count: 0,
        created_at: now,
        updated_at: now,
    };

    state.store.agents_upsert(&record)?;
    Ok(record)
}
