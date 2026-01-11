use std::path::{Path, PathBuf};

use serde::Serialize;

use crate::error::AppError;
use crate::tools::security;

#[derive(Debug, Clone, Serialize)]
pub struct FileEntry {
    pub path: String,
    pub is_dir: bool,
    pub size: Option<u64>,
}

pub fn list_files(root: &Path, dir: Option<&str>) -> Result<Vec<FileEntry>, AppError> {
    let root = security::canonicalize_root(root)?;

    let rel_dir = dir
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .map(security::validate_relative_path)
        .transpose()?
        .unwrap_or_else(|| PathBuf::from(""));

    let target = security::resolve_existing_path(&root, &rel_dir)?;
    if !target.is_dir() {
        return Err(AppError::Message("Target is not a directory".to_string()));
    }

    let mut entries = Vec::new();
    for entry in std::fs::read_dir(&target).map_err(|e| AppError::Message(e.to_string()))? {
        let entry = entry.map_err(|e| AppError::Message(e.to_string()))?;
        let meta = entry
            .metadata()
            .map_err(|e| AppError::Message(e.to_string()))?;
        let path = entry.path();
        let rel = path
            .strip_prefix(&root)
            .unwrap_or(&path)
            .to_string_lossy()
            .replace('\\', "/");
        entries.push(FileEntry {
            path: rel,
            is_dir: meta.is_dir(),
            size: if meta.is_file() {
                Some(meta.len())
            } else {
                None
            },
        });
    }

    entries.sort_by(|a, b| match (a.is_dir, b.is_dir) {
        (true, false) => std::cmp::Ordering::Less,
        (false, true) => std::cmp::Ordering::Greater,
        _ => a.path.cmp(&b.path),
    });

    Ok(entries)
}

pub fn read_file(
    root: &Path,
    path: &str,
    offset: Option<u64>,
    limit: Option<u64>,
    max_bytes: u64,
) -> Result<(String, u64, bool), AppError> {
    use std::io::{Read, Seek, SeekFrom};

    let root = security::canonicalize_root(root)?;
    let rel = security::validate_relative_path(path)?;
    let full = security::resolve_existing_path(&root, &rel)?;
    let meta = std::fs::metadata(&full).map_err(|e| AppError::Message(e.to_string()))?;
    if !meta.is_file() {
        return Err(AppError::Message("Path is not a file".to_string()));
    }

    let total_size = meta.len();
    let offset = offset.unwrap_or(0);
    if offset >= total_size {
        return Ok((String::new(), total_size, false));
    }

    let requested_limit = limit.unwrap_or(max_bytes);
    let effective_limit = requested_limit.min(max_bytes);
    if effective_limit == 0 {
        return Ok((String::new(), total_size, true));
    }

    if offset == 0 {
        let truncated = total_size > effective_limit;
        let (text, _lossy) = security::read_to_string_limited(&full, effective_limit)?;
        return Ok((text, total_size, truncated));
    }

    let mut file = std::fs::File::open(&full).map_err(|e| AppError::Message(e.to_string()))?;
    file.seek(SeekFrom::Start(offset))
        .map_err(|e| AppError::Message(e.to_string()))?;

    let mut buf = Vec::new();
    let mut handle = file.take(effective_limit);
    handle
        .read_to_end(&mut buf)
        .map_err(|e| AppError::Message(e.to_string()))?;

    let truncated = offset.saturating_add(buf.len() as u64) < total_size;
    let text = match String::from_utf8(buf) {
        Ok(s) => s,
        Err(e) => String::from_utf8_lossy(e.as_bytes()).to_string(),
    };

    Ok((text, total_size, truncated))
}

pub fn write_file(root: &Path, path: &str, content: &str) -> Result<(), AppError> {
    let root = security::canonicalize_root(root)?;
    let rel = security::validate_relative_path(path)?;
    let full = security::resolve_write_path(&root, &rel)?;
    std::fs::write(full, content).map_err(|e| AppError::Message(e.to_string()))?;
    Ok(())
}

pub fn append_to_file(root: &Path, path: &str, content: &str) -> Result<(), AppError> {
    use std::io::Write;
    let root = security::canonicalize_root(root)?;
    let rel = security::validate_relative_path(path)?;
    let full = security::resolve_write_path(&root, &rel)?;
    let mut f = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(full)
        .map_err(|e| AppError::Message(e.to_string()))?;
    f.write_all(content.as_bytes())
        .map_err(|e| AppError::Message(e.to_string()))?;
    Ok(())
}

pub fn create_directory(root: &Path, path: &str) -> Result<(), AppError> {
    let root = security::canonicalize_root(root)?;
    let rel = security::validate_relative_path(path)?;
    let _ = security::ensure_safe_dir(&root, &rel)?;
    Ok(())
}

pub fn delete_file(root: &Path, path: &str) -> Result<(), AppError> {
    let root = security::canonicalize_root(root)?;
    let rel = security::validate_relative_path(path)?;
    let full = security::resolve_existing_path(&root, &rel)?;

    let meta = std::fs::metadata(&full).map_err(|e| AppError::Message(e.to_string()))?;
    if meta.is_file() {
        std::fs::remove_file(&full).map_err(|e| AppError::Message(e.to_string()))?;
        return Ok(());
    }

    if meta.is_dir() {
        let mut it = std::fs::read_dir(&full).map_err(|e| AppError::Message(e.to_string()))?;
        if it.next().is_some() {
            return Err(AppError::Message(
                "Refusing to delete non-empty directory".to_string(),
            ));
        }
        std::fs::remove_dir(&full).map_err(|e| AppError::Message(e.to_string()))?;
        return Ok(());
    }

    Err(AppError::Message("Unsupported path type".to_string()))
}

pub fn rename_file(root: &Path, old_path: &str, new_path: &str) -> Result<(), AppError> {
    let root = security::canonicalize_root(root)?;
    let rel_old = security::validate_relative_path(old_path)?;
    let rel_new = security::validate_relative_path(new_path)?;

    let src = security::resolve_existing_path(&root, &rel_old)?;
    let dst = security::resolve_write_path(&root, &rel_new)?;
    std::fs::rename(src, dst).map_err(|e| AppError::Message(e.to_string()))?;
    Ok(())
}
