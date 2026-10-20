from pathlib import Path
import types

import numpy as np
import pytest
from PIL import Image
from streamlit.testing.v1 import AppTest

from studio.models import Script, RenderOptions
from studio.renderer import ScenePainter, VISUAL_STYLES, transition_frame
from studio.writer import parse_response
from studio.ui import video_preview_width

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("style", list(VISUAL_STYLES))
@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("size", [(240, 426), (426, 240), (240, 240), (240, 300)])
def test_every_sample_layout_renders_at_all_ratios(style, theme, size):
    script = Script.read(ROOT / "examples/script-mau.json")
    options = RenderOptions(width=size[0], height=size[1], theme=theme, visual_style=style)
    for i, scene in enumerate(script.scenes):
        painter = ScenePainter(script, scene, i, options, ROOT, {"captions": []})
        frames = [painter.frame(time, time, 10) for time in (.05, .4, 1.8)]
        assert all(frame.size == size and frame.mode == "RGB" for frame in frames)
        assert np.any(np.asarray(frames[0]) != np.asarray(frames[-1]))


@pytest.mark.parametrize("kind", ["fade", "wipe", "slide", "cut"])
def test_transition_endpoints(kind):
    before, after = Image.new("RGB", (100, 60), "red"), Image.new("RGB", (100, 60), "blue")
    assert transition_frame(before, after, 1, kind).tobytes() == after.tobytes()
    if kind != "cut":
        assert transition_frame(before, after, 0, kind).tobytes() == before.tobytes()
        middle = transition_frame(before, after, .5, kind)
        assert middle.tobytes() != before.tobytes()
        assert middle.tobytes() != after.tobytes()


def test_llm_parser_keeps_new_layouts_and_effects():
    script = Script.read(ROOT / "examples/script-mau.json")
    assert parse_response(script.model_dump_json()) == script


def test_sidebar_sample_and_preview(monkeypatch):
    import studio.ui
    monkeypatch.setattr(studio.ui, "voice_preview", lambda settings, directory: b"RIFF-preview")
    app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=20)
    assert not app.exception
    assert {item.label for item in app.sidebar.selectbox} == {
        "Tỷ lệ khung hình", "FPS", "Giao diện", "Chọn giọng đọc"}
    assert not app.sidebar.text_input
    assert len(next(item for item in app.sidebar.selectbox if item.label == "Chọn giọng đọc").options) > 1
    next(button for button in app.button if "Nghe thử" in button.label).click().run()
    assert not app.exception
    assert app.session_state["voice_preview"][1] == b"RIFF-preview"
    next(button for button in app.button if "Mở script mẫu" in button.label).click().run()
    assert not app.exception
    script = Script.model_validate_json(app.session_state["script_editor"])
    assert len(script.scenes) == 8
    next(item for item in app.selectbox if item.label == "Phong cách chuyển động").select("neon").run()
    assert not app.exception


def test_preview_cache_uses_selected_voice(monkeypatch, tmp_path):
    from studio.audio import TtsSettings
    import studio.ui
    import threading
    calls = []
    def engine(settings):
        def synthesize(text, path):
            calls.append(settings.voice)
            path.write_bytes(b"RIFF-test")
        return types.SimpleNamespace(identity={"voice": settings.voice}, synthesize=synthesize), threading.Lock()
    monkeypatch.setattr(studio.ui, "preview_engine", engine)
    for voice in ("Hải Đăng", "Hải Đăng", "Trúc Ly"):
        assert studio.ui.voice_preview(TtsSettings(voice=voice), tmp_path) == b"RIFF-test"
    assert calls == ["Hải Đăng", "Trúc Ly"]


def test_portrait_player_is_compact():
    assert video_preview_width(720, 1280) <= 300
    assert video_preview_width(1280, 720) <= 760
