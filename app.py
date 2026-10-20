from dotenv import load_dotenv
load_dotenv()

from dataclasses import replace
from datetime import datetime
from pathlib import Path
import re
import uuid
import streamlit as st

from studio.audio import TtsSettings
from studio.models import Script, RenderOptions, parse_size
from studio.pipeline import build
from studio.writer import read_source, generate_script
from studio.skills import get_available_skills
from studio.renderer import VISUAL_STYLES, ScenePainter
from studio.ui import apply_theme, voice_preview, video_preview_width
from studio.voices import voice_catalogue

ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT / "examples/script-mau.json"
st.set_page_config(page_title="VieNeu Video Studio", page_icon="🎬", layout="wide")
apply_theme()
st.caption("VIENEU / CREATIVE STUDIO")
st.title("Biến ý tưởng thành video.")
st.caption("Viết câu chuyện của bạn. Chọn một phong cách. Để giọng đọc và chuyển động làm phần còn lại.")
if "job_id" not in st.session_state:
    st.session_state.job_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]

# The compact UI always uses Turbo on CPU; other SDK clients can use .env.
env_tts = replace(TtsSettings.from_env(), mode="v3turbo", backend="onnx", ref_audio="")
with st.sidebar:
    st.markdown("### 🎬 Video Studio")
    st.caption("KHUNG HÌNH & HIỂN THỊ")
    size = st.selectbox("Tỷ lệ khung hình", ["9:16", "16:9", "1:1", "4:5", "Tùy chỉnh"])
    if size == "Tùy chỉnh":
        c1, c2 = st.columns(2)
        width = c1.number_input("Rộng (px)", 240, 3840, 1920, step=2)
        height = c2.number_input("Cao (px)", 240, 3840, 1080, step=2)
        size = f"{width}x{height}"
    c1, c2 = st.columns(2)
    fps = c1.selectbox("FPS", [24, 30, 60])
    theme = c2.selectbox("Giao diện", ["dark", "light"], format_func=lambda x: "Tối" if x == "dark" else "Sáng")
    st.divider()
    st.caption("GIỌNG ĐỌC")
    voices = voice_catalogue()
    voice_ids = [v.id for v in voices]
    voice_map = {v.id: v for v in voices}
    default_voice = env_tts.voice if env_tts.voice in voice_ids else "Hải Đăng"
    voice = st.selectbox("Chọn giọng đọc", voice_ids,
        index=voice_ids.index(default_voice) if default_voice in voice_ids else 0,
        format_func=lambda v: ("★ " if voice_map[v].featured else "") + v)
    with st.container(border=True):
        st.markdown(f"**{voice}**")
        st.caption(voice_map[voice].description or "Giọng đọc tiếng Việt")
        if st.button("▶ Nghe thử giọng này", use_container_width=True):
            try:
                with st.spinner("Đang tạo đoạn nghe thử; lần đầu có thể tải model…"):
                    audio = voice_preview(replace(env_tts, voice=voice), ROOT / "output/voice-previews")
                st.session_state.voice_preview = (voice, audio)
            except Exception as exc:
                st.error(str(exc))
        preview = st.session_state.get("voice_preview")
        if preview and preview[0] == voice:
            st.audio(preview[1], format="audio/wav")
    st.caption("Đoạn nghe thử được lưu để nghe lại nhanh hơn.")
    st.divider()
    st.link_button("↗ Lấy Gemini API key", "https://aistudio.google.com/apikey", use_container_width=True)
    st.caption("Dán key vào GEMINI_API_KEY trong file .env, rồi khởi động lại ứng dụng.")

