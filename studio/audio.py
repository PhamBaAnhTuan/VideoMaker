"""VieNeu SDK adapter, content-addressed speech cache and sample-accurate timeline.

Adapted workflow: per-scene TTS + measured timing + gap, auto-video-gen (MIT).
Modified: per-utterance captions, content hashing, WAV timeline, optional local SFX.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import subprocess
import wave
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable
import numpy as np
from .models import Script, RenderOptions, json_write

SAMPLE_RATE = 48000


def command(args: list[str]) -> None:
    try:
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError as exc:
        raise RuntimeError(f"Không tìm thấy {args[0]}. Cài FFmpeg và thêm vào PATH.") from exc
    if result.returncode:
        raise RuntimeError(f"{Path(args[0]).name} thất bại: {result.stderr[-2500:]}")


def write_wav(path: Path, samples: np.ndarray):
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = np.nan_to_num(np.asarray(samples, dtype=np.float32).reshape(-1))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes((np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes())


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, SAMPLE_RATE):
            raise ValueError("Cache WAV phải là mono PCM16 48 kHz.")
        return np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(np.float32) / 32768


def normalize_wav(source: Path, destination: Path):
    command([os.getenv("FFMPEG_BIN", "ffmpeg"), "-y", "-v", "error", "-i", str(source),
             "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(destination)])


@dataclass(frozen=True)
class TtsSettings:
    mode: str = "v3turbo"
    backend: str = "onnx"
    voice: str = "Hải Đăng"
    precision: str = "fp32"
    ref_audio: str = ""

    @classmethod
    def from_env(cls):
        return cls(mode=os.getenv("VIENEU_MODE", "v3turbo"),
                   backend=os.getenv("VIENEU_BACKEND", "onnx"),
                   voice=os.getenv("VIENEU_VOICE", "Hải Đăng"),
                   precision=os.getenv("VIENEU_PRECISION", "fp32"),
                   ref_audio=os.getenv("VIENEU_REF_AUDIO", ""))


class VieNeuSpeech:
    """Real VieNeu integration. Import/load once, only when speech is needed."""
    def __init__(self, settings: TtsSettings):
        if settings.mode not in ("v3turbo", "v3nano"):
            raise ValueError("VIENEU_MODE: v3turbo hoặc v3nano.")
        if settings.backend not in ("onnx", "auto"):
            raise ValueError("VIENEU_BACKEND: onnx hoặc auto.")
        if settings.precision not in ("fp32", "int8"):
            raise ValueError("VIENEU_PRECISION: fp32 hoặc int8.")
        self.settings = settings
        self.engine = None

    @property
    def identity(self):
        try:
            version = importlib.metadata.version("vieneu")
        except importlib.metadata.PackageNotFoundError:
            version = "not-installed"
        payload = asdict(self.settings) | {"sdk_version": version, "adapter_version": 1}
        if self.settings.ref_audio:
            reference = Path(self.settings.ref_audio).expanduser().resolve()
            payload["reference_sha256"] = hashlib.sha256(reference.read_bytes()).hexdigest()
        return payload

    def load(self):
        if self.engine is None:
            # Disable optional telemetry before model/session creation. Model files
            # may still be downloaded from Hugging Face on first use.
            os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
            os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
            try:
                import onnxruntime
                onnxruntime.disable_telemetry_events()
                from vieneu import Vieneu
            except ImportError as exc:
                raise RuntimeError('Thiếu VieNeu. Chạy: python -m pip install -e ".[tts]"') from exc
            kwargs = {"mode": self.settings.mode}
            if self.settings.mode == "v3turbo":
                kwargs["precision"] = self.settings.precision
                if self.settings.backend != "auto":
                    kwargs["backend"] = self.settings.backend
            self.engine = Vieneu(**kwargs)
        return self.engine

    def synthesize(self, text: str, path: Path):
        engine = self.load()
        kwargs = {"ref_audio": str(Path(self.settings.ref_audio).expanduser().resolve())} if self.settings.ref_audio else {"voice": self.settings.voice}
        audio = engine.infer(text, **kwargs)
        engine.save(audio, str(path))

    def voices(self):
        return self.load().list_preset_voices()


class DemoTone:
    """Explicit TEST-ONLY tone. It is never selected as a fallback for real speech."""
    identity = {"provider": "TEST_TONE_NOT_SPEECH", "version": 1}

    def synthesize(self, text: str, path: Path):
        seconds = max(0.8, min(3.0, len(text.split()) / 5))
        t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
        signal = 0.025 * np.sin(2 * np.pi * 440 * t)
        signal *= np.minimum(t * 12, 1) * np.minimum((seconds - t) * 12, 1)
        write_wav(path, signal)


def cache_key(text: str, identity: dict) -> str:
    value = json.dumps({"text": text, "tts": identity}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(value.encode()).hexdigest()


def speech_chunk(text: str, engine, cache: Path) -> np.ndarray:
    key = cache_key(text, engine.identity)
    cached = cache / f"{key}.wav"
    cache.mkdir(parents=True, exist_ok=True)
    if cached.exists():
        try:
            samples = read_wav(cached)
            if samples.size > 100:
                return samples
        except (ValueError, wave.Error, EOFError):
            pass
        cached.unlink(missing_ok=True)
    original = cache / f"{key}.raw.wav"
    normalized = cache / f"{key}.tmp.wav"
    try:
        engine.synthesize(text, original)
        normalize_wav(original, normalized)
        samples = read_wav(normalized)
        if samples.size < 100 or not np.any(np.abs(samples) > 0.0001):
            raise RuntimeError("TTS trả audio rỗng hoặc im lặng; không tiếp tục dựng video.")
        normalized.replace(cached)
        return samples
    finally:
        original.unlink(missing_ok=True)
        normalized.unlink(missing_ok=True)


def srt_time(seconds: float) -> str:
    ms = max(0, round(seconds * 1000))
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def save_srt(captions: list[dict], path: Path):
    content = "\n\n".join(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}"
                          for i, c in enumerate(captions, 1))
    path.write_text(content + "\n", encoding="utf-8")


def make_audio(script: Script, options: RenderOptions, output: Path, engine,
               progress: Callable[[str], None] = print) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    pieces, scenes, captions = [], [], []
    cursor = 0
    for index, scene in enumerate(script.scenes):
        start = cursor
        progress(f"Giọng đọc {index+1}/{len(script.scenes)}: {scene.title}")
        for j, line in enumerate(scene.narration):
            data = speech_chunk(line.text, engine, output / "cache")
            pieces.append(data)
            end = cursor + len(data)
            captions.append({"scene": scene.id, "start": cursor / SAMPLE_RATE,
                             "end": end / SAMPLE_RATE, "text": line.caption})
            cursor = end
            # A small silence separates separately synthesized utterances naturally.
            if j < len(scene.narration) - 1:
                pause = np.zeros(round(0.10 * SAMPLE_RATE), dtype=np.float32)
                pieces.append(pause)
                cursor += len(pause)
        hold = options.outro_hold if index == len(script.scenes) - 1 else options.scene_gap
        pause = np.zeros(round(hold * SAMPLE_RATE), dtype=np.float32)
        pieces.append(pause)
        cursor += len(pause)
        scenes.append({"id": scene.id, "start": start / SAMPLE_RATE, "end": cursor / SAMPLE_RATE})
    raw = np.concatenate(pieces)
    # Pad once to an exact video frame count so audio and video share an end time.
    frames = math.ceil(len(raw) / SAMPLE_RATE * options.fps)
    target_samples = round(frames / options.fps * SAMPLE_RATE)
    raw = np.pad(raw, (0, max(0, target_samples - len(raw))))
    scenes[-1]["end"] = frames / options.fps
    write_wav(output / "narration.wav", raw)
    mixed = raw.copy()
    if options.sfx:
        # Original synthesized transition chime; no external SFX library needed.
        t = np.arange(int(0.16 * SAMPLE_RATE)) / SAMPLE_RATE
        effect = 0.035 * np.sin(2 * np.pi * (520 * t + 900 * t*t)) * np.sin(np.pi * t / 0.16)**2
        for scene in scenes[1:]:
            at = round(scene["start"] * SAMPLE_RATE)
            count = min(len(effect), len(mixed) - at)
            mixed[at:at+count] += effect[:count]
    peak = float(np.max(np.abs(mixed)))
    if peak > 0.97:
        mixed *= 0.97 / peak
    write_wav(output / "voice.wav", mixed)
    timeline = {"duration": frames / options.fps, "frames": frames, "fps": options.fps,
                "sample_rate": SAMPLE_RATE, "scenes": scenes, "captions": captions,
                "tts": engine.identity, "test_audio": isinstance(engine, DemoTone)}
    json_write(output / "timeline.json", timeline)
    save_srt(captions, output / "subtitles.srt")
    (output / "script.txt").write_text("\n\n".join(" ".join(n.text for n in s.narration) for s in script.scenes), encoding="utf-8")
    return timeline
