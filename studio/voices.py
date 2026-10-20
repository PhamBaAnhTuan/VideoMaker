"""Read the installed SDK voice catalogue without loading a speech model."""
from dataclasses import dataclass
from importlib.metadata import distribution, PackageNotFoundError
import json
from pathlib import Path


@dataclass(frozen=True)
class Voice:
    id: str
    description: str = ""
    featured: int = 0


def voice_catalogue() -> list[Voice]:
    try:
        path = Path(distribution("vieneu").locate_file("vieneu/assets/voices_v3_turbo.json"))
        data = json.loads(path.read_text(encoding="utf-8"))
        voices = [Voice(name, value.get("description", ""), int(value.get("featured") or 0))
                  for name, value in data["presets"].items()]
        return sorted(voices, key=lambda voice: voice.featured or 10000)
    except (PackageNotFoundError, OSError, ValueError, KeyError, TypeError):
        return [Voice("Hải Đăng", "Giọng mặc định; cài VieNeu để xem đầy đủ danh sách.")]


PREVIEW_TEXT = "Xin chào bạn! Hãy cùng khám phá những ý tưởng mới và biến kiến thức thành video thật sinh động."
