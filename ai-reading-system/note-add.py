# -*- coding: utf-8 -*-
"""
note-add.py · 笔记 / 要点 / 洞察的持久化入口（读完留下的东西不能丢）

一条笔记 = 一行 JSON，落在 <data>/data/notes/<书名>.jsonl。
写完自动重建知识索引（kb-build.py），立刻可被 kb-search.py 检索到。

用法：
  python note-add.py --data <dir> --book "思考，快与慢" --kind insight \
      --text "损失厌恶在房产谈判里的用法：先给锚点" --tags 决策,房产 --stage 3 --chapter "第26章"
  echo "随手一句想法" | python note-add.py --data <dir> --book "原则" --stdin
  python note-add.py --data <dir> --book "原则" --file ./读后随想.md   # 按 ## 或空行分段批量导入
  python note-add.py --data <dir> --book "原则" --list [--kind insight] [--q 关键词]
  python note-add.py --data <dir> --book "原则" --del 20261008-003

kind 取值：insight 洞察 / note 笔记 / quote 金句 / question 疑问 / action 待办（默认 note）
"""
import argparse
import json
import os
import re
import sys

import importlib.util

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_reading as L  # noqa: E402


def _load(name, fn):
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), fn)
    spec = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


build = _load("kb_build", "kb-build.py").build

KINDS = ["insight", "note", "quote", "question", "action"]


def cmd_add(args, data):
    book = args.book or "未分类"
    b = L.find_book(data, book) if data else None
    book_title = b.get("title") if b else book
    text = args.text
    if args.stdin:
        text = sys.stdin.read()
    if args.file:
        raw = open(args.file, encoding="utf-8", errors="ignore").read()
        chunks = [x.strip() for x in re.split(r"\n(?=##\s)|\n\s*\n", raw) if x.strip()]
        for c in chunks:
            c = re.sub(r"^#{1,6}\s*", "", c).strip()
            if len(c) < 4:
                continue
            n = make_note(data, book_title, b, c, args)
            L.append_note(args.data, n)
        print("已导入 %d 条 → %s" % (len(chunks), L.notes_file(args.data, book_title)))
    else:
        if not text or not text.strip():
            sys.exit("需要 --text / --stdin / --file")
        n = make_note(data, book_title, b, text.strip(), args)
        fp = L.append_note(args.data, n)
        print("已记录 %s（%s）→ %s" % (n["id"], n["kind"], fp))
    build(args.data, args.vault or None, quiet=True)


def make_note(data, book_title, b, text, args):
    return {
        "id": L.next_note_id(args.data, book_title),
        "ts": L.now_iso(),
        "book": book_title,
        "bookId": (b or {}).get("id", ""),
        "kind": args.kind,
        "stage": int(args.stage or 0),
        "chapter": args.chapter or "",
        "text": text,
        "tags": [x.strip() for x in (args.tags or "").split(",") if x.strip()],
        "links": [x.strip() for x in (args.links or "").split(",") if x.strip()],
        "source": args.source or "",
        "weight": int(args.weight or 3),
    }


def cmd_list(args):
    notes = L.read_notes(args.data, args.book)
    if args.kind:
        notes = [n for n in notes if n.get("kind") == args.kind]
    if args.q:
        notes = [n for n in notes if args.q.lower() in json.dumps(n, ensure_ascii=False).lower()]
    notes.sort(key=lambda n: n.get("ts", ""), reverse=True)
    print("共 %d 条\n" % len(notes))
    for n in notes:
        print("[%s] %s %-6s %s" % (n.get("id"), n.get("ts", "")[:10], n.get("kind"), (n.get("text") or "").replace("\n", " ")[:70]))
        if n.get("tags"):
            print("        #%s" % " #".join(n["tags"]))
    return notes


def cmd_del(args):
    fp = L.notes_file(args.data, args.book)
    if not os.path.exists(fp):
        sys.exit("没有笔记文件：%s" % fp)
    keep, removed = [], 0
    for line in open(fp, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            n = json.loads(line)
        except Exception:
            keep.append(line)
            continue
        if n.get("id") == args.del_id:
            removed += 1
            continue
        keep.append(json.dumps(n, ensure_ascii=False))
    with open(fp, "w", encoding="utf-8") as f:
        f.write("\n".join(keep) + ("\n" if keep else ""))
    print("已删除 %d 条" % removed)
    build(args.data, args.vault or None, quiet=True)


def main():
    ap = argparse.ArgumentParser(description="阅读系统 · 笔记与洞察落盘")
    ap.add_argument("--data", required=True)
    ap.add_argument("--book")
    ap.add_argument("--text")
    ap.add_argument("--stdin", action="store_true", help="从 stdin 读正文")
    ap.add_argument("--file", help="md/txt 文件批量导入（按 ## 或空行分段）")
    ap.add_argument("--kind", default="note", choices=KINDS)
    ap.add_argument("--chapter")
    ap.add_argument("--tags", help="逗号分隔")
    ap.add_argument("--links", help="关联原子卡 id，逗号分隔")
    ap.add_argument("--stage", help="关联环节 1-8")
    ap.add_argument("--source", help="出处，如 P123 / 自述")
    ap.add_argument("--weight", default="3", help="重要度 1-5")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--q", help="--list 时的过滤关键词")
    ap.add_argument("--del", dest="del_id")
    ap.add_argument("--vault", default=os.environ.get("READING_VAULT", ""))
    args = ap.parse_args()

    data = L.load_state(L.state_file(args.data)) if os.path.exists(L.state_file(args.data)) else {"books": []}
    if args.list:
        cmd_list(args)
    elif args.del_id:
        cmd_del(args)
    else:
        cmd_add(args, data)


if __name__ == "__main__":
    main()
