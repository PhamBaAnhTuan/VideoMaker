from dotenv import load_dotenv
load_dotenv()

from dataclasses import replace
from datetime import datetime
from pathlib import Path
import re
import uuid
import streamlit as st
import json

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
# 1. CẤU HÌNH TRANG & CSS TÙY CHỈNH (LÀM RÕ BORDER)
# ==========================================
st.set_page_config(page_title="VieNeu Video Studio", page_icon="🎬", layout="wide")

st.markdown("""
<style>
    /* Tông màu chủ đạo */
    :root {
        --primary-color: #00875A; /* Xanh lá giống HRM */
        --bg-color: #F4F5F7;      /* Nền xám nhạt tổng thể */
        --card-bg: #FFFFFF;       /* Nền trắng cho các box */
        --text-color: #172B4D;
        --border-color: #C1C7D0;  /* Màu viền đậm hơn để rõ nét */
    }
    
    /* Nền tổng thể */
    .stApp {
        background-color: var(--bg-color);
    }
    
    /* === LÀM RÕ BORDER CÁC CONTAINER (BOX) === */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px !important;
        border: 1px solid var(--border-color) !important; /* Viền rõ hơn */
        background-color: var(--card-bg) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important; /* Đổ bóng nổi khối */
        padding: 1.5rem !important;
        margin-bottom: 1rem !important;
    }
    
    /* Hiệu ứng hover cho các box để tăng tương tác */
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #A5ADBA !important;
        transition: border-color 0.3s ease;
    }

    /* Style cho Input/Select */
    .stTextInput > div > div > input, .stSelectbox > div > div > div, .stTextArea > div > div > textarea {
        border-radius: 8px !important;
        border: 1px solid #DFE1E6 !important;
        background-color: #FAFBFC !important;
    }
    .stTextInput > div > div > input:focus, .stSelectbox > div > div > div:focus {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 2px rgba(0, 135, 90, 0.2) !important;
        background-color: #FFFFFF !important;
    }
    
    /* Nút bấm chính */
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
    
    /* Nút phụ */
    .stButton > button {
        border-radius: 8px !important;
        border: 1px solid #DFE1E6 !important;
        color: var(--text-color) !important;
        background-color: #FFFFFF !important;
    }
    
    /* Tiêu đề Section */
    h3 {
        color: var(--text-color) !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        margin-bottom: 1rem !important;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #EBECF0; /* Gạch chân tiêu đề */
    }
    
    /* Làm đẹp sidebar */
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
    
    # Tỷ lệ khung hình
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
    
    # Giọng đọc
    st.caption("GIỌNG ĐỌC")
    voices = voice_catalogue()
    voice_ids = [v.id for v in voices]
    voice_map = {v.id: v for v in voices}
    default_voice = env_tts.voice if env_tts.voice in voice_ids else "Hải Đăng"
    
    voice = st.selectbox("Chọn giọng đọc", voice_ids,
        index=voice_ids.index(default_voice) if default_voice in voice_ids else 0,
        format_func=lambda v: ("★ " if voice_map[v].featured else "") + v)
    
    # Box giọng đọc có border rõ
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
                st.error(str(exc))
        
        if st.session_state.voice_preview_audio and st.session_state.current_voice == voice:
            st.audio(st.session_state.voice_preview_audio, format="audio/wav")

# ==========================================
# 3. GIAO DIỆN CHÍNH
# ==========================================
st.title("Biến ý tưởng thành video.")
st.caption("Viết câu chuyện của bạn. Chọn một phong cách. Để giọng đọc và chuyển động làm phần còn lại.")

col_left, col_right = st.columns([1, 1], gap="large")

# --- CỘT TRÁI: INPUT & CẤU HÌNH NỘI DUNG ---
with col_left:
    with st.container(border=True):
        st.markdown("### 01 / Nội dung đầu vào")
        
        kind = st.radio("Nguồn dữ liệu", ["Chủ đề", "Văn bản", "URL", "File .txt/.md"], horizontal=True)
        
        content = ""
        file = None
        if kind == "File .txt/.md":
            file = st.file_uploader("Tài liệu nguồn", type=["txt", "md"])
        elif kind == "URL":
            content = st.text_input("Đường dẫn bài viết", placeholder="https://...")
        else:
            content = st.text_area("Nội dung", height=150, placeholder="Nhập nội dung hoặc chủ đề bạn muốn tạo video...")
            
        skills_list = get_available_skills(ROOT)
        skill_map = {s.id: s for s in skills_list}
        selected_skill_id = st.selectbox("Phong cách biên tập", list(skill_map),
            format_func=lambda x: skill_map[x].name)
        if skill_map[selected_skill_id].description:
            st.caption(skill_map[selected_skill_id].description)
            
        c1, c2 = st.columns(2)
        channel = c1.text_input("Tên kênh", "Góc kiến thức")
        style = c2.text_input("Ghi chú phong cách", "Rõ ràng, gần gũi, dễ hiểu")
        
        c3, c4 = st.columns(2)
        seconds = c3.slider("Thời lượng mục tiêu (giây)", 15, 300, 60, 5)
        scenes = c4.slider("Số bối cảnh (tối đa 20)", 3, 20, 5)
        
        create_btn = st.button("✨ AI viết kịch bản", type="primary", use_container_width=True)
        
        with st.expander("Bắt đầu từ kịch bản mẫu"):
            if st.button("Mở script mẫu", use_container_width=True):
                st.session_state.script_editor = SAMPLE.read_text(encoding="utf-8")
                st.session_state.script_base = str(ROOT / "examples")
            st.download_button("↓ Tải script mẫu", SAMPLE.read_bytes(), file_name="script-mau.json", mime="application/json")

# --- CỘT PHẢI: KỊCH BẢN (JSON & PREVIEW) ---
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
                
                with st.expander("Xem kịch bản dạng văn bản (Dễ đọc)"):
                    for i, scene in enumerate(checked.scenes):
                        st.markdown(f"**Cảnh {i+1}: {scene.title}** · *Layout: {scene.layout}*")
                        st.info(" ".join(line.text for line in scene.narration))
                        st.divider()
                        
                st.download_button("↓ Tải script.json", text, file_name="script.json", mime="application/json")
            except Exception as exc:
                st.warning(f"JSON chưa hợp lệ: {exc}")
        else:
            st.info("Vui lòng nhập nội dung bên trái và nhấn 'AI viết kịch bản', hoặc tải file JSON lên.")

# ==========================================
# 4. PHONG CÁCH & XUẤT VIDEO
# ==========================================
st.divider()

with st.container(border=True):
    st.markdown("### 03 / Phong cách & Âm thanh nền")
    c_style, c_preview = st.columns([1, 1], gap="large")
    
    with c_style:
        visual_style = st.selectbox("Phong cách chuyển động", list(VISUAL_STYLES),
            format_func=lambda x: VISUAL_STYLES[x][0])
        st.caption(VISUAL_STYLES[visual_style][1])
        
        bgm_url = st.text_input("Link Youtube nhạc nền (Tùy chọn)", placeholder="https://www.youtube.com/watch?v=...")
        st.caption("Hệ thống sẽ tự động tải và gắn nhạc nền từ link này (nếu có).")
        
        with st.expander("Tùy chọn bổ sung"):
            subtitles = st.checkbox("Hiện phụ đề theo đoạn", True)
            sfx = st.checkbox("Âm chuyển cảnh nhẹ", True)
            music_volume = st.slider("Âm lượng nhạc nền", 0.0, 1.0, 0.10, 0.01)

    with c_preview:
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
            st.caption("Ảnh xem trước bố cục và màu sắc.")
        except Exception as exc:
            st.warning(f"Chưa thể xem trước: {exc}")

# --- XUẤT VIDEO ---
with st.container(border=True):
    st.markdown("### 04 / Xuất video")
    
    job_name = st.text_input("Tên thư mục kết quả", st.session_state.job_id, 
                             help="Chỉ gồm chữ không dấu, số, dấu - hoặc _")
    
    render_btn = st.button("🎬 Tạo giọng đọc và Render Video", type="primary", disabled=checked is None, use_container_width=True)

# ==========================================
# 5. XỬ LÝ LOGIC (LOADING & RENDER)
# ==========================================

# Logic tạo kịch bản AI
if create_btn:
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
            
        with st.spinner("AI đang viết và kiểm tra cấu trúc kịch bản..."):
            script = generate_script(source, mode="topic" if kind == "Chủ đề" else "source",
                seconds=seconds, scene_count=scenes, channel=channel, style=style,
                source_label=content.strip() if kind == "URL" else (file.name if file else ""),
                skill=selected_skill_id)
        
        st.session_state.script_editor = script.model_dump_json(indent=2)
        st.session_state.script_base = str(ROOT)
        st.session_state.pop("video_result", None)
        st.rerun()
        
    except Exception as exc:
        st.error(str(exc))

# Logic Render Video
if render_btn:
    try:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", job_name):
            raise ValueError("Tên thư mục chỉ gồm chữ không dấu, số, dấu - hoặc _.")
            
        script = Script.model_validate_json(text)
        w, h = parse_size(size)
        output = ROOT / "output" / job_name
        output.mkdir(parents=True, exist_ok=True)
        
        music_path = None
        if bgm_url:
            st.info("Đang xử lý link nhạc nền Youtube...")
            # TODO: Thêm logic tải nhạc từ URL tại đây
        
        options = RenderOptions(
            width=w, height=h, fps=fps, theme=theme, visual_style=visual_style,
            subtitles=subtitles, sfx=sfx, 
            bgm=music_path,
            bgm_volume=music_volume
        )
        
        settings = replace(env_tts, voice=voice, ref_audio="")
        status = st.empty()
        
        with st.spinner("Hệ thống đang tạo audio và render video. Quá trình này có thể mất vài phút..."):
            result = build(script, output, options, settings,
                source_dir=Path(st.session_state.get("script_base", str(ROOT))), progress=status.info)
                
        st.session_state.video_result = str(result)
        st.session_state.video_dimensions = (w, h)
        st.success("✅ Video đã hoàn tất!")
        st.rerun()
        
    except Exception as exc:
        st.session_state.pop("video_result", None)
        st.error(f"Lỗi Render: {exc}")

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