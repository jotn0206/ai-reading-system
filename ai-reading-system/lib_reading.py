# -*- coding: utf-8 -*-
"""
阅读系统共享库（AI 阅读执行系统）

被 tts.py / kb-build.py / kb-search.py / gen-dashboard.py / personalize.py / note-add.py 共用。
用法：脚本里 `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` 后 `import lib_reading as L`。

只依赖标准库。Windows 控制台为 GBK，所有脚本开头都会 reconfigure stdout 为 utf-8。
"""
import json
import os
import re
import sys
import shutil
import hashlib
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

STAGE_NAMES = {
    1: "新书推荐", 2: "粗读", 3: "逐章拆解", 4: "全书逻辑链",
    5: "重点推荐", 6: "原子笔记", 7: "行动清单", 8: "书评与发布",
}
STAGE_ICONS = {1: "📚", 2: "🔍", 3: "🧩", 4: "🔗", 5: "🎯", 6: "🗂", 7: "✅", 8: "✍️"}


# ---------------------------------------------------------------- state.js
def load_state(path):
    """读 data/state.js（window.READING_DATA = {...};）→ dict。"""
    with open(path, "r", encoding="utf-8") as f:
        s = f.read()
    s = re.sub(r"^[\s\S]*?window\.READING_DATA\s*=\s*", "", s)
    s = s.rstrip()
    if s.endswith(";"):
        s = s[:-1]
    return json.loads(s)


def dump_state(data):
    return "window.READING_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n"


def backup(path):
    if not os.path.exists(path):
        return None
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = path + ".bak-" + ts
    shutil.copy2(path, dst)
    return dst


def state_file(data_dir):
    return os.path.join(data_dir, "data", "state.js")


def find_book(data, title):
    """书名模糊匹配（去掉书名号、空格后比较）。"""
    t = norm_title(title)
    for b in data.get("books", []):
        if norm_title(b.get("title", "")) == t:
            return b
    for b in data.get("books", []):
        if t and t in norm_title(b.get("title", "")):
            return b
    return None


def norm_title(s):
    return re.sub(r"[\s《》<>\"'“”‘’·:：,，。.!！?？/\\|*\[\]()（）]", "", str(s or "")).lower()


def slug(s):
    """文件名安全化（保留中日韩与字母数字）。"""
    s = re.sub(r"[\\/:*?\"<>|\r\n\t]", "_", str(s or "")).strip().strip(".")
    return s[:60] if s else "untitled"


# ---------------------------------------------------------------- stages
def stage_obj(b, sid):
    st = (b.get("stages") or {}).get(str(sid)) or (b.get("stages") or {}).get(sid) or {}
    return st


def stage_data(b, sid):
    return stage_obj(b, sid).get("data") or {}


def stage_done(b, sid):
    """兼容两种写法：status==='done' / done===true。"""
    st = stage_obj(b, sid)
    if st.get("status") == "done":
        return True
    if st.get("done") is True:
        return True
    return False


def done_stages(b):
    return [i for i in range(1, 9) if stage_done(b, i)]


def progress(b):
    """完成度 0~1（八环节完成数 / 8）。"""
    return len(done_stages(b)) / 8.0


# ---------------------------------------------------------------- 可读文本抽取（复刻 index.html extractReadable）
def _lines(s):
    return [x.strip() for x in str(s or "").split("\n") if x.strip()]


def _sec(S, title, *paras):
    ps = [str(x).strip() for x in paras if x is not None and str(x).strip()]
    if ps:
        S.append((str(title), ps))


