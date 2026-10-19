from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Utterance(StrictModel):
    text: str = Field(min_length=1, max_length=320)
    caption: str = Field(min_length=1, max_length=180)


class Comparison(StrictModel):
    label: str = Field(min_length=1, max_length=35)
    value: str = Field(min_length=1, max_length=65)


class Scene(StrictModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    layout: Literal["hook", "comparison", "stat-hero", "feature-list", "callout", "outro"]
    title: str = Field(min_length=1, max_length=90)
    subtitle: str = Field(default="", max_length=160)
    bullets: list[str] = Field(default_factory=list, max_length=4)
    value: str = Field(default="", max_length=24)
    left: Comparison | None = None
    right: Comparison | None = None
    narration: list[Utterance] = Field(min_length=1, max_length=10)
    image: str | None = None

    @field_validator("bullets")
    @classmethod
    def validate_bullets(cls, value):
        if any(not s.strip() or len(s) > 100 for s in value):
            raise ValueError("Mỗi ý phải có 1–100 ký tự.")
        return value

    @model_validator(mode="after")
    def validate_layout(self):
        if self.layout == "comparison" and (not self.left or not self.right):
            raise ValueError("comparison cần cả left và right.")
        if self.layout == "stat-hero" and not self.value:
            raise ValueError("stat-hero cần value.")
        if self.layout == "feature-list" and not self.bullets:
            raise ValueError("feature-list cần bullets.")
        return self


class Script(StrictModel):
    version: Literal["1.0"] = "1.0"
    title: str = Field(min_length=1, max_length=120)
    channel: str = Field(default="Góc kiến thức", min_length=1, max_length=50)
    source: str = Field(default="", max_length=500)
    scenes: list[Scene] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def unique_ids(self):
        if len({s.id for s in self.scenes}) != len(self.scenes):
            raise ValueError("ID cảnh phải duy nhất.")
        return self

    @classmethod
    def read(cls, path: Path):
        return cls.model_validate_json(path.read_text(encoding="utf-8-sig"))

    def write(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")


PRESETS = {"9:16": (720, 1280), "16:9": (1280, 720), "1:1": (1080, 1080), "4:5": (1080, 1350)}


def parse_size(value: str) -> tuple[int, int]:
    if value in PRESETS:
        return PRESETS[value]
    match = re.fullmatch(r"(\d+)[xX](\d+)", value.strip())
    if not match:
        raise ValueError("Khung hình: 9:16, 16:9, 1:1, 4:5 hoặc WIDTHxHEIGHT (vd 1920x1080).")
    return int(match[1]), int(match[2])


class RenderOptions(StrictModel):
    width: int = Field(default=720, ge=240, le=3840)
    height: int = Field(default=1280, ge=240, le=3840)
    fps: int = Field(default=24, ge=1, le=60)
    theme: Literal["dark", "light"] = "dark"
    subtitles: bool = True
    scene_gap: float = Field(default=0.3, ge=0, le=3)
    outro_hold: float = Field(default=1.5, ge=0, le=10)
    bgm: str | None = None
    bgm_volume: float = Field(default=0.10, ge=0, le=1)
    sfx: bool = True
    font: str | None = None

    @model_validator(mode="after")
    def dimensions(self):
        if self.width % 2 or self.height % 2:
            raise ValueError("Chiều rộng và cao phải là số chẵn để xuất H.264/yuv420p.")
        if not 0.4 <= self.width / self.height <= 2.5:
            raise ValueError("Tỷ lệ khung hỗ trợ từ 0,4 đến 2,5; khung quá hẹp sẽ khó đọc chữ.")
        if self.width * self.height > 8_294_400:
            raise ValueError("Tối đa 8.294.400 pixel mỗi khung hình (4K).")
        return self


def json_write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
