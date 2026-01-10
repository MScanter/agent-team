use std::path::{Path, PathBuf};

use regex::Regex;
use serde::Serialize;

use crate::error::AppError;
use crate::tools::builtin::files;
use crate::tools::security;

#[derive(Debug, Clone, Serialize)]
pub struct ContentMatch {
    pub path: String,
    pub line: u32,
    pub column: u32,
    pub snippet: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct FileInfo {
    pub path: String,
    pub is_dir: bool,
    pub size: Option<u64>,
    pub modified_unix_ms: Option<u64>,
}

fn walk_files(root: &Path, start_rel: &Path, max_files: usize) -> Result<Vec<PathBuf>, AppError> {
    let root = security::canonicalize_root(root)?;
    let start = security::resolve_existing_path(&root, start_rel)?;
    if !start.is_dir() {
        return Err(AppError::Message("Search path is not a directory".to_string()));
    }

    let mut out = Vec::new();
    let mut stack = vec![start];
    while let Some(dir) = stack.pop() {
        if out.len() >= max_files {
            break;
        }
        for entry in std::fs::read_dir(&dir).map_err(|e| AppError::Message(e.to_string()))? {
            if out.len() >= max_files {
                break;
            }
            let entry = entry.map_err(|e| AppError::Message(e.to_string()))?;
            let path = entry.path();
            let meta = std::fs::symlink_metadata(&path).map_err(|e| AppError::Message(e.to_string()))?;
            if meta.file_type().is_symlink() {
                continue;
            }
            if meta.is_dir() {
                stack.push(path);
            } else if meta.is_file() {
                out.push(path);
            }
        }
    }
    Ok(out)
}

fn matches_file_pattern(file_name: &str, pattern: Option<&str>) -> Result<bool, AppError> {
    let Some(pat) = pattern.map(|s| s.trim()).filter(|s| !s.is_empty()) else {
        return Ok(true);
    };

    if let Some(re_pat) = pat.strip_prefix("re:") {
        let rx = Regex::new(re_pat).map_err(|e| AppError::Message(e.to_string()))?;
        return Ok(rx.is_match(file_name));
    }

    // Support simple glob-like patterns. If no glob chars, do a substring match.
    if pat.contains('*') || pat.contains('?') {
        let mut re = String::from("^");
        for ch in pat.chars() {
            match ch {
                '*' => re.push_str(".*"),
                '?' => re.push('.'),
                '.' | '+' | '(' | ')' | '|' | '^' | '$' | '{' | '}' | '[' | ']' | '\\' => {
                    re.push('\\');
                    re.push(ch);
                }
                _ => re.push(ch),
            }
        }
        re.push('$');
        let rx = Regex::new(&re).map_err(|e| AppError::Message(e.to_string()))?;
        return Ok(rx.is_match(file_name));
    }

    Ok(file_name.contains(pat))
}

pub fn search_content(
    root: &Path,
    pattern: &str,
    path: Option<&str>,
    file_pattern: Option<&str>,
    max_matches: usize,
    max_files: usize,
    max_read_bytes: u64,
) -> Result<Vec<ContentMatch>, AppError> {
    let root = security::canonicalize_root(root)?;
    let rel_dir = path
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .map(security::validate_relative_path)
        .transpose()?
        .unwrap_or_else(|| PathBuf::from(""));

    let rx = Regex::new(pattern).map_err(|e| AppError::Message(e.to_string()))?;
    let files = walk_files(&root, &rel_dir, max_files)?;

    let mut out = Vec::new();
    for file in files {
        if out.len() >= max_matches {
            break;
        }
        let name = file.file_name().and_then(|s| s.to_str()).unwrap_or("");
        if !matches_file_pattern(name, file_pattern)? {
            continue;
        }
        let rel = file
            .strip_prefix(&root)
            .unwrap_or(&file)
            .to_string_lossy()
            .replace('\\', "/");

        let meta = std::fs::metadata(&file).map_err(|e| AppError::Message(e.to_string()))?;
        if meta.len() > max_read_bytes.saturating_mul(10) {
            continue;
        }

        let (text, _truncated) = files::read_file(&root, &rel, max_read_bytes)?;
        for (idx, line) in text.lines().enumerate() {
            if out.len() >= max_matches {
                break;
            }
            if let Some(m) = rx.find(line) {
                out.push(ContentMatch {
                    path: rel.clone(),
                    line: (idx + 1) as u32,
                    column: (m.start() + 1) as u32,
                    snippet: line.trim().to_string(),
                });
            }
        }
    }
    Ok(out)
}

pub fn search_files(root: &Path, pattern: &str, path: Option<&str>, max_matches: usize, max_files: usize) -> Result<Vec<String>, AppError> {
    let root = security::canonicalize_root(root)?;
    let rel_dir = path
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .map(security::validate_relative_path)
        .transpose()?
        .unwrap_or_else(|| PathBuf::from(""));

    let rx = Regex::new(pattern).map_err(|e| AppError::Message(e.to_string()))?;
    let files = walk_files(&root, &rel_dir, max_files)?;

    let mut out = Vec::new();
    for f in files {
        if out.len() >= max_matches {
            break;
        }
        let file_name = f.file_name().and_then(|s| s.to_str()).unwrap_or("");
        if !rx.is_match(file_name) {
            continue;
        }
        let rel = f.strip_prefix(&root).unwrap_or(&f).to_string_lossy().replace('\\', "/");
        out.push(rel);
    }
    Ok(out)
}

pub fn get_file_info(root: &Path, path: &str) -> Result<FileInfo, AppError> {
    let root = security::canonicalize_root(root)?;
    let rel = security::validate_relative_path(path)?;
    let full = security::resolve_existing_path(&root, &rel)?;
    let meta = std::fs::metadata(&full).map_err(|e| AppError::Message(e.to_string()))?;
    let modified_unix_ms = meta.modified().ok().and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok()).map(|d| d.as_millis() as u64);

    Ok(FileInfo {
        path: path.to_string(),
        is_dir: meta.is_dir(),
        size: if meta.is_file() { Some(meta.len()) } else { None },
        modified_unix_ms,
    })
}

pub fn count_lines(root: &Path, path: &str, max_read_bytes: u64) -> Result<u64, AppError> {
    let (text, _truncated) = files::read_file(root, path, max_read_bytes)?;
    Ok(text.lines().count() as u64)
}

pub fn diff_files(root: &Path, path1: &str, path2: &str, max_read_bytes: u64) -> Result<String, AppError> {
    let (a, a_trunc) = files::read_file(root, path1, max_read_bytes)?;
    let (b, b_trunc) = files::read_file(root, path2, max_read_bytes)?;
    let diff = similar::TextDiff::from_lines(&a, &b).unified_diff().header(path1, path2).to_string();
    if a_trunc || b_trunc {
        return Ok(format!("{diff}\n\n[diff truncated due to file size limit]"));
    }
    Ok(diff)
}
