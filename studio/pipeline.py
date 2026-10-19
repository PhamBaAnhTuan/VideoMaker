from __future__ import annotations

import hashlib
import shutil
from contextlib import contextmanager
from pathlib import Path
from .audio import VieNeuSpeech, TtsSettings, make_audio
from .models import Script, RenderOptions, json_write
from .renderer import render_video


@contextmanager
def output_lock(output: Path):
    output.mkdir(parents=True,exist_ok=True)
    path = output / ".render.lock"
    try:
        handle = path.open("x")
    except FileExistsError as exc:
        raise RuntimeError("Thư mục này đang chạy. Chọn thư mục khác; nếu lần trước bị tắt đột ngột, xóa .render.lock.") from exc
    try:
        with handle:
            handle.write("render in progress\n")
        yield
    finally:
        path.unlink(missing_ok=True)


def portable_script(script: Script, base: Path, output: Path) -> Script:
    result = script.model_copy(deep=True)
    for scene in result.scenes:
        if scene.image:
            image = Path(scene.image).expanduser()
            image = image if image.is_absolute() else base / image
            image = image.resolve()
            if not image.is_file():
                raise ValueError(f"Không tìm thấy ảnh cảnh {scene.id}: {image}")
            digest = hashlib.sha256(image.read_bytes()).hexdigest()[:20]
            relative = Path("assets") / f"{digest}{image.suffix.lower()}"
            destination = output / relative
            destination.parent.mkdir(parents=True,exist_ok=True)
            if image != destination.resolve():
                shutil.copyfile(image,destination)
            scene.image = relative.as_posix()
    return result


def build(script: Script, output: Path, options: RenderOptions | None = None,
          settings: TtsSettings | None = None, *, source_dir: Path | None = None,
          engine=None, progress=print) -> Path:
    options = options or RenderOptions()
    output = output.expanduser().resolve()
    with output_lock(output):
        # Keep the real TTS default even when an external service fails.
        engine = engine if engine is not None else VieNeuSpeech(settings or TtsSettings.from_env())
        prepared = portable_script(script,source_dir or Path.cwd(),output)
        prepared.write(output / "script.json")
        json_write(output / "render-options.json",options.model_dump())
        json_write(output / "status.json",{"state":"running"})
        try:
            timeline = make_audio(prepared,options,output,engine,progress)
            result = render_video(prepared,timeline,options,output,progress)
        except BaseException:
            json_write(output / "status.json",{"state":"failed","note":"Xem lỗi trong terminal. Video cũ, nếu có, không phải kết quả lần chạy này."})
            raise
        json_write(output / "status.json",{"state":"complete","video":result.name,
                                          "test_audio":timeline["test_audio"],"duration":timeline["duration"]})
        return result
