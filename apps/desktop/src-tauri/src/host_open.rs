use std::path::Path;
use std::process::Command;

use tauri::AppHandle;
use tauri_plugin_opener::OpenerExt;

#[derive(Clone, Copy)]
enum Action {
    Open,
    Reveal,
}

fn explorer_args(action: Action, windows_path: &str) -> Vec<String> {
    match action {
        Action::Open => vec![windows_path.to_string()],
        Action::Reveal => vec![format!("/select,{windows_path}")],
    }
}

fn check_target(action: Action, path: &str) -> Result<(), String> {
    let target = Path::new(path);
    if !target.is_absolute() {
        return Err(format!("Path must be absolute: {path}"));
    }
    let is_pdf = target
        .extension()
        .is_some_and(|extension| extension.eq_ignore_ascii_case("pdf"));
    if matches!(action, Action::Open) && !is_pdf {
        return Err(format!("Only PDF files can be opened: {path}"));
    }
    if !target.exists() {
        return Err(format!("File not found: {path}"));
    }
    Ok(())
}

// A WSL distro usually has no PDF viewer or file manager: xdg-open then reports
// "No applications found" yet exits 0, so the Windows side has to do the work.
fn running_under_wsl() -> bool {
    std::env::var_os("WSL_DISTRO_NAME").is_some()
}

fn windows_path(path: &str) -> Result<String, String> {
    let output = Command::new("wslpath")
        .args(["-w", path])
        .output()
        .map_err(|error| format!("wslpath failed: {error}"))?;
    if !output.status.success() {
        return Err(format!("wslpath could not convert {path}"));
    }
    Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
}

// explorer.exe exits with 1 even when it succeeded, so only a failed launch is an error.
fn run_explorer(action: Action, path: &str) -> Result<(), String> {
    let args = explorer_args(action, &windows_path(path)?);
    Command::new("explorer.exe")
        .args(args)
        .status()
        .map(|_| ())
        .map_err(|error| format!("Could not start Windows Explorer: {error}"))
}

#[tauri::command]
pub fn open_in_host(app: AppHandle, path: String, reveal: bool) -> Result<(), String> {
    let action = if reveal { Action::Reveal } else { Action::Open };
    check_target(action, &path)?;
    if running_under_wsl() {
        return run_explorer(action, &path);
    }
    match action {
        Action::Open => app.opener().open_path(&path, None::<&str>),
        Action::Reveal => app.opener().reveal_item_in_dir(&path),
    }
    .map_err(|error| error.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn explorer_opens_a_file_by_its_path() {
        assert_eq!(explorer_args(Action::Open, r"\\wsl.localhost\Ubuntu\out\song.pdf"), vec![r"\\wsl.localhost\Ubuntu\out\song.pdf"]);
    }

    #[test]
    fn explorer_reveals_a_file_with_select() {
        assert_eq!(explorer_args(Action::Reveal, r"C:\out\song.pdf"), vec![r"/select,C:\out\song.pdf"]);
    }

    #[test]
    fn only_pdf_files_may_be_opened() {
        assert!(check_target(Action::Open, "/tmp/song.txt").is_err());
        assert!(check_target(Action::Open, "relative/song.pdf").is_err());
    }

    #[test]
    fn missing_files_are_rejected_with_the_path_in_the_message() {
        let error = check_target(Action::Reveal, "/definitely/not/here.pdf").unwrap_err();
        assert!(error.contains("/definitely/not/here.pdf"));
    }

    #[test]
    fn an_existing_pdf_is_accepted_for_both_actions() {
        let file = std::env::temp_dir().join("ascurix-host-open-test.pdf");
        std::fs::write(&file, b"%PDF").unwrap();
        let path = file.to_str().unwrap();
        assert!(check_target(Action::Open, path).is_ok());
        assert!(check_target(Action::Reveal, path).is_ok());
        std::fs::remove_file(file).unwrap();
    }

    #[test]
    fn pdf_extension_check_ignores_case() {
        assert!(check_target(Action::Open, "/no/such/SONG.PDF").unwrap_err().contains("not found"));
    }
}
