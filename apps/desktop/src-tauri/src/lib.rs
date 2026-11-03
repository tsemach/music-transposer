mod host_open;
#[tauri::command]
fn ui_log(message: String) {
    eprintln!("[ui] {message}");
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![ui_log, host_open::open_in_host])
        .run(tauri::generate_context!())
        .expect("error while running Music Transpose");
}
