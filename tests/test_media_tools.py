from pathlib import Path
import pytest
from studio import media_tools


def test_configured_binary_has_priority(monkeypatch):
    monkeypatch.setenv("FFMPEG_BIN", '"C:/custom/ffmpeg.exe"')
    monkeypatch.setattr(media_tools.shutil, "which", lambda value: value if value == "C:/custom/ffmpeg.exe" else None)
    assert media_tools.resolve_media_tool("ffmpeg") == str(Path("C:/custom/ffmpeg.exe").resolve())


@pytest.mark.parametrize("name", ["ffmpeg", "ffprobe"])
def test_windows_install_found_without_process_path(monkeypatch, tmp_path, name):
    monkeypatch.setenv(f"{name.upper()}_BIN", "")
    monkeypatch.setattr(media_tools.sys, "platform", "win32")
    monkeypatch.setattr(media_tools.shutil, "which", lambda value: None)
    monkeypatch.setattr(media_tools, "windows_search_dirs", lambda: [tmp_path])
    binary = tmp_path / f"{name}.exe"
    binary.touch()
    assert media_tools.resolve_media_tool(name) == str(binary.resolve())


def test_missing_binary_explains_env_setting(monkeypatch):
    monkeypatch.setattr(media_tools.sys, "platform", "linux")
    monkeypatch.setattr(media_tools.shutil, "which", lambda value: None)
    with pytest.raises(RuntimeError, match="FFMPEG_BIN"):
        media_tools.resolve_media_tool("ffmpeg")
