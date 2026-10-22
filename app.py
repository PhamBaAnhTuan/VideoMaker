from dotenv import load_dotenv
load_dotenv()

from dataclasses import replace
from datetime import datetime
from pathlib import Path
import re
import uuid
import streamlit as st
import json
import sys
import traceback

# Import các module hiện có của bạn
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

# ==========================================
# 1. CẤU HÌNH TRANG & CSS TÙY CHỈNH
# ==========================================
st.set_page_config(page_title="VieNeu Video Studio", page_icon="🎬", layout="wide")

st.markdown("""
<style>
    :root {
        --primary-color: #00875A;
        --bg-color: #F4F5F7;
        --card-bg: #FFFFFF;
        --text-color: #172B4D;
        --border-color: #C1C7D0;
    }
    .stApp { background-color: var(--bg-color); }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px !important;
        border: 1px solid var(--border-color) !important;
        background-color: var(--card-bg) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
        padding: 1.5rem !important;
        margin-bottom: 1rem !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #A5ADBA !important;
        transition: border-color 0.3s ease;
    }
    .stTextInput > div > div > input, .stSelectbox > div > div > div, .stTextArea > div > div > textarea {
        border-radius: 8px !important;
        border: 1px solid #DFE1E6 !important;
        background-color: #FAFBFC !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 2px rgba(0, 135, 90, 0.2) !important;
        background-color: #FFFFFF !important;
    }
    .stButton > button[kind="primary"] {
        background-color: var(--primary-color) !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0, 135, 90, 0.2);
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #006644 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0, 135, 90, 0.3);
    }
    .stButton > button {
        border-radius: 8px !important;
        border: 1px solid #DFE1E6 !important;
        color: var(--text-color) !important;
        background-color: #FFFFFF !important;
    }
    h3 {
        color: var(--text-color) !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        margin-bottom: 1rem !important;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #EBECF0;
    }
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid var(--border-color);
        box-shadow: 2px 0 5px rgba(0,0,0,0.02);
    }
</style>
""", unsafe_allow_html=True)

apply_theme()

# Khởi tạo session state
if "job_id" not in st.session_state:
    st.session_state.job_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
if "script_editor" not in st.session_state:
    st.session_state.script_editor = ""
if "script_base" not in st.session_state:
    st.session_state.script_base = str(ROOT)
if "voice_preview_audio" not in st.session_state:
    st.session_state.voice_preview_audio = None
if "current_voice" not in st.session_state:
    st.session_state.current_voice = None

# ==========================================
# 2. SIDEBAR: CẤU HÌNH CHUNG
# ==========================================
env_tts = replace(TtsSettings.from_env(), mode="v3turbo", backend="onnx", ref_audio="")

with st.sidebar:
    st.markdown("### 🎬 Video Studio")
    st.caption("THIẾT LẬP VIDEO")
    
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
                with st.spinner("Đang tạo đoạn nghe thử..."):
                    audio = voice_preview(replace(env_tts, voice=voice), ROOT / "output/voice-previews")
                st.session_state.voice_preview_audio = audio
                st.session_state.current_voice = voice
            except Exception as exc:
                st.error(f"Lỗi tạo audio: {exc}")
        
        if st.session_state.voice_preview_audio and st.session_state.current_voice == voice:
            st.audio(st.session_state.voice_preview_audio, format="audio/wav")

# ==========================================
# 3. GIAO DIỆN CHÍNH
# ==========================================
st.title("Biến ý tưởng thành video.")
st.caption("Viết câu chuyện của bạn. Chọn một phong cách. Để giọng đọc và chuyển động làm phần còn lại.")

col_left, col_right = st.columns([1, 1], gap="large")

# --- CỘT TRÁI: INPUT ---
with col_left:
    with st.container(border=True):
        st.markdown("### 01 / Nội dung đầu vào")
        
        kind = st.radio("Nguồn dữ liệu", ["Chủ đề", "Văn bản", "URL", "File .txt/.md"], horizontal=True)
        
        content, file = "", None
        if kind == "File .txt/.md":
            file = st.file_uploader("Tài liệu nguồn", type=["txt", "md"])
        elif kind == "URL":
            content = st.text_input("Đường dẫn bài viết", placeholder="https://...")
        else:
            content = st.text_area("Nội dung", height=150, placeholder="Nhập nội dung hoặc chủ đề...")
            
        skills_list = get_available_skills(ROOT)
        skill_map = {s.id: s for s in skills_list}
        selected_skill_id = st.selectbox("Phong cách biên tập", list(skill_map), format_func=lambda x: skill_map[x].name)
            
        c1, c2 = st.columns(2)
        channel = c1.text_input("Tên kênh", "Góc kiến thức")
        style = c2.text_input("Ghi chú phong cách", "Rõ ràng, gần gũi")
        
        c3, c4 = st.columns(2)
        seconds = c3.slider("Thời lượng (giây)", 15, 300, 60, 5)
        scenes = c4.slider("Số bối cảnh", 3, 20, 5)
        
        create_btn = st.button("✨ AI viết kịch bản", type="primary", use_container_width=True)
        
        with st.expander("Bắt đầu từ kịch bản mẫu"):
            if st.button("Mở script mẫu", use_container_width=True):
                st.session_state.script_editor = SAMPLE.read_text(encoding="utf-8")
                st.session_state.script_base = str(ROOT / "examples")

