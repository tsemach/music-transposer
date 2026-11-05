use std::path::Path;

use tauri::ipc::Response;

fn check_pdf(path: &str) -> Result<(), String> {
    let target = Path::new(path);
    let is_pdf = target
        .extension()
        .is_some_and(|extension| extension.eq_ignore_ascii_case("pdf"));
    if !target.is_absolute() || !is_pdf {
        return Err(format!("Not an absolute PDF path: {path}"));
    }
    Ok(())
}

#[tauri::command]
pub fn read_pdf_bytes(path: String) -> Result<Response, String> {
    check_pdf(&path)?;
    std::fs::read(&path)
        .map(Response::new)
        .map_err(|error| format!("Could not read {path}: {error}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn only_absolute_pdf_paths_are_readable() {
        assert!(check_pdf("/music/song.PDF").is_ok());
        assert!(check_pdf("/music/song.txt").is_err());
        assert!(check_pdf("song.pdf").is_err());
    }
}
