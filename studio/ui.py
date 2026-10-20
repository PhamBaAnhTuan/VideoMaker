"""Presentation helpers and on-demand voice previews."""
from pathlib import Path
import threading
import uuid

import streamlit as st
from .audio import TtsSettings, VieNeuSpeech, cache_key
from .voices import PREVIEW_TEXT


@st.cache_resource(max_entries=1, show_spinner=False)
def preview_engine(settings: TtsSettings):
    return VieNeuSpeech(settings), threading.Lock()


def voice_preview(settings: TtsSettings, directory: Path) -> bytes:
    engine, lock = preview_engine(settings)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (cache_key(PREVIEW_TEXT, engine.identity) + ".wav")
    with lock:
        if not target.is_file():
            temporary = directory / f"{uuid.uuid4().hex}.wav"
            try:
                engine.synthesize(PREVIEW_TEXT, temporary)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        return target.read_bytes()


def video_preview_width(width: int, height: int) -> int:
    """Keep the player below 520px high, even for portrait output."""
    return min(760, max(180, round(520 * width / height)))


def apply_theme():
    st.markdown("""<style>
    .block-container {max-width: 1280px; padding-top: 2.4rem; padding-bottom: 3rem;}
    [data-testid="stSidebar"] {border-right: 1px solid rgba(128,128,160,.16);}
    [data-testid="stSidebar"] .block-container {padding-top: 1.5rem;}
    h1 {letter-spacing: -.045em; font-weight: 800 !important;}
    h2, h3 {letter-spacing: -.025em;}
    [data-testid="stVerticalBlockBorderWrapper"] {border-radius: 18px;}
    .stButton > button, .stDownloadButton > button, .stLinkButton > a {border-radius: 10px;}
    [data-testid="stVideo"] video {max-height: 520px; border-radius: 16px; background: #0b1220;}
    </style>""", unsafe_allow_html=True)
