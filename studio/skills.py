"""Skill loader and manager for VieNeu Video Studio.
Allows dynamic selection of video creation styles/skills from markdown files."""
from __future__ import annotations

import os
import re
from pathlib import Path
from dataclasses import dataclass
import yaml


@dataclass
class VideoSkill:
    id: str
    name: str
    description: str
    file_path: Path
    content: str
    
    @property
    def prompt_guidelines(self) -> str:
        """Extract the editorial guidelines for the LLM prompt from the skill markdown."""
        text = self.content
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                text = parts[2].strip()
                
        # If the skill contains an agent workflow (Step 1, Step 2, etc.),
        # extract from Step 4 / editorial sections to avoid confusing the LLM with tool-calling steps
        m = re.search(r"(###?\s+(?:Step 4|Quy chuẩn|Phát âm|Biên tập|Hướng dẫn|Script|TTS|Phong cách).*)", text, re.DOTALL | re.IGNORECASE)
        if m:
            text = m.group(1).strip()
            # Also cut off any trailing agent CLI execution steps like Step 6 / Step 7 / Step 8
            m_end = re.search(r"(###?\s+Step [6-9]:\s+(?:Write|Run|Generate TikTok|Report).*)", text, re.IGNORECASE)
            if m_end:
                text = text[:m_end.start()].strip()
                
        return text


def parse_skill_file(file_path: Path) -> VideoSkill | None:
    if not file_path.is_file():
        return None
    try:
        raw_text = file_path.read_text(encoding="utf-8-sig")
    except Exception:
        return None
        
    skill_id = file_path.stem if file_path.name != "SKILL.md" else file_path.parent.name
    name = skill_id.replace("-", " ").title()
    description = ""
    
    if raw_text.startswith("---"):
        parts = raw_text.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1].strip()
            parsed_fm = {}
            try:
                loaded = yaml.safe_load(fm_text)
                if isinstance(loaded, dict):
                    parsed_fm = loaded
            except Exception:
                pass
            
            # Regex fallback if YAML safe_load failed due to unquoted colons
            if not parsed_fm:
                m_name = re.search(r"^name:\s*([^\r\n]+)", fm_text, re.M)
                if m_name:
                    parsed_fm["name"] = m_name.group(1).strip().strip("'\"")
                m_title = re.search(r"^title:\s*([^\r\n]+)", fm_text, re.M)
                if m_title:
                    parsed_fm["title"] = m_title.group(1).strip().strip("'\"")
                m_desc = re.search(r"^description:\s*([^\r\n]+)", fm_text, re.M)
                if m_desc:
                    parsed_fm["description"] = m_desc.group(1).strip().strip("'\"")
                    
            if "name" in parsed_fm:
                skill_id = str(parsed_fm["name"])
            if "title" in parsed_fm:
                name = str(parsed_fm["title"])
            elif "name" in parsed_fm:
                name = str(parsed_fm["name"]).replace("-", " ").title()
            if "description" in parsed_fm:
                description = str(parsed_fm["description"])
                
    # Fallback title if name equals id
    if name == skill_id:
        m = re.search(r"^#\s+(.+)$", raw_text, re.MULTILINE)
        if m:
            name = m.group(1).strip()
            
    return VideoSkill(
        id=skill_id,
        name=name,
        description=description,
        file_path=file_path,
        content=raw_text
    )


def get_available_skills(root_dir: Path | None = None) -> list[VideoSkill]:
    root = root_dir or Path(__file__).resolve().parent.parent
    skills: dict[str, VideoSkill] = {}
    
    # 1. Look in skills/ directory
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        for p in skills_dir.glob("**/*.md"):
            s = parse_skill_file(p)
            if s and s.id not in skills:
                skills[s.id] = s
                
    # 2. Look in skill/SKILL.md (user's provided file)
    user_skill = root / "skill" / "SKILL.md"
    if user_skill.is_file():
        s = parse_skill_file(user_skill)
        if s and s.id not in skills:
            skills[s.id] = s
            
    # Sort with create-news-video first, then alphabetically
    skill_list = list(skills.values())
    skill_list.sort(key=lambda x: (x.id != "create-news-video", x.name))
    return skill_list


def load_skill(skill_id_or_path: str | Path | None = None, root_dir: Path | None = None) -> VideoSkill:
    root = root_dir or Path(__file__).resolve().parent.parent
    available = get_available_skills(root)
    
    if not skill_id_or_path or str(skill_id_or_path).lower() in ("default", "none"):
        if available:
            return available[0]
            
    # Check if direct file path
    p = Path(skill_id_or_path)
    if not p.is_absolute():
        p = root / p
    if p.is_file():
        s = parse_skill_file(p)
        if s:
            return s
            
    # Check by id (exact or partial)
    target = str(skill_id_or_path).lower().strip()
    for s in available:
        if s.id.lower() == target:
            return s
    for s in available:
        if target in s.id.lower() or target in s.name.lower():
            return s
            
    if available:
        return available[0]
        
    return VideoSkill(
        id="default",
        name="Mặc định",
        description="Phong cách biên tập video ngắn tiêu chuẩn",
        file_path=root / "skill/SKILL.md",
        content="Quy chuẩn video ngắn tiếng Việt chuẩn motion-graphic."
    )
