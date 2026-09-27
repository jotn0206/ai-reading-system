#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py — ai-reading-system 一键构建（2026-09-26）
产出：
  1. dist/ai-reading-system.skill            本地/粉丝群分发版（zip 改后缀，frontmatter 精简为 name+description）
  2. dist/ai-reading-system-marketplace.zip  WorkBuddy 开放平台提交版（frontmatter 全字段，官方规范）
  3. 同步本机 ~/.workbuddy/skills/ai-reading-system/（frontmatter 精简版，重启会话生效）
用法: python build.py
"""
import io
import os
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / 'ai-reading-system'
DIST = ROOT / 'dist'
LOCAL_SKILLS = Path.home() / '.workbuddy' / 'skills'
SKILL_NAME = 'ai-reading-system'

# 本地 WorkBuddy 技能规范允许的 frontmatter 字段（其余为市场扩展字段，本地版剔除）
LOCAL_ALLOWED = ('name', 'description', 'allowed-tools', 'compatibility', 'license', 'metadata')


def split_frontmatter(text: str):
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.S)
    return m.group(1), m.group(2) if m else ('', text)


def local_frontmatter(fm: str) -> str:
    lines = []
    key = None
    for line in fm.split('\n'):
        if re.match(r'^[A-Za-z_-]+:', line):
            key = line.split(':', 1)[0].strip()
        if key in LOCAL_ALLOWED:
            lines.append(line)
    return '\n'.join(lines).strip()


def build_local_variant() -> str:
    """返回精简版 SKILL.md 全文"""
    text = (SRC / 'SKILL.md').read_text(encoding='utf-8')
    fm, body = split_frontmatter(text)
    return f'---\n{local_frontmatter(fm)}\n---\n{body}'


def check_flat_structure():
    """硬约束：技能包内只允许两级目录（ai-reading-system/文件），禁止任何子目录嵌套。"""
    bad = []
    for f in sorted(SRC.rglob('*')):
        if f.is_file():
            rel = f.relative_to(SRC).as_posix()
            if '/' in rel:
                bad.append(rel)
    if bad:
        raise SystemExit(f'❌ 包内有子目录嵌套（市场解析会失败）：\n   ' + '\n   '.join(bad)
                         + '\n   请把这些文件全部拍平到技能根目录。')
    print(f'✅ 目录结构合规：包内 {len(list(SRC.rglob("*")))} 个文件全部平铺在 {SKILL_NAME}/ 下一层')


def zip_skill(frontmatter_override: str | None, out_path: Path):
    if out_path.exists():
        out_path.unlink()
    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(SRC.rglob('*')):
            if f.is_file():
                arc = f'{SKILL_NAME}/{f.relative_to(SRC).as_posix()}'
                if f.name == 'SKILL.md' and frontmatter_override is not None:
                    z.writestr(arc, frontmatter_override)
                else:
                    z.write(f, arc)
    # 复核压缩包内路径深度
    with zipfile.ZipFile(out_path) as z:
        for n in z.namelist():
            if n.count('/') > 1:
                raise SystemExit(f'❌ 压缩包内层级超限：{n}')


def main():
    DIST.mkdir(exist_ok=True)
    check_flat_structure()
    local_md = build_local_variant()

    # 1/2. 两种分发包
    zip_skill(local_md, DIST / f'{SKILL_NAME}.skill')
    zip_skill(None, DIST / f'{SKILL_NAME}-marketplace.zip')

    # 3. 本机安装（frontmatter 精简版）
    dest = LOCAL_SKILLS / SKILL_NAME
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(SRC, dest)
    (dest / 'SKILL.md').write_text(local_md, encoding='utf-8')

    for p in (DIST / f'{SKILL_NAME}.skill', DIST / f'{SKILL_NAME}-marketplace.zip'):
        size = p.stat().st_size
        assert size < 3 * 1024 * 1024, f'{p.name} 超过 3MB 限制'
        print(f'✅ {p.name}  {size/1024:.0f} KB')
    print(f'✅ 本机已安装 → {dest}（重启 WorkBuddy 会话生效）')


if __name__ == '__main__':
    main()
