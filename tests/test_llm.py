import httpx
import pytest

from studio.llm import DEFAULT_BASE_URL, DEFAULT_MODEL, LlmSettings
from studio.models import Script
from studio.writer import generate_script
from pathlib import Path


@pytest.fixture(autouse=True)
def clean_llm_env(monkeypatch):
    for name in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY", "GEMINI_API_KEY",
                 "GOOGLE_API_KEY", "COHERE_API_KEY", "LLM_JSON_MODE"):
        monkeypatch.delenv(name, raising=False)


def test_key_only_and_empty_defaults(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-google-key")
    monkeypatch.setenv("LLM_BASE_URL", " ")
    monkeypatch.setenv("LLM_MODEL", "")
    settings = LlmSettings.resolve()
    assert (settings.base_url, settings.model, settings.api_key) == (
        DEFAULT_BASE_URL, DEFAULT_MODEL, "test-google-key")
    assert "test-google-key" not in repr(settings)


def test_other_provider_does_not_receive_google_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "google-secret")
    settings = LlmSettings.resolve(base_url="http://localhost:11434/v1", model="local")
    assert settings.api_key == ""
    monkeypatch.setenv("LLM_API_KEY", "provider-secret")
    assert LlmSettings.resolve(base_url="https://example.com/v1", model="other").api_key == "provider-secret"
    assert LlmSettings.resolve(api_key="").api_key == ""


def test_missing_google_key():
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        generate_script("Nội dung")


def test_ui_uses_shared_google_defaults(monkeypatch):
    from streamlit.testing.v1 import AppTest
    # Blank environment values also exercise fallback with an existing .env.
    for name in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.setenv(name, "")
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=20)
    assert not app.exception
    inputs = {item.label: item.value for item in app.text_input}
    assert "Địa chỉ API" not in inputs
    assert "Model" not in inputs
    assert "API key" not in inputs
    assert any("Lấy Gemini API key" in item.label for item in app.get("link_button"))


def test_google_request_and_json_repair(monkeypatch):
    script = Script.read(Path(__file__).resolve().parents[1] / "examples/excel.json")
    calls = []

    def respond(request):
        import json
        calls.append(json.loads(request.content))
        assert str(request.url) == DEFAULT_BASE_URL + "/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-google-key"
        assert calls[-1]["model"] == DEFAULT_MODEL
        assert calls[-1]["response_format"] == {"type": "json_object"}
        return httpx.Response(200, json={"choices": [{"message": {
            "content": "invalid JSON" if len(calls) == 1 else script.model_dump_json()}}]})

    original_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kw: original_client(
        transport=httpx.MockTransport(respond), **kw))
    monkeypatch.setenv("GEMINI_API_KEY", "test-google-key")
    result = generate_script("Nội dung", scene_count=len(script.scenes), channel="Kênh", source_label="nguon.txt")
    assert len(calls) == 2
    assert result.channel == "Kênh"
    assert result.source == "nguon.txt"


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429])
def test_provider_errors_do_not_expose_key(monkeypatch, status):
    original_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kw: original_client(
        transport=httpx.MockTransport(lambda request: httpx.Response(status, json={"error": "secret-key"})), **kw))
    with pytest.raises(RuntimeError, match=str(status)) as error:
        generate_script("Nội dung", api_key="secret-key")
    assert "secret-key" not in str(error.value)
