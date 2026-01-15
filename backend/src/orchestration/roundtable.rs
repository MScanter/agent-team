use crate::agents::instance::AgentInstance;
use crate::error::AppError;
use crate::orchestration::state::{Opinion, OrchestrationPhase, OrchestrationState};
use crate::orchestration::tool_events::emit_tool_traces;
use crate::tools::definition::ToolDefinition;
use crate::tools::executor::ToolExecutor;

pub async fn run_roundtable(
    mut agents: Vec<AgentInstance>,
    state: &mut OrchestrationState,
    emit: &mut impl FnMut(&str, serde_json::Value, Option<String>) -> Result<(), AppError>,
    enable_response_phase: bool,
    tool_defs: &[ToolDefinition],
    tool_executor: Option<ToolExecutor>,
) -> Result<Vec<AgentInstance>, AppError> {
    state.phase = OrchestrationPhase::Parallel;

    let recent = state.recent_opinions_json(6);
    let topic = state.topic.clone();
    let summary = state.summary.clone();

    let mut round_one = Vec::new();

    // 顺序执行：逐个 agent 发言
    for agent in agents.iter_mut() {
        let result = agent
            .generate_opinion_with_tools(
                &topic,
                &summary,
                &recent,
                "initial",
                tool_defs,
                tool_executor.as_ref(),
            )
            .await;

        match result {
            Ok((resp, traces)) => {
                let agent_id = agent.id.clone();
                let agent_name = agent.name.clone();
                emit_tool_traces(emit, &traces, &agent_id, &agent_name, state.round)?;
                let input_tokens = resp
                    .metadata
                    .get("input_tokens")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(0) as u32;
                let output_tokens = resp
                    .metadata
                    .get("output_tokens")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(0) as u32;
                let tokens_estimated = resp
                    .metadata
                    .get("tokens_estimated")
                    .and_then(|v| v.as_bool())
                    .unwrap_or(false);
                let opinion = Opinion {
                    agent_id: agent_id.clone(),
                    agent_name: agent_name.clone(),
                    content: resp.content.clone(),
                    round: state.round,
                    phase: "initial".to_string(),
                    wants_to_continue: resp.wants_to_continue,
                    responding_to: resp.responding_to.clone(),
                    input_tokens,
                    output_tokens,
                };
                state.add_opinion(opinion);
                round_one.push(serde_json::json!({"agent_id": agent_id.clone(), "agent_name": agent_name.clone(), "content": resp.content.clone()}));

                emit(
                    "opinion",
                    serde_json::json!({
                        "agent_name": agent_name,
                        "content": resp.content,
                        "wants_to_continue": resp.wants_to_continue,
                        "round": state.round,
                        "phase": "initial",
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "tokens_estimated": tokens_estimated,
                        "metadata": resp.metadata
                    }),
                    Some(agent_id),
                )?;
            }
            Err(e) => {
                let agent_id = agent.id.clone();
                emit(
                    "status",
                    serde_json::json!({
                        "message": format!("{} 回复失败: {}", agent.name, e),
                        "phase": "agent_error",
                        "round": state.round
                    }),
                    Some(agent_id),
                )?;
            }
        }
    }

    // 检查是否所有 Agent 都认为讨论已完成
    let all_done = state
        .agent_wants_continue
        .values()
        .all(|&wants| !wants);

    if !enable_response_phase || all_done {
        if all_done {
            emit(
                "status",
                serde_json::json!({
                    "message": "所有专家认为讨论已充分完成",
                    "phase": "auto_complete",
                    "round": state.round
                }),
                None,
            )?;
        }
        state.phase = OrchestrationPhase::Completed;
        return Ok(agents);
    }

    state.phase = OrchestrationPhase::Responding;

    // 顺序执行：逐个 agent 回应
    for agent in agents.iter_mut() {
        let result = agent
            .generate_opinion_with_tools(
                &topic,
                &summary,
                &round_one,
                "response",
                tool_defs,
                tool_executor.as_ref(),
            )
            .await;

        match result {
            Ok((resp, traces)) => {
                let agent_id = agent.id.clone();
                let agent_name = agent.name.clone();
                emit_tool_traces(emit, &traces, &agent_id, &agent_name, state.round)?;
                let input_tokens = resp
                    .metadata
                    .get("input_tokens")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(0) as u32;
                let output_tokens = resp
                    .metadata
                    .get("output_tokens")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(0) as u32;
                let tokens_estimated = resp
                    .metadata
                    .get("tokens_estimated")
                    .and_then(|v| v.as_bool())
                    .unwrap_or(false);
                let opinion = Opinion {
                    agent_id: agent_id.clone(),
                    agent_name: agent_name.clone(),
                    content: resp.content.clone(),
                    round: state.round,
                    phase: "response".to_string(),
                    wants_to_continue: resp.wants_to_continue,
                    responding_to: resp.responding_to.clone(),
                    input_tokens,
                    output_tokens,
                };
                state.add_opinion(opinion);

                emit(
                    "opinion",
                    serde_json::json!({
                        "agent_name": agent_name,
                        "content": resp.content,
                        "wants_to_continue": resp.wants_to_continue,
                        "round": state.round,
                        "phase": "response",
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "tokens_estimated": tokens_estimated,
                        "metadata": resp.metadata
                    }),
                    Some(agent_id),
                )?;
            }
            Err(e) => {
                let agent_id = agent.id.clone();
                emit(
                    "status",
                    serde_json::json!({
                        "message": format!("{} 回复失败: {}", agent.name, e),
                        "phase": "agent_error",
                        "round": state.round
                    }),
                    Some(agent_id),
                )?;
            }
        }
    }

    state.phase = OrchestrationPhase::Completed;
    Ok(agents)
}