# --- CỘT PHẢI: KỊCH BẢN ---
with col_right:
    with st.container(border=True):
        st.markdown("### 02 / Kịch bản & Chỉnh sửa")
        uploaded = st.file_uploader("Mở script.json đã lưu", type=["json"])
        if uploaded and st.button("Nạp JSON này"):
            try:
                checked = Script.model_validate_json(uploaded.getvalue().decode("utf-8-sig"))
                st.session_state.script_editor = checked.model_dump_json(indent=2)
                st.session_state.script_base = str(ROOT)
            except Exception as exc:
                st.error(f"Lỗi định dạng JSON: {exc}")
                
        text = st.text_area("Kịch bản JSON — sửa trực tiếp", key="script_editor", height=300)
        
        checked = None
        if text.strip():
            try:
                checked = Script.model_validate_json(text)
                st.success(f"✅ {checked.title} · {len(checked.scenes)} cảnh")
                with st.expander("Xem kịch bản dạng văn bản"):
                    for i, scene in enumerate(checked.scenes):
                        st.markdown(f"**Cảnh {i+1}: {scene.title}**")
                        st.info(" ".join(line.text for line in scene.narration))
            except Exception as exc:
                st.warning(f"JSON chưa hợp lệ: {exc}")

# ==========================================
# 4. PHONG CÁCH, TEMPLATE & XUẤT VIDEO
# ==========================================
st.divider()

# Định nghĩa các Template
TEMPLATES = {
    "modern": "Modern Kinetic (Chữ động, hiện đại - Phù hợp TikTok/Reels)",
    "cinematic": "Cinematic Parallax (Điện ảnh, chuyển động 3D - Phù hợp kể chuyện)",
    "neon_glitch": "Neon Glitch (Công nghệ, Cyberpunk - Phù hợp AI/Gaming)",
    "minimal": "Minimal Clean (Tối giản, sang trọng - Phù hợp Doanh nghiệp)"
}

with st.container(border=True):
    st.markdown("### 03 / Phong cách & Template")
    c_style, c_preview = st.columns([1, 1], gap="large")
    
    with c_style:
        visual_style = st.selectbox("Phong cách chuyển động", list(VISUAL_STYLES), format_func=lambda x: VISUAL_STYLES[x][0])
        
        # --- CHỌN TEMPLATE ---
        selected_template = st.selectbox(
            "Mẫu hiệu ứng (Template)", 
            list(TEMPLATES.keys()), 
            format_func=lambda x: TEMPLATES[x]
        )
        
        bgm_url = st.text_input("Link Youtube nhạc nền (Tùy chọn)", placeholder="https://...")
        st.caption("Hệ thống sẽ tự động tải và gắn nhạc nền từ link này (nếu có).")
        
        with st.expander("Tùy chọn bổ sung"):
            subtitles = st.checkbox("Hiện phụ đề", True)
            sfx = st.checkbox("Âm chuyển cảnh", True)
            music_volume = st.slider("Âm lượng nhạc nền", 0.0, 1.0, 0.10, 0.01)

    with c_preview:
        try:
            preview_script = checked or Script.read(SAMPLE)
            scene_ids = [s.id for s in preview_script.scenes]
            preview_id = st.selectbox("Xem trước bố cục", scene_ids, format_func=lambda v: next(s.title for s in preview_script.scenes if s.id == v))
            index = scene_ids.index(preview_id)
            w, h = parse_size(size)
            scale = min(1, 480 / max(w, h))
            pw, ph = round(w*scale/2)*2, round(h*scale/2)*2
            painter = ScenePainter(preview_script, preview_script.scenes[index], index, RenderOptions(width=pw, height=ph, theme=theme, visual_style=visual_style), Path(st.session_state.get("script_base", str(ROOT))), {"captions": []})
            st.image(painter.frame(1.8, 1.8, 10), width=min(360, pw))
            st.caption("Ảnh xem trước bố cục và màu sắc.")
        except Exception as exc:
            st.warning(f"Chưa thể xem trước: {exc}")

