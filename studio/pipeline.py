from __future__ import annotations

import hashlib
import shutil
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
from .audio import VieNeuSpeech, TtsSettings, make_audio
from .models import Script, RenderOptions, json_write
from .renderer import render_video


@contextmanager
def output_lock(output: Path):
    output.mkdir(parents=True, exist_ok=True)
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
            destination.parent.mkdir(parents=True, exist_ok=True)
            if image != destination.resolve():
                shutil.copyfile(image, destination)
            scene.image = relative.as_posix()
    return result


def build(script: Script, output: Path, options: RenderOptions | None = None,
          settings: TtsSettings | None = None, *, source_dir: Path | None = None,
          engine=None, progress=print) -> Path:
    
    options = options or RenderOptions()
    output = output.expanduser().resolve()
    
    # Hàm wrapper để ghi log ra file status.json và gọi callback của UI
    def log_progress(message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        # Ghi ra file status.json để UI có thể poll (nếu cần)
        # Cấu trúc: {"state": "running", "logs": ["...", "..."]}
        status_file = output / "status.json"
        current_status = {"state": "running", "logs": []}
        if status_file.exists():
            try:
                import json
                current_status = json.loads(status_file.read_text(encoding="utf-8"))
            except:
                pass
        
        current_status["logs"].append(log_entry)
        # Giữ tối đa 50 dòng log để file không quá nặng
        if len(current_status["logs"]) > 50:
            current_status["logs"] = current_status["logs"][-50:]
            
        json_write(status_file, current_status)
        
        # Gọi callback gốc (in ra terminal hoặc cập nhật Streamlit)
        if progress:
            progress(message)

    with output_lock(output):
        log_progress("Bắt đầu quá trình render...")
        
        # Khởi tạo engine TTS
        engine = engine if engine is not None else VieNeuSpeech(settings or TtsSettings.from_env())
        
        log_progress("Đang chuẩn bị script và tài nguyên...")
        prepared = portable_script(script, source_dir or Path.cwd(), output)
        prepared.write(output / "script.json")
        json_write(output / "render-options.json", options.model_dump())
        
        # Ghi status ban đầu
        json_write(output / "status.json", {"state": "running", "logs": [f"[{datetime.now().strftime('%H:%M:%S')}] Khởi tạo..."]})
        
        try:
            log_progress("Đang tạo audio (TTS)...")
            # Truyền options (chứa template) vào make_audio nếu cần
            timeline = make_audio(prepared, options, output, engine, log_progress)
            
            log_progress("Đang render video (ghép hình, hiệu ứng, template)...")
            # Truyền options (chứa template) vào render_video
            result = render_video(prepared, timeline, options, output, log_progress)
            
            log_progress("Hoàn tất render video.")
            
        except BaseException as e:
            error_msg = f"Lỗi: {str(e)}"
            log_progress(error_msg)
            json_write(output / "status.json", {
                "state": "failed", 
                "logs": [error_msg],
                "note": "Xem lỗi trong terminal. Video cũ, nếu có, không phải kết quả lần chạy này."
            })
            raise
        
        # Ghi status thành công
        json_write(output / "status.json", {
            "state": "complete", 
            "video": result.name,
            "test_audio": timeline["test_audio"], 
            "duration": timeline["duration"],
            "logs": ["Hoàn tất!"]
        })
        
        return result