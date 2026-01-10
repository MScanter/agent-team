use crate::agents::instance::AgentInstance;
use crate::error::AppError;
use crate::orchestration::state::{Opinion, OrchestrationPhase, OrchestrationState};

pub async fn run_debate(
    agents: Vec<AgentInstance>,
    state: &mut OrchestrationState,
    emit: &mut impl FnMut(&str, serde_json::Value, Option<String>) -> Result<(), AppError>,
    max_rounds: i32,
) -> Result<Vec<AgentInstance>, AppError> {
    state.phase = OrchestrationPhase::Initializing;

    let mut agents = agents;
    if agents.is_empty() {
        return Ok(agents);
    }

    // Auto-assign: last agent as judge, split remaining into pro/con.
    let judge = agents.pop().unwrap();
    let mid = agents.len() / 2;
    let mut pro = agents[..mid].to_vec();
    let mut con = agents[mid..].to_vec();

    emit(
        "status",
        serde_json::json!({
            "message": "Debate started",
            "pro_team": pro.iter().map(|a| a.name.clone()).collect::<Vec<_>>(),
            "con_team": con.iter().map(|a| a.name.clone()).collect::<Vec<_>>(),
            "judge": judge.name.clone()
        }),
        None,
    )?;

    state.round = 1;
    state.phase = OrchestrationPhase::Sequential;

    // Opening: pro then con
    let pro_prompt = format!("论题：{}\n\n你是正方，请给出开场陈述。", state.topic);
    let mut pro_args = Vec::new();
    for agent in pro.iter_mut() {
        let resp = agent.generate_opinion(&pro_prompt, "", &[], "initial").await?;

        let input_tokens = resp.metadata.get("input_tokens").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
        let output_tokens = resp.metadata.get("output_tokens").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
        state.add_opinion(Opinion {
            agent_id: agent.id.clone(),
            agent_name: agent.name.clone(),
            content: resp.content.clone(),
            round: state.round,
            phase: "pro_opening".to_string(),
            confidence: resp.confidence,
            wants_to_continue: true,
            responding_to: None,
            input_tokens,
            output_tokens,
        });
        pro_args.push(serde_json::json!({"agent_name": agent.name.clone(), "content": resp.content.clone()}));
        emit(
            "opinion",
            serde_json::json!({
                "agent_name": agent.name.clone(),
                "content": resp.content.clone(),
                "round": state.round,
                "phase": "pro_opening"
            }),
            Some(agent.id.clone()),
        )?;
    }

    let con_prompt = format!("论题：{}\n\n你是反方，请回应正方并给出开场陈述。", state.topic);
    for agent in con.iter_mut() {
        let resp = agent.generate_opinion(&con_prompt, "", &pro_args, "response").await?;
        let input_tokens = resp.metadata.get("input_tokens").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
        let output_tokens = resp.metadata.get("output_tokens").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
        state.add_opinion(Opinion {
            agent_id: agent.id.clone(),
            agent_name: agent.name.clone(),
            content: resp.content.clone(),
            round: state.round,
            phase: "con_opening".to_string(),
            confidence: resp.confidence,
            wants_to_continue: true,
            responding_to: None,
            input_tokens,
            output_tokens,
        });
        emit(
            "opinion",
            serde_json::json!({
                "agent_name": agent.name.clone(),
                "content": resp.content.clone(),
                "round": state.round,
                "phase": "con_opening"
            }),
            Some(agent.id.clone()),
        )?;
    }

    // Rebuttals
    for round_num in 1..=max_rounds {
        state.round += 1;
        emit(
            "status",
            serde_json::json!({ "message": format!("Rebuttal round {}", round_num), "round": state.round, "phase": "rebuttal" }),
            None,
        )?;
        let last = state
            .opinions
            .iter()
            .rev()
            .take(pro.len() + con.len())
            .map(|op| serde_json::json!({"agent_name": op.agent_name.clone(), "content": op.content.clone(), "phase": op.phase.clone()}))
            .collect::<Vec<_>>();

        for agent in pro.iter_mut() {
            let resp = agent.generate_opinion(&state.topic, "", &last, "response").await?;
            state.add_opinion(Opinion {
                agent_id: agent.id.clone(),
                agent_name: agent.name.clone(),
                content: resp.content.clone(),
                round: state.round,
                phase: "pro_rebuttal".to_string(),
                confidence: resp.confidence,
                wants_to_continue: true,
                responding_to: None,
                input_tokens: resp.metadata.get("input_tokens").and_then(|v| v.as_u64()).unwrap_or(0) as u32,
                output_tokens: resp.metadata.get("output_tokens").and_then(|v| v.as_u64()).unwrap_or(0) as u32,
            });
            emit(
                "opinion",
                serde_json::json!({
                    "agent_name": agent.name.clone(),
                    "content": resp.content.clone(),
                    "round": state.round,
                    "phase": "pro_rebuttal"
                }),
                Some(agent.id.clone()),
            )?;
        }

        for agent in con.iter_mut() {
            let resp = agent.generate_opinion(&state.topic, "", &last, "response").await?;
            state.add_opinion(Opinion {
                agent_id: agent.id.clone(),
                agent_name: agent.name.clone(),
                content: resp.content.clone(),
                round: state.round,
                phase: "con_rebuttal".to_string(),
                confidence: resp.confidence,
                wants_to_continue: true,
                responding_to: None,
                input_tokens: resp.metadata.get("input_tokens").and_then(|v| v.as_u64()).unwrap_or(0) as u32,
                output_tokens: resp.metadata.get("output_tokens").and_then(|v| v.as_u64()).unwrap_or(0) as u32,
            });
            emit(
                "opinion",
                serde_json::json!({
                    "agent_name": agent.name.clone(),
                    "content": resp.content.clone(),
                    "round": state.round,
                    "phase": "con_rebuttal"
                }),
                Some(agent.id.clone()),
            )?;
        }
    }

    // Judge verdict
    state.phase = OrchestrationPhase::Summarizing;
    let pro_text = state
        .opinions
        .iter()
        .filter(|o| o.phase.starts_with("pro_"))
        .map(|o| format!("- {}: {}", o.agent_name, o.content))
        .collect::<Vec<_>>()
        .join("\n");
    let con_text = state
        .opinions
        .iter()
        .filter(|o| o.phase.starts_with("con_"))
        .map(|o| format!("- {}: {}", o.agent_name, o.content))
        .collect::<Vec<_>>()
        .join("\n");
    let verdict_prompt = format!(
        "作为裁判，请评判以下辩论：\n\n论题：{}\n\n正方观点：\n{}\n\n反方观点：\n{}\n\n请给出裁决：\n1. 双方论点总结\n2. 优势与不足\n3. 最终判断",
        state.topic, pro_text, con_text
    );

    let mut judge = judge;
    let verdict = judge.generate_opinion(&verdict_prompt, "", &[], "initial").await?;

    state.summary = verdict.content.clone();
    state.add_opinion(Opinion {
        agent_id: judge.id.clone(),
        agent_name: judge.name.clone(),
        content: verdict.content.clone(),
        round: state.round,
        phase: "judge_verdict".to_string(),
        confidence: verdict.confidence,
        wants_to_continue: false,
        responding_to: None,
        input_tokens: verdict.metadata.get("input_tokens").and_then(|v| v.as_u64()).unwrap_or(0) as u32,
        output_tokens: verdict.metadata.get("output_tokens").and_then(|v| v.as_u64()).unwrap_or(0) as u32,
    });
    emit(
        "opinion",
        serde_json::json!({
            "agent_name": judge.name.clone(),
            "content": verdict.content.clone(),
            "round": state.round,
            "phase": "judge_verdict"
        }),
        Some(judge.id.clone()),
    )?;

    state.phase = OrchestrationPhase::Completed;

    let mut all = Vec::new();
    all.extend(pro.into_iter());
    all.extend(con.into_iter());
    all.push(judge);
    Ok(all)
}
