pub mod code;
pub mod files;
pub mod search;
pub mod text;

use serde_json::json;

use crate::tools::definition::ToolDefinition;

pub fn definitions() -> Vec<ToolDefinition> {
    vec![
        ToolDefinition {
            name: "list_files".to_string(),
            description: "List directory entries under the execution workspace.".to_string(),
            parameters: json!({
                "type": "object",
                "properties": { "path": { "type": "string", "description": "Relative directory path (optional)." } },
                "required": []
            }),
        },
        ToolDefinition {
            name: "read_file".to_string(),
            description: "Read a UTF-8 text file under the execution workspace.".to_string(),
            parameters: json!({
                "type": "object",
                "properties": { "path": { "type": "string" } },
                "required": ["path"]
            }),
        },
        ToolDefinition {
            name: "write_file".to_string(),
            description: "Write or create a UTF-8 text file under the execution workspace.".to_string(),
            parameters: json!({
                "type": "object",
                "properties": { "path": { "type": "string" }, "content": { "type": "string" } },
                "required": ["path", "content"]
            }),
        },
        ToolDefinition {
            name: "delete_file".to_string(),
            description: "Delete a file (or empty directory) under the execution workspace.".to_string(),
            parameters: json!({
                "type": "object",
                "properties": { "path": { "type": "string" } },
                "required": ["path"]
            }),
        },
        ToolDefinition {
            name: "rename_file".to_string(),
            description: "Rename or move a file under the execution workspace.".to_string(),
            parameters: json!({
                "type": "object",
                "properties": { "old_path": { "type": "string" }, "new_path": { "type": "string" } },
                "required": ["old_path", "new_path"]
            }),
        },
        ToolDefinition {
            name: "create_directory".to_string(),
            description: "Create a directory under the execution workspace.".to_string(),
            parameters: json!({
                "type": "object",
                "properties": { "path": { "type": "string" } },
                "required": ["path"]
            }),
        },
        ToolDefinition {
            name: "search_content".to_string(),
            description: "Search file contents under the workspace using a regular expression.".to_string(),
            parameters: json!({
                "type": "object",
                "properties": {
                    "pattern": { "type": "string" },
                    "path": { "type": "string", "description": "Relative directory path (optional)." },
                    "file_pattern": { "type": "string", "description": "Optional filename filter (glob-like, e.g. \"*.rs\")." }
                },
                "required": ["pattern"]
            }),
        },
        ToolDefinition {
            name: "search_files".to_string(),
            description: "Search filenames under the workspace.".to_string(),
            parameters: json!({
                "type": "object",
                "properties": {
                    "pattern": { "type": "string" },
                    "path": { "type": "string", "description": "Relative directory path (optional)." }
                },
                "required": ["pattern"]
            }),
        },
        ToolDefinition {
            name: "get_file_info".to_string(),
            description: "Get file metadata (size, modified time, type) under the workspace.".to_string(),
            parameters: json!({
                "type": "object",
                "properties": { "path": { "type": "string" } },
                "required": ["path"]
            }),
        },
        ToolDefinition {
            name: "count_lines".to_string(),
            description: "Count lines in a text file under the workspace.".to_string(),
            parameters: json!({
                "type": "object",
                "properties": { "path": { "type": "string" } },
                "required": ["path"]
            }),
        },
        ToolDefinition {
            name: "diff_files".to_string(),
            description: "Compute a unified diff between two text files under the workspace.".to_string(),
            parameters: json!({
                "type": "object",
                "properties": { "path1": { "type": "string" }, "path2": { "type": "string" } },
                "required": ["path1", "path2"]
            }),
        },
        ToolDefinition {
            name: "find_definition".to_string(),
            description: "Find likely function/class/type definitions by name (regex-based).".to_string(),
            parameters: json!({
                "type": "object",
                "properties": {
                    "name": { "type": "string" },
                    "path": { "type": "string", "description": "Relative directory path (optional)." }
                },
                "required": ["name"]
            }),
        },
        ToolDefinition {
            name: "find_references".to_string(),
            description: "Find references by name (word-boundary regex) under the workspace.".to_string(),
            parameters: json!({
                "type": "object",
                "properties": {
                    "name": { "type": "string" },
                    "path": { "type": "string", "description": "Relative directory path (optional)." }
                },
                "required": ["name"]
            }),
        },
        ToolDefinition {
            name: "list_functions".to_string(),
            description: "List functions in a file (regex-based).".to_string(),
            parameters: json!({
                "type": "object",
                "properties": { "path": { "type": "string" } },
                "required": ["path"]
            }),
        },
        ToolDefinition {
            name: "list_imports".to_string(),
            description: "List imports in a file (regex-based).".to_string(),
            parameters: json!({
                "type": "object",
                "properties": { "path": { "type": "string" } },
                "required": ["path"]
            }),
        },
        ToolDefinition {
            name: "replace_in_file".to_string(),
            description: "Replace content in a file using a regular expression.".to_string(),
            parameters: json!({
                "type": "object",
                "properties": {
                    "path": { "type": "string" },
                    "search": { "type": "string" },
                    "replace": { "type": "string" },
                    "all": { "type": "boolean" }
                },
                "required": ["path", "search", "replace"]
            }),
        },
        ToolDefinition {
            name: "insert_at_line".to_string(),
            description: "Insert content at a 1-based line number in a file.".to_string(),
            parameters: json!({
                "type": "object",
                "properties": {
                    "path": { "type": "string" },
                    "line": { "type": "integer", "minimum": 1 },
                    "content": { "type": "string" }
                },
                "required": ["path", "line", "content"]
            }),
        },
        ToolDefinition {
            name: "delete_lines".to_string(),
            description: "Delete an inclusive 1-based line range in a file.".to_string(),
            parameters: json!({
                "type": "object",
                "properties": {
                    "path": { "type": "string" },
                    "start": { "type": "integer", "minimum": 1 },
                    "end": { "type": "integer", "minimum": 1 }
                },
                "required": ["path", "start", "end"]
            }),
        },
        ToolDefinition {
            name: "append_to_file".to_string(),
            description: "Append content to a file.".to_string(),
            parameters: json!({
                "type": "object",
                "properties": { "path": { "type": "string" }, "content": { "type": "string" } },
                "required": ["path", "content"]
            }),
        },
    ]
}

