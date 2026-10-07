# -*- coding: utf-8 -*-
"""
kb-build.py · 本地知识沉淀索引（让读过的书能被检索到）

把三类内容统一打成一份可检索索引：
  1) data/state.js 的八环节产出（环节 / 逐章拆解 / 原子卡 / 行动 / 重点章）
  2) data/notes/*.jsonl 的笔记·要点·洞察（note-add.py 写入）
  3) 可选：vault 里已沉淀的卡片（02 Wiki/12_单书笔记 + 13_原子笔记）

用法：
  python kb-build.py --data <工作目录>                 # 标准建索引
  python kb-build.py --data <dir> --vault $READING_VAULT    # 连 vault 卡片一起收（推荐，沉淀互通）
  python kb-build.py --data <dir> --include-raw        # 连同 01 Raw Sources 原文分章（索引会变大）
  python kb-build.py --data <dir> --stats              # 只看统计

产物：<data>/data/kb/kb-index.json（docs + 倒排统计）、kb-stats.json
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_reading as L  # noqa: E402

MAX_TEXT = 4000
STOP = set("的了是在和与及为对把我你这他那它我们你们他们一个不没有就很都要会也能还说被给从到以之于其此所但而或如若则吧呢啊哦嗯并且".strip())


def tokenize(s):
    """中文 bigram + 英文/数字词。无第三方分词依赖。"""
    s = str(s or "").lower()
    toks = []
    for w in re.findall(r"[a-z0-9]{2,}", s):
        toks.append(w)
    for seg in re.findall(r"[\u4e00-\u9fff]+", s):
        if len(seg) == 1:
            if seg not in STOP:
                toks.append(seg)
            continue
        for i in range(len(seg) - 1):
            bg = seg[i:i + 2]
            if bg[0] in STOP and bg[1] in STOP:
                continue
            toks.append(bg)
    return toks


def add(docs, d):
    if not d.get("text", "").strip():
        return
    docs.append(d)


def plain(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return "\n".join(str(x) for x in v)
    return str(v)


def collect_state(data, data_dir):
    docs = []
    for b in data.get("books", []):
        bid = b.get("id", "")
        bt = b.get("title", "")
        tags = b.get("tags") or []
        for sid in range(1, 9):
            st = L.stage_obj(b, sid)
            secs = L.readable_sections(b, sid)
            if not secs:
                continue
            body = "\n".join(t + "\n" + "\n".join(ps) for t, ps in secs)
            add(docs, {
                "id": "%s-s%d" % (bid, sid),
                "type": "stage", "book": bt, "bookId": bid, "stage": sid,
                "title": "%s 环节%d · %s" % (L.STAGE_ICONS[sid], sid, L.STAGE_NAMES[sid]),
                "text": body[:MAX_TEXT], "tags": tags,
                "path": "data/state.js#%s/stage%s" % (bt, sid),
                "done": L.stage_done(b, sid), "mtime": st.get("doneAt") or b.get("addedDate") or "",
            })
        # 逐章拆解
        for i, c in enumerate(L.stage_data(b, 3).get("chapters") or []):
            body = "\n".join(filter(None, [plain(c.get("title")), plain(c.get("summary")),
                                           plain(c.get("personal")), plain(c.get("quotes")),
                                           plain(c.get("cases")), plain(c.get("deepCard"))]))
            add(docs, {
                "id": "%s-c%d" % (bid, i + 1), "type": "chapter", "book": bt, "bookId": bid, "stage": 3,
                "title": "第%d章 · %s" % (i + 1, c.get("title") or "未命名"),
                "text": body[:MAX_TEXT], "tags": tags + (str(c.get("tags", "")).split() if c.get("tags") else []),
                "path": "data/state.js#%s/ch%d" % (bt, i + 1), "done": True, "mtime": "",
            })
        # 原子卡
        for c in L.stage_data(b, 6).get("cards") or []:
            body = "\n".join(filter(None, [plain(c.get("concept")), plain(c.get("oneLiner")),
                                           plain(c.get("points")), plain(c.get("content")),
                                           plain(c.get("myThought")), plain(c.get("source"))]))
            add(docs, {
                "id": c.get("id") or "", "type": "card", "book": bt, "bookId": bid, "stage": 6,
                "title": "%s · %s" % (c.get("type") or "概念卡", c.get("concept") or "未命名"),
                "text": body[:MAX_TEXT],
                "tags": tags + [c.get("type") or "概念卡"] + (str(c.get("tags", "")).split() if c.get("tags") else []),
                "path": "data/state.js#%s/card/%s" % (bt, c.get("id") or ""), "done": True, "mtime": "",
            })
        # 行动
        for i, a in enumerate(L.stage_data(b, 7).get("actions") or []):
            body = "\n".join(filter(None, [plain(a.get("content")), plain(a.get("verify")), plain(a.get("from"))]))
            add(docs, {
                "id": "%s-a%d" % (bid, i + 1), "type": "action", "book": bt, "bookId": bid, "stage": 7,
                "title": "行动%d · %s" % (i + 1, (a.get("content") or "")[:24]),
                "text": body[:MAX_TEXT], "tags": tags + [a.get("layer") or "", a.get("priority") or ""],
                "path": "data/state.js#%s/act%d" % (bt, i + 1),
                "done": bool(a.get("done")), "mtime": a.get("doneAt") or "",
            })
        # 重点章
        for r in L.stage_data(b, 5).get("recommended") or []:
            if not r.get("isKey"):
                continue
            add(docs, {
                "id": "%s-k%s" % (bid, L.sha1(plain(r.get("title")))[:6]), "type": "key",
                "book": bt, "bookId": bid, "stage": 5,
                "title": "重点章 · %s" % (r.get("title") or ""),
                "text": "\n".join(filter(None, [plain(r.get("title")), plain(r.get("rationale"))]))[:MAX_TEXT],
                "tags": tags + ["重点"], "path": "data/state.js#%s/key" % bt, "done": True, "mtime": "",
            })
    return docs


def collect_notes(data_dir):
    docs = []
    for n in L.read_notes(data_dir):
        add(docs, {
            "id": n.get("id") or "", "type": n.get("kind") or "note",
            "book": n.get("book") or "", "bookId": n.get("bookId") or "", "stage": n.get("stage") or 0,
            "title": "[%s] %s" % (n.get("kind") or "note", (n.get("text") or "")[:30]),
            "text": "\n".join(filter(None, [n.get("text", ""), n.get("source", ""), n.get("chapter", "")])),
            "tags": (n.get("tags") or []) + [n.get("kind") or "note"],
            "path": "data/notes/%s.jsonl#%s" % (L.slug(n.get("book") or "未分类"), n.get("id") or ""),
            "done": True, "mtime": n.get("ts") or "",
        })
    return docs


def collect_vault(vault, include_raw=False):
    docs = []
    if not vault or not os.path.isdir(vault):
        return docs
    roots = [os.path.join(vault, "02 Wiki", "12_单书笔记"),
             os.path.join(vault, "02 Wiki", "13_原子笔记(Zettelkasten)")]
    if include_raw:
        roots.append(os.path.join(vault, "01 Raw Sources", "20_书籍原文"))
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dp, dn, fn in os.walk(root):
            for f in fn:
                if not f.endswith(".md"):
                    continue
                fp = os.path.join(dp, f)
                try:
                    raw = open(fp, encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                if len(raw) > 200000:
                    raw = raw[:200000]
                rel = os.path.relpath(fp, vault).replace("\\", "/")
                book = ""
                m = re.match(r"02 Wiki/12_单书笔记/([^/]+)/", rel)
                if m:
                    book = m.group(1)
                title = f[:-3]
                add(docs, {
                    "id": rel, "type": "vault", "book": book, "bookId": "", "stage": 0,
                    "title": "vault · %s" % title,
                    "text": raw[:MAX_TEXT],
                    "tags": ["vault"] + ([book] if book else []) + re.findall(r"#([^\s#/]+)", raw[:1500])[:12],
                    "path": rel, "done": True, "mtime": "",
                })
    return docs


def build(data_dir, vault=None, include_raw=False, quiet=False):
    data = L.load_state(L.state_file(data_dir))
    docs = []
    docs += collect_state(data, data_dir)
    docs += collect_notes(data_dir)
    if vault:
        docs += collect_vault(vault, include_raw)
    for d in docs:
        # 标题词计两遍 → 标题命中权重更高（检索时直接受益，无需额外打分逻辑）
        tt = tokenize(d.get("title") or "")
        c = Counter(tt)
        c.update(tt)
        c.update(tokenize(d.get("text") or ""))
        d["tokens"] = c
    df = Counter()
    for d in docs:
        for t in d["tokens"].keys():
            df[t] += 1
    out_dir = os.path.join(data_dir, "data", "kb")
    os.makedirs(out_dir, exist_ok=True)
    idx = {
        "built": L.now_iso(),
        "vault": vault or "",
        "docs": [{k: (v if k != "tokens" else dict(v)) for k, v in d.items()} for d in docs],
        "df": dict(df),
        "avgdl": (sum(len(d["tokens"]) for d in docs) / len(docs)) if docs else 0,
    }
    with open(os.path.join(out_dir, "kb-index.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False)
    stats = {
        "built": idx["built"], "docs": len(docs),
        "by_type": dict(Counter(d["type"] for d in docs)),
        "by_book": dict(Counter(d["book"] for d in docs if d["book"])),
        "vault_docs": sum(1 for d in docs if d["type"] == "vault"),
        "note_docs": sum(1 for d in docs if d["type"] in ("note", "insight", "quote", "question")),
        "chars": sum(len(d["text"]) for d in docs),
    }
    with open(os.path.join(out_dir, "kb-stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)
    if not quiet:
        print("索引已建：%d 条文档 → %s" % (len(docs), os.path.join(out_dir, "kb-index.json")))
        print("  类型分布：%s" % stats["by_type"])
        print("  覆盖书目：%d 本 ｜ 笔记/洞察 %d 条 ｜ vault %d 条"
              % (len(stats["by_book"]), stats["note_docs"], stats["vault_docs"]))
    return idx, stats


def main():
    ap = argparse.ArgumentParser(description="阅读系统 · 本地知识索引构建")
    ap.add_argument("--data", required=True, help="工作目录")
    ap.add_argument("--vault", default=os.environ.get("READING_VAULT", ""), help="Obsidian vault 根（可选）")
    ap.add_argument("--include-raw", action="store_true", help="连 01 Raw Sources 原文分章一起收")
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()
    if args.stats:
        p = os.path.join(args.data, "data", "kb", "kb-stats.json")
        if os.path.exists(p):
            print(open(p, encoding="utf-8").read())
        else:
            print("尚未建索引")
        return
    build(args.data, args.vault or None, args.include_raw)


if __name__ == "__main__":
    main()
