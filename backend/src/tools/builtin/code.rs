use std::path::Path;

use regex::Regex;
use serde::Serialize;

use crate::error::AppError;
use crate::tools::builtin::search;
use crate::tools::security;

#[derive(Debug, Clone, Serialize)]
pub struct CodeMatch {
    pub path: String,
    pub line: u32,
    pub snippet: String,
}

fn default_code_file_pattern() -> &'static str {
    // Match common code file extensions.
    r"re:.*\.(rs|ts|tsx|js|jsx|py|go|java|kt|swift|c|cc|cpp|h|hpp)$"
}

pub fn find_definition(
    root: &Path,
    name: &str,
    path: Option<&str>,
    max_matches: usize,
    max_files: usize,
    max_read_bytes: u64,
) -> Result<Vec<CodeMatch>, AppError> {
    let escaped = regex::escape(name);
    let patterns = [
        format!(r"^\s*(pub\s+)?(async\s+)?fn\s+{escaped}\b"),
        format!(r"^\s*(export\s+)?(async\s+)?function\s+{escaped}\b"),
        format!(r"^\s*(export\s+)?class\s+{escaped}\b"),
        format!(r"^\s*(export\s+)?(const|let|var)\s+{escaped}\s*="),
        format!(r"^\s*def\s+{escaped}\b"),
        format!(r"^\s*class\s+{escaped}\b"),
        format!(r"^\s*(pub\s+)?(struct|enum|trait)\s+{escaped}\b"),
        format!(r"^\s*(export\s+)?(interface|type)\s+{escaped}\b"),
    ];

    let mut results = Vec::new();
    for pat in patterns {
        if results.len() >= max_matches {
            break;
        }
        let hits = search::search_content(
            root,
            &format!(r"(?m){pat}"),
            path,
            Some(default_code_file_pattern()),
            max_matches.saturating_sub(results.len()),
            max_files,
            max_read_bytes,
        )?;
        results.extend(hits.into_iter().map(|m| CodeMatch {
            path: m.path,
            line: m.line,
            snippet: m.snippet,
        }));
    }

    Ok(results)
}

pub fn find_references(
    root: &Path,
    name: &str,
    path: Option<&str>,
    max_matches: usize,
    max_files: usize,
    max_read_bytes: u64,
) -> Result<Vec<CodeMatch>, AppError> {
    let escaped = regex::escape(name);
    let pattern = format!(r"\b{escaped}\b");
    let matches = search::search_content(
        root,
        &pattern,
        path,
        Some(default_code_file_pattern()),
        max_matches,
        max_files,
        max_read_bytes,
    )?;
    Ok(matches
        .into_iter()
        .map(|m| CodeMatch {
            path: m.path,
            line: m.line,
            snippet: m.snippet,
        })
        .collect())
}

pub fn list_functions(
    root: &Path,
    path: &str,
    max_read_bytes: u64,
) -> Result<Vec<CodeMatch>, AppError> {
    let root = security::canonicalize_root(root)?;
    let rel = security::validate_relative_path(path)?;
    let full = security::resolve_existing_path(&root, &rel)?;
    let file_name = full.file_name().and_then(|s| s.to_str()).unwrap_or("");
    let ext = Path::new(file_name)
        .extension()
        .and_then(|s| s.to_str())
        .unwrap_or("");

    let (text, _total_size, _truncated) =
        crate::tools::builtin::files::read_file(&root, path, None, None, max_read_bytes)?;

    let rx = match ext {
        "rs" => Regex::new(r"^\s*(pub\s+)?(async\s+)?fn\s+([A-Za-z0-9_]+)\b").unwrap(),
        "py" => Regex::new(r"^\s*def\s+([A-Za-z0-9_]+)\b").unwrap(),
        _ => Regex::new(r"^\s*(export\s+)?(async\s+)?function\s+([A-Za-z0-9_]+)\b").unwrap(),
    };

    let mut out = Vec::new();
    for (idx, line) in text.lines().enumerate() {
        if let Some(caps) = rx.captures(line) {
            let name = caps.get(caps.len() - 1).map(|m| m.as_str()).unwrap_or("");
            out.push(CodeMatch {
                path: path.to_string(),
                line: (idx + 1) as u32,
                snippet: name.to_string(),
            });
        }
    }
    Ok(out)
}

pub fn list_imports(
    root: &Path,
    path: &str,
    max_read_bytes: u64,
) -> Result<Vec<CodeMatch>, AppError> {
    let (text, _total_size, _truncated) =
        crate::tools::builtin::files::read_file(root, path, None, None, max_read_bytes)?;
    let mut out = Vec::new();
    for (idx, line) in text.lines().enumerate() {
        let l = line.trim();
        if l.starts_with("use ") || l.starts_with("import ") || l.starts_with("from ") {
            out.push(CodeMatch {
                path: path.to_string(),
                line: (idx + 1) as u32,
                snippet: l.to_string(),
            });
        }
        if l.starts_with("import ") && l.contains(" as ") {
            out.push(CodeMatch {
                path: path.to_string(),
                line: (idx + 1) as u32,
                snippet: l.to_string(),
            });
        }
    }
    Ok(out)
}
