use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaginatedResponse<T> {
    pub items: Vec<T>,
    pub total: usize,
    pub page: usize,
    pub page_size: usize,
    pub total_pages: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SuccessResponse {
    #[serde(default = "default_success")]
    pub success: bool,
    #[serde(default = "default_success_message")]
    pub message: String,
}

fn default_success() -> bool {
    true
}

fn default_success_message() -> String {
    "Operation completed successfully".to_string()
}

