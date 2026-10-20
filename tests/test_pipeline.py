import json
import subprocess
import sys
import types
from pathlib import Path
import numpy as np
import pytest
from studio.models import Script, RenderOptions, parse_size
from studio.audio import (DemoTone, VieNeuSpeech, TtsSettings, cache_key, make_audio,
                          read_wav, write_wav, srt_time)
from studio.pipeline import build, output_lock
from studio.renderer import ScenePainter, text_tile, font_path
from studio.writer import parse_response, generate_script, read_source

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def script():
    return Script.read(ROOT/"examples/excel.json")


def test_invalid_dimensions_and_schema(script):
    assert parse_size("16:9")== (1280,720)
    assert parse_size("1920x1080")== (1920,1080)
    with pytest.raises(ValueError):
        RenderOptions(width=721)
    with pytest.raises(ValueError):
        RenderOptions(width=240,height=3840)
    obj=script.model_dump()
    obj["scenes"][1]["id"]=obj["scenes"][0]["id"]
    with pytest.raises(ValueError):
        Script.model_validate(obj)
    obj=script.model_dump()
    obj["scenes"][1]["left"]=None
    with pytest.raises(ValueError):
        Script.model_validate(obj)


def test_source_and_fenced_json(script,tmp_path):
    assert parse_response("```json\n"+script.model_dump_json()+"\n```")==script
    with pytest.raises(ValueError):
        read_source(text="")
    with pytest.raises(ValueError):
        read_source(text="a",url="https://example.org")
    with pytest.raises(ValueError):
        read_source(text="a"*24001)
    path=tmp_path/"nguon.txt"
    path.write_text("\ufeffBài học tiếng Việt",encoding="utf-8")
    assert read_source(file=path)=="Bài học tiếng Việt"


def test_llm_repair_path_and_authoritative_metadata(script,monkeypatch):
    import httpx
    calls=[]
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {"choices":[{"message":{"content":"not JSON" if len(calls)==1 else script.model_dump_json()}}]}
    class Client:
        def __init__(self,**kw): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def post(self,url,**kwargs):
            calls.append(kwargs)
            return Response()
    monkeypatch.setattr(httpx,"Client",Client)
    result=generate_script("Nguồn tham khảo",scene_count=6,channel="Kênh của tôi",source_label="source.txt",
                           base_url="http://localhost:11434/v1",model="test-model",api_key="")
    assert len(calls)==2
    assert result.channel=="Kênh của tôi"
    assert result.source=="source.txt"
    assert calls[1]["json"]["messages"][-1]["role"]=="user"


def test_cache_invalidation():
    assert cache_key("Xin chào",{"voice":"A"})==cache_key("Xin chào",{"voice":"A"})
    assert cache_key("Xin chào",{"voice":"A"})!=cache_key("Xin chào bạn",{"voice":"A"})
    assert cache_key("Xin chào",{"voice":"A"})!=cache_key("Xin chào",{"voice":"B"})


def test_vieneu_adapter_contract(monkeypatch,tmp_path):
    calls=[]
    telemetry=[]
    monkeypatch.setitem(sys.modules,"onnxruntime",types.SimpleNamespace(disable_telemetry_events=lambda:telemetry.append("disabled")))
    class Engine:
        def infer(self,text,**kwargs):
            calls.append((text,kwargs)); return np.ones(100)
        def save(self,audio,path): calls.append(path)
        def list_preset_voices(self): return [("Hải Đăng","id")]
    def factory(**kwargs): calls.append(kwargs); return Engine()
    monkeypatch.setitem(sys.modules,"vieneu",types.SimpleNamespace(Vieneu=factory))
    adapter=VieNeuSpeech(TtsSettings())
    adapter.synthesize("Xin chào",tmp_path/"a.wav")
    adapter.synthesize("Lần hai",tmp_path/"b.wav")
    assert calls[0]=={"mode":"v3turbo","precision":"fp32","backend":"onnx"}
    assert calls[1]==("Xin chào",{"voice":"Hải Đăng"})
    assert sum(isinstance(v,dict) for v in calls)==1
    assert telemetry==["disabled"]


