# -*- coding: utf-8 -*-
"""
kb-search.py · 本地知识检索与复用（读过的东西，要能一秒找回来）

索引由 kb-build.py 生成（<data>/data/kb/kb-index.json），BM25 打分，中文 bigram 分词，零第三方依赖。

用法：
  python kb-search.py --data <dir> "复利 守富"                  # 默认 top8
  python kb-search.py --data <dir> "怎么止损" --type card,note   # 只看原子卡和笔记
  python kb-search.py --data <dir> "止损" --book 韭菜修行记
  python kb-search.py --data <dir> "写公众号选题" --md > ctx.md  # 导出可直接粘贴的写作上下文
  python kb-search.py --data <dir> "复利" --json
  python kb-search.py --data <dir> "复利" --rebuild             # 先重建索引再查
  python kb-search.py --data <dir> --recent 20                  # 最近新增的笔记/卡片（不查询）
"""
import argparse
import json
import math
import os
import re
import sys
from collections import Counter

import importlib.util

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_reading as L  # noqa: E402

# kb-build.py 文件名带连字符，不能直接 import，按路径加载
def _load(name, fn):
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), fn)
    spec = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_kb = _load("kb_build", "kb-build.py")
build, tokenize = _kb.build, _kb.tokenize

K1, B = 1.5, 0.75
TYPE_CN = {"stage": "环节", "chapter": "章节", "card": "原子卡", "action": "行动",
           "key": "重点章", "note": "笔记", "insight": "洞察", "quote": "金句",
           "question": "疑问", "vault": "vault卡"}


def load_index(data_dir):
    p = os.path.join(data_dir, "data", "kb", "kb-index.json")
    if not os.path.exists(p):
        return None
    return json.load(open(p, encoding="utf-8"))


def search(idx, query, topk=8, types=None, book=None, stage=None):
    q = Counter(tokenize(query))
    if not q:
        return []
    docs, df, avgdl = idx["docs"], idx.get("df", {}), idx.get("avgdl") or 1
    N = len(docs)
    out = []
    for d in docs:
        if types and d.get("type") not in types:
            continue
        if book and book not in (d.get("book") or ""):
            continue
        if stage and int(d.get("stage") or 0) != int(stage):
            continue
        tf = d.get("tokens") or {}
        dl = sum(tf.values()) or 1
        score = 0.0
        hit = []
        for t, qn in q.items():
            f = tf.get(t, 0)
            if not f:
                continue
            idf = math.log(1 + (N - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))
            score += idf * (f * (K1 + 1)) / (f + K1 * (1 - B + B * dl / avgdl))
            hit.append(t)
        if score <= 0:
            continue
        out.append((score, d, hit))
    out.sort(key=lambda x: -x[0])
    return out[:topk]


def snippet(text, hits, width=90):
    low = text.lower()
    pos = -1
    for h in hits:
        p = low.find(h)
        if p >= 0:
            pos = p
            break
    if pos < 0:
        pos = 0
    s = max(0, pos - width // 3)
    frag = text[s:s + width].replace("\n", " ")
    for h in hits:
        frag = re.sub("(?i)" + re.escape(h), "【%s】" % h, frag)
    return ("…" if s > 0 else "") + frag + ("…" if s + width < len(text) else "")


def print_hits(hits, full=False):
    for i, (sc, d, hit) in enumerate(hits, 1):
        print("%2d. [%.2f] %s｜%s｜%s" % (i, sc, TYPE_CN.get(d.get("type"), d.get("type")),
                                         d.get("book") or "—", d.get("title") or ""))
        print("    %s" % snippet(d.get("text", ""), hit, 120 if not full else 100000))
        print("    ↳ %s" % d.get("path", ""))


def as_md(hits, query, data_dir):
    lines = ["# 检索上下文 · %s" % query,
             "> 来源：本地阅读知识库（`%s`）｜ 生成 %s ｜ 命中 %d 条\n"
             % (os.path.join(data_dir, "data", "kb", "kb-index.json"), L.now_iso(), len(hits))]
    for i, (sc, d, hit) in enumerate(hits, 1):
        lines.append("## %d. %s（%s · %s · %.2f）" % (
            i, d.get("title") or "", d.get("book") or "—", TYPE_CN.get(d.get("type"), d.get("type")), sc))
        lines.append("路径：`%s`\n" % d.get("path", ""))
        body = d.get("text", "")
        lines.append(body[:1200] + ("\n…（截断）" if len(body) > 1200 else ""))
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="阅读系统 · 本地知识检索")
    ap.add_argument("--data", required=True, help="工作目录")
    ap.add_argument("query", nargs="?", help="查询词（空格分隔，多词=与）")
    ap.add_argument("--topk", type=int, default=8)
    ap.add_argument("--type", help="限定类型，逗号分隔：stage,chapter,card,action,key,note,insight,quote,question,vault")
    ap.add_argument("--book", help="限定书名（子串）")
    ap.add_argument("--stage", type=int, help="限定环节 1-8")
    ap.add_argument("--md", action="store_true", help="输出 Markdown 上下文块（写作复用）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--full", action="store_true", help="摘要不截断")
    ap.add_argument("--rebuild", action="store_true", help="先重建索引")
    ap.add_argument("--vault", default=os.environ.get("READING_VAULT", ""))
    ap.add_argument("--recent", type=int, help="列出最近新增的 N 条（不查询）")
    args = ap.parse_args()

    if args.rebuild:
        build(args.data, args.vault or None)
    idx = load_index(args.data)
    if not idx:
        print("没有索引，先跑：python kb-build.py --data %s" % args.data)
        sys.exit(1)

    if args.recent:
        docs = [d for d in idx["docs"] if d.get("mtime")]
        docs.sort(key=lambda d: str(d.get("mtime")), reverse=True)
        for d in docs[:args.recent]:
            print("%s ｜ %s ｜ %s ｜ %s" % (d.get("mtime", "")[:10], TYPE_CN.get(d.get("type"), ""),
                                           d.get("book") or "—", d.get("title", "")[:60]))
        return

    if not args.query:
        sys.exit("需要查询词（或用 --recent N）")
    types = [x.strip() for x in args.type.split(",")] if args.type else None
    hits = search(idx, args.query, args.topk, types, args.book, args.stage)
    if not hits:
        print("没有命中。试试更短的词，或先 --rebuild 重建索引。")
        return
    if args.json:
        print(json.dumps([{"score": round(s, 3), **d} for s, d, _ in hits], ensure_ascii=False, indent=1))
    elif args.md:
        print(as_md(hits, args.query, args.data))
    else:
        print("命中 %d 条（索引 %d 条文档，建于 %s）\n" % (len(hits), len(idx["docs"]), idx["built"]))
        print_hits(hits, args.full)


if __name__ == "__main__":
    main()
