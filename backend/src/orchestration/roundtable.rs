use futures::{stream::FuturesUnordered, StreamExt};

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
    emit(
        "status",
        serde_json::json!({
            "message": format!("第 {} 轮：并行发言", state.round),
            "round": state.round,
            "phase": "parallel"
        }),
        None,
    )?;

    let recent = state.recent_opinions_json(6);
    let topic = state.topic.clone();
    let summary = state.summary.clone();

    let mut tasks = FuturesUnordered::new();
    for agent in agents.into_iter() {
        let topic = topic.clone();
        let summary = summary.clone();
        let recent = recent.clone();
        let tool_executor = tool_executor.clone();
        let tool_defs = tool_defs;
        tasks.push(async move {
            let mut agent = agent;
            let res = agent
                .generate_opinion_with_tools(&topic, &summary, &recent, "initial", tool_defs, tool_executor.as_ref())
                .await;
            (agent, res)
        });
    }

    let mut completed_agents = Vec::new();
    let mut round_one = Vec::new();
    while let Some((agent, result)) = tasks.next().await {
        match result {
            Ok((resp, traces)) => {
                let agent_id = agent.id.clone();
                let agent_name = agent.name.clone();
                emit_tool_traces(emit, &traces, &agent_id, &agent_name, state.round)?;
                let input_tokens = resp.metadata.get("input_tokens").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
                let output_tokens = resp.metadata.get("output_tokens").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
                let opinion = Opinion {
                    agent_id: agent_id.clone(),
                    agent_name: agent_name.clone(),
                    content: resp.content.clone(),
                    round: state.round,
                    phase: "initial".to_string(),
                    confidence: resp.confidence,
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
                        "confidence": resp.confidence,
                        "wants_to_continue": resp.wants_to_continue,
                        "round": state.round,
                        "phase": "initial",
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
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
        completed_agents.push(agent);
    }

    agents = completed_agents;
    if !enable_response_phase {
        state.phase = OrchestrationPhase::Completed;
        return Ok(agents);
    }

    state.phase = OrchestrationPhase::Responding;
    emit(
        "status",
        serde_json::json!({
            "message": format!("第 {} 轮：互相回应", state.round),
            "round": state.round,
            "phase": "response"
        }),
        None,
    )?;

    let topic = state.topic.clone();
    let summary = state.summary.clone();
    let mut tasks = FuturesUnordered::new();
    for agent in agents.into_iter() {
        let topic = topic.clone();
        let summary = summary.clone();
        let context = round_one.clone();
        let tool_executor = tool_executor.clone();
        let tool_defs = tool_defs;
        tasks.push(async move {
            let mut agent = agent;
            let res = agent
                .generate_opinion_with_tools(&topic, &summary, &context, "response", tool_defs, tool_executor.as_ref())
                .await;
            (agent, res)
        });
    }

    let mut completed_agents = Vec::new();
    while let Some((agent, result)) = tasks.next().await {
        match result {
            Ok((resp, traces)) => {
                let agent_id = agent.id.clone();
                let agent_name = agent.name.clone();
                emit_tool_traces(emit, &traces, &agent_id, &agent_name, state.round)?;
                let input_tokens = resp.metadata.get("input_tokens").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
                let output_tokens = resp.metadata.get("output_tokens").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
                let opinion = Opinion {
                    agent_id: agent_id.clone(),
                    agent_name: agent_name.clone(),
                    content: resp.content.clone(),
                    round: state.round,
                    phase: "response".to_string(),
                    confidence: resp.confidence,
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
                        "confidence": resp.confidence,
                        "wants_to_continue": resp.wants_to_continue,
                        "round": state.round,
                        "phase": "response",
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
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
        completed_agents.push(agent);
    }

    state.phase = OrchestrationPhase::Completed;
    Ok(completed_agents)
}