left, right = st.columns([1, 1], gap="large")
with left:
    st.subheader("01 / Nội dung")
    kind = st.radio("Nguồn", ["Chủ đề", "Văn bản", "URL", "File .txt/.md"], horizontal=True)
    file = None
    if kind == "File .txt/.md":
        file = st.file_uploader("Tài liệu nguồn", type=["txt", "md"])
        content = ""
    else:
        content = st.text_area("Nội dung" if kind != "URL" else "Đường dẫn bài viết", height=160,
            placeholder="Ví dụ: Ba bước để biến một ý tưởng thành video chia sẻ kiến thức")
    skills_list = get_available_skills(ROOT)
    skill_map = {s.id: s for s in skills_list}
    selected_skill_id = st.selectbox("Phong cách biên tập", list(skill_map),
        format_func=lambda x: skill_map[x].name)
    if skill_map[selected_skill_id].description:
        st.caption(skill_map[selected_skill_id].description)
    channel = st.text_input("Tên kênh", "Góc kiến thức")
    c1, c2 = st.columns(2)
    seconds = c1.slider("Thời lượng mục tiêu (giây)", 15, 300, 60, 5)
    scenes = c2.slider("Số cảnh", 3, 12, 5)
    style = st.text_input("Ghi chú phong cách bổ sung", "Rõ ràng, gần gũi, dễ hiểu")
    auto = st.checkbox("Tạo video ngay sau khi AI viết xong", False)
    create = st.button("✨ AI viết kịch bản", type="primary", use_container_width=True)
    with st.expander("Bắt đầu từ kịch bản mẫu"):
        sample = st.button("Mở script mẫu — xem đủ bố cục và hiệu ứng", use_container_width=True)
        excel_sample = st.button("Mở kịch bản Excel mẫu — không gọi AI", use_container_width=True)
        st.download_button("↓ Tải script mẫu", SAMPLE.read_bytes(), file_name="script-mau.json", mime="application/json")
        st.caption("Mẫu có lời đọc, chữ trên hình và hiệu ứng riêng từng cảnh. Có thể dùng ngay, không cần gọi AI.")

auto_build = False
if sample or excel_sample:
    source_path = SAMPLE if sample else ROOT / "examples/excel.json"
    st.session_state.script_editor = source_path.read_text(encoding="utf-8")
    st.session_state.script_base = str(ROOT / "examples")
    st.session_state.pop("video_result", None)
if create:
    try:
        w, h = parse_size(size)
        RenderOptions(width=w, height=h, fps=fps)
        if kind == "File .txt/.md":
            if file is None:
                raise ValueError("Hãy chọn file nguồn.")
            source = read_source(text=file.getvalue().decode("utf-8-sig"))
        elif kind == "URL":
            source = read_source(url=content.strip())
        else:
            source = read_source(text=content)
        with st.spinner("AI đang viết và kiểm tra cấu trúc kịch bản…"):
            script = generate_script(source, mode="topic" if kind == "Chủ đề" else "source",
                seconds=seconds, scene_count=scenes, channel=channel, style=style,
                source_label=content.strip() if kind == "URL" else (file.name if file else ""),
                skill=selected_skill_id)
        st.session_state.script_editor = script.model_dump_json(indent=2)
        st.session_state.script_base = str(ROOT)
        st.session_state.pop("video_result", None)
        auto_build = auto
    except Exception as exc:
        st.error(str(exc))

with right:
    st.subheader("02 / Kịch bản")
    uploaded = st.file_uploader("Mở script.json đã lưu", type=["json"])
    if uploaded and st.button("Nạp JSON này"):
        try:
            checked = Script.model_validate_json(uploaded.getvalue().decode("utf-8-sig"))
            st.session_state.script_editor = checked.model_dump_json(indent=2)
            st.session_state.script_base = str(ROOT)
        except Exception as exc:
            st.error(str(exc))
    text = st.text_area("Kịch bản JSON — sửa lời đọc, chữ và bố cục", key="script_editor", height=410)
    checked = None
    if text.strip():
        try:
            checked = Script.model_validate_json(text)
            st.success(f"{checked.title} · {len(checked.scenes)} cảnh")
            with st.expander("Đọc kịch bản dạng dễ xem"):
                for scene in checked.scenes:
                    st.markdown(f"**{scene.title}** · {scene.layout}")
                    st.write(" ".join(line.text for line in scene.narration))
            st.download_button("↓ Tải script.json", text, file_name="script.json", mime="application/json")
        except Exception as exc:
            st.warning(f"JSON chưa hợp lệ: {exc}")
    else:
        st.info("Viết bằng AI hoặc mở script mẫu để bắt đầu.")

