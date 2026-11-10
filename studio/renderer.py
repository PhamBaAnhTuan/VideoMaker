"""Responsive Pillow motion graphics → FFmpeg H.264.

Six layout concepts and entrance timings ported from auto-video-gen (MIT,
Copyright (c) 2026 CuongIT). Reimplemented in Python: no browser/GSAP/Node runtime.
Changes: responsive geometry, measured text fitting, captions, image motion,
light theme, eight visual styles, workflow/quote layouts, spring/reveal effects,
bounce/glitch/wave animations, icon decorators, particles/bokeh ambient effects,
transitions, configurable frame rate and safe raw-frame encoding.
"""
from __future__ import annotations

import math
import os
import re
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageColor
from .models import Script, Scene, RenderOptions
from .media_tools import resolve_media_tool


VISUAL_STYLES = {
    "studio":    ("Studio",        "Tinh giản · chữ rõ · chuyển động dịu"),
    "neon":      ("Neon Tech",     "Quầng sáng · hạt chuyển động · mở dần"),
    "editorial": ("Tạp chí",      "Tông ấm · chữ hiện dần · chuyển cảnh mềm"),
    "playful":   ("Pop & Bounce",  "Màu tươi · hình học · thẻ nảy lần lượt"),
    "cyberpunk": ("Cyber·Punk",    "Neon hồng-xanh · scan-line · glitch sốc mắt"),
    "nature":    ("Nature Calm",   "Xanh thiên nhiên · bokeh · chuyển động nhẹ nhàng"),
    "retro":     ("Retro Wave",    "Tím-cam vintage · dots · vibe 80s"),
    "glass":     ("Glassmorphism","Kính mờ · blur · gradient trong suốt"),
    "runway":    ("Runway Editorial", "Màu thời trang · bố cục lệch · chữ serif"),
}

# ── Icon decorators per layout ──────────────────────────────────────────────
LAYOUT_ICONS = {
    "hook":         "🔥",
    "outro":        "💡",
    "stat-hero":    "📊",
    "feature-list": "✨",
    "workflow":     "🚀",
    "quote":        "💬",
    "comparison":   "⚖️",
    "callout":      "🎯",
}

# ── Palette definitions ──────────────────────────────────────────────────────
STYLE_PALETTES = {
    # (bg_top, bg_bottom, accent, accent_alt, card_dark, card_light, grid_dark, grid_light)
    "studio": {
        "dark":  {"top": (24,24,27),   "bot": (31,31,35),   "accent": "#D5B98C", "alt": "#E8D7B7",
                  "card": (39,39,43,244), "grid": (52,52,57,255)},
        "light": {"top": (248,247,244),"bot": (242,240,235),"accent": "#956F42", "alt": "#B08A5C",
                  "card": (255,254,251,248), "grid": (222,219,212,255)},
    },
    "runway": {
        "dark":  {"top": (28,26,27), "bot": (39,34,35), "accent": "#D99A83", "alt": "#D8C6A8",
                  "card": (46,41,41,238), "grid": (174,151,143,255)},
        "light": {"top": (245,242,235), "bot": (236,230,219), "accent": "#8B4550", "alt": "#A77B58",
                  "card": (250,247,240,245), "grid": (151,122,105,255)},
    },
    "neon": {
        "dark":  {"top": (5,2,20),     "bot": (10,5,35),    "accent": "#AE92FF", "alt": "#64E3FA",
                  "card": (18,8,45,250), "grid": (30,15,60,255)},
        "light": {"top": (240,238,255),"bot": (220,210,250),"accent": "#7054CF", "alt": "#007F95",
                  "card": (210,200,240,250), "grid": (190,180,230,255)},
    },
    "editorial": {
        "dark":  {"top": (27,24,24),   "bot": (43,31,29),   "accent": "#FFBC8F", "alt": "#FFD4A8",
                  "card": (48,38,35,250), "grid": (60,45,40,255)},
        "light": {"top": (252,248,240),"bot": (237,228,215),"accent": "#AC4B25", "alt": "#C95E35",
                  "card": (238,228,214,250), "grid": (210,200,190,255)},
    },
    "playful": {
        "dark":  {"top": (15,10,30),   "bot": (25,15,45),   "accent": "#FF9CCA", "alt": "#95C8FF",
                  "card": (35,25,60,247), "grid": (45,30,70,255)},
        "light": {"top": (255,248,252),"bot": (240,230,255),"accent": "#A6376A", "alt": "#2765B0",
                  "card": (235,220,240,250), "grid": (215,200,230,255)},
    },
    "cyberpunk": {
        "dark":  {"top": (5,0,15),     "bot": (0,5,20),     "accent": "#FF2D78", "alt": "#00F5FF",
                  "card": (15,0,30,250), "grid": (0,40,60,255)},
        "light": {"top": (10,0,30),    "bot": (0,10,40),    "accent": "#FF1060", "alt": "#00D4E8",
                  "card": (20,5,50,240), "grid": (0,50,70,255)},
    },
    "nature": {
        "dark":  {"top": (5,20,10),    "bot": (8,35,18),    "accent": "#5EFFA0", "alt": "#A8FFD8",
                  "card": (10,40,20,247), "grid": (15,50,25,255)},
        "light": {"top": (240,252,244),"bot": (220,245,230),"accent": "#1A7A40", "alt": "#28A055",
                  "card": (210,240,220,250), "grid": (185,225,200,255)},
    },
    "retro": {
        "dark":  {"top": (20,5,30),    "bot": (35,8,20),    "accent": "#FF6B35", "alt": "#CC44AA",
                  "card": (40,10,50,247), "grid": (55,15,35,255)},
        "light": {"top": (255,245,235),"bot": (248,230,210),"accent": "#CC3300", "alt": "#993388",
                  "card": (240,220,200,250), "grid": (220,195,175,255)},
    },
    "glass": {
        "dark":  {"top": (10,15,35),   "bot": (20,10,50),   "accent": "#88CCFF", "alt": "#CC88FF",
                  "card": (255,255,255,35), "grid": (100,130,200,40)},
        "light": {"top": (200,220,255),"bot": (220,200,250),"accent": "#2255CC", "alt": "#8833BB",
                  "card": (255,255,255,150), "grid": (150,180,230,80)},
    },
}


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


