"""Find FFmpeg even when a running Windows process has an outdated PATH."""
import os
from pathlib import Path
import shutil
import sys


def windows_search_dirs() -> list[Path]:
    directories = []
    import winreg
    for hive, key in (
        (winreg.HKEY_CURRENT_USER, "Environment"),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    ):
        try:
            with winreg.OpenKey(hive, key) as handle:
                value, _ = winreg.QueryValueEx(handle, "Path")
            directories.extend(Path(os.path.expandvars(p.strip(' "'))) for p in value.split(";") if p.strip())
        except OSError:
            pass
    directories += [Path("C:/ffmpeg/bin"), Path("C:/ffmpeg"),
                    Path(os.getenv("ProgramFiles", "C:/Program Files")) / "ffmpeg/bin"]
    if local := os.getenv("LOCALAPPDATA"):
        root = Path(local) / "Microsoft/WinGet"
        directories.append(root / "Links")
        try:
            directories.extend(path.parent for path in (root / "Packages").glob("*FFmpeg*/**/ffmpeg.exe"))
        except OSError:
            pass
    return directories


def resolve_media_tool(name: str) -> str:
    if name not in ("ffmpeg", "ffprobe"):
        raise ValueError("Chỉ hỗ trợ ffmpeg và ffprobe.")
    configured = os.getenv(f"{name.upper()}_BIN", "").strip().strip('"')
    for candidate in (configured, name):
        if candidate and (found := shutil.which(os.path.expandvars(candidate))):
            return str(Path(found).resolve())
    if sys.platform == "win32":
        # A configured FFmpeg path also locates FFprobe installed beside it.
        other = os.getenv("FFMPEG_BIN" if name == "ffprobe" else "FFPROBE_BIN", "").strip().strip('"')
        directories = ([Path(os.path.expandvars(other)).parent] if other else []) + windows_search_dirs()
        for directory in directories:
            candidate = directory / f"{name}.exe"
            if candidate.is_file():
                return str(candidate.resolve())
    raise RuntimeError(
        f"Không tìm thấy {name}. Đặt {name.upper()}_BIN trong .env thành đường dẫn đầy đủ "
        f"đến {name}.exe (ví dụ C:/ffmpeg/bin/{name}.exe), rồi khởi động lại ứng dụng.")
