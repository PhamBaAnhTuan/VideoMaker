from dotenv import load_dotenv
load_dotenv()

from dataclasses import replace
from datetime import datetime
from pathlib import Path
import os
import re
import uuid
import streamlit as st
from studio.audio import TtsSettings, VieNeuSpeech
from studio.models import Script, RenderOptions, parse_size
from studio.pipeline import build
from studio.writer import read_source, generate_script
ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="VieNeu Video Studio",page_icon="🎬",layout="wide")
st.title("VieNeu Video Studio")
st.caption("Viết kịch bản · Giọng đọc tiếng Việt · Video theo khung hình của bạn")
if "job_id" not in st.session_state:
    st.session_state.job_id = datetime.now().strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6]

with st.sidebar:
    st.subheader("Khung hình")
    size = st.selectbox("Tỷ lệ",["9:16","16:9","1:1","4:5","Tùy chỉnh"])
    if size == "Tùy chỉnh":
        width = st.number_input("Chiều rộng (px)",240,3840,1920,step=2)
        height = st.number_input("Chiều cao (px)",240,3840,1080,step=2)
        size = f"{width}x{height}"
    fps = st.selectbox("FPS",[24,30,60],index=0)
    theme = st.selectbox("Giao diện",["dark","light"],format_func=lambda x:"Tối" if x=="dark" else "Sáng")
    subtitles = st.checkbox("Hiện phụ đề theo đoạn",True)
    sfx = st.checkbox("Âm chuyển cảnh nhẹ",True)
    st.subheader("Giọng đọc")
    env_tts = TtsSettings.from_env()
    mode = st.selectbox("Model VieNeu",["v3turbo","v3nano"],index=0 if env_tts.mode=="v3turbo" else 1)
    default_voice = env_tts.voice if mode==env_tts.mode else ("Minh Quân" if mode=="v3nano" else "Hải Đăng")
    voice = st.text_input("Tên giọng preset",default_voice,key=f"voice_{mode}")
    backend = st.selectbox("Thiết bị",["onnx","auto"],index=0 if env_tts.backend=="onnx" else 1,
                           format_func=lambda x:"CPU (ONNX)" if x=="onnx" else "Tự chọn CPU/GPU")
    reference = st.file_uploader("Giọng mẫu tùy chọn (thay preset)",type=["wav","mp3","flac"])
    if st.button("Liệt kê giọng có sẵn"):
        try:
            with st.spinner("Đang nạp VieNeu; lần đầu có thể tải model..."):
                settings = replace(env_tts,mode=mode,backend=backend,voice=voice)
                st.write([name for name,_ in VieNeuSpeech(settings).voices()])
        except Exception as exc:
            st.error(str(exc))
    music = st.file_uploader("Nhạc nền tùy chọn",type=["mp3","wav","m4a","flac"])
    music_volume = st.slider("Âm lượng nhạc nền",0.0,1.0,0.10,0.01)
    with st.expander("AI viết kịch bản"):
        base = st.text_input("Địa chỉ API", os.getenv("LLM_BASE_URL", "https://api.cohere.ai/compatibility/v1"))
        model = st.text_input("Model", os.getenv("LLM_MODEL", "command-a-plus-05-2026"))
        api_key = st.text_input("API key (nếu cần)", os.getenv("LLM_API_KEY", os.getenv("COHERE_API_KEY", "")), type="password")

left,right = st.columns([1,1])
with left:
    st.subheader("1. Nội dung đầu vào")
    kind = st.radio("Nguồn",["Chủ đề","Văn bản","URL","File .txt/.md"],horizontal=True)
    file = None
    if kind == "File .txt/.md":
        file = st.file_uploader("Tài liệu nguồn",type=["txt","md"])
        content = ""
    else:
        content = st.text_area("Nội dung" if kind!="URL" else "Đường dẫn bài viết",height=180,
                               placeholder="Ví dụ: Hướng dẫn dùng VLOOKUP cho người mới học Excel")
    from studio.skills import get_available_skills
    skills_list = get_available_skills(ROOT)
    skill_map = {s.id: s for s in skills_list}
    selected_skill_id = st.selectbox(
        "Phong cách / Skill biên tập",
        options=list(skill_map.keys()),
        format_func=lambda x: f"{skill_map[x].name} ({x})",
        index=0
    )
    selected_skill = skill_map.get(selected_skill_id)
    if selected_skill and selected_skill.description:
        st.caption(f"✨ **Đặc điểm gu:** {selected_skill.description}")

    channel = st.text_input("Tên kênh","Góc kiến thức")
    seconds = st.slider("Thời lượng mục tiêu (giây)",15,300,60,5)
    scenes = st.slider("Số cảnh",3,12,5)
    style = st.text_input("Ghi chú phong cách bổ sung","Rõ ràng, gần gũi, dễ hiểu")
    auto = st.checkbox("Tạo audio và video ngay sau khi AI viết xong",False)
    create = st.button("AI viết kịch bản",type="primary",use_container_width=True)
    sample = st.button("Mở kịch bản Excel mẫu — không gọi AI",use_container_width=True)

