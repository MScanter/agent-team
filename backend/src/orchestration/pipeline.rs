use crate::agents::instance::AgentInstance;
use crate::error::AppError;
use crate::orchestration::state::{Opinion, OrchestrationPhase, OrchestrationState};
use crate::orchestration::tool_events::emit_tool_traces;
use crate::tools::definition::ToolDefinition;
use crate::tools::executor::ToolExecutor;

pub async fn run_pipeline(
    agents: Vec<AgentInstance>,
    state: &mut OrchestrationState,
    emit: &mut impl FnMut(&str, serde_json::Value, Option<String>) -> Result<(), AppError>,
    tool_defs: &[ToolDefinition],
    tool_executor: Option<ToolExecutor>,
) -> Result<Vec<AgentInstance>, AppError> {
    state.phase = OrchestrationPhase::Sequential;
    emit(
        "status",
        serde_json::json!({ "message": "Pipeline started", "stages": agents.len(), "phase": "pipeline" }),
        None,
    )?;

    let original_topic = state.topic.clone();
    let mut current_input = original_topic.clone();

    let mut out_agents = Vec::new();
    for (idx, mut agent) in agents.into_iter().enumerate() {
        let stage = (idx + 1) as i32;
        emit(
            "status",
            serde_json::json!({ "message": format!("Processing Stage {stage}: {}", agent.name), "stage": stage, "phase": "pipeline" }),
            Some(agent.id.clone()),
        )?;

        let (resp, traces) = agent
            .generate_opinion_with_tools(&current_input, "", &[], "initial", tool_defs, tool_executor.as_ref())
            .await?;
        emit_tool_traces(emit, &traces, &agent.id, &agent.name, state.round)?;

        let input_tokens = resp.metadata.get("input_tokens").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
        let output_tokens = resp.metadata.get("output_tokens").and_then(|v| v.as_u64()).unwrap_or(0) as u32;

        let opinion = Opinion {
            agent_id: agent.id.clone(),
            agent_name: agent.name.clone(),
            content: resp.content.clone(),
            round: state.round,
            phase: format!("stage_{stage}"),
            confidence: resp.confidence,
            wants_to_continue: true,
            responding_to: None,
            input_tokens,
            output_tokens,
        };
        state.add_opinion(opinion);

        emit(
            "opinion",
            serde_json::json!({
                "agent_name": agent.name,
                "content": resp.content,
                "round": state.round,
                "phase": format!("stage_{stage}"),
                "stage": stage,
                "metadata": resp.metadata
            }),
            Some(agent.id.clone()),
        )?;

        current_input = format!(
            "原始任务：{original_topic}\n\n上一阶段（第{stage}阶段）的输出：\n{}\n\n请基于上述内容，从你的专业角度进行处理和完善。",
            resp.content
        );

        out_agents.push(agent);
    }

    state.phase = OrchestrationPhase::Completed;
    Ok(out_agents)
}