with st.container(border=True):
    st.markdown("### 04 / Xuất video")
    job_name = st.text_input("Tên thư mục kết quả", st.session_state.job_id)
    render_btn = st.button("🎬 Tạo giọng đọc và Render Video", type="primary", disabled=checked is None, use_container_width=True)


# ==========================================
# 5. XỬ LÝ LOGIC (LOG & BẮT LỖI)
# ==========================================

# Hàm hiển thị lỗi chi tiết
def show_error_details(error_msg, exc_info):
    st.error(f"❌ Đã xảy ra lỗi: {error_msg}")
    with st.expander("🔍 Xem chi tiết lỗi (Debug)"):
        st.code("".join(traceback.format_exception(*exc_info)), language="python")

# --- LOGIC TẠO KỊCH BẢN AI ---
if create_btn:
    with st.status("🤖 AI đang xử lý kịch bản...", expanded=True) as status:
        log_area = st.empty()
        log_area.markdown("> Đang khởi tạo kết nối...")
        
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
                
            log_area.markdown("> Đang gửi yêu cầu tới AI...")
            
            script = generate_script(
                source, mode="topic" if kind == "Chủ đề" else "source",
                seconds=seconds, scene_count=scenes, channel=channel, style=style,
                source_label=content.strip() if kind == "URL" else (file.name if file else ""),
                skill=selected_skill_id
            )
            
            st.session_state.script_editor = script.model_dump_json(indent=2)
            st.session_state.script_base = str(ROOT)
            st.session_state.pop("video_result", None)
            
            status.update(label="✅ Tạo kịch bản thành công!", state="complete", expanded=False)
            st.rerun()
            
        except Exception as e:
            status.update(label="❌ Lỗi khi tạo kịch bản", state="error", expanded=True)
            log_area.markdown(f"> **Lỗi:** {str(e)}")
            show_error_details(str(e), sys.exc_info())

# --- LOGIC RENDER VIDEO ---
if render_btn:
    with st.status("🎬 Hệ thống đang Render Video...", expanded=True) as status:
        log_container = st.empty()
        logs = []
        
        def ui_progress_callback(msg):
            timestamp = datetime.now().strftime("%H:%M:%S")
            logs.append(f"[{timestamp}] {msg}")
            # Hiển thị 10 dòng log gần nhất
            log_container.markdown(
                f"<div style='font-family: monospace; font-size: 0.85rem; background: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #e0e0e0; height: 200px; overflow-y: auto;'>{'<br>'.join(logs[-10:])}</div>", 
                unsafe_allow_html=True
            )
            
        try:
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", job_name):
                raise ValueError("Tên thư mục chỉ gồm chữ không dấu, số, dấu - hoặc _.")
                
            script = Script.model_validate_json(text)
            w, h = parse_size(size)
            output = ROOT / "output" / job_name
            output.mkdir(parents=True, exist_ok=True)
            
            # Xử lý nhạc nền (nếu có)
            music_path = None
            if bgm_url:
                ui_progress_callback("Đang xử lý link nhạc nền Youtube...")
                # TODO: Tích hợp hàm tải nhạc tại đây
                # music_path = download_youtube_audio(bgm_url, output)
                ui_progress_callback("Cảnh báo: Tính năng tải nhạc từ URL chưa được cấu hình.")
            
            # --- TRUYỀN TEMPLATE VÀO ĐÂY ---
            options = RenderOptions(
                width=w, height=h, fps=fps, theme=theme, visual_style=visual_style,
                template=selected_template, 
                subtitles=subtitles, sfx=sfx, bgm=music_path, bgm_volume=music_volume
            )
            settings = replace(env_tts, voice=voice, ref_audio="")
            
            ui_progress_callback("Bắt đầu gọi pipeline.build()...")
            
            # Gọi pipeline (truyền callback log)
            result = build(
                script, output, options, settings,
                source_dir=Path(st.session_state.get("script_base", str(ROOT))), 
                progress=ui_progress_callback
            )
            
            st.session_state.video_result = str(result)
            st.session_state.video_dimensions = (w, h)
            
            status.update(label="✅ Render Video thành công!", state="complete", expanded=False)
            st.rerun()
            
        except Exception as e:
            status.update(label="❌ Lỗi trong quá trình Render", state="error", expanded=True)
            ui_progress_callback(f"LỖI NGHIÊM TRỌNG: {str(e)}")
            show_error_details(str(e), sys.exc_info())

# Hiển thị kết quả
if st.session_state.get("video_result"):
    video = Path(st.session_state.video_result)
    if video.is_file():
        with st.container(border=True):
            st.markdown("### 🎉 Video của bạn đã sẵn sàng")
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
                    col.download_button(label, path.read_bytes(), file_name=name, mime=mime, use_container_width=True)