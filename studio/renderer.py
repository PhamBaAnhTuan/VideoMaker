"""Responsive Pillow motion graphics → FFmpeg H.264.

Six layout concepts and entrance timings ported from auto-video-gen (MIT,
Copyright (c) 2026 CuongIT). Reimplemented in Python: no browser/GSAP/Node runtime.
Changes: responsive geometry, measured text fitting, captions, image motion,
light theme, configurable frame rate and safe raw-frame encoding.
"""
from __future__ import annotations

import math
import os
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
from .models import Script, Scene, RenderOptions


def font_path(custom: str | None = None) -> str:
    if custom:
        if not Path(custom).is_file():
            raise ValueError(f"Không tìm thấy font: {custom}")
        return str(Path(custom).resolve())
    candidates = [Path(__file__).parent / "assets" / "DejaVuSans.ttf",
                  Path("C:/Windows/Fonts/arial.ttf"),
                  Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                  Path("/System/Library/Fonts/Supplemental/Arial.ttf")]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise RuntimeError("Chưa có font Unicode. Đặt VIDEO_FONT tới font TTF hỗ trợ tiếng Việt.")


@lru_cache(maxsize=128)
def load_font(path: str, size: int):
    return ImageFont.truetype(path, size)


def wrap(text: str, font, width: int) -> list[str]:
    lines = []
    for paragraph in text.splitlines() or [""]:
        line = ""
        for word in paragraph.split():
            if font.getlength(word) > width:
                if line:
                    lines.append(line)
                    line = ""
                for char in word:
                    if font.getlength(line + char) > width and line:
                        lines.append(line)
                        line = ""
                    line += char
                continue
            candidate = (line + " " + word).strip()
            if line and font.getlength(candidate) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines


def text_tile(text: str, width: int, height: int, *, path: str, max_size: int,
              fill, align="left", background=None, padding=0, min_size=6) -> Image.Image:
    width, height = max(1, int(width)), max(1, int(height))
    available_w = width - 2 * padding
    available_h = height - 2 * padding
    for size in range(max(min_size, int(max_size)), min_size - 1, -1):
        font = load_font(path, size)
        lines = wrap(text, font, available_w)
        line_h = math.ceil(size * 1.36)
        if len(lines) * line_h <= available_h and all(font.getlength(s) <= available_w for s in lines):
            break
    else:
        raise ValueError(f"Chữ không vừa khung: {text[:70]!r}. Rút gọn nội dung hoặc tăng khung hình.")
    tile = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)
    if background:
        draw.rounded_rectangle((0, 0, width-1, height-1), radius=max(6, padding), fill=background)
    y = (height - len(lines) * line_h) / 2
    for line in lines:
        x = (width - font.getlength(line)) / 2 if align == "center" else padding
        bbox = font.getbbox(line or " ")
        draw.text((int(x), int(y - bbox[1] + (line_h - (bbox[3]-bbox[1]))/2)), line, font=font, fill=fill)
        y += line_h
    return tile


@dataclass
class Element:
    tile: Image.Image
    x: int
    y: int
    delay: float = 0.15
    duration: float = 0.5
    motion: str = "up"

    def paint(self, canvas: Image.Image, time: float):
        p = max(0.0, min(1.0, (time - self.delay) / self.duration))
        if p == 0:
            return
        ease = 1 - (1-p)**3
        tile = self.tile
        x, y = self.x, self.y
        if p < 1:
            if self.motion == "zoom":
                scale = 0.65 + 0.35 * ease
                size = (max(1, round(tile.width*scale)), max(1, round(tile.height*scale)))
                tile = tile.resize(size, Image.Resampling.BICUBIC)
                x += (self.tile.width-tile.width)//2
                y += (self.tile.height-tile.height)//2
            elif self.motion in ("left", "right"):
                x += round((1-ease) * self.tile.width * 0.13 * (-1 if self.motion == "left" else 1))
            else:
                y += round((1-ease) * self.tile.height * 0.25)
            tile = tile.copy()
            tile.putalpha(tile.getchannel("A").point(lambda a: round(a*p)))
        canvas.alpha_composite(tile, (x, y))


