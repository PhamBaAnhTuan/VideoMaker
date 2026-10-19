from __future__ import annotations

import argparse
import importlib.metadata
import os
import shutil
import sys
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .audio import DemoTone, TtsSettings, VieNeuSpeech
from .models import Script, RenderOptions, parse_size
from .pipeline import build
from .writer import read_source, generate_script


def add_source(parser):
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--topic", help="Chủ đề để AI phát triển")
    group.add_argument("--text", help="Nội dung nguồn")
    group.add_argument("--file", type=Path, help="File UTF-8 .txt/.md")
    group.add_argument("--url", help="URL bài viết")
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--scenes", type=int, default=5)
    parser.add_argument("--channel", default="Góc kiến thức")
    parser.add_argument("--style", default="Rõ ràng, gần gũi, dễ hiểu")
    parser.add_argument("--skill", default="create-news-video", help="ID skill hoặc đường dẫn file .md (vd: create-news-video, knowledge-sharing)")


def add_render(parser):
    parser.add_argument("--size", default="9:16", help="9:16 | 16:9 | 1:1 | 4:5 | 1920x1080")
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--theme", choices=["dark","light"], default="dark")
    parser.add_argument("--no-subtitles", action="store_true")
    parser.add_argument("--no-sfx", action="store_true")
    parser.add_argument("--bgm", help="Nhạc nền trên máy")
    parser.add_argument("--bgm-volume", type=float, default=.10)
    parser.add_argument("--voice", help="Tên preset VieNeu")
    parser.add_argument("--ref-audio", help="File giọng mẫu thay cho preset")
    parser.add_argument("--font", help="Font TTF hỗ trợ tiếng Việt")


def options_from_args(args):
    width,height = parse_size(args.size)
    return RenderOptions(width=width,height=height,fps=args.fps,theme=args.theme,
                         subtitles=not args.no_subtitles,sfx=not args.no_sfx,bgm=args.bgm,
                         bgm_volume=args.bgm_volume,font=args.font)


def settings_from_args(args):
    from dataclasses import replace
    settings = TtsSettings.from_env()
    if args.voice:
        settings = replace(settings,voice=args.voice)
    if args.ref_audio:
        settings = replace(settings,ref_audio=args.ref_audio)
    return settings


def write_from_args(args):
    source = read_source(text=args.topic or args.text,file=args.file,url=args.url)
    script = generate_script(source,mode="topic" if args.topic else "source",seconds=args.seconds,
                             scene_count=args.scenes,channel=args.channel,style=args.style,
                             source_label=args.url or (args.file.name if args.file else ""),
                             skill=getattr(args, "skill", "create-news-video"))
    return script


def main(argv=None):
    load_dotenv()
    parser = argparse.ArgumentParser(description="VieNeu Video Studio — kịch bản → giọng đọc → video")
    sub = parser.add_subparsers(dest="command",required=True)
    p = sub.add_parser("plan",help="AI viết script.json; chưa tạo audio")
    add_source(p)
    p.add_argument("--out",type=Path,default=Path("output/my-video/script.json"))
    p = sub.add_parser("run",help="Tự động viết kịch bản, TTS, render")
    add_source(p)
    add_render(p)
    p.add_argument("--out",type=Path,default=Path("output/my-video"))
    p = sub.add_parser("build",help="Tạo video từ kịch bản đã kiểm tra/sửa")
    p.add_argument("script",type=Path)
    add_render(p)
    p.add_argument("--out",type=Path,default=Path("output/my-video"))
    p = sub.add_parser("demo",help="Kiểm tra dựng hình bằng âm thử, KHÔNG dùng AI/TTS")
    p.add_argument("script",type=Path,nargs="?",default=Path("examples/excel.json"))
    add_render(p)
    p.add_argument("--out",type=Path,default=Path("output/demo"))
    sub.add_parser("voices",help="Nạp VieNeu và liệt kê preset (có thể tải model lần đầu)")
    sub.add_parser("skills",help="Liệt kê các phong cách video / skill có sẵn")
    sub.add_parser("doctor",help="Kiểm tra môi trường, không tải model")
    args = parser.parse_args(argv)
    try:
        if args.command == "skills":
            from .skills import get_available_skills
            for s in get_available_skills():
                print(f"{s.id:20} | {s.name:45} | {s.description}")
            return 0
        if args.command == "doctor":
            print(f"Python {sys.version.split()[0]}")
            for tool,var in (("ffmpeg","FFMPEG_BIN"),("ffprobe","FFPROBE_BIN")):
                print(f"{tool}: {shutil.which(os.getenv(var,tool)) or 'THIẾU'}")
            for package in ("vieneu","Pillow","streamlit","httpx"):
                try:
                    print(f"{package}: {importlib.metadata.version(package)}")
                except importlib.metadata.PackageNotFoundError:
                    print(f"{package}: chưa cài")
            print(f"LLM model: {os.getenv('LLM_MODEL','command-a-plus-05-2026')} (chưa kiểm tra kết nối)")
            return 0
        if args.command == "voices":
            for label,voice_id in VieNeuSpeech(TtsSettings.from_env()).voices():
                print(f"{label}\t{voice_id}")
            return 0
        if args.command == "plan":
            script = write_from_args(args)
            script.write(args.out)
            print(f"Đã lưu kịch bản: {args.out}")
            return 0
        # Validate dimensions BEFORE spending time/money generating content.
        options = options_from_args(args)
        if args.command == "run":
            script = write_from_args(args)
            source_dir = Path.cwd()
        else:
            script = Script.read(args.script)
            source_dir = args.script.resolve().parent
        engine = DemoTone() if args.command == "demo" else None
        if engine:
            print("DEMO KỸ THUẬT: âm thử, không phải giọng VieNeu hay nội dung do AI viết.")
        build(script,args.out,options,settings_from_args(args),source_dir=source_dir,engine=engine)
        return 0
    except KeyboardInterrupt:
        print("Đã dừng. Các đoạn audio hoàn tất vẫn được giữ trong cache.",file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Lỗi: {exc}",file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