def _blend_color(c1: tuple, c2: tuple, t: float) -> tuple:
    """Nội suy tuyến tính giữa 2 RGB tuple."""
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


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
            if self.motion in ("zoom", "spring"):
                spring = 1 - math.exp(-6*p) * math.cos(10*p)
                scale = 0.88 + 0.12 * (spring if self.motion == "spring" else ease)
                size = (max(1, round(tile.width*scale)), max(1, round(tile.height*scale)))
                tile = tile.resize(size, Image.Resampling.BICUBIC)
                x += (self.tile.width-tile.width)//2
                y += (self.tile.height-tile.height)//2

            elif self.motion == "bounce":
                # Overshoot bounce: spring với độ nảy mạnh hơn
                bounce = 1 - math.exp(-5*p) * math.cos(14*p)
                scale = 0.55 + 0.45 * bounce
                size = (max(1, round(tile.width*scale)), max(1, round(tile.height*scale)))
                tile = tile.resize(size, Image.Resampling.BICUBIC)
                x += (self.tile.width-tile.width)//2
                y += (self.tile.height-tile.height)//2

            elif self.motion == "glitch":
                # Glitch: dịch ngang ngẫu nhiên theo p, có alpha nhấp nháy
                glitch_p = max(0, (time - self.delay))
                offset_x = round(math.sin(glitch_p * 47) * self.tile.width * 0.03 * (1 - ease))
                offset_y = round(math.cos(glitch_p * 31) * self.tile.height * 0.01 * (1 - ease))
                x += offset_x
                y += offset_y

            elif self.motion == "wave":
                # Wave: mỗi dòng lên xuống như sóng biển
                alpha = np.array(tile.getchannel("A"))
                occupied = np.any(alpha > 0, axis=1)
                changes = np.diff(np.r_[False, occupied, False].astype(int))
                bands = list(zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)))
                if bands:
                    parts = []
                    for i, (top, bottom) in enumerate(bands):
                        band_progress = max(0, min(1, p * len(bands) - i * 0.3))
                        wave_y = round((1 - band_progress) * self.tile.height * 0.18)
                        part_tile = Image.new("RGBA", (tile.width, bottom - top), (0, 0, 0, 0))
                        part_tile.paste(tile.crop((0, int(top), tile.width, int(bottom))), (0, 0))
                        # Áp alpha theo progress
                        part_alpha = part_tile.getchannel("A").point(lambda a: round(a * band_progress))
                        part_tile.putalpha(part_alpha)
                        parts.append((int(top) - wave_y, part_tile))
                    tile = tile.copy()
                    tile.putalpha(tile.getchannel("A").point(lambda _: 0))
                    for (ty, pt) in parts:
                        canvas.alpha_composite(pt, (x, y + ty))
                    return

            elif self.motion in ("left", "right"):
                x += round((1-ease) * self.tile.width * 0.06 * (-1 if self.motion == "left" else 1))

            elif self.motion == "wipe":
                mask = Image.new("L", tile.size, 0)
                ImageDraw.Draw(mask).rectangle((0, 0, round(tile.width*ease), tile.height), fill=255)
                tile = tile.copy()
                tile.putalpha(Image.fromarray(np.minimum(np.array(tile.getchannel("A")), np.array(mask))))

            elif self.motion == "runway":
                # A crisp editorial reveal with a small, deliberate lateral settle.
                mask = Image.new("L", tile.size, 0)
                reveal = ImageDraw.Draw(mask)
                reveal.rectangle((0, 0, round(tile.width * ease), tile.height), fill=255)
                tile = tile.copy()
                tile.putalpha(Image.fromarray(np.minimum(np.array(tile.getchannel("A")), np.array(mask))))
                x += round((1 - ease) * self.tile.width * .025)

            elif self.motion == "typewriter":
                alpha = np.array(tile.getchannel("A"))
                occupied = np.any(alpha > 0, axis=1)
                changes = np.diff(np.r_[False, occupied, False].astype(int))
                bands = list(zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)))
                mask = Image.new("L", tile.size, 0)
                reveal = ImageDraw.Draw(mask)
                for i, (top, bottom) in enumerate(bands):
                    fraction = max(0, min(1, p*len(bands)-i))
                    if fraction:
                        columns = np.flatnonzero(np.any(alpha[top:bottom] > 0, axis=0))
                        left, right = int(columns[0]), int(columns[-1])+1
                        reveal.rectangle((left, int(top), round(left+(right-left)*fraction), int(bottom)-1), fill=255)
                tile = tile.copy()
                tile.putalpha(Image.fromarray(np.minimum(np.array(tile.getchannel("A")), np.array(mask))))

            elif self.motion != "fade":
                y += round((1-ease) * self.tile.height * 0.08)

            tile = tile.copy()
            tile.putalpha(tile.getchannel("A").point(lambda a: round(a*ease)))

        canvas.alpha_composite(tile, (x, y))


