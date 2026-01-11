use std::path::{Component, Path, PathBuf};

use crate::error::AppError;

pub fn validate_relative_path(input: &str) -> Result<PathBuf, AppError> {
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
                ));
            }
            Component::RootDir | Component::Prefix(_) => {
                return Err(AppError::Message("Invalid path component".to_string()));
            }
        }
    }
    Ok(out)
}

pub fn ensure_within_root(root: &Path, candidate: &Path) -> Result<(), AppError> {
    if !candidate.starts_with(root) {
        return Err(AppError::Message("Path is outside workspace".to_string()));
    }
    Ok(())
}

pub fn ensure_safe_dir(root: &Path, rel_dir: &Path) -> Result<PathBuf, AppError> {
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

pub fn canonicalize_root(root: &Path) -> Result<PathBuf, AppError> {
    let canonical = root
        .canonicalize()
        .map_err(|e| AppError::Message(e.to_string()))?;
    if !canonical.is_dir() {
        return Err(AppError::Message(
            "Workspace root is not a directory".to_string(),
        ));
    }
    Ok(canonical)
}

pub fn resolve_existing_path(root: &Path, rel: &Path) -> Result<PathBuf, AppError> {
    let candidate = root.join(rel);
    let meta =
        std::fs::symlink_metadata(&candidate).map_err(|e| AppError::Message(e.to_string()))?;
    if meta.file_type().is_symlink() {
        return Err(AppError::Message("Symlinks are not allowed".to_string()));
    }
    let canonical = candidate
        .canonicalize()
        .map_err(|e| AppError::Message(e.to_string()))?;
    ensure_within_root(root, &canonical)?;
    Ok(canonical)
}

pub fn resolve_write_path(root: &Path, rel: &Path) -> Result<PathBuf, AppError> {
    let file_name = rel
        .file_name()
        .ok_or_else(|| AppError::Message("Invalid path".to_string()))?;
    let parent_rel = rel.parent().unwrap_or_else(|| Path::new(""));

    let parent_full = ensure_safe_dir(root, parent_rel)?;
    let full = parent_full.join(file_name);
    ensure_within_root(root, &full)?;

    if full.exists() {
        let meta =
            std::fs::symlink_metadata(&full).map_err(|e| AppError::Message(e.to_string()))?;
        if meta.file_type().is_symlink() {
            return Err(AppError::Message(
                "Refusing to write through symlink".to_string(),
            ));
        }
    }

    Ok(full)
}

pub fn read_to_string_limited(path: &Path, max_bytes: u64) -> Result<(String, bool), AppError> {
    use std::io::Read;

    let file = std::fs::File::open(path).map_err(|e| AppError::Message(e.to_string()))?;
    let mut buf = Vec::new();
    let mut handle = file.take(max_bytes);
    handle
        .read_to_end(&mut buf)
        .map_err(|e| AppError::Message(e.to_string()))?;

    match String::from_utf8(buf) {
        Ok(s) => Ok((s, false)),
        Err(e) => Ok((String::from_utf8_lossy(e.as_bytes()).to_string(), true)),
    }
}
