use std::path::{Component, Path, PathBuf};

use serde::Serialize;
use tauri::State;

use crate::error::AppError;
use crate::state::AppState;

#[derive(Debug, Clone, Serialize)]
pub struct FileEntry {
    pub path: String,
    pub is_dir: bool,
    pub size: Option<u64>,
}

#[tauri::command]
pub fn list_files(
    state: State<AppState>,
    execution_id: String,
    dir: Option<String>,
) -> Result<Vec<FileEntry>, AppError> {
    let root = workspace_root(&state, &execution_id)?;
    let root = root
        .canonicalize()
        .map_err(|e| AppError::Message(format!("Invalid workspace_path: {e}")))?;

    let rel_dir = dir
        .as_deref()
        .filter(|s| !s.trim().is_empty())
        .map(validate_relative_path)
        .transpose()?
        .unwrap_or_else(|| PathBuf::from(""));

    let target = root.join(rel_dir);
    let target = target
        .canonicalize()
        .map_err(|e| AppError::Message(format!("Invalid dir: {e}")))?;

    ensure_within_root(&root, &target)?;

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

#[tauri::command]
pub fn read_file(
    state: State<AppState>,
    execution_id: String,
    path: String,
) -> Result<String, AppError> {
    let root = workspace_root(&state, &execution_id)?;
    let root = root
        .canonicalize()
        .map_err(|e| AppError::Message(format!("Invalid workspace_path: {e}")))?;
    let rel = validate_relative_path(&path)?;

    let full = root.join(rel);
    let full = full
        .canonicalize()
        .map_err(|e| AppError::Message(format!("Invalid path: {e}")))?;
    ensure_within_root(&root, &full)?;

    std::fs::read_to_string(&full).map_err(|e| AppError::Message(e.to_string()))
}

#[tauri::command]
pub fn write_file(
    state: State<AppState>,
    execution_id: String,
    path: String,
    content: String,
) -> Result<(), AppError> {
    let root = workspace_root(&state, &execution_id)?;
    let root = root
        .canonicalize()
        .map_err(|e| AppError::Message(format!("Invalid workspace_path: {e}")))?;
    let rel = validate_relative_path(&path)?;

    let file_name = rel
        .file_name()
        .ok_or_else(|| AppError::Message("Invalid path".to_string()))?;
    let parent_rel = rel.parent().unwrap_or_else(|| Path::new(""));

    let parent_full = ensure_safe_dir(&root, parent_rel)?;
    let full = parent_full.join(file_name);
    ensure_within_root(&root, &full)?;

    if full.exists() {
        let meta =
            std::fs::symlink_metadata(&full).map_err(|e| AppError::Message(e.to_string()))?;
        if meta.file_type().is_symlink() {
            return Err(AppError::Message(
                "Refusing to write through symlink".to_string(),
            ));
        }
    }

    std::fs::write(full, content).map_err(|e| AppError::Message(e.to_string()))?;
    Ok(())
}

fn workspace_root(state: &State<AppState>, execution_id: &str) -> Result<PathBuf, AppError> {
    let execution = state
        .store
        .executions_get(execution_id)?
        .ok_or_else(|| AppError::Message(format!("Execution {execution_id} not found")))?;

    let raw = execution
        .workspace_path
        .as_deref()
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .ok_or_else(|| AppError::Message("Execution workspace_path is not set".to_string()))?;

    Ok(PathBuf::from(raw))
}

fn validate_relative_path(input: &str) -> Result<PathBuf, AppError> {
    let p = Path::new(input);
    if p.is_absolute() {
        return Err(AppError::Message(
            "Absolute paths are not allowed".to_string(),
        ));
    }

    let mut out = PathBuf::new();
    for c in p.components() {
        match c {
            Component::Normal(seg) => out.push(seg),
            Component::CurDir => {}
            Component::ParentDir => {
                return Err(AppError::Message(
                    "Parent dir '..' is not allowed".to_string(),
                ))
            }
            Component::RootDir | Component::Prefix(_) => {
                return Err(AppError::Message("Invalid path component".to_string()))
            }
        }
    }
    Ok(out)
}

fn ensure_within_root(root: &Path, candidate: &Path) -> Result<(), AppError> {
    if !candidate.starts_with(root) {
        return Err(AppError::Message("Path is outside workspace".to_string()));
    }
    Ok(())
}

fn ensure_safe_dir(root: &Path, rel_dir: &Path) -> Result<PathBuf, AppError> {
    let mut current = root.to_path_buf();

    for component in rel_dir.components() {
        current.push(component);
        if current.exists() {
            let meta = std::fs::symlink_metadata(&current)
                .map_err(|e| AppError::Message(e.to_string()))?;
            if meta.file_type().is_symlink() {
                return Err(AppError::Message(
                    "Symlinks are not allowed in workspace paths".to_string(),
                ));
            }
            if !meta.is_dir() {
                return Err(AppError::Message(
                    "Path component is not a directory".to_string(),
                ));
            }
        } else {
            std::fs::create_dir(&current).map_err(|e| AppError::Message(e.to_string()))?;
        }
    }

    let canonical = current
        .canonicalize()
        .map_err(|e| AppError::Message(e.to_string()))?;
    ensure_within_root(root, &canonical)?;
    Ok(canonical)
}