class ScenePainter:
    def __init__(self, script: Script, scene: Scene, index: int, options: RenderOptions,
                 base_dir: Path, timeline: dict):
        self.script, self.scene, self.index, self.o = script, scene, index, options
        self.w, self.h = options.width, options.height
        self.unit = min(self.w, self.h)
        self.font = font_path(options.font or os.getenv("VIDEO_FONT") or None)
        serif_candidates = [Path("C:/Windows/Fonts/times.ttf"),
                            Path("C:/Windows/Fonts/georgia.ttf"),
                            Path(__file__).parent / "assets" / "DejaVuSerif.ttf",
                            Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf")]
        self.display_font = next((str(p) for p in serif_candidates if p.is_file()), self.font)
        self.light = options.theme == "light"
        self.style = options.visual_style

        # ── Palette ──────────────────────────────────────────────────────────
        palette_key = self.style if self.style in STYLE_PALETTES else "studio"
        theme_key = "light" if self.light else "dark"
        pal = STYLE_PALETTES[palette_key][theme_key]
        self.pal = pal
        self.fg   = "#242321" if self.light else "#F1EFEA"
        self.muted = "#77736D" if self.light else "#AAA69F"
        self.card  = pal["card"]

        # Accent color — per scene cycling for styles that want variety
        accents_dark  = {"playful": ["#FF9CCA","#95C8FF","#AAE9A0","#FFD97D"],
                         "cyberpunk": ["#FF2D78","#00F5FF","#FF2D78","#00F5FF"],
                         "retro":  ["#FF6B35","#CC44AA","#FF9933","#8833CC"],
                         "nature": ["#5EFFA0","#A8FFD8","#3DFFB0","#7AFFCC"],
                         "neon":   ["#AE92FF","#64E3FA","#D0B8FF","#50D8FF"],
                         "glass":  ["#88CCFF","#CC88FF","#AAEEFF","#EE88FF"]}
        accents_light = {"playful": ["#A6376A","#2765B0","#247C53","#B86D10"],
                         "cyberpunk": ["#FF1060","#0090CC","#FF1060","#0090CC"],
                         "retro":  ["#CC3300","#993388","#AA5500","#661188"],
                         "nature": ["#1A7A40","#28A055","#0E5C2D","#1D8A47"],
                         "neon":   ["#7054CF","#007F95","#5040AF","#006080"],
                         "glass":  ["#2255CC","#8833BB","#1144AA","#772299"]}
        cycle_map = accents_dark if not self.light else accents_light
        if self.style in cycle_map:
            cycle = cycle_map[self.style]
            self.accent = cycle[index % len(cycle)]
            self.accent_alt = cycle[(index + 1) % len(cycle)]
        else:
            self.accent = pal["accent"]
            self.accent_alt = pal.get("alt", pal["accent"])

        # Foreground override for very dark cyberpunk themes
        if self.style == "cyberpunk":
            self.fg = "#EEFFFF"
            self.muted = "#88BBCC"

        self.elements: list[Element] = []
        self.captions = [c for c in timeline["captions"] if c["scene"] == scene.id]
        self.caption_tiles: dict[str, Image.Image] = {}
        self.background = self.make_background()

        # ── Ambient glow blob ──────────────────────────────────────────────
        radius = max(24, round(self.unit * .24))
        self.glow = Image.new("RGBA", (radius*4, radius*4))
        glow_alpha = {"neon": 90, "cyberpunk": 100, "glass": 60, "nature": 50, "retro": 70, "playful": 55}.get(self.style, 30)
        glow_color = ImageColor.getrgb(self.accent) + (glow_alpha,)
        ImageDraw.Draw(self.glow).ellipse((radius, radius, radius*3, radius*3), fill=glow_color)
        self.glow = self.glow.filter(ImageFilter.GaussianBlur(radius * .55))

        # Second glow for styles with dual color
        self.glow2 = None
        if self.style in ("cyberpunk", "neon", "glass", "retro"):
            radius2 = max(18, round(self.unit * .18))
            self.glow2 = Image.new("RGBA", (radius2*4, radius2*4))
            glow2_color = ImageColor.getrgb(self.accent_alt) + (glow_alpha,)
            ImageDraw.Draw(self.glow2).ellipse((radius2, radius2, radius2*3, radius2*3), fill=glow2_color)
            self.glow2 = self.glow2.filter(ImageFilter.GaussianBlur(radius2 * .6))

        self.stat_tiles = {}
        self.photo = None
        if scene.image:
            path = Path(scene.image)
            path = path if path.is_absolute() else base_dir / path
            with Image.open(path) as img:
                self.photo = ImageOps.fit(ImageOps.exif_transpose(img).convert("RGB"), (self.w, self.h))
        self.build_elements()
        self.shell = self.build_shell(timeline.get("test_audio", False))

    def make_background(self):
        pal = self.pal
        top, bottom = pal["top"], pal["bot"]

        y = np.linspace(0, 1, self.h)[:, None, None]
        arr = np.broadcast_to(
            np.array(top)[None, None, :] * (1-y) + np.array(bottom)[None, None, :] * y,
            (self.h, self.w, 3)
        ).astype(np.uint8).copy()
        canvas = Image.fromarray(arr).convert("RGBA")
        draw = ImageDraw.Draw(canvas)
        grid = pal["grid"]
        step = max(30, self.unit // 9)

        if self.style == "neon":
            for x in range(0, self.w, step):
                draw.line((x, 0, x, self.h), fill=grid[:3] + (22,))
            for yy in range(0, self.h, step):
                draw.line((0, yy, self.w, yy), fill=grid[:3] + (22,))

        elif self.style == "editorial":
            draw.rectangle(
                (round(self.w*.065), round(self.h*.15), round(self.w*.075), round(self.h*.72)),
                fill=self.accent
            )

        elif self.style == "cyberpunk":
            # Scanlines + horizontal neon bars
            for yy in range(0, self.h, 4):
                draw.line((0, yy, self.w, yy), fill=(0, 255, 255, 12))
            for x in range(0, self.w, step * 2):
                draw.line((x, 0, x, self.h), fill=(255, 0, 120, 18))
            # Corner accent bars
            bar_w = max(3, self.unit // 100)
            accent_rgb = ImageColor.getrgb(self.accent) + (200,)
            alt_rgb = ImageColor.getrgb(self.accent_alt) + (200,)
            draw.rectangle((0, 0, bar_w, self.h), fill=accent_rgb)
            draw.rectangle((self.w - bar_w, 0, self.w, self.h), fill=alt_rgb)
            draw.rectangle((0, 0, self.w, bar_w), fill=accent_rgb)
            draw.rectangle((0, self.h - bar_w, self.w, self.h), fill=alt_rgb)

        elif self.style == "nature":
            # Organic curved lines (leaf veins)
            vein_color = ImageColor.getrgb(self.accent) + (20,)
            for i in range(5):
                pts = []
                base_x = round(self.w * (0.1 + i * 0.2))
                for yy in range(0, self.h, 8):
                    offset = round(math.sin(yy / 80 + i * 1.2) * self.unit * 0.04)
                    pts.append((base_x + offset, yy))
                if len(pts) >= 2:
                    draw.line(pts, fill=vein_color, width=max(1, self.unit // 200))

        elif self.style == "retro":
            # Dot grid pattern (halftone feel)
            dot_r = max(1, self.unit // 160)
            dot_color = ImageColor.getrgb(self.accent) + (35,)
            for gy in range(dot_r * 2, self.h, step):
                for gx in range(dot_r * 2, self.w, step):
                    draw.ellipse((gx - dot_r, gy - dot_r, gx + dot_r, gy + dot_r), fill=dot_color)
            # Horizontal stripe bands
            for i in range(4):
                band_y = round(self.h * (0.2 + i * 0.2))
                stripe_color = ImageColor.getrgb(self.accent_alt) + (12,)
                draw.rectangle((0, band_y, self.w, band_y + max(2, self.unit // 120)), fill=stripe_color)

        elif self.style == "glass":
            # Frosted glass circles in background
            for i in range(3):
                cx = round(self.w * (0.2 + i * 0.3))
                cy = round(self.h * (0.25 + i * 0.2))
                r = round(self.unit * (0.25 + i * 0.07))
                blob = Image.new("RGBA", (r*2, r*2))
                circle_color = ImageColor.getrgb(self.accent if i % 2 == 0 else self.accent_alt) + (22,)
                ImageDraw.Draw(blob).ellipse((0, 0, r*2-1, r*2-1), fill=circle_color)
                blob = blob.filter(ImageFilter.GaussianBlur(r * 0.4))
                canvas.alpha_composite(blob, (cx - r, cy - r))

        elif self.style == "playful":
            # No grid — clean, just the gradient. Decorations done in ambient.
            pass

        elif self.style == "runway":
            # Lookbook registration mark: one quiet margin rule and a short footer dash.
            rule = grid[:3] + (38,)
            draw.line((round(self.w*.105), round(self.h*.16), round(self.w*.105), round(self.h*.86)),
                      fill=rule, width=max(1, self.unit // 500))
            draw.line((round(self.w*.105), round(self.h*.86), round(self.w*.19), round(self.h*.86)),
                      fill=ImageColor.getrgb(self.accent) + (180,), width=max(1, self.unit // 220))

        # Rounded corner decoration (neon/glass)
        if self.style in ("neon", "glass"):
            draw.rounded_rectangle(
                (int(self.w*.84), int(self.h*.13), int(self.w*1.1), int(self.h*.45)),
                radius=int(self.unit*.12), outline=grid, width=max(2, self.unit//200)
            )
        return canvas

    def build_shell(self, test_audio: bool):
        layer = Image.new("RGBA", (self.w, self.h))
        draw = ImageDraw.Draw(layer)
        margin = round(self.w * .065)
        channel = text_tile(self.script.channel, int(self.w*.68), int(self.h*.045), path=self.font,
                            max_size=int(self.unit*.030), fill=self.muted)
        layer.alpha_composite(channel, (margin, round(self.h * .055)))
        number = f"{self.index+1:02d} / {len(self.script.scenes):02d}"
        tag = text_tile(number, int(self.w*.16), int(self.h*.045), path=self.font,
                       max_size=int(self.unit*.026), fill=self.accent, align="center")
        layer.alpha_composite(tag, (round(self.w*.79), round(self.h*.055)))
        line_color = self.muted
        if self.style == "cyberpunk":
            line_color = self.accent
        draw.line((margin, round(self.h*.115), self.w-margin, round(self.h*.115)), fill=line_color, width=1)
        # Keep the header quiet and typographic; decorative emoji badges compete with the title.
        if test_audio:
            label = text_tile("DEMO KỸ THUẬT • ÂM THỬ", int(self.w*.8), max(14, int(self.h*.035)),
                              path=self.font, max_size=int(self.unit*.022), fill="#E99D35", align="center")
            layer.alpha_composite(label, (round(self.w*.1), round(self.h*.94)))
        return layer

    def add_text(self, text, box, *, size=.052, color=None, delay=.15, motion="up",
                 align="left", card=False, glow_accent=False, serif=False):
        if not text:
            return
        x, y, w, h = box
        fill = color or self.fg

        # Cyberpunk text glow: tạo shadow layer với accent color
        if glow_accent and self.style in ("cyberpunk", "neon"):
            glow_tile = text_tile(text, round(w), round(h), path=self.font,
                                  max_size=round(self.unit*size), fill=self.accent,
                                  align=align, padding=round(self.unit*.025) if card else 0)
            glow_tile = glow_tile.filter(ImageFilter.GaussianBlur(max(1, self.unit // 80)))
            self.elements.append(Element(glow_tile, round(x - 2), round(y - 2), delay=delay, duration=.4, motion="fade"))

        font = self.display_font if serif else self.font
        tile = text_tile(text, round(w), round(h), path=font, max_size=round(self.unit*size),
                         fill=fill, align=align, background=self.card if card else None,
                         padding=round(self.unit*.025) if card else 0)

        selected = self.scene.animation
        if selected == "auto":
            style_defaults = {
                "studio":    motion,
                "neon":      "fade",
                "editorial": "fade",
                "playful":   "fade",
                "cyberpunk": "fade",
                "nature":    "fade",
                "retro":     "fade",
                "glass":     "fade",
                "runway":    "runway",
            }
            selected = style_defaults.get(self.style, motion)
        elif selected == "slide":
            selected = motion if motion in ("left", "right") else "up"
        if selected == "typewriter" and card:
            selected = "wipe"

        dur = {"typewriter": 1.1, "wave": 0.9, "glitch": 0.7, "bounce": 0.7}.get(selected, .78)
        self.elements.append(Element(tile, round(x), round(y), delay=delay, duration=dur, motion=selected))

    def build_elements(self):
        s, w, h = self.scene, self.w, self.h
        x, width = w * .075, w * .85

        if self.style == "runway":
            self._build_runway_elements()
            return

        if s.layout in ("hook", "outro"):
            label = "KHÁM PHÁ" if s.layout == "hook" else "GHI NHỚ"
            self.add_text(label, (x, h*.19, width, h*.055),
                          size=.029, color=self.accent, align="center", delay=.05, glow_accent=True)
            self.add_text(s.title, (x, h*.28, width, h*.25), size=.093, align="center", motion="zoom")
            self.add_text(s.subtitle, (x, h*.56, width, h*.15), size=.041, color=self.muted, align="center", delay=.55)

        elif s.layout == "stat-hero":
            self.add_text(s.title, (x, h*.18, width, h*.12), size=.052)
            self.add_text(s.subtitle, (x, h*.59, width, h*.13), size=.040, color=self.muted, align="center", delay=.55)

        elif s.layout == "feature-list":
            self.add_text(s.title, (x, h*.17, width, h*.13), size=.059, glow_accent=True)
            count = len(s.bullets)
            row_h = min(h*.105, h*.40 / count)
            for i, bullet in enumerate(s.bullets):
                # Bullet icon per style
                bullet_icon = {"cyberpunk": "▶", "nature": "🌿", "retro": "★", "glass": "◆",
                               "neon": "◈", "playful": "●"}.get(self.style, "›")
                self.add_text(f"{bullet_icon}  {bullet}",
                              (x, h*.33 + i*(row_h + h*.015), width, row_h),
                              size=.041, card=True, delay=.60 + i*.15, motion="left")

        elif s.layout == "workflow":
            self.add_text(s.title, (x, h*.17, width, h*.12), size=.060, glow_accent=True)
            count = len(s.bullets)
            wide = w > h * 1.2
            for i, step in enumerate(s.bullets):
                if wide:
                    bw = width / count
                    box = (x + i*bw, h*.39, bw*.88, h*.23)
                    arrow = (x + i*bw + bw*.88, h*.45, bw*.12, h*.09)
                else:
                    row = h * .40 / count
                    box = (x, h*.32 + i*row, width, row*.74)
                    arrow = (w*.45, h*.32 + i*row + row*.74, w*.1, row*.26)
                step_num = {"cyberpunk": f"[{i+1:02d}]", "retro": f"0{i+1}", "nature": f"({i+1})"}.get(self.style, f"{i+1:02d}")
                self.add_text(f"{step_num}   {step}", box, size=.040, card=True, delay=.2 + i*.27, motion="zoom")
                if i < count - 1:
                    ax, ay, aw, ah = map(round, arrow)
                    tile = Image.new("RGBA", (max(1, aw), max(1, ah)))
                    draw = ImageDraw.Draw(tile)
                    accent_rgb = ImageColor.getrgb(self.accent)
                    points = [(aw*.15, ah*.5), (aw*.8, ah*.5)] if wide else [(aw*.5, ah*.05), (aw*.5, ah*.85)]
                    head = [(aw*.5, ah*.25), (aw*.8, ah*.5), (aw*.5, ah*.75)] if wide else \
                           [(aw*.3, ah*.45), (aw*.5, ah*.85), (aw*.7, ah*.45)]
                    draw.line(points, fill=self.accent, width=max(1, self.unit//180))
                    draw.line(head, fill=self.accent, width=max(1, self.unit//180))
                    # Neon glow on arrow for cyberpunk
                    if self.style in ("cyberpunk", "neon"):
                        glow_line = tile.filter(ImageFilter.GaussianBlur(max(1, self.unit // 120)))
                        self.elements.append(Element(glow_line, ax, ay, delay=.5 + i*.27, motion="fade"))
                    self.elements.append(Element(tile, ax, ay, delay=.4 + i*.27, motion="fade"))

        elif s.layout == "quote":
            # Large quotation mark
            self.add_text("\u201c", (x, h*.17, width, h*.16), size=.19, color=self.accent,
                          align="center", motion="zoom", glow_accent=True)
            self.add_text(s.title, (x, h*.32, width, h*.24), size=.072, align="center")
            self.add_text(s.subtitle, (x, h*.60, width, h*.12), size=.035, color=self.muted, align="center", delay=.6)

        elif s.layout == "comparison":
            self.add_text(s.title, (x, h*.17, width, h*.13), size=.055)
            wide = w >= h * .95
            for i, side in enumerate((s.left, s.right)):
                assert side is not None
                box = (x + i*width*.52, h*.34, width*.48, h*.36) if wide else \
                      (x, h*.33 + i*h*.205, width, h*.18)
                bx, by, bw, bh = box
                # Card background with style-specific coloring
                card_img = Image.new("RGBA", (round(bw), round(bh)), self.card)
                if self.style in ("cyberpunk", "neon"):
                    # Subtle border glow
                    border_draw = ImageDraw.Draw(card_img)
                    border_color = ImageColor.getrgb(self.accent if i == 1 else self.accent_alt) + (120,)
                    border_draw.rounded_rectangle((0, 0, round(bw)-1, round(bh)-1),
                                                  radius=max(6, round(self.unit*.02)), outline=border_color,
                                                  width=max(1, self.unit // 200))
                self.elements.append(Element(card_img, round(bx), round(by), delay=.15 + i*.45,
                                             motion="left" if i == 0 else "right"))
                self.add_text(side.label, (bx + bw*.06, by + bh*.08, bw*.88, bh*.29),
                              size=.035, color=self.muted, delay=.25 + i*.45, align="center")
                self.add_text(side.value, (bx + bw*.06, by + bh*.40, bw*.88, bh*.49), size=.060,
                              color=self.accent if i else self.fg, delay=.35 + i*.45, align="center")
        else:  # callout
            self.add_text(s.title, (x, h*.25, width, h*.29), size=.075, align="center",
                          card=True, motion="zoom", glow_accent=True)
            self.add_text(s.subtitle, (x, h*.58, width, h*.14), size=.041, color=self.muted,
                          align="center", delay=.55)

    def _build_runway_elements(self):
        """Asymmetric fashion lookbook composition with restrained typography."""
        s, w, h = self.scene, self.w, self.h
        x, width = w * .145, w * .74
        self.add_text(f"LOOK {self.index + 1:02d}   /   {s.layout.upper()}",
                      (x, h*.17, width, h*.055), size=.023, color=self.accent, delay=.06)

        if s.layout in ("hook", "outro"):
            self.add_text(s.title, (x, h*.31, width, h*.26), size=.105,
                          motion="runway", serif=True)
            self.add_text(s.subtitle, (x, h*.61, width*.82, h*.13), size=.038,
                          color=self.muted, delay=.48)
        elif s.layout == "stat-hero":
            self.add_text(s.title, (x, h*.22, width, h*.13), size=.052, serif=True)
            self.add_text(s.subtitle, (x, h*.66, width*.82, h*.12), size=.036,
                          color=self.muted, delay=.5)
        elif s.layout == "feature-list":
            self.add_text(s.title, (x, h*.22, width, h*.14), size=.066, serif=True)
            count = max(1, len(s.bullets))
            row_h = min(h*.12, h*.43/count)
            for i, item in enumerate(s.bullets):
                yy = h*.42 + i*row_h
                self.add_text(f"{i+1:02d}  /", (x, yy, width*.18, row_h*.76), size=.027,
                              color=self.accent, delay=.36 + i*.12, motion="runway")
                self.add_text(item, (x + width*.17, yy, width*.83, row_h*.76), size=.039,
                              delay=.42 + i*.12, motion="runway")
        elif s.layout == "workflow":
            self.add_text(s.title, (x, h*.21, width, h*.13), size=.065, serif=True)
            count = max(1, len(s.bullets))
            row_h = h*.44/count
            for i, item in enumerate(s.bullets):
                yy = h*.40 + i*row_h
                self.add_text(f"{i+1:02d}   {item}", (x, yy, width, row_h*.75), size=.037,
                              delay=.30 + i*.15, motion="runway")
        elif s.layout == "quote":
            self.add_text("“", (x, h*.20, width*.2, h*.13), size=.17,
                          color=self.accent, motion="runway", serif=True)
            self.add_text(s.title, (x, h*.34, width, h*.25), size=.066,
                          motion="runway", serif=True)
            self.add_text(s.subtitle, (x, h*.64, width*.8, h*.10), size=.034,
                          color=self.muted, delay=.48)
        elif s.layout == "comparison":
            self.add_text(s.title, (x, h*.21, width, h*.13), size=.061, serif=True)
            wide = w >= h*.95
            for i, side in enumerate((s.left, s.right)):
                if side is None:
                    continue
                bx = x + width*i*.52 if wide else x
                by = h*.42 if wide else h*(.40 + i*.22)
                bw = width*.46 if wide else width
                self.add_text(side.label.upper(), (bx, by, bw, h*.055), size=.024,
                              color=self.muted, delay=.30 + i*.13)
                self.add_text(side.value, (bx, by+h*.065, bw, h*.16), size=.057,
                              color=self.accent if i else self.fg, delay=.38 + i*.13,
                              motion="runway", serif=True)
        else:
            self.add_text(s.title, (x, h*.31, width, h*.23), size=.087,
                          motion="runway", serif=True)
            self.add_text(s.subtitle, (x, h*.60, width*.82, h*.13), size=.038,
                          color=self.muted, delay=.48)

    def paint_ambient(self, image: Image.Image, time: float):
        overlay = Image.new("RGBA", image.size)
        draw = ImageDraw.Draw(overlay)
        accent_rgb = ImageColor.getrgb(self.accent)
        alt_rgb = ImageColor.getrgb(self.accent_alt)

        if self.style in ("neon", "playful", "cyberpunk", "glass", "retro", "nature"):
            # Primary glow blob — floating animation
            gx = round(self.w * .7 + math.sin(time * .35) * self.unit * .12) - self.glow.width // 2
            gy = round(self.h * .35 + math.cos(time * .3) * self.unit * .14) - self.glow.height // 2
            image.alpha_composite(self.glow, (gx, gy))

        if self.glow2 and self.style in ("cyberpunk", "neon", "glass", "retro"):
            # Secondary glow at opposite position
            gx2 = round(self.w * .2 + math.sin(time * .28 + 2) * self.unit * .10) - self.glow2.width // 2
            gy2 = round(self.h * .65 + math.cos(time * .32 + 1) * self.unit * .12) - self.glow2.height // 2
            image.alpha_composite(self.glow2, (gx2, gy2))

        if self.style == "neon":
            # Floating neon particles
            color = accent_rgb + (65,)
            for i in range(18):
                px = round((i * .618 * self.w + time * (6 + i % 4)) % self.w)
                py = round((i * .381 * self.h - time * (9 + i % 3)) % self.h)
                r = max(1, self.unit // 250)
                draw.ellipse((px-r, py-r, px+r, py+r), fill=color)

        elif self.style == "cyberpunk":
            # Scan-line flicker overlay
            scan_alpha = round(12 + 8 * math.sin(time * 4.7))
            for yy in range(0, self.h, 3):
                draw.line((0, yy, self.w, yy), fill=(0, 240, 255, scan_alpha))
            # Glitch horizontal bars
            if math.sin(time * 13.3) > 0.82:
                bar_y = round(abs(math.sin(time * 7.1)) * self.h)
                bar_h = max(2, self.unit // 60)
                shift = round(math.sin(time * 23) * self.w * 0.04)
                draw.rectangle((0, bar_y, self.w, bar_y + bar_h), fill=(255, 0, 120, 35))
                # RGB channel split hint
                draw.rectangle((shift, bar_y + bar_h // 3, self.w + shift, bar_y + bar_h * 2 // 3),
                                fill=(0, 255, 255, 20))
            # Fast flickering particles
            for i in range(12):
                px = round((i * .573 * self.w + time * (8 + i % 5)) % self.w)
                py = round((i * .419 * self.h + time * (6 + i % 3)) % self.h)
                r = max(1, self.unit // 300)
                c = accent_rgb if i % 2 == 0 else alt_rgb
                draw.ellipse((px-r, py-r, px+r, py+r), fill=c + (80,))

        elif self.style == "playful":
            # Bouncing ring decorations on the sides
            for i in range(4):
                px = round(self.w * (.03 if i % 2 == 0 else .96))
                py = round(self.h * (.22 + i * .17) + math.sin(time * 1.3 + i) * self.unit * .025)
                r = round(self.unit * (.025 + i * .005))
                draw.ellipse((px-r, py-r, px+r, py+r), outline=self.accent, width=max(1, self.unit//140))
            # Small filled dots at corners
            dot_r = max(2, self.unit // 180)
            corners = [(round(self.w*.08), round(self.h*.14)), (round(self.w*.92), round(self.h*.14)),
                       (round(self.w*.08), round(self.h*.86)), (round(self.w*.92), round(self.h*.86))]
            for (cx, cy) in corners:
                draw.ellipse((cx-dot_r, cy-dot_r, cx+dot_r, cy+dot_r),
                             fill=ImageColor.getrgb(self.accent) + (180,))

        elif self.style == "nature":
            # Bokeh floating circles (soft focus bubbles)
            for i in range(10):
                bx = round((i * .419 * self.w + time * (2 + i * .3)) % self.w)
                by = round((i * .573 * self.h - time * (1.5 + i * .4)) % self.h)
                r = max(3, round(self.unit * (.015 + (i % 4) * .008)))
                alpha = round(20 + 15 * math.sin(time * .8 + i))
                col = accent_rgb + (alpha,)
                blob = Image.new("RGBA", (r*2, r*2))
                ImageDraw.Draw(blob).ellipse((0, 0, r*2-1, r*2-1), fill=col)
                blob = blob.filter(ImageFilter.GaussianBlur(r * .5))
                overlay.alpha_composite(blob, (bx - r, by - r))
            # Leaf-vein animated line
            vein_alpha = round(25 + 10 * math.sin(time * .6))
            pts = []
            for yy in range(0, self.h, 6):
                offset = round(math.sin(yy / 70 + time * .4) * self.unit * .03)
                pts.append((round(self.w * .04) + offset, yy))
            if len(pts) >= 2:
                draw.line(pts, fill=accent_rgb + (vein_alpha,), width=max(1, self.unit // 220))

        elif self.style == "retro":
            # CRT scanlines (subtle)
            for yy in range(0, self.h, 5):
                draw.line((0, yy, self.w, yy), fill=(0, 0, 0, 18))
            # VHS-style corner date stamp decoration
            y_stamp = round(self.h * .115)
            stamp_w = max(2, self.unit // 180)
            draw.line((round(self.w * .065), y_stamp - stamp_w,
                       round(self.w * .22), y_stamp - stamp_w),
                      fill=ImageColor.getrgb(self.accent) + (90,), width=stamp_w)
            # Floating star particles
            for i in range(8):
                px = round((i * .729 * self.w + time * (3 + i % 3)) % self.w)
                py = round((i * .437 * self.h - time * (4 + i % 4)) % self.h)
                r = max(1, self.unit // 280)
                draw.ellipse((px-r, py-r, px+r, py+r),
                             fill=(accent_rgb if i % 2 == 0 else alt_rgb) + (70,))

        elif self.style == "glass":
            # Shimmer sweeping highlight
            sweep_x = round((time * 0.12 % 1.4 - 0.2) * self.w)
            sweep_w = max(10, self.unit // 12)
            shimmer = Image.new("RGBA", (max(1, sweep_w), self.h))
            for sx in range(max(1, sweep_w)):
                alpha = round(30 * math.sin(sx / max(1, sweep_w) * math.pi))
                for sy in range(self.h):
                    shimmer.putpixel((sx, sy), (255, 255, 255, alpha))
            if 0 <= sweep_x < self.w:
                overlay.alpha_composite(shimmer, (sweep_x, 0))

        elif self.style == "studio":
            # A still accent mark keeps the frame composed while the content animates.
            draw.line((round(self.w*.86), round(self.h*.115), round(self.w*.95), round(self.h*.115)),
                      fill=ImageColor.getrgb(self.accent) + (150,), width=max(1, self.unit // 500))

        elif self.style == "runway":
            # A low contrast sweep reads like light crossing a catwalk backdrop.
            sweep = round((time * .12 % 1.25 - .12) * self.w)
            if 0 <= sweep < self.w:
                draw.line((sweep, round(self.h*.16), sweep, round(self.h*.86)),
                          fill=accent_rgb + (22,), width=max(1, self.unit // 360))

        image.alpha_composite(overlay)

    def paint_stat(self, image: Image.Image, time: float):
        if self.scene.layout != "stat-hero" or time <= .15:
            return
        value = self.scene.value
        progress = min(1, max(0, (time - .15) / 1.1))
        match = re.fullmatch(r"([^\d]*)(\d+(?:[.,]\d+)?)([^\d]*)", value)
        if match and progress < 1:
            prefix, number, suffix = match.groups()
            decimals = len(re.split(r"[.,]", number)[1]) if re.search(r"[.,]", number) else 0
            current = float(number.replace(",", ".")) * (1 - (1-progress)**3)
            digits = f"{current:.{decimals}f}"
            value = prefix + (digits.replace(".", ",") if "," in number else digits) + suffix
        if value not in self.stat_tiles:
            self.stat_tiles[value] = text_tile(value, round(self.w*.85), round(self.h*.23),
                path=self.display_font if self.style == "runway" else self.font,
                max_size=round(self.unit*.16), fill=self.accent, align="center")
        tile = self.stat_tiles[value]
        # Glow behind stat number for cyberpunk/neon
        if self.style in ("cyberpunk", "neon"):
            glow_tile = tile.filter(ImageFilter.GaussianBlur(max(2, self.unit // 60)))
            Element(glow_tile, round(self.w*.075) - 3, round(self.h*.33) - 3, delay=.15, motion="spring").paint(image, time)
        if self.style == "runway":
            Element(tile, round(self.w*.075), round(self.h*.33), delay=.15, motion="runway").paint(image, time)
        else:
            Element(tile, round(self.w*.075), round(self.h*.33), delay=.15, motion="spring").paint(image, time)

    def _draw_progress_bar(self, draw: ImageDraw.ImageDraw, progress: float):
        """Draws a styled progress bar at the bottom of the frame."""
        bar_h = 4
        bar_y = self.h - bar_h
        bar_w = round(self.w * progress)

        if self.style == "cyberpunk":
            # Segmented progress bar with glow
            seg = max(4, self.unit // 60)
            accent_rgb = ImageColor.getrgb(self.accent)
            alt_rgb = ImageColor.getrgb(self.accent_alt)
            for sx in range(0, bar_w, seg + 2):
                col = accent_rgb if (sx // (seg + 2)) % 2 == 0 else alt_rgb
                draw.rectangle((sx, bar_y - 1, min(sx + seg, bar_w), self.h), fill=col + (220,))
        elif self.style in ("nature", "glass", "runway"):
            # Rounded pill progress bar
            accent_rgb = ImageColor.getrgb(self.accent)
            if bar_w > 0:
                draw.rounded_rectangle((0, bar_y - 1, bar_w, self.h), radius=bar_h, fill=accent_rgb + (200,))
        elif self.style == "retro":
            # Thick retro bar with border
            draw.rectangle((0, bar_y - 2, self.w, self.h), fill=ImageColor.getrgb(self.accent_alt) + (60,))
            draw.rectangle((0, bar_y - 2, bar_w, self.h), fill=self.accent)
        else:
            draw.rectangle((0, bar_y, bar_w, self.h), fill=self.accent)

    def frame(self, local_time: float, global_time: float, total_duration: float):
        image = self.background.copy()
        if self.photo is not None:
            scale = 1 + min(local_time * .004, .08)
            photo = self.photo.resize((round(self.w*scale), round(self.h*scale)), Image.Resampling.BILINEAR)
            dx, dy = (photo.width-self.w)//2, (photo.height-self.h)//2
            photo = photo.crop((dx, dy, dx+self.w, dy+self.h)).convert("RGBA")
            blend_alpha = .80 if self.light else .72
            if self.style in ("glass",):
                blend_alpha = .65  # show more photo through glass effect
            image = Image.blend(photo, self.background, blend_alpha)
        self.paint_ambient(image, local_time)
        image.alpha_composite(self.shell)
        for element in self.elements:
            element.paint(image, local_time)
        self.paint_stat(image, local_time)
        if self.o.subtitles:
            active = next((c for c in self.captions if c["start"] <= global_time < c["end"]), None)
            if active:
                text = active["text"]
                if text not in self.caption_tiles:
                    # Style-specific caption background
                    cap_bg = self.card
                    if self.style == "cyberpunk":
                        cap_bg = ImageColor.getrgb(self.accent) + (30,)
                    self.caption_tiles[text] = text_tile(
                        text, round(self.w*.88), round(self.h*.13),
                        path=self.font, max_size=round(self.unit*.037),
                        fill=self.fg, align="center", background=cap_bg,
                        padding=round(self.unit*.023)
                    )
                image.alpha_composite(self.caption_tiles[text], (round(self.w*.06), round(self.h*.79)))
        draw = ImageDraw.Draw(image)
        progress = max(0, min(1, global_time / total_duration))
        self._draw_progress_bar(draw, progress)
        return image.convert("RGB")


def transition_frame(previous: Image.Image, current: Image.Image, progress: float, kind: str) -> Image.Image:
    p = max(0.0, min(1.0, progress))
    if kind == "cut" or p >= 1:
        return current
    if kind == "fade":
        smooth = p * p * (3 - 2 * p)
        return Image.blend(previous, current, smooth)
    width, height = current.size
    offset = round(width * (1 - (1-p)**3))
    result = previous.copy()
    if kind == "slide":
        result.paste(previous, (-offset, 0))
        result.paste(current, (width - offset, 0))
    else:
        result.paste(current.crop((0, 0, offset, height)), (0, 0))
    return result


def render_video(script: Script, timeline: dict, options: RenderOptions, output: Path,
                 progress: Callable[[str], None] = print) -> Path:
    if timeline["fps"] != options.fps:
        raise ValueError("FPS timeline khác cấu hình. Chạy lại build để căn audio theo FPS mới.")
    count = timeline["frames"]
    duration = count / options.fps
    partial = output / "video.partial.mp4"
    destination = output / "video.mp4"
    args = [resolve_media_tool("ffmpeg"), "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{options.width}x{options.height}", "-r", str(options.fps), "-i", "pipe:0",
            "-i", str(output / "voice.wav")]
    if options.bgm:
        music = Path(options.bgm).expanduser().resolve()
        if not music.is_file():
            raise ValueError(f"Không tìm thấy nhạc nền: {music}")
        args += ["-stream_loop", "-1", "-i", str(music), "-filter_complex",
                 f"[2:a]volume={options.bgm_volume},afade=t=out:st={max(0,duration-1):.6f}:d=1[bg];"
                 "[1:a][bg]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:latency=1[a]",
                 "-map", "0:v", "-map", "[a]"]
    else:
        args += ["-map", "0:v", "-map", "1:a"]
    args += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-t", f"{duration:.6f}", "-movflags", "+faststart", str(partial)]
    # Preflight every scene so layout/image errors occur before encoding.
    painters = [ScenePainter(script, s, i, options, output, timeline) for i, s in enumerate(script.scenes)]
    scene_index = 0
    log_path = output / "render.log"
    proc = None
    try:
        with log_path.open("wb") as log:
            proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log)
            assert proc.stdin is not None
            for frame_index in range(count):
                time = frame_index / options.fps
                while scene_index + 1 < len(painters) and time >= timeline["scenes"][scene_index]["end"]:
                    scene_index += 1
                start = timeline["scenes"][scene_index]["start"]
                frame = painters[scene_index].frame(time - start, time, duration)
                transition_duration = min(.35, (timeline["scenes"][scene_index]["end"] - start) * .25)
                if scene_index > 0 and time - start < transition_duration:
                    previous_timing = timeline["scenes"][scene_index - 1]
                    previous = painters[scene_index - 1].frame(
                        previous_timing["end"] - previous_timing["start"],
                        previous_timing["end"], duration)
                    kind = script.scenes[scene_index].transition
                    if kind == "auto":
                        kind = {"studio": "fade", "neon": "fade", "editorial": "fade",
                                "playful": "fade", "cyberpunk": "fade", "nature": "fade",
                                "retro": "fade", "glass": "fade", "runway": "fade"}[options.visual_style]
                    frame = transition_frame(previous, frame, (time-start) / transition_duration, kind)
                if frame_index == min(count - 1, round(options.fps * 1.1)):
                    frame.save(output / "poster.jpg", quality=92)
                proc.stdin.write(frame.tobytes())
                if frame_index % max(1, options.fps * 2) == 0:
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
        if isinstance(exc, (BrokenPipeError, RuntimeError)) and log_path.exists():
            details = log_path.read_text(encoding="utf-8", errors="replace")[-2500:]
            raise RuntimeError(f"Render thất bại: {details or str(exc)}") from exc
        raise
