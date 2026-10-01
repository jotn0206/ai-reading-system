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


REQUIRED_FM = ('name', 'version', 'display_name', 'display_name_en',
               'description', 'description_zh', 'description_en')


def check_frontmatter():
    """硬约束：市场解析器必填字段。缺一个就提交失败（2026-09-27 display_name_en 事故）。"""
    fm_text = (SRC / 'SKILL.md').read_text(encoding='utf-8')
    if not fm_text.startswith('---\n'):
        raise SystemExit('❌ SKILL.md 首行必须是 ---')
    end = fm_text.find('\n---\n', 3)
    fm = fm_text[4:end]
    try:
        import yaml
        data = yaml.safe_load(fm)
    except Exception as e:  # 没有 yaml 模块就退化为逐行检查
        data = None
        print(f'⚠️  未装 pyyaml，跳过 YAML 解析（{e}）')
    if data is None:
        data = {}
        for l in fm.split('\n'):
            if ':' in l and not l.startswith(' '):
                k, v = l.split(':', 1)
                data[k.strip()] = v.strip().strip('"\'')
    missing = [k for k in REQUIRED_FM if not str(data.get(k, '')).strip()]
    if missing:
        raise SystemExit('❌ SKILL.md frontmatter 缺少市场必填字段：'
                         + ', '.join(missing))
    for k in REQUIRED_FM:
        print(f'   {k}: {str(data[k])[:48]}…')
    print('✅ frontmatter 合规：市场必填字段齐全（含 display_name_en）')


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


PLACEHOLDER_PASS = 'AIREAD2026'


def check_pass_placeholder():
    """硬约束：模板里的访问口令必须是占位符，不许把真实口令写死随包分发（2026-09-28 加固）。"""
    html = (SRC / 'index.html').read_text(encoding='utf-8')
    m = re.search(r"var\s+PASS\s*=\s*['\"]([^'\"]+)['\"]", html)
    if not m:
        raise SystemExit('❌ index.html 里没找到 var PASS=，口令门可能已被破坏')
    if m.group(1) == PLACEHOLDER_PASS:
        print(f'✅ 口令占位符合规：var PASS=\'{PLACEHOLDER_PASS}\'（部署前改这一处）')
    else:
        raise SystemExit(f"❌ index.html 里的口令是 '{m.group(1)}'，不是占位符 {PLACEHOLDER_PASS}"
                         f'\n   把 var PASS= 改回占位符再打包。')
    # 排除 xmlns 这类 `p://` 误报：盘符前一个字符不能是字母数字/点下划线
    if re.search(r'(?<![A-Za-z0-9._-])[A-Za-z]:[\\/]', html):
        hits = [l.strip()[:90] for l in html.split('\n')
                if re.search(r'(?<![A-Za-z0-9._-])[A-Za-z]:[\\/]', l)]
        raise SystemExit('❌ index.html 里出现本机盘符路径（对外分发会泄露你的目录结构）：\n   '
                         + '\n   '.join(hits[:5]))


def check_no_fulltext():
    """硬约束：版权红线。工作台模板不得引用/内嵌书全文。"""
    html = (SRC / 'index.html').read_text(encoding='utf-8')
    if 'data/fulltext' in html:
        raise SystemExit('❌ index.html 出现 data/fulltext 引用（会带出书全文）')
    print('✅ 版权红线：模板未引用 data/fulltext')


def clean_dist():
    """清掉 dist/ 里的中间产物，只留三个正式包。"""
    keep = (f'{SKILL_NAME}.skill', f'{SKILL_NAME}-marketplace.zip', f'{SKILL_NAME}-root.zip')
    removed = []
    for p in sorted(DIST.glob('*')):
        if p.is_file() and p.name not in keep:
            p.unlink()
            removed.append(p.name)
    if removed:
        print('🧹 清理 dist 中间产物：' + ', '.join(removed))
    else:
        print('✅ dist 目录干净')


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
    check_frontmatter()
    check_flat_structure()
    check_pass_placeholder()
    check_no_fulltext()
    clean_dist()
    local_md = build_local_variant()

    # 1/2/3. 三种分发包
    zip_skill(local_md, DIST / f'{SKILL_NAME}.skill')                          # 粉丝群/本地导入
    zip_skill(None, DIST / f'{SKILL_NAME}-marketplace.zip')                    # 市场提交（主推）
    zip_skill(None, DIST / f'{SKILL_NAME}-root.zip')                           # 零前缀，备用

    # 3. 本机安装（frontmatter 精简版）
    dest = LOCAL_SKILLS / SKILL_NAME
    # 注意：不要「先 rmtree 再 copytree」——某些环境（WorkBuddy 沙箱 / 系统回收站失败）
    # 会在 rmtree 抛错时把目标目录删掉一半，导致本机技能目录整体丢失（2026-10-01 事故）。
    # 改为幂等覆盖：目标已存在的文件被同名覆盖，源包已删除的旧文件尝试清理但失败不致命。
    dest.mkdir(parents=True, exist_ok=True)
    src_files = {p.relative_to(SRC).as_posix() for p in SRC.rglob('*') if p.is_file()}
    for p in sorted(dest.rglob('*'), reverse=True):
        if p.is_file() and p.relative_to(dest).as_posix() not in src_files:
            try:
                p.unlink()
            except OSError:
                pass
    shutil.copytree(SRC, dest, dirs_exist_ok=True)
    (dest / 'SKILL.md').write_text(local_md, encoding='utf-8')

    for p in (DIST / f'{SKILL_NAME}.skill', DIST / f'{SKILL_NAME}-marketplace.zip',
              DIST / f'{SKILL_NAME}-root.zip'):
        size = p.stat().st_size
        assert size < 3 * 1024 * 1024, f'{p.name} 超过 3MB 限制'
        print(f'✅ {p.name}  {size/1024:.0f} KB')
    print(f'✅ 本机已安装 → {dest}（重启 WorkBuddy 会话生效）')


if __name__ == '__main__':
    main()