class ScenePainter:
    def __init__(self, script: Script, scene: Scene, index: int, options: RenderOptions,
                 base_dir: Path, timeline: dict):
        self.script, self.scene, self.index, self.o = script, scene, index, options
        self.w, self.h = options.width, options.height
        self.unit = min(self.w, self.h)
        self.font = font_path(options.font or os.getenv("VIDEO_FONT") or None)
        self.light = options.theme == "light"
        self.fg = "#122238" if self.light else "#F2F5FC"
        self.muted = "#40536A" if self.light else "#9CADC8"
        self.accent = "#007E84" if self.light else "#67E8D1"
        self.card = (224, 233, 243, 250) if self.light else (23, 35, 56, 247)
        self.elements: list[Element] = []
        self.captions = [c for c in timeline["captions"] if c["scene"] == scene.id]
        self.caption_tiles: dict[str, Image.Image] = {}
        self.background = self.make_background()
        self.photo = None
        if scene.image:
            path = Path(scene.image)
            path = path if path.is_absolute() else base_dir / path
            with Image.open(path) as img:
                self.photo = ImageOps.fit(ImageOps.exif_transpose(img).convert("RGB"), (self.w, self.h))
        self.build_elements()
        self.shell = self.build_shell(timeline.get("test_audio", False))

    def make_background(self):
        top, bottom = ((247, 249, 252), (226, 236, 247)) if self.light else ((9, 17, 31), (15, 32, 49))
        y = np.linspace(0, 1, self.h)[:, None, None]
        arr = np.broadcast_to(np.array(top)[None,None,:]*(1-y) + np.array(bottom)[None,None,:]*y,
                              (self.h, self.w, 3)).astype(np.uint8).copy()
        canvas = Image.fromarray(arr).convert("RGBA")
        draw = ImageDraw.Draw(canvas)
        grid = (209, 222, 234, 255) if self.light else (21, 37, 54, 255)
        step = max(30, self.unit//9)
        for x in range(0, self.w, step):
            draw.line((x, 0, x, self.h), fill=grid)
        for yy in range(0, self.h, step):
            draw.line((0, yy, self.w, yy), fill=grid)
        draw.rounded_rectangle((int(self.w*.84), int(self.h*.13), int(self.w*1.1), int(self.h*.45)),
                               radius=int(self.unit*.12), outline=grid, width=max(2,self.unit//200))
        return canvas

    def build_shell(self, test_audio: bool):
        layer = Image.new("RGBA", (self.w, self.h))
        draw = ImageDraw.Draw(layer)
        margin = round(self.w*.065)
        channel = text_tile(self.script.channel, int(self.w*.68), int(self.h*.045), path=self.font,
                            max_size=int(self.unit*.030), fill=self.muted)
        layer.alpha_composite(channel, (margin, round(self.h*.055)))
        number = f"{self.index+1:02d} / {len(self.script.scenes):02d}"
        tag = text_tile(number, int(self.w*.16), int(self.h*.045), path=self.font,
                       max_size=int(self.unit*.026), fill=self.accent, align="center")
        layer.alpha_composite(tag, (round(self.w*.79), round(self.h*.055)))
        draw.line((margin, round(self.h*.115), self.w-margin, round(self.h*.115)), fill=self.muted, width=1)
        if test_audio:
            label = text_tile("DEMO KỸ THUẬT • ÂM THỬ", int(self.w*.8), max(14,int(self.h*.035)),
                              path=self.font, max_size=int(self.unit*.022), fill="#E99D35", align="center")
            layer.alpha_composite(label, (round(self.w*.1), round(self.h*.94)))
        return layer

    def add_text(self, text, box, *, size=.052, color=None, delay=.15, motion="up", align="left", card=False):
        if not text:
            return
        x,y,w,h = box
        tile = text_tile(text, round(w), round(h), path=self.font, max_size=round(self.unit*size),
                         fill=color or self.fg, align=align, background=self.card if card else None,
                         padding=round(self.unit*.025) if card else 0)
        self.elements.append(Element(tile, round(x), round(y), delay=delay, motion=motion))

    def build_elements(self):
        s, w, h = self.scene, self.w, self.h
        x, width = w*.075, w*.85
        if s.layout in ("hook", "outro"):
            self.add_text("KHÁM PHÁ" if s.layout == "hook" else "GHI NHỚ", (x,h*.19,width,h*.055),
                          size=.029,color=self.accent,align="center",delay=.05)
            self.add_text(s.title,(x,h*.28,width,h*.25),size=.093,align="center",motion="zoom")
            self.add_text(s.subtitle,(x,h*.56,width,h*.15),size=.041,color=self.muted,align="center",delay=.55)
        elif s.layout == "stat-hero":
            self.add_text(s.title,(x,h*.18,width,h*.12),size=.052)
            self.add_text(s.value,(x,h*.33,width,h*.23),size=.16,color=self.accent,align="center",motion="zoom")
            self.add_text(s.subtitle,(x,h*.59,width,h*.13),size=.040,color=self.muted,align="center",delay=.55)
        elif s.layout == "feature-list":
            self.add_text(s.title,(x,h*.17,width,h*.13),size=.059)
            count = len(s.bullets)
            row_h = min(h*.105, h*.40/count)
            for i, bullet in enumerate(s.bullets):
                self.add_text(f"{i+1:02d}   {bullet}",(x,h*.33+i*(row_h+h*.015),width,row_h),
                              size=.041,card=True,delay=.60+i*.15,motion="left")
        elif s.layout == "comparison":
            self.add_text(s.title,(x,h*.17,width,h*.13),size=.055)
            wide = w >= h*.95
            for i, side in enumerate((s.left,s.right)):
                assert side is not None
                box = (x+i*width*.52,h*.34,width*.48,h*.36) if wide else (x,h*.33+i*h*.205,width,h*.18)
                bx,by,bw,bh = box
                tile = Image.new("RGBA", (round(bw),round(bh)), self.card)
                self.elements.append(Element(tile,round(bx),round(by),delay=.15+i*.45,motion="left" if i==0 else "right"))
                self.add_text(side.label,(bx+bw*.06,by+bh*.08,bw*.88,bh*.29),size=.035,color=self.muted,
                              delay=.25+i*.45,align="center")
                self.add_text(side.value,(bx+bw*.06,by+bh*.40,bw*.88,bh*.49),size=.060,
                              color=self.accent if i else self.fg,delay=.35+i*.45,align="center")
        else:  # callout
            self.add_text(s.title,(x,h*.25,width,h*.29),size=.075,align="center",card=True,motion="zoom")
            self.add_text(s.subtitle,(x,h*.58,width,h*.14),size=.041,color=self.muted,align="center",delay=.55)

    def frame(self, local_time: float, global_time: float, total_duration: float):
        image = self.background.copy()
        if self.photo is not None:
            # Slow Ken Burns motion, capped to keep memory predictable.
            scale = 1 + min(local_time*.004, .08)
            photo = self.photo.resize((round(self.w*scale),round(self.h*scale)),Image.Resampling.BILINEAR)
            dx,dy = (photo.width-self.w)//2,(photo.height-self.h)//2
            photo = photo.crop((dx,dy,dx+self.w,dy+self.h)).convert("RGBA")
            image = Image.blend(photo,self.background,.80 if self.light else .72)
        image.alpha_composite(self.shell)
        for element in self.elements:
            element.paint(image,local_time)
        if self.o.subtitles:
            active = next((c for c in self.captions if c["start"] <= global_time < c["end"]),None)
            if active:
                text = active["text"]
                if text not in self.caption_tiles:
                    self.caption_tiles[text] = text_tile(text,round(self.w*.88),round(self.h*.13),
                        path=self.font,max_size=round(self.unit*.037),fill=self.fg,align="center",
                        background=self.card,padding=round(self.unit*.023))
                image.alpha_composite(self.caption_tiles[text],(round(self.w*.06),round(self.h*.79)))
        draw = ImageDraw.Draw(image)
        progress = max(0,min(1,global_time/total_duration))
        draw.rectangle((0,self.h-4,round(self.w*progress),self.h),fill=self.accent)
        return image.convert("RGB")


def render_video(script: Script, timeline: dict, options: RenderOptions, output: Path,
                 progress: Callable[[str],None] = print) -> Path:
    if timeline["fps"] != options.fps:
        raise ValueError("FPS timeline khác cấu hình. Chạy lại build để căn audio theo FPS mới.")
    count = timeline["frames"]
    duration = count/options.fps
    partial = output / "video.partial.mp4"
    destination = output / "video.mp4"
    args = [os.getenv("FFMPEG_BIN","ffmpeg"),"-y","-v","error","-f","rawvideo","-pix_fmt","rgb24",
            "-s",f"{options.width}x{options.height}","-r",str(options.fps),"-i","pipe:0",
            "-i",str(output/"voice.wav")]
    if options.bgm:
        music = Path(options.bgm).expanduser().resolve()
        if not music.is_file():
            raise ValueError(f"Không tìm thấy nhạc nền: {music}")
        args += ["-stream_loop","-1","-i",str(music),"-filter_complex",
                 f"[2:a]volume={options.bgm_volume},afade=t=out:st={max(0,duration-1):.6f}:d=1[bg];"
                 "[1:a][bg]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:latency=1[a]",
                 "-map","0:v","-map","[a]"]
    else:
        args += ["-map","0:v","-map","1:a"]
    args += ["-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p",
             "-c:a","aac","-b:a","192k","-t",f"{duration:.6f}","-movflags","+faststart",str(partial)]
    # Preflight every scene so layout/image errors occur before encoding.
    painters = [ScenePainter(script,s,i,options,output,timeline) for i,s in enumerate(script.scenes)]
    scene_index = 0
    log_path = output / "render.log"
    proc = None
    try:
        with log_path.open("wb") as log:
            proc = subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log)
            assert proc.stdin is not None
            for frame_index in range(count):
                time = frame_index/options.fps
                while scene_index+1 < len(painters) and time >= timeline["scenes"][scene_index]["end"]:
                    scene_index += 1
                start = timeline["scenes"][scene_index]["start"]
                frame = painters[scene_index].frame(time-start,time,duration)
                if frame_index == min(count-1, round(options.fps*1.1)):
                    frame.save(output/"poster.jpg",quality=92)
                proc.stdin.write(frame.tobytes())
                if frame_index % max(1,options.fps*2) == 0:
                    progress(f"Render {frame_index/count:.0%} — {time:.1f}/{duration:.1f} giây")
            proc.stdin.close()
            if proc.wait(timeout=180) != 0:
                raise RuntimeError("FFmpeg render thất bại.")
        partial.replace(destination)
        progress(f"Hoàn thành: {destination}")
        return destination
    except BaseException as exc:
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.wait()
        partial.unlink(missing_ok=True)
        if isinstance(exc,(BrokenPipeError,RuntimeError)) and log_path.exists():
            details = log_path.read_text(encoding="utf-8",errors="replace")[-2500:]
            raise RuntimeError(f"Render thất bại: {details or str(exc)}") from exc
        raise
