from pathlib import Path

import pytest

from backend.audiveris_locator import find_audiveris
from backend.errors import AudiverisNotFoundError


def make_executable(directory: Path, name: str = "Audiveris") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text("#!/bin/sh\n")
    path.chmod(0o755)
    return path


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    monkeypatch.delenv("AUDIVERIS_PATH", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path / "empty-path"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def test_override_wins_over_env_and_path(monkeypatch, tmp_path):
    override = make_executable(tmp_path / "override")
    monkeypatch.setenv("AUDIVERIS_PATH", str(make_executable(tmp_path / "env")))
    monkeypatch.setenv("PATH", str(make_executable(tmp_path / "onpath").parent))

    assert find_audiveris(override) == override


def test_env_var_used_when_no_override(monkeypatch, tmp_path):
    from_env = make_executable(tmp_path / "env")
    monkeypatch.setenv("AUDIVERIS_PATH", str(from_env))
    monkeypatch.setenv("PATH", str(make_executable(tmp_path / "onpath").parent))

    assert find_audiveris() == from_env


def test_path_lookup_finds_capitalised_binary(monkeypatch, tmp_path):
    on_path = make_executable(tmp_path / "onpath", "Audiveris")
    monkeypatch.setenv("PATH", str(on_path.parent))

    assert find_audiveris().name == "Audiveris"


def test_known_install_dir_under_home_is_searched(tmp_path):
    installed = make_executable(
        tmp_path / "home" / ".local" / "opt" / "audiveris" / "opt" / "audiveris" / "bin"
    )

    assert find_audiveris() == installed


def test_override_pointing_at_missing_file_raises(tmp_path):
    with pytest.raises(AudiverisNotFoundError, match="missing"):
        find_audiveris(tmp_path / "missing")


def test_nothing_found_raises_and_lists_searched_locations(monkeypatch, tmp_path):
    with pytest.raises(AudiverisNotFoundError) as raised:
        find_audiveris()

    message = str(raised.value)
    assert "AUDIVERIS_PATH" in message
    assert "PATH" in message
    assert str(tmp_path / "home") in message
