use std::path::Path;

use regex::Regex;

use crate::error::AppError;
use crate::tools::builtin::files;

pub fn replace_in_file(root: &Path, path: &str, search: &str, replace: &str, all: bool, max_read_bytes: u64) -> Result<u64, AppError> {
    let (text, _trunc) = files::read_file(root, path, max_read_bytes)?;
    let rx = Regex::new(search).map_err(|e| AppError::Message(e.to_string()))?;

    let mut count: u64 = 0;
    let next = if all {
        count = rx.find_iter(&text).count() as u64;
        rx.replace_all(&text, replace).to_string()
    } else {
        if rx.is_match(&text) {
            count = 1;
        }
        rx.replace(&text, replace).to_string()
    };

    files::write_file(root, path, &next)?;
    Ok(count)
}

pub fn insert_at_line(root: &Path, path: &str, line: u64, content: &str, max_read_bytes: u64) -> Result<(), AppError> {
    let (text, _trunc) = files::read_file(root, path, max_read_bytes)?;
    let mut lines: Vec<String> = text.lines().map(|s| s.to_string()).collect();
    let idx = line.saturating_sub(1) as usize;
    let insert = content.trim_end_matches('\n').to_string();
    if idx >= lines.len() {
        lines.push(insert);
    } else {
        lines.insert(idx, insert);
    }
    let next = if text.ends_with('\n') {
        format!("{}\n", lines.join("\n"))
    } else {
        lines.join("\n")
    };
    files::write_file(root, path, &next)?;
    Ok(())
}

pub fn delete_lines(root: &Path, path: &str, start: u64, end: u64, max_read_bytes: u64) -> Result<(), AppError> {
    if end < start {
        return Err(AppError::Message("end must be >= start".to_string()));
    }
    let (text, _trunc) = files::read_file(root, path, max_read_bytes)?;
    let mut lines: Vec<String> = text.lines().map(|s| s.to_string()).collect();
    let s = start.saturating_sub(1) as usize;
    let e = end.saturating_sub(1) as usize;
    if s >= lines.len() {
        return Ok(());
    }
    let end_idx = e.min(lines.len().saturating_sub(1));
    lines.drain(s..=end_idx);
    let next = if text.ends_with('\n') {
        format!("{}\n", lines.join("\n"))
    } else {
        lines.join("\n")
    };
    files::write_file(root, path, &next)?;
    Ok(())
}

pub fn append_to_file(root: &Path, path: &str, content: &str) -> Result<(), AppError> {
    files::append_to_file(root, path, content)
}

