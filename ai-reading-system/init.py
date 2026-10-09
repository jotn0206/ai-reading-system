#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init.py — AI 阅读执行系统 · 一键初始化工作目录（P2 · 2026-10-09）

把「技能模板」变成「可运行的工作台」，等价于作者当时的形态：
  - 复制 index.html（工作台 SPA，含占位口令 AIREAD2026）
  - 放置 data/state.js（单一事实源：空模板 或 --seed 演示种子书）
  - 建齐 data/{audio,fulltext,kb,notes}/ 与 data/profile-learned.json

用法：
  python init.py                          # 在当前目录下建 reading-data/（空状态）
  python init.py --data <目录>            # 指定工作目录（也可用环境变量 READING_DATA）
  python init.py --seed                   # 带 1 本全跑通 + 1 本进行中的演示种子书
  python init.py --seed --name 斌哥 --pass mypass123   # 注入昵称与访问口令

说明：本地用浏览器直接打开 index.html 不设口令门（功能不变）；要发布成公网链接时，
再按 SKILL.md 的「全部更新一遍」动线跑 publish-online.js。
"""
import argparse
import os
import re
import shutil
import sys

# 让本脚本可直接 import 同目录的 lib_reading（标准库依赖，安全）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_reading as L  # noqa: E402


def skill_dir():
    return os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(
        prog="init.py",
        description="AI 阅读执行系统 · 一键初始化工作目录",
    )
    ap.add_argument("--data", default=os.environ.get("READING_DATA", ""),
                    help="工作目录（含 index.html 与 data/）；缺省为 <当前目录>/reading-data")
    ap.add_argument("--seed", action="store_true",
                    help="带入演示种子书：1 本跑通 8 环节 + 1 本进行中（公版，原创样例，可分发）")
    ap.add_argument("--name", default=None, help="身份昵称，写入 data/state.js 的 profile.name")
    ap.add_argument("--pass", dest="passwd", default=None,
                    help="工作台访问口令，注入 index.html 的 var PASS（本地打开可留空）")
    args = ap.parse_args()

    if not args.data:
        args.data = os.path.join(os.getcwd(), "reading-data")
    data_dir = os.path.abspath(args.data)
    ddir = os.path.join(data_dir, "data")

    # 1) 建目录骨架
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(ddir, exist_ok=True)
    for sub in ("audio", "fulltext", "kb", "notes"):
        os.makedirs(os.path.join(ddir, sub), exist_ok=True)

    # 2) 复制工作台模板
    shutil.copy2(os.path.join(skill_dir(), "index.html"),
                 os.path.join(data_dir, "index.html"))

    # 3) 放置 state.js（种子 or 空模板）
    if args.seed and os.path.exists(os.path.join(skill_dir(), "seed-state.js")):
        shutil.copy2(os.path.join(skill_dir(), "seed-state.js"),
                     os.path.join(ddir, "state.js"))
        seed_tag = "演示种子书（小王子·全跑通 + 沉思录·进行中）"
    else:
        shutil.copy2(os.path.join(skill_dir(), "state.js"),
                     os.path.join(ddir, "state.js"))
        seed_tag = "空模板"

    # 4) profile-learned.json（个性化引擎产物，初始为空）
    pl = os.path.join(ddir, "profile-learned.json")
    if not os.path.exists(pl):
        with open(pl, "w", encoding="utf-8") as f:
            f.write("{}\n")

    # 5) 注入昵称（改写 state.js，复用 lib_reading 保证格式合法）
    if args.name:
        data = L.load_state(os.path.join(ddir, "state.js"))
        data.setdefault("profile", {})["name"] = args.name
        with open(os.path.join(ddir, "state.js"), "w", encoding="utf-8") as f:
            f.write(L.dump_state(data))

    # 6) 注入访问口令（改写运行版 index.html，本地打开可留空）
    if args.passwd:
        ih = os.path.join(data_dir, "index.html")
        t = open(ih, encoding="utf-8").read()
        t2 = re.sub(r"var\s+PASS\s*=\s*'[^']*'", "var PASS='%s'" % args.passwd, t, count=1)
        with open(ih, "w", encoding="utf-8") as f:
            f.write(t2)

    # 7) 自检 + 指引
    data = L.load_state(os.path.join(ddir, "state.js"))
    nbooks = len(data.get("books", []))
    print("✅ 工作目录已就绪：%s" % data_dir)
    print("   数据形态 ：%s" % seed_tag)
    print("   书目数量 ：%d 本" % nbooks)
    if args.name:
        print("   昵称     ：%s" % args.name)
    print("\n下一步：")
    print("   1) 用浏览器打开 %s （或：python -m http.server -d %s 5210）"
          % (os.path.join(data_dir, "index.html"), data_dir))
    print("   2) 完成身份画像：工作台「🎯 身份画像」按钮，或直接改 data/state.js 的 profile")
    print("   3) 新书入库 / 跑八环节：参见技能 SKILL.md 的 WF1–WF8")
    if args.seed:
        print("   注：种子书为演示用途，真实阅读请用 add-book 流程入库你自己的书。")


if __name__ == "__main__":
    main()
