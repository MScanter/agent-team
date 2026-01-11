use crate::error::AppError;
use crate::tools::definition::ToolTrace;

fn truncate(s: &str, max: usize) -> String {
    if s.len() <= max {
        return s.to_string();
    }
    let mut out = s[..max].to_string();
    out.push_str("…");
    out
}

pub fn emit_tool_traces(
    emit: &mut impl FnMut(&str, serde_json::Value, Option<String>) -> Result<(), AppError>,
    traces: &[ToolTrace],
    agent_id: &str,
    agent_name: &str,
    round: i32,
) -> Result<(), AppError> {
    for t in traces {
        let args_preview = t.call.arguments.to_string();
        emit(
            "tool_call",
            serde_json::json!({
                "phase": "tool_call",
                "round": round,
                "agent_name": agent_name,
                "tool_name": t.call.name,
                "tool_call_id": t.call.id,
                "arguments": t.call.arguments,
                "content": format!("CALL {} {}", t.call.name, truncate(&args_preview, 200))
            }),
            Some(agent_id.to_string()),
        )?;

        let ok = t.result.ok;
        let output_preview = t.result.output.to_string();
        let status = if ok { "OK" } else { "ERROR" };
        emit(
            "tool_result",
            serde_json::json!({
                "phase": "tool_result",
                "round": round,
                "agent_name": agent_name,
                "tool_name": t.result.name,
                "tool_call_id": t.result.tool_call_id,
                "ok": ok,
                "output": t.result.output,
                "error": t.result.error,
                "duration_ms": t.result.duration_ms,
                "content": format!("{status} {} {}", t.result.name, truncate(&output_preview, 200))
            }),
            Some(agent_id.to_string()),
        )?;
    }
    Ok(())
}