def readable_sections(b, sid):
    """返回 [(标题, [段落...]), ...]——与工作台「🔊 朗读本环节」同源。"""
    d = stage_data(b, sid)
    S = []
    if sid == 1:
        _sec(S, "书籍信息", "《%s》 %s" % (b.get("title", ""), b.get("author") or ""),
             ("来源：%s" % b.get("source")) if b.get("source") else None,
             ("标签：" + "、".join(b.get("tags") or [])) if (b.get("tags") or []) else None)
        for i, c in enumerate(d.get("chapters") or []):
            _sec(S, "章节 %d：%s" % (i + 1, c.get("title") or "未命名"), c.get("summary"), c.get("note"))
        _sec(S, "入库理由", d.get("reason"))
    elif sid == 2:
        _sec(S, "一句话总结", d.get("oneLiner"))
        _sec(S, "这本书在回答什么问题", d.get("coreQuestion"))
        _sec(S, "作者的答案", d.get("authorAnswer"))
        _sec(S, "作者信息", d.get("authorInfo"))
        _sec(S, "写作背景", d.get("authorBackground"))
        if d.get("authorWorks"):
            _sec(S, "作者其他作品", *_lines(d.get("authorWorks")))
        if d.get("authorRelations"):
            _sec(S, "名人关联", *_lines(d.get("authorRelations")))
        for c in d.get("concepts") or []:
            _sec(S, "核心概念：%s" % (c.get("name") or "未命名"), c.get("definition"),
                 ("人话翻译：%s" % c["plain"]) if c.get("plain") else None,
                 ("什么时候用：%s" % c["whenUse"]) if c.get("whenUse") else None)
        if d.get("insights"):
            _sec(S, "深度洞察", *_lines(d.get("insights")))
        if d.get("expertReviews"):
            _sec(S, "专家与媒体评价", *_lines(d.get("expertReviews")))
        if d.get("hotReviews"):
            _sec(S, "网络热评", *_lines(d.get("hotReviews")))
    elif sid == 3:
        for c in d.get("chapters") or []:
            t = c.get("title") or "未命名"
            _sec(S, "章节：%s" % t, c.get("summary"),
                 ("个人理解：%s" % c["personal"]) if c.get("personal") else None)
            qs = _lines(c.get("quotes"))
            if qs:
                _sec(S, "%s · 金句" % t, *qs)
            cs = _lines(c.get("cases"))
            if cs:
                _sec(S, "%s · 案例" % t, *cs)
            dc = _lines(c.get("deepCard"))
            if dc:
                _sec(S, "%s · 六维深化卡" % t, *dc)
    elif sid == 4:
        for i, c in enumerate(d.get("chain") or []):
            _sec(S, "逻辑环节 %d：%s" % (i + 1, c.get("label") or "未命名"), c.get("note"))
    elif sid == 5:
        for r in d.get("recommended") or []:
            if r.get("isKey"):
                _sec(S, "重点章节：%s" % r.get("title"), r.get("rationale"))
        _sec(S, "针对性阅读总结", d.get("note"))
    elif sid == 6:
        for c in d.get("cards") or []:
            _sec(S, "%s：%s" % (c.get("type") or "概念卡", c.get("concept") or "未命名"),
                 c.get("oneLiner"), *_lines(c.get("points")),
                 ("我的思考：%s" % c["myThought"]) if c.get("myThought") else None)
    elif sid == 7:
        items = []
        for i, a in enumerate(d.get("actions") or []):
            items.append("%d. %s%s%s" % (
                i + 1, a.get("content") or "",
                ("（做到算数：%s）" % a["verify"]) if a.get("verify") else "",
                " ✅" if a.get("done") else ""))
        _sec(S, "行动清单", *items)
    elif sid == 8:
        _sec(S, "书评草稿", *_lines(d.get("draft")))
        _sec(S, "发布状态", "当前状态：%s%s" % (
            d.get("publishStatus") or "草稿",
            ("，爆款评分 %s" % d["hitScore"]) if d.get("hitScore") else ""))
    return S


def readable_book(b):
    """全 8 环节合并成「全书朗读稿」。"""
    S = []
    for sid in range(1, 9):
        secs = readable_sections(b, sid)
        if secs:
            S.append(("%s 环节%d · %s" % (STAGE_ICONS[sid], sid, STAGE_NAMES[sid]), []))
            S.extend(secs)
    return S


# ---------------------------------------------------------------- 全本原文
def fulltext_path(data_dir, book):
    return os.path.join(data_dir, "data", "fulltext", slug(book) + ".md")