st.divider()
st.subheader("03 / Phong cách hình ảnh")
design, preview_col = st.columns([1, 1], gap="large")
with design:
    visual_style = st.selectbox("Phong cách chuyển động", list(VISUAL_STYLES),
        format_func=lambda x: VISUAL_STYLES[x][0])
    st.caption(VISUAL_STYLES[visual_style][1])
    st.caption("Hiệu ứng tự động theo phong cách. Có thể đặt animation và transition riêng cho từng cảnh trong JSON.")
    with st.expander("Âm thanh & tùy chọn bổ sung"):
        subtitles = st.checkbox("Hiện phụ đề theo đoạn", True)
        sfx = st.checkbox("Âm chuyển cảnh nhẹ", True)
        reference = st.file_uploader("Giọng mẫu tùy chọn (thay preset)", type=["wav", "mp3", "flac"])
        music = st.file_uploader("Nhạc nền tùy chọn", type=["mp3", "wav", "m4a", "flac"])
        music_volume = st.slider("Âm lượng nhạc nền", 0.0, 1.0, 0.10, 0.01)
with preview_col:
    try:
        preview_script = checked or Script.read(SAMPLE)
        scene_ids = [s.id for s in preview_script.scenes]
        preview_id = st.selectbox("Xem trước bố cục", scene_ids,
            format_func=lambda value: next(s.title for s in preview_script.scenes if s.id == value))
        index = scene_ids.index(preview_id)
        w, h = parse_size(size)
        RenderOptions(width=w, height=h)
        scale = min(1, 480 / max(w, h))
        scale = max(scale, 240 / min(w, h))
        pw, ph = round(w*scale/2)*2, round(h*scale/2)*2
        painter = ScenePainter(preview_script, preview_script.scenes[index], index,
            RenderOptions(width=pw, height=ph, theme=theme, visual_style=visual_style),
            Path(st.session_state.get("script_base", str(ROOT))), {"captions": []})
        st.image(painter.frame(1.8, 1.8, 10), width=min(360, pw))
        st.caption("Ảnh xem trước bố cục và màu sắc; chuyển động được áp dụng khi render.")
    except Exception as exc:
        st.warning(f"Chưa thể xem trước: {exc}")

st.divider()
st.subheader("04 / Xuất video")
with st.expander("Thư mục kết quả"):
    job = st.text_input("Tên thư mục kết quả", st.session_state.job_id)
    st.caption("Dùng lại tên để tái sử dụng audio; đổi tên để tạo phiên bản riêng.")
render = st.button("🎬 Tạo giọng đọc và render video", type="primary", disabled=checked is None)
if render or auto_build:
    try:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", job):
            raise ValueError("Tên thư mục chỉ gồm chữ không dấu, số, dấu - hoặc _.")
        script = Script.model_validate_json(text)
        w, h = parse_size(size)
        output = ROOT / "output" / job
        upload_dir = output / "inputs"
        upload_dir.mkdir(parents=True, exist_ok=True)
        ref_path = TtsSettings.from_env().ref_audio
        if reference:
            ref = upload_dir / ("reference" + Path(reference.name).suffix.lower())
            ref.write_bytes(reference.getvalue())
            ref_path = str(ref)
        music_path = None
        if music:
            path = upload_dir / ("music" + Path(music.name).suffix.lower())
            path.write_bytes(music.getvalue())
            music_path = str(path)
        options = RenderOptions(width=w, height=h, fps=fps, theme=theme, visual_style=visual_style,
            subtitles=subtitles, sfx=sfx, bgm=music_path, bgm_volume=music_volume)
        settings = replace(env_tts, voice=voice, ref_audio=ref_path)
        status = st.empty()
        with st.spinner("Đang tạo audio và video; model có thể được tải ở lần chạy đầu…"):
            result = build(script, output, options, settings,
                source_dir=Path(st.session_state.get("script_base", str(ROOT))), progress=status.info)
        st.session_state.video_result = str(result)
        st.session_state.video_dimensions = (w, h)
        st.success("Video đã hoàn tất.")
    except Exception as exc:
        st.session_state.pop("video_result", None)
        st.error(str(exc))

if st.session_state.get("video_result"):
    video = Path(st.session_state.video_result)
    if video.is_file():
        st.subheader("Video của bạn")
        vw, vh = st.session_state.get("video_dimensions", (720, 1280))
        with st.container(width=video_preview_width(vw, vh)):
            st.video(str(video))
        downloads = st.columns(3)
        for col, (name, label, mime) in zip(downloads, [
            ("video.mp4", "↓ Tải video", "video/mp4"),
            ("subtitles.srt", "↓ Tải phụ đề", "text/plain"),
            ("narration.wav", "↓ Tải giọng đọc", "audio/wav")]):
            path = video.parent / name
            if path.is_file():
                col.download_button(label, path.read_bytes(), file_name=name, mime=mime)
