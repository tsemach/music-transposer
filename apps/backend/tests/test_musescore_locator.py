import pytest
from executable_helpers import make_executable

from backend.errors import MuseScoreNotFoundError
from backend.musescore_locator import find_musescore


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    monkeypatch.delenv("MUSESCORE_PATH", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path / "empty-path"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def test_override_wins_over_env_and_path(monkeypatch, tmp_path):
    override = make_executable(tmp_path / "override", "mscore")
    monkeypatch.setenv("MUSESCORE_PATH", str(make_executable(tmp_path / "env", "mscore")))
    monkeypatch.setenv("PATH", str(make_executable(tmp_path / "onpath", "mscore").parent))

    assert find_musescore(override) == override


def test_env_var_used_when_no_override(monkeypatch, tmp_path):
    from_env = make_executable(tmp_path / "env", "mscore")
    monkeypatch.setenv("MUSESCORE_PATH", str(from_env))

    assert find_musescore() == from_env


def test_path_lookup_finds_known_binary_name(monkeypatch, tmp_path):
    on_path = make_executable(tmp_path / "onpath", "mscore")
    monkeypatch.setenv("PATH", str(on_path.parent))

    assert find_musescore() == on_path


def test_user_level_appimage_install_is_found(tmp_path):
    installed = make_executable(tmp_path / "home" / ".local" / "opt" / "musescore", "MuseScore.AppImage")

    assert find_musescore() == installed


def test_missing_override_raises_musescore_error(tmp_path):
    with pytest.raises(MuseScoreNotFoundError, match="missing"):
        find_musescore(tmp_path / "missing")


def test_nothing_found_lists_searched_locations(tmp_path):
    with pytest.raises(MuseScoreNotFoundError) as raised:
        find_musescore()

    message = str(raised.value)
    assert "MuseScore not found" in message
    assert "MUSESCORE_PATH" in message and str(tmp_path / "home") in message
