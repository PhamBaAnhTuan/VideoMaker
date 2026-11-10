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
    :root {--studio-accent:#a98251; --studio-ink:#262522; --studio-muted:#77736d;}
    .stApp {font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;}
    .block-container {max-width: 1380px; padding-top: 2rem; padding-bottom: 4rem;}
    [data-testid="stSidebar"] {border-right: 1px solid rgba(120,112,98,.16);}
    [data-testid="stSidebar"] .block-container {padding-top: 1.25rem;}
    h1 {letter-spacing: -.055em; font-weight: 650 !important; line-height: 1.04 !important;}
    h2, h3 {letter-spacing: -.035em; font-weight: 620 !important;}
    [data-testid="stCaptionContainer"] {color: var(--studio-muted);}
    [data-testid="stVerticalBlockBorderWrapper"] {border-radius: 14px; border-color: rgba(120,112,98,.2);}
    [data-testid="stExpander"] {border-color: rgba(120,112,98,.2); border-radius: 12px;}
    .stButton > button, .stDownloadButton > button, .stLinkButton > a {
      border-radius: 9px; transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {
      transform: translateY(-1px); box-shadow: 0 5px 16px rgba(35,31,25,.09);
    }
    [data-testid="stVideo"] video {max-height: 520px; border-radius: 12px; background: #191919;}
    [data-testid="stImage"] img {border-radius: 10px;}
    hr {border-color: rgba(120,112,98,.18);}
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {transition-duration: .01ms !important; animation-duration: .01ms !important;}
    }
    </style>""", unsafe_allow_html=True)
