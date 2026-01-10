use std::path::PathBuf;
use std::time::Instant;

use serde_json::Value;

use crate::error::AppError;
use crate::tools::builtin;
use crate::tools::definition::{ToolCall, ToolResult};
use crate::tools::security;

#[derive(Debug, Clone)]
pub struct ToolLimits {
    pub max_read_bytes: u64,
    pub max_search_matches: usize,
    pub max_search_files: usize,
    pub timeout_ms: u64,
}

impl Default for ToolLimits {
    fn default() -> Self {
        Self {
            max_read_bytes: 50_000,
            max_search_matches: 200,
            max_search_files: 2_000,
            timeout_ms: 10_000,
        }
    }
}

#[derive(Debug, Clone)]
pub struct ToolExecutor {
    root: PathBuf,
    limits: ToolLimits,
}

impl ToolExecutor {
    pub fn new(workspace_root: PathBuf) -> Result<Self, AppError> {
        let root = security::canonicalize_root(&workspace_root)?;
        Ok(Self {
            root,
            limits: ToolLimits::default(),
        })
    }

    #[allow(dead_code)]
    pub fn with_limits(mut self, limits: ToolLimits) -> Self {
        self.limits = limits;
        self
    }

    pub fn definitions(&self) -> Vec<crate::tools::definition::ToolDefinition> {
        builtin::definitions()
    }

    pub async fn execute(&self, call: ToolCall) -> ToolResult {
        let started = Instant::now();
        let root = self.root.clone();
        let limits = self.limits.clone();
        let name = call.name.clone();
        let id = call.id.clone();
        let args = call.arguments.clone();

        let timeout_ms = limits.timeout_ms;
        let name_for_exec = name.clone();
        let fut = tokio::task::spawn_blocking(move || execute_blocking(&root, &limits, &name_for_exec, &args));
        let output = match tokio::time::timeout(std::time::Duration::from_millis(timeout_ms), fut).await {
            Ok(Ok(res)) => res,
            Ok(Err(join_err)) => Err(AppError::Message(join_err.to_string())),
            Err(_) => Err(AppError::Message("Tool execution timed out".to_string())),
        };

        let duration_ms = started.elapsed().as_millis().min(u128::from(u64::MAX)) as u64;
        match output {
            Ok(v) => ToolResult {
                tool_call_id: id,
                name,
                ok: true,
                output: v,
                error: None,
                duration_ms: Some(duration_ms),
            },
            Err(e) => ToolResult {
                tool_call_id: id,
                name,
                ok: false,
                output: serde_json::json!({}),
                error: Some(e.to_string()),
                duration_ms: Some(duration_ms),
            },
        }
    }
}

fn as_str(args: &Value, key: &str) -> Option<String> {
    args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
}

fn as_bool(args: &Value, key: &str) -> Option<bool> {
    args.get(key).and_then(|v| v.as_bool())
}

fn as_u64(args: &Value, key: &str) -> Option<u64> {
    args.get(key).and_then(|v| v.as_u64())
}