def test_audio_timeline_and_resume(script,tmp_path):
    class Counting(DemoTone):
        def __init__(self): self.calls=0
        def synthesize(self,text,path):
            self.calls+=1; super().synthesize(text,path)
    engine=Counting()
    options=RenderOptions(width=320,height=568,fps=12)
    timeline=make_audio(script,options,tmp_path,engine,lambda _:None)
    calls=engine.calls
    again=make_audio(script,options,tmp_path,engine,lambda _:None)
    assert engine.calls==calls
    assert again["scenes"]==timeline["scenes"]
    assert abs(len(read_wav(tmp_path/"voice.wav"))/48000-timeline["duration"]) < 1/48000
    assert timeline["frames"]==round(timeline["duration"]*12)
    for prev,nxt in zip(timeline["captions"],timeline["captions"][1:]):
        assert nxt["start"]>=prev["end"]
    script.scenes[0].narration[0].text+=" Thay đổi."
    make_audio(script,options,tmp_path,engine,lambda _:None)
    assert engine.calls==calls+1
    assert "-->" in (tmp_path/"subtitles.srt").read_text(encoding="utf-8")
    assert srt_time(59.9996)=="00:01:00,000"


@pytest.mark.parametrize("size",["320x568","568x320","320x320","320x400"])
def test_real_ffmpeg_end_to_end_all_ratios(script,tmp_path,size):
    # Exercise every template, ffmpeg encoding, AAC, mux timing and odd aspect handling.
    w,h=parse_size(size)
    options=RenderOptions(width=w,height=h,fps=6,outro_hold=.3)
    result=build(script,tmp_path,options,engine=DemoTone(),source_dir=ROOT/"examples",progress=lambda _:None)
    info=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(result)]))
    video=next(s for s in info["streams"] if s["codec_type"]=="video")
    audio=next(s for s in info["streams"] if s["codec_type"]=="audio")
    timeline=json.loads((tmp_path/"timeline.json").read_text(encoding="utf-8"))
    assert (video["width"],video["height"])==(w,h)
    assert video["codec_name"]=="h264" and audio["codec_name"]=="aac"
    assert int(video["nb_frames"])==timeline["frames"]
    assert abs(float(video["duration"])-float(audio["duration"]))<.06
    assert not (tmp_path/".render.lock").exists()


def test_bgm_image_and_light_theme(script,tmp_path):
    from PIL import Image
    source=tmp_path/"source";source.mkdir()
    Image.new("RGB",(400,300),"#335577").save(source/"ảnh mẫu.png")
    script.scenes=script.scenes[:1]
    script.scenes[0].image="ảnh mẫu.png"
    music=source/"nhạc nền.wav"
    write_wav(music,.02*np.sin(np.arange(48000)*2*np.pi*220/48000))
    out=tmp_path/"kết quả có dấu"
    build(script,out,RenderOptions(width=320,height=320,fps=6,theme="light",bgm=str(music)),
          engine=DemoTone(),source_dir=source,progress=lambda _:None)
    saved=Script.read(out/"script.json")
    assert (out/saved.scenes[0].image).is_file()
    assert (out/"video.mp4").stat().st_size>1000


def test_output_lock_and_long_text(tmp_path):
    with output_lock(tmp_path):
        with pytest.raises(RuntimeError):
            with output_lock(tmp_path): pass
    assert not (tmp_path/".render.lock").exists()
    with pytest.raises(ValueError):
        text_tile("Từ dài "*1000,100,30,path=font_path(),max_size=30,fill="white")


def test_ui_boots():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(ROOT/"app.py")).run(timeout=20)
    assert not app.exception
    sample=next(b for b in app.button if "Excel mẫu" in b.label)
    sample.click().run(timeout=20)
    assert not app.exception
    assert "VLOOKUP" in app.session_state["script_editor"]