def fulltext_sections(data_dir, book, max_chars=None):
    """按 '## ' 一级标题切章 → [(章名, [段落]), ...]。无文件返回 []。"""
    p = fulltext_path(data_dir, book)
    if not os.path.exists(p):
        return []
    with open(p, "r", encoding="utf-8", errors="ignore") as f:
        txt = f.read()
    txt = re.sub(r"\[第\s*\d+\s*页\]", "", txt)
    secs = []
    cur_t, cur_p = "开篇", []
    for line in txt.split("\n"):
        if re.match(r"^#{1,3}\s+", line):
            if cur_p:
                secs.append((cur_t, cur_p))
            cur_t = re.sub(r"^#{1,3}\s+", "", line).strip() or "开篇"
            cur_p = []
        else:
            s = line.strip()
            if s:
                cur_p.append(s)
    if cur_p:
        secs.append((cur_t, cur_p))
    return secs


# ---------------------------------------------------------------- 切块（TTS 用）
_SENT_END = "。！？!?；;\n"


def split_blocks(paras, max_chars=800):
    """把段落列表切成 ≤max_chars 的朗读块，优先在句末断开。"""
    blocks, buf = [], ""
    for p in paras:
        p = p.strip()
        if not p:
            continue
        if len(p) > max_chars:
            if buf:
                blocks.append(buf)
                buf = ""
            start = 0
            while start < len(p):
                chunk = p[start:start + max_chars]
                cut = -1
                for ch in _SENT_END:
                    cut = max(cut, chunk.rfind(ch))
                if cut > max_chars * 0.35:
                    cut += 1
                    blocks.append(chunk[:cut])
                    start += cut
                else:
                    blocks.append(chunk)
                    start += max_chars
            continue
        if len(buf) + len(p) + 1 <= max_chars:
            buf = (buf + p) if not buf else (buf + " " + p)
        else:
            if buf:
                blocks.append(buf)
            buf = p
    if buf:
        blocks.append(buf)
    return blocks


# ---------------------------------------------------------------- 笔记 / 洞察（jsonl）
def notes_dir(data_dir):
    return os.path.join(data_dir, "data", "notes")


def notes_file(data_dir, book):
    return os.path.join(notes_dir(data_dir), slug(book) + ".jsonl")


def read_notes(data_dir, book=None):
    """读笔记 jsonl → list[dict]。book=None 读全部。"""
    d = notes_dir(data_dir)
    if not os.path.isdir(d):
        return []
    out = []
    if book:
        files = [notes_file(data_dir, book)]
    else:
        files = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".jsonl")]
    for fp in files:
        if not os.path.exists(fp):
            continue
        with open(fp, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    return out


def append_note(data_dir, note):
    d = notes_dir(data_dir)
    os.makedirs(d, exist_ok=True)
    fp = notes_file(data_dir, note.get("book") or "未分类")
    with open(fp, "a", encoding="utf-8") as f:
        f.write(json.dumps(note, ensure_ascii=False) + "\n")
    return fp


def next_note_id(data_dir, book):
    notes = read_notes(data_dir, book)
    today = datetime.now().strftime("%Y%m%d")
    n = sum(1 for x in notes if str(x.get("id", "")).startswith(today)) + 1
    while any(x.get("id") == "%s-%03d" % (today, n) for x in notes):
        n += 1
    return "%s-%03d" % (today, n)


# ---------------------------------------------------------------- 杂项
def today():
    return datetime.now().strftime("%Y-%m-%d")


def now_iso():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def add_days(dstr, n):
    try:
        d = datetime.strptime(dstr, "%Y-%m-%d")
    except Exception:
        d = datetime.now()
    return (d + timedelta(days=n)).strftime("%Y-%m-%d")


def days_between(a, b):
    try:
        da = datetime.strptime(a, "%Y-%m-%d")
        db = datetime.strptime(b, "%Y-%m-%d")
        return (db - da).days
    except Exception:
        return None


def sha1(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def cjk_chars(s):
    return len(re.findall(r"[\u4e00-\u9fff]", str(s or "")))
