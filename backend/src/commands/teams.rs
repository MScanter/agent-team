use chrono::Utc;
use serde_json::Value;
use tauri::State;
use uuid::Uuid;

use crate::error::AppError;
use crate::models::common::{PaginatedResponse, SuccessResponse};
use crate::models::team::{
    Team, TeamCreate, TeamListItem, TeamMember, TeamMemberCreate, TeamUpdate,
};
use crate::state::AppState;

const LOCAL_USER_ID: &str = "local";

#[tauri::command]
pub fn list_teams(
    state: State<AppState>,
    page: Option<usize>,
    page_size: Option<usize>,
    search: Option<String>,
    collaboration_mode: Option<String>,
    is_template: Option<bool>,
) -> Result<PaginatedResponse<TeamListItem>, AppError> {
    let page = page.unwrap_or(1).max(1);
    let page_size = page_size.unwrap_or(20).clamp(1, 100);

    let mut teams = state.store.teams_list()?;
    teams = teams
        .into_iter()
        .filter(|t| t.user_id == LOCAL_USER_ID || t.is_public)
        .collect();

    if let Some(search) = search {
        let needle = search.to_lowercase();
        teams = teams
            .into_iter()
            .filter(|t| {
                t.name.to_lowercase().contains(&needle)
                    || t.description
                        .as_ref()
                        .map(|d| d.to_lowercase().contains(&needle))
                        .unwrap_or(false)
            })
            .collect();
    }

    if let Some(mode) = collaboration_mode {
        teams = teams
            .into_iter()
            .filter(|t| t.collaboration_mode == mode)
            .collect();
    }

    if let Some(is_template) = is_template {
        teams = teams
            .into_iter()
            .filter(|t| t.is_template == is_template)
            .collect();
    }

    teams.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));

    let total = teams.len();
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
        &teams[start..end]
    };

    let items = slice
        .iter()
        .map(|t| TeamListItem {
            id: t.id.clone(),
            name: t.name.clone(),
            description: t.description.clone(),
            icon: t.icon.clone(),
            collaboration_mode: t.collaboration_mode.clone(),
            member_count: t.members.len(),
            is_template: t.is_template,
            is_public: t.is_public,
            usage_count: t.usage_count,
            rating: t.rating,
            created_at: t.created_at,
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
pub fn get_team(state: State<AppState>, id: String) -> Result<Team, AppError> {
    state
        .store
        .teams_get(&id)?
        .ok_or_else(|| AppError::Message(format!("Team {id} not found")))
}

#[tauri::command]
pub fn create_team(state: State<AppState>, team: TeamCreate) -> Result<Team, AppError> {
    let now = Utc::now();
    let members = build_members(team.members, &[], now);

    let record = Team {
        id: Uuid::new_v4().to_string(),
        user_id: LOCAL_USER_ID.to_string(),
        name: team.name,
        description: team.description,
        icon: team.icon,
        collaboration_mode: team.collaboration_mode,
        mode_config: team.mode_config,
        coordinator_id: team.coordinator_id,
        coordination_rules: team.coordination_rules,
        output_rules: team.output_rules,
        is_template: team.is_template,
        is_public: team.is_public,
        usage_count: 0,
        rating: 0.0,
        rating_count: 0,
        members,
        created_at: now,
        updated_at: now,
    };

    state.store.teams_upsert(&record)?;
    Ok(record)
}

#[tauri::command]
pub fn update_team(
    state: State<AppState>,
    id: String,
    update: TeamUpdate,
) -> Result<Team, AppError> {
    let mut existing = state
        .store
        .teams_get(&id)?
        .ok_or_else(|| AppError::Message(format!("Team {id} not found")))?;

    if let Some(v) = update.name {
        existing.name = v;
    }
    if let Some(v) = update.description {
        existing.description = Some(v);
    }
    if let Some(v) = update.icon {
        existing.icon = Some(v);
    }
    if let Some(v) = update.collaboration_mode {
        existing.collaboration_mode = v;
    }
    if let Some(v) = update.mode_config {
        existing.mode_config = v;
    }
    if let Some(v) = update.coordinator_id {
        existing.coordinator_id = Some(v);
    }
    if let Some(v) = update.coordination_rules {
        existing.coordination_rules = v;
    }
    if let Some(v) = update.output_rules {
        existing.output_rules = v;
    }
    if let Some(v) = update.is_public {
        existing.is_public = v;
    }
    if let Some(members) = update.members {
        let now = Utc::now();
        existing.members = build_members(members, &existing.members, now);
    }

    existing.updated_at = Utc::now();
    state.store.teams_upsert(&existing)?;
    Ok(existing)
}

#[tauri::command]
pub fn delete_team(state: State<AppState>, id: String) -> Result<SuccessResponse, AppError> {
    state.store.teams_delete(&id)?;
    Ok(SuccessResponse {
        success: true,
        message: "Team deleted successfully".to_string(),
    })
}

#[tauri::command]
pub fn duplicate_team(
    state: State<AppState>,
    id: String,
    new_name: Option<String>,
) -> Result<Team, AppError> {
    let original = state
        .store
        .teams_get(&id)?
        .ok_or_else(|| AppError::Message(format!("Team {id} not found")))?;

    let now = Utc::now();
    let members = original
        .members
        .iter()
        .map(|m| TeamMember {
            id: Uuid::new_v4().to_string(),
            agent_id: m.agent_id.clone(),
            role_override: m.role_override.clone(),
            priority_override: m.priority_override,
            config_override: m.config_override.clone(),
            position: m.position,
            is_active: m.is_active,
            created_at: now,
            updated_at: now,
        })
        .collect::<Vec<_>>();

    let record = Team {
        id: Uuid::new_v4().to_string(),
        user_id: LOCAL_USER_ID.to_string(),
        name: new_name.unwrap_or_else(|| format!("{} (副本)", original.name)),
        description: original.description.clone(),
        icon: original.icon.clone(),
        collaboration_mode: original.collaboration_mode.clone(),
        mode_config: original.mode_config.clone(),
        coordinator_id: original.coordinator_id.clone(),
        coordination_rules: original.coordination_rules.clone(),
        output_rules: original.output_rules.clone(),
        is_template: false,
        is_public: false,
        usage_count: 0,
        rating: 0.0,
        rating_count: 0,
        members,
        created_at: now,
        updated_at: now,
    };

    state.store.teams_upsert(&record)?;
    Ok(record)
}

#[tauri::command]
pub fn add_team_member(
    state: State<AppState>,
    team_id: String,
    member: TeamMemberCreate,
) -> Result<TeamMember, AppError> {
    let mut team = state
        .store
        .teams_get(&team_id)?
        .ok_or_else(|| AppError::Message(format!("Team {team_id} not found")))?;

    // Ensure agent exists.
    if state.store.agents_get(&member.agent_id)?.is_none() {
        return Err(AppError::Message("Agent not found".to_string()));
    }

    let existing = team.members.iter().find(|m| m.agent_id == member.agent_id);
    if let Some(m) = existing {
        return Ok(m.clone());
    }

    let now = Utc::now();
    let next_pos = team.members.iter().map(|m| m.position).max().unwrap_or(-1) + 1;
    let record = TeamMember {
        id: Uuid::new_v4().to_string(),
        agent_id: member.agent_id,
        role_override: member.role_override,
        priority_override: member.priority_override,
        config_override: member.config_override,
        position: member.position.unwrap_or(next_pos),
        is_active: true,
        created_at: now,
        updated_at: now,
    };

    team.members.push(record.clone());
    team.members.sort_by_key(|m| m.position);
    team.updated_at = now;
    state.store.teams_upsert(&team)?;
    Ok(record)
}

#[tauri::command]
pub fn remove_team_member(
    state: State<AppState>,
    team_id: String,
    agent_id: String,
) -> Result<SuccessResponse, AppError> {
    let mut team = state
        .store
        .teams_get(&team_id)?
        .ok_or_else(|| AppError::Message(format!("Team {team_id} not found")))?;

    let before = team.members.len();
    team.members.retain(|m| m.agent_id != agent_id);
    if team.members.len() == before {
        return Err(AppError::Message("Member not found".to_string()));
    }

    team.updated_at = Utc::now();
    state.store.teams_upsert(&team)?;
    Ok(SuccessResponse {
        success: true,
        message: "Member removed successfully".to_string(),
    })
}

#[tauri::command]
pub fn reorder_team_members(
    state: State<AppState>,
    team_id: String,
    agent_ids: Vec<String>,
) -> Result<SuccessResponse, AppError> {
    let mut team = state
        .store
        .teams_get(&team_id)?
        .ok_or_else(|| AppError::Message(format!("Team {team_id} not found")))?;

    let mut seen = std::collections::HashSet::new();
    for id in &agent_ids {
        if !seen.insert(id.clone()) {
            return Err(AppError::Message(
                "agent_ids contains duplicates".to_string(),
            ));
        }
    }

    let mut by_agent: std::collections::HashMap<String, TeamMember> = team
        .members
        .iter()
        .cloned()
        .map(|m| (m.agent_id.clone(), m))
        .collect();

    for (idx, agent_id) in agent_ids.iter().enumerate() {
        let Some(mut member) = by_agent.get(agent_id).cloned() else {
            return Err(AppError::Message(format!(
                "Unknown agent_id in team: {agent_id}"
            )));
        };
        member.position = idx as i32;
        by_agent.insert(agent_id.clone(), member);
    }

    let mut remaining = team
        .members
        .iter()
        .filter(|m| !agent_ids.contains(&m.agent_id))
        .cloned()
        .collect::<Vec<_>>();
    remaining.sort_by_key(|m| m.position);
    let start = agent_ids.len() as i32;
    for (offset, mut m) in remaining.into_iter().enumerate() {
        m.position = start + offset as i32;
        by_agent.insert(m.agent_id.clone(), m);
    }

    let mut members = by_agent.into_values().collect::<Vec<_>>();
    members.sort_by_key(|m| m.position);
    team.members = members;
    team.updated_at = Utc::now();
    state.store.teams_upsert(&team)?;

    Ok(SuccessResponse {
        success: true,
        message: "Members reordered successfully".to_string(),
    })
}

fn build_members(
    members: Vec<TeamMemberCreate>,
    existing: &[TeamMember],
    now: chrono::DateTime<Utc>,
) -> Vec<TeamMember> {
    let existing_by_agent: std::collections::HashMap<String, &TeamMember> =
        existing.iter().map(|m| (m.agent_id.clone(), m)).collect();

    let mut out = Vec::new();
    for (idx, m) in members.into_iter().enumerate() {
        let pos = m.position.unwrap_or(idx as i32);
        if let Some(prev) = existing_by_agent.get(&m.agent_id) {
            out.push(TeamMember {
                id: prev.id.clone(),
                agent_id: prev.agent_id.clone(),
                role_override: m.role_override.or_else(|| prev.role_override.clone()),
                priority_override: m.priority_override.or(prev.priority_override),
                config_override: merge_json(&prev.config_override, &m.config_override),
                position: pos,
                is_active: true,
                created_at: prev.created_at,
                updated_at: now,
            });
        } else {
            out.push(TeamMember {
                id: Uuid::new_v4().to_string(),
                agent_id: m.agent_id,
                role_override: m.role_override,
                priority_override: m.priority_override,
                config_override: m.config_override,
                position: pos,
                is_active: true,
                created_at: now,
                updated_at: now,
            });
        }
    }
    out.sort_by_key(|m| m.position);
    out
}

fn merge_json(a: &Value, b: &Value) -> Value {
    if !a.is_object() || !b.is_object() {
        return b.clone();
    }
    let mut out = a.clone();
    if let (Some(ao), Some(bo)) = (out.as_object_mut(), b.as_object()) {
        for (k, v) in bo {
            ao.insert(k.clone(), v.clone());
        }
    }
    out
}