fn execute_blocking(root: &PathBuf, limits: &ToolLimits, tool_name: &str, args: &Value) -> Result<Value, AppError> {
    match tool_name {
        "list_files" => {
            let path = as_str(args, "path");
            let entries = builtin::files::list_files(root, path.as_deref())?;
            Ok(serde_json::to_value(entries).map_err(|e| AppError::Message(e.to_string()))?)
        }
        "read_file" => {
            let path = as_str(args, "path").ok_or_else(|| AppError::Message("Missing path".to_string()))?;
            let (content, truncated) = builtin::files::read_file(root, &path, limits.max_read_bytes)?;
            Ok(serde_json::json!({ "path": path, "content": content, "truncated": truncated }))
        }
        "write_file" => {
            let path = as_str(args, "path").ok_or_else(|| AppError::Message("Missing path".to_string()))?;
            let content = as_str(args, "content").unwrap_or_default();
            builtin::files::write_file(root, &path, &content)?;
            Ok(serde_json::json!({ "path": path, "written": content.len() }))
        }
        "append_to_file" => {
            let path = as_str(args, "path").ok_or_else(|| AppError::Message("Missing path".to_string()))?;
            let content = as_str(args, "content").unwrap_or_default();
            builtin::text::append_to_file(root, &path, &content)?;
            Ok(serde_json::json!({ "path": path, "appended": content.len() }))
        }
        "delete_file" => {
            let path = as_str(args, "path").ok_or_else(|| AppError::Message("Missing path".to_string()))?;
            builtin::files::delete_file(root, &path)?;
            Ok(serde_json::json!({ "path": path, "deleted": true }))
        }
        "rename_file" => {
            let old_path = as_str(args, "old_path").ok_or_else(|| AppError::Message("Missing old_path".to_string()))?;
            let new_path = as_str(args, "new_path").ok_or_else(|| AppError::Message("Missing new_path".to_string()))?;
            builtin::files::rename_file(root, &old_path, &new_path)?;
            Ok(serde_json::json!({ "old_path": old_path, "new_path": new_path }))
        }
        "create_directory" => {
            let path = as_str(args, "path").ok_or_else(|| AppError::Message("Missing path".to_string()))?;
            builtin::files::create_directory(root, &path)?;
            Ok(serde_json::json!({ "path": path, "created": true }))
        }
        "search_content" => {
            let pattern = as_str(args, "pattern").ok_or_else(|| AppError::Message("Missing pattern".to_string()))?;
            let path = as_str(args, "path");
            let file_pattern = as_str(args, "file_pattern");
            let matches = builtin::search::search_content(
                root,
                &pattern,
                path.as_deref(),
                file_pattern.as_deref(),
                limits.max_search_matches,
                limits.max_search_files,
                limits.max_read_bytes,
            )?;
            Ok(serde_json::to_value(matches).map_err(|e| AppError::Message(e.to_string()))?)
        }
        "search_files" => {
            let pattern = as_str(args, "pattern").ok_or_else(|| AppError::Message("Missing pattern".to_string()))?;
            let path = as_str(args, "path");
            let matches = builtin::search::search_files(root, &pattern, path.as_deref(), limits.max_search_matches, limits.max_search_files)?;
            Ok(serde_json::json!({ "matches": matches }))
        }
        "get_file_info" => {
            let path = as_str(args, "path").ok_or_else(|| AppError::Message("Missing path".to_string()))?;
            let info = builtin::search::get_file_info(root, &path)?;
            Ok(serde_json::to_value(info).map_err(|e| AppError::Message(e.to_string()))?)
        }
        "count_lines" => {
            let path = as_str(args, "path").ok_or_else(|| AppError::Message("Missing path".to_string()))?;
            let lines = builtin::search::count_lines(root, &path, limits.max_read_bytes)?;
            Ok(serde_json::json!({ "path": path, "lines": lines }))
        }
        "diff_files" => {
            let path1 = as_str(args, "path1").ok_or_else(|| AppError::Message("Missing path1".to_string()))?;
            let path2 = as_str(args, "path2").ok_or_else(|| AppError::Message("Missing path2".to_string()))?;
            let diff = builtin::search::diff_files(root, &path1, &path2, limits.max_read_bytes)?;
            Ok(serde_json::json!({ "path1": path1, "path2": path2, "diff": diff }))
        }
        "find_definition" => {
            let name = as_str(args, "name").ok_or_else(|| AppError::Message("Missing name".to_string()))?;
            let path = as_str(args, "path");
            let matches = builtin::code::find_definition(root, &name, path.as_deref(), limits.max_search_matches, limits.max_search_files, limits.max_read_bytes)?;
            Ok(serde_json::json!({ "matches": matches }))
        }
        "find_references" => {
            let name = as_str(args, "name").ok_or_else(|| AppError::Message("Missing name".to_string()))?;
            let path = as_str(args, "path");
            let matches = builtin::code::find_references(root, &name, path.as_deref(), limits.max_search_matches, limits.max_search_files, limits.max_read_bytes)?;
            Ok(serde_json::json!({ "matches": matches }))
        }
        "list_functions" => {
            let path = as_str(args, "path").ok_or_else(|| AppError::Message("Missing path".to_string()))?;
            let matches = builtin::code::list_functions(root, &path, limits.max_read_bytes)?;
            Ok(serde_json::json!({ "functions": matches }))
        }
        "list_imports" => {
            let path = as_str(args, "path").ok_or_else(|| AppError::Message("Missing path".to_string()))?;
            let matches = builtin::code::list_imports(root, &path, limits.max_read_bytes)?;
            Ok(serde_json::json!({ "imports": matches }))
        }
        "replace_in_file" => {
            let path = as_str(args, "path").ok_or_else(|| AppError::Message("Missing path".to_string()))?;
            let search = as_str(args, "search").ok_or_else(|| AppError::Message("Missing search".to_string()))?;
            let replace = as_str(args, "replace").unwrap_or_default();
            let all = as_bool(args, "all").unwrap_or(true);
            let count = builtin::text::replace_in_file(root, &path, &search, &replace, all, limits.max_read_bytes)?;
            Ok(serde_json::json!({ "path": path, "replaced": count }))
        }
        "insert_at_line" => {
            let path = as_str(args, "path").ok_or_else(|| AppError::Message("Missing path".to_string()))?;
            let line = as_u64(args, "line").ok_or_else(|| AppError::Message("Missing line".to_string()))?;
            let content = as_str(args, "content").unwrap_or_default();
            builtin::text::insert_at_line(root, &path, line, &content, limits.max_read_bytes)?;
            Ok(serde_json::json!({ "path": path, "inserted_at": line }))
        }
        "delete_lines" => {
            let path = as_str(args, "path").ok_or_else(|| AppError::Message("Missing path".to_string()))?;
            let start = as_u64(args, "start").ok_or_else(|| AppError::Message("Missing start".to_string()))?;
            let end = as_u64(args, "end").ok_or_else(|| AppError::Message("Missing end".to_string()))?;
            builtin::text::delete_lines(root, &path, start, end, limits.max_read_bytes)?;
            Ok(serde_json::json!({ "path": path, "deleted_lines": { "start": start, "end": end } }))
        }
        _ => Err(AppError::Message(format!("Unknown tool '{tool_name}'"))),
    }
}
