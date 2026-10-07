# -*- coding: utf-8 -*-
"""
sync-from-local.py —— 反方向同步：本机安装目录 → 本仓库源码（唯一口径的一半）

背景（为什么必须有它）：
  build.py 是「仓库 → 本机安装目录 + dist 包」的单向链路。如果只在那边改、不回灌，
  下次跑 build.py 会把本机改动整体覆盖掉（2026-10-08 就在本机加了一整套能力，差点被覆盖）。
  所以：本机改完 → 跑本脚本回灌仓库 → 再跑 build.py 三包一致。

做了三件讲究的事：
  1. SKILL.md 只替换**正文**，保留仓库的市场版 frontmatter（version/display_name/description_zh…
     这些是本地精简版没有的，丢了会让 build.py 的 frontmatter 闸失败）。
  2. 排除 __pycache__ / .pyc / 临时产物，不进仓库。
  3. 同步后跑一遍 build.py 的去个人化规则自检，漏个人路径直接报错。

用法：
  python sync-from-local.py            # 干跑：只报差异
  python sync-from-local.py --apply    # 真正回灌
"""
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = Path.home() / ".workbuddy" / "skills" / "ai-reading-system"   # 本机安装目录（canonical 源）
DST = ROOT / "ai-reading-system"                                     # 仓库源码
SKIP = {"__pycache__", ".DS_Store", "_ping.mp3"}
SKIP_SUFFIX = {".pyc", ".pyo", ".bak", ".mp3", ".tmp"}

FORBIDDEN = [
    (r"https?://[^\s)'\"]*workbuddy\.host", "个人线上工作台链接"),
    (r"\b[A-Z]{4}-[A-Z0-9]{4}\b", "疑似真实访问口令"),
    (r"[Dd]:/dwjotn", "个人 vault 绝对路径"),
    (r"C:/Users/Administrator|C:\\\\Users\\\\Administrator", "本机用户名路径"),
]


def split_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    return (m.group(1), m.group(2)) if m else ("", text)


def scan_leaks():
    leaks = []
    for f in sorted(DST.rglob("*")):
        if not f.is_file() or f.suffix.lower() in (".png", ".jpg", ".zip"):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.split("\n"), 1):
            for pat, why in FORBIDDEN:
                if re.search(pat, line):
                    leaks.append("%s:%d（%s）%s" % (f.name, i, why, line.strip()[:70]))
                    break
    return leaks


def main():
    apply = "--apply" in sys.argv
    if not SRC.is_dir():
        raise SystemExit("找不到本机技能目录：%s" % SRC)
    DST.mkdir(parents=True, exist_ok=True)

    src_files = {p.relative_to(SRC).as_posix()
                 for p in SRC.rglob("*") if p.is_file()
                 and p.name not in SKIP and p.suffix.lower() not in SKIP_SUFFIX}
    dst_files = {p.relative_to(DST).as_posix()
                 for p in DST.rglob("*") if p.is_file()
                 and p.name not in SKIP and p.suffix.lower() not in SKIP_SUFFIX}

    added = sorted(src_files - dst_files)
    removed = sorted(dst_files - src_files)
    common = sorted(src_files & dst_files)
    diff = []
    for rel in common:
        a, b = (SRC / rel).read_bytes(), (DST / rel).read_bytes()
        if a != b and rel != "SKILL.md":
            diff.append(rel)
    # SKILL.md 特殊：只比正文
    fm_dst = split_frontmatter((DST / "SKILL.md").read_text(encoding="utf-8"))[0]
    body_src = split_frontmatter((SRC / "SKILL.md").read_text(encoding="utf-8"))[1]
    body_dst = split_frontmatter((DST / "SKILL.md").read_text(encoding="utf-8"))[1]
    skill_md_diff = body_src != body_dst

    print("本机安装目录：%s" % SRC)
    print("仓库源码目录：%s" % DST)
    print("  新增 %d：%s" % (len(added), "、".join(added) if added else "—"))
    print("  删除 %d：%s" % (len(removed), "、".join(removed) if removed else "—"))
    print("  内容变化 %d：%s" % (len(diff), "、".join(diff) if diff else "—"))
    print("  SKILL.md 正文变化：%s（frontmatter 保留仓库市场版）" % ("是" if skill_md_diff else "否"))

    if not apply:
        print("\n干跑结束，加 --apply 真正回灌。")
        return

    for rel in added + diff:
        (DST / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SRC / rel, DST / rel)
    for rel in removed:
        try:
            (DST / rel).unlink()
        except OSError:
            pass
    if skill_md_diff:
        (DST / "SKILL.md").write_text("---\n%s\n---\n%s" % (fm_dst, body_src), encoding="utf-8")

    # 清掉仓库里的 pycache
    for p in DST.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)

    leaks = scan_leaks()
    if leaks:
        raise SystemExit("❌ 回灌后出现个人化内容，先改占位符再同步：\n   " + "\n   ".join(leaks[:8]))
    print("\n✅ 已回灌仓库（SKILL.md frontmatter 保留市场版）")
    print("✅ 去个人化自检通过")
    print("下一步：python build.py（三包 + 回灌本机）")


if __name__ == "__main__":
    main()
