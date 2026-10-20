"""Shared LLM defaults for the UI, CLI and script writer."""
from dataclasses import dataclass, field
import os
from urllib.parse import urlparse

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
DEFAULT_MODEL = "gemini-3.8-flash"


@dataclass(frozen=True)
class LlmSettings:
    base_url: str
    model: str
    api_key: str = field(repr=False)

    @property
    def is_google(self) -> bool:
        return urlparse(self.base_url).hostname == "generativelanguage.googleapis.com"

    @classmethod
    def resolve(cls, *, base_url=None, model=None, api_key=None):
        base = (base_url or os.getenv("LLM_BASE_URL", "")).strip() or DEFAULT_BASE_URL
        base = base.rstrip("/")
        selected_model = (model or os.getenv("LLM_MODEL", "")).strip()
        host = urlparse(base).hostname
        google = host == "generativelanguage.googleapis.com"
        if not selected_model and google:
            selected_model = DEFAULT_MODEL
        if api_key is None:
            if google:
                api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
                           or os.getenv("LLM_API_KEY", ""))
            else:
                api_key = os.getenv("LLM_API_KEY", "")
                if not api_key and host == "api.cohere.ai":
                    api_key = os.getenv("COHERE_API_KEY", "")
        return cls(base, selected_model, api_key.strip())