auto_build = False
if sample:
    st.session_state.script_editor = (ROOT/"examples/excel.json").read_text(encoding="utf-8")
    st.session_state.script_base = str(ROOT/"examples")
    st.session_state.pop("video_result",None)
if create:
    try:
        # Validate costly options first, including dimensions.
        w,h = parse_size(size)
        RenderOptions(width=w,height=h,fps=fps)
        if kind=="File .txt/.md":
            if file is None:
                raise ValueError("Hãy chọn file nguồn.")
            source = read_source(text=file.getvalue().decode("utf-8-sig"))
        elif kind=="URL":
            source = read_source(url=content.strip())
        else:
            source = read_source(text=content)
        with st.spinner("AI đang viết và kiểm tra cấu trúc kịch bản theo Skill..."):
            script = generate_script(source,mode="topic" if kind=="Chủ đề" else "source",
                seconds=seconds,scene_count=scenes,channel=channel,style=style,
                base_url=base,model=model,api_key=api_key,
                source_label=content.strip() if kind=="URL" else (file.name if file else ""),
                skill=selected_skill_id)
        st.session_state.script_editor = script.model_dump_json(indent=2)
        st.session_state.script_base = str(ROOT)
        st.session_state.pop("video_result",None)
        auto_build = auto
    except Exception as exc:
        st.error(str(exc))

with right:
    st.subheader("2. Xem và chỉnh kịch bản")
    uploaded = st.file_uploader("Hoặc mở script.json đã lưu",type=["json"])
    if uploaded and st.button("Nạp JSON này"):
        try:
            checked = Script.model_validate_json(uploaded.getvalue().decode("utf-8-sig"))
            st.session_state.script_editor = checked.model_dump_json(indent=2)
            st.session_state.script_base = str(ROOT)
        except Exception as exc:
            st.error(str(exc))
    text = st.text_area("Kịch bản JSON — có thể sửa lời đọc, chữ và bố cục",key="script_editor",height=450)
    if text.strip():
        try:
            checked = Script.model_validate_json(text)
            st.success(f"{checked.title} · {len(checked.scenes)} cảnh")
            with st.expander("Đọc kịch bản dạng dễ xem",expanded=False):
                for scene in checked.scenes:
                    st.markdown(f"**{scene.title}** · {scene.layout}")
                    st.write(" ".join(line.text for line in scene.narration))
            st.download_button("Tải script.json",text,file_name="script.json",mime="application/json")
        except Exception as exc:
            st.warning(f"JSON chưa hợp lệ: {exc}")

st.subheader("3. Tạo video")
job = st.text_input("Tên thư mục kết quả",st.session_state.job_id)
st.caption("Dùng lại tên thư mục để tái sử dụng audio. Đổi tên để tạo một phiên bản riêng.")
render = st.button("Tạo giọng đọc và render video",type="primary",disabled=not bool(text.strip()))
if render or auto_build:
    try:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}",job):
            raise ValueError("Tên thư mục chỉ gồm chữ không dấu, số, dấu - hoặc _.")
        script = Script.model_validate_json(text)
        w,h = parse_size(size)
        output = ROOT/"output"/job
        upload_dir = output/"inputs"
        upload_dir.mkdir(parents=True,exist_ok=True)
        ref_path = env_tts.ref_audio
        if reference:
            ref = upload_dir/("reference"+Path(reference.name).suffix.lower())
            ref.write_bytes(reference.getvalue())
            ref_path = str(ref)
        music_path = None
        if music:
            path = upload_dir/("music"+Path(music.name).suffix.lower())
            path.write_bytes(music.getvalue())
            music_path = str(path)
        options = RenderOptions(width=w,height=h,fps=fps,theme=theme,subtitles=subtitles,sfx=sfx,
                                bgm=music_path,bgm_volume=music_volume)
        settings = replace(env_tts,mode=mode,backend=backend,voice=voice,ref_audio=ref_path)
        status = st.empty()
        with st.spinner("Đang tạo audio và video; model được tải ở lần chạy đầu..."):
            result = build(script,output,options,settings,
                           source_dir=Path(st.session_state.get("script_base",str(ROOT))),progress=status.info)
        st.session_state.video_result = str(result)
        st.success("Video đã hoàn tất.")
    except Exception as exc:
        st.session_state.pop("video_result",None)
        st.error(str(exc))

if st.session_state.get("video_result"):
    video = Path(st.session_state.video_result)
    if video.is_file():
        st.video(str(video))
        for name,label,mime in [("video.mp4","Tải video","video/mp4"),
                                ("subtitles.srt","Tải phụ đề","text/plain"),
                                ("narration.wav","Tải giọng đọc sạch","audio/wav")]:
            path = video.parent/name
            st.download_button(label,path.read_bytes(),file_name=name,mime=mime)
