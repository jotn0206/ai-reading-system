# -*- coding: utf-8 -*-
"""把运行工作台的 index.html 同步进技能分发模板，并重打 5 处脱敏 patch。

流程：整篇覆盖源码 -> 精确替换 5 处个人数据 -> 校验无残留。
每处替换都断言命中（count>0），漏改即报错，避免静默把个人数据带进分发包。
幂等：可重复运行。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))  # 脚本在仓库根，只需一层
# 运行工作台根目录（含 index.html），由 READING_ROOT 指定，避免硬编码个人路径
SRC_ROOT = os.environ.get("READING_ROOT")
if not SRC_ROOT:
    print("请设置环境变量 READING_ROOT 指向运行工作台根目录（含 index.html）")
    sys.exit(1)
SRC = os.path.join(SRC_ROOT, "index.html")
TPL = os.path.join(ROOT, "ai-reading-system", "index.html")
if not os.path.exists(SRC):
    print("❌ READING_ROOT 下找不到 index.html:", SRC)
    sys.exit(1)

# 5 处脱敏 patch：(说明, 源码串, 模板安全串)
PATCHES = [
    ("口令", "var PASS='RAC2-9EZS'", "var PASS='AIREAD2026'"),
    ("昵称", "profile:{name:'洋葱姐'}", "profile:{name:'读者'}"),
    ("发布流程名", "（dwjotn 公众号发布工作流）", "（公众号发布工作流）"),
    ("示例书名", 'placeholder="例如：置身事内"', 'placeholder="例如：思考，快与慢"'),
]

# 第 5 处：发布说明整块（含 D:/dwjotn 路径 + 具体命令），用正则整段收敛
NOTE_RE = re.compile(r"实际 API 发布请在.*?完成后将 media_id 回填至此", re.S)
NOTE_NEW = "实际 API 发布请用你自己的公众号发布工具执行；完成后将 media_id 回填至此"

# 残留红线：这些串一旦出现在模板里就是泄漏
FORBIDDEN = ["RAC2-9EZS", "洋葱姐", "dwjotn", "置身事内", "D:/dwjotn", "wechat-api.ts"]

src = open(SRC, encoding="utf-8").read()
out = src

for name, old, new in PATCHES:
    n = out.count(old)
    if n == 0:
        print("❌ patch 未命中: %s | %s" % (name, old[:40]))
        sys.exit(1)
    out = out.replace(old, new)
    print("  ✅ %-8s x%d" % (name, n))

n = len(NOTE_RE.findall(out))
if n == 0:
    print("❌ patch 未命中: 发布说明整块")
    sys.exit(1)
out = NOTE_RE.sub(NOTE_NEW, out)
print("  ✅ %-8s x%d" % ("发布说明", n))

# 校验残留
leaks = [f for f in FORBIDDEN if f in out]
if leaks:
    print("❌ 模板仍有个人数据残留:", leaks)
    sys.exit(1)

# 校验安全串都在
must = ["AIREAD2026", "profile:{name:'读者'}", "（公众号发布工作流）", "思考，快与慢"]
miss = [m for m in must if m not in out]
if miss:
    print("❌ 模板缺少应有的脱敏串:", miss)
    sys.exit(1)

open(TPL, "w", encoding="utf-8").write(out)
print("\n✅ 模板已同步: %d B -> %d B" % (len(src), len(out)))
print("   %s" % TPL)
