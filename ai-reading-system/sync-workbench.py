# -*- coding: utf-8 -*-
"""
sync-workbench.py —— 模板 → 运行工作台（sync_template.py 的逆操作）

两套 index.html 的关系，一句话说清：
  技能模板（脱敏，随包分发，含 var PASS='AIREAD2026'）
      ⇅ sync_template.py（运行→模板，脱敏）/ sync-workbench.py（模板→运行，注入个人化）
  运行工作台（你的真实数据目录，含你的口令）

本脚本：把技能模板的最新特性同步到运行工作台，同时**保留你的个人化设置**
（从当前运行版里抽取，不在脚本里写死——所以技能包里不含任何个人信息）。
5 处个人化：访问口令 / 昵称 / 发布流程名 / 示例书名 placeholder / 发布说明块。

用法：
  python sync-workbench.py [--data <工作目录>]           # 干跑：报有没有落后
  python sync-workbench.py --apply                       # 备份后覆盖
  python sync-workbench.py --data $READING_DATA --apply
"""
import argparse
import os
import re
import shutil
import sys
from datetime import datetime

SAFE = {
    "pass": "AIREAD2026",
    "name": "读者",
    "flow": "（公众号发布工作流）",
    "ph": "例如：思考，快与慢",
}


def skill_dir():
    return os.path.dirname(os.path.abspath(__file__))


def grab(html, pat, group=1):
    m = re.search(pat, html)
    return m.group(group) if m else None


def personalize(src_html, tpl_html):
    """从运行版抽取个人值，替换成模板安全串，得到「脱敏后的运行版」用于比对。"""
    out = src_html
    pairs = []
    p = grab(src_html, r"var\s+PASS\s*=\s*'([^']+)'")
    if p and p != SAFE["pass"]:
        pairs.append(("口令", "var PASS='%s'" % p, "var PASS='%s'" % SAFE["pass"]))
    n = grab(src_html, r"profile:\{name:'([^']+)'\}")
    if n and n != SAFE["name"]:
        pairs.append(("昵称", "profile:{name:'%s'}" % n, "profile:{name:'%s'}" % SAFE["name"]))
    f = grab(src_html, r"（([^）]*公众号发布工作流)）")
    if f and f != "公众号发布工作流":
        pairs.append(("流程名", "（%s）" % f, SAFE["flow"]))
    ph = grab(src_html, r'placeholder="例如：([^"]+)"')
    if ph and ph != "思考，快与慢":
        pairs.append(("示例书名", 'placeholder="例如：%s"' % ph, 'placeholder="%s"' % SAFE["ph"]))
    note = re.search(r"实际 API 发布请在.*?完成后将 media_id 回填至此", src_html, re.S)
    note_safe = re.search(r"实际 API 发布请用你自己的公众号发布工具执行；完成后将 media_id 回填至此", tpl_html)
    if note and note_safe and note.group(0) != note_safe.group(0):
        pairs.append(("发布说明", note.group(0), note_safe.group(0)))
    for _, old, new in pairs:
        out = out.replace(old, new)
    return out, pairs


def inject(tpl_html, pairs):
    """把个人值注入模板（pairs 顺序：old=个人值, new=安全串 → 反向替换）。"""
    out = tpl_html
    missed = []
    for name, old, new in pairs:
        if new not in out:
            missed.append(name)
            continue
        out = out.replace(new, old)
    return out, missed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.environ.get("READING_DATA", ""), help="工作目录（含 index.html）")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--tpl", default=os.path.join(skill_dir(), "index.html"), help="技能模板 index.html")
    args = ap.parse_args()
    if not args.data:
        sys.exit("需要 --data 或设置环境变量 READING_DATA")
    run = os.path.join(args.data, "index.html")
    if not os.path.exists(run):
        sys.exit("运行工作台不存在：%s" % run)
    if not os.path.exists(args.tpl):
        sys.exit("技能模板不存在：%s" % args.tpl)

    src = open(run, encoding="utf-8").read()
    tpl = open(args.tpl, encoding="utf-8").read()
    stripped, pairs = personalize(src, tpl)
    same = stripped == tpl
    print("运行工作台：%s（%d B）" % (run, len(src)))
    print("技能模板　：%s（%d B）" % (args.tpl, len(tpl)))
    print("个人化项　：%s" % ("、".join(p[0] for p in pairs) or "无（运行版=脱敏版）"))
    if same:
        print("\n✅ 运行工作台与模板内容一致（仅差个人化），无需更新。")
        return
    print("\n⚠ 运行工作台落后/分叉于模板。差异片段：")
    import difflib
    d = list(difflib.unified_diff(stripped.splitlines(), tpl.splitlines(),
                                  lineterm="", n=0))
    print("\n".join(d[:40]) or "（无法逐行比对）")
    if not args.apply:
        print("\n干跑结束，加 --apply 覆盖（会先备份运行版）。")
        return
    out, missed = inject(tpl, pairs)
    if missed:
        print("⚠ 这些个人化项在新模板里找不到对应串，需手工补：%s" % "、".join(missed))
    bak = run + ".bak-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(run, bak)
    open(run, "w", encoding="utf-8").write(out)
    print("\n✅ 已更新运行工作台（备份：%s）" % os.path.basename(bak))
    print("   本地 file:// 打开不设口令门，功能不变；发布前用 publish-online.js 重新生成发布包。")


if __name__ == "__main__":
    main()
