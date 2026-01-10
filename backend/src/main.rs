#![cfg_attr(all(not(debug_assertions), target_os = "windows"), windows_subsystem = "windows")]

mod commands;
mod error;
mod agents;
mod llm;
mod models;
mod orchestration;
mod store;
mod state;

use tauri::Manager;
use state::AppState;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let state = AppState::init(app.handle())?;
            app.manage(state);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::agents::list_agents,
            commands::agents::get_agent,
            commands::agents::create_agent,
            commands::agents::update_agent,
            commands::agents::delete_agent,
            commands::agents::duplicate_agent,
            commands::teams::list_teams,
            commands::teams::get_team,
            commands::teams::create_team,
            commands::teams::update_team,
            commands::teams::delete_team,
            commands::teams::duplicate_team,
            commands::teams::add_team_member,
            commands::teams::remove_team_member,
            commands::teams::reorder_team_members,
            commands::executions::list_executions,
            commands::executions::get_execution,
            commands::executions::create_execution,
            commands::executions::delete_execution,
            commands::executions::control_execution,
            commands::executions::start_execution,
            commands::executions::followup_execution,
            commands::executions::set_execution_workspace,
            commands::fs::list_files,
            commands::fs::read_file,
            commands::fs::write_file,
            commands::llm::test_llm
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
