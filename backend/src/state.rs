use std::sync::Arc;

use tauri::AppHandle;

use crate::error::AppError;
use crate::store::sqlite::SqliteStore;

#[derive(Clone)]
pub struct AppState {
    pub store: Arc<SqliteStore>,
}

impl AppState {
    pub fn init(_app: &AppHandle) -> Result<Self, AppError> {
        let store = SqliteStore::new("agent-team")?;
        Ok(Self {
            store: Arc::new(store),
        })
    }
}
