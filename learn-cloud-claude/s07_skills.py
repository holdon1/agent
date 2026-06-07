"""
skills 文件组成
metadata：技能名称，技能描述，作者，版本，标签
body：正文，技能具体内容
格式：
---
name: git
description: Git assistant
---
# git
git content
"""
import os.path
from pathlib import Path

import yaml
WORK_DIR = Path.cwd()
# 工具函数：解析md文件
def _parse_frontmatter(text:str) -> tuple[dict,str]:
    """Parse YAML frontmatter from SKILL.md. Returns (meta, body)."""
    # 如果文档不以 "---" 开头，返回空的metadata
    if not text.startswith("---"):
        return ({},text)
    # 拆分文档，如果文档长度少于3，返回空的metadata
    parts = text.split("---",2)
    print(f"parts: {parts}")
    if len(parts) < 3:
        return ({},text)
    # 解析yaml
    try:
        meta = yaml.safe_load(parts[1]) or {}
        print(f"meta: {meta}")
    except yaml.YAMLError as exc:
        meta = {}
    return meta,parts[2].strip()

    # 返回正确的metadata 和 body
# skills 注册表
SKILLS_REGISTRY : dict[str, dict] = {}

# 工具函数（扫描器）：扫描skills文件并初始化skills注册表
SKILLS_DIR = WORK_DIR / "skills"
print(f"SKILLS_DIR: {SKILLS_DIR}")
def _scan_skills():
    """Scan skills/ dir, populate SKILL_REGISTRY with name/description/content."""
    # 检查skills目录是否存在
    if not os.path.exists(SKILLS_DIR):
        return
    # 遍历skills 下所有目录
    for dir in sorted(SKILLS_DIR.iterdir()):
        # 过滤非目录
        if not Path.is_dir(dir):
            continue
        # 构造md文件路径
        manifest = dir / "SKILL.md"
        if manifest.exists():
            # 读取文件，获取文本
            raw = manifest.read_text()
            # 解析文件
            meta,body = _parse_frontmatter(raw)
            # 注册到SKILLS 注册表
            # 获取名称 ，其中key优先使用meta中的name，其次是目录名称
            name = meta.get("name",dir.name)
            # 获取描述
            desc = meta.get("description",raw.split("\n")[0].lstrip("#").strip())
            SKILLS_REGISTRY[name] = {
                "name":name,
                "description":desc,
                "content":raw # 整个skills文件
            }
# 初始化skills注册表
_scan_skills()

# 工具函数：展示所有的skills
def list_skills() -> str:
    return "\n".join(f"- **{s['name']}**: {s['description']}" for s in SKILLS_REGISTRY.values())
# 工具函数：整合上述函数，构建系统提示词
def build_system() -> str:
    catalog = list_skills()
    return (
        f"You are a coding agent at {WORK_DIR}. "
        f"Skills available:\n{catalog}\n"
        "Use load_skill to get full details when needed."
    )


def load_skill(name: str) -> str:
    skill = SKILLS_REGISTRY.get(name)
    if not skill:
        return f"Skill not found: {name}"
    return skill["content"]

if __name__ == '__main__':
    SYSTEM = build_system()
    print(f"SYSTEM:{SYSTEM}")
