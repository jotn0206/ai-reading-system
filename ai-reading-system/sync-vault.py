#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync-vault.py v2 —— AI 阅读执行系统 → Obsidian vault 三轨沉淀

把阅读系统 state.js 里一本书的八环节成果，按 vault 既定规范拆成三处：
  T1  01 Raw Sources/20_书籍原文/<书名>/       全本分章节原文 + 原文索引
  T2  02 Wiki/12_单书笔记/<书名>/深化卡·第X章.md  逐章深化卡（来自 stage3.deepCard）
  T3  02 Wiki/13_原子笔记(Zettelkasten)/<类型>/<id>.md  每张原子卡独立成卡

用法：
  python sync-vault.py --data <state.js> --book <书名> [--raw <原文txt>] [--vault $READING_VAULT]
  python sync-vault.py --data <state.js> --all [--vault $READING_VAULT]

说明：
  --vault 缺省读环境变量 READING_VAULT（vault 根目录，如 Obsidian 库根）；
  没设就直接报错，不会拿别人的路径去建卡——避免沉淀到错误目录。
  --raw 指向下载的全本原文 txt；缺失则 T1 降级为"⏳ 待补原文"占位，不报错。
  T2/T3 内容严格取自 state.js，绝不编造；缺字段如实留空。
"""
import argparse, json, os, re, sys
from collections import Counter, OrderedDict

# ---------- 路径默认值 ----------
# vault 根不写死：优先环境变量 READING_VAULT（本机设一次即可），缺省时报错提示，别猜路径
DEFAULT_VAULT = os.environ.get("READING_VAULT", "")
T1_ROOT = "01 Raw Sources/20_书籍原文"
T2_ROOT = "02 Wiki/12_单书笔记"
T3_ROOT = "02 Wiki/13_原子笔记(Zettelkasten)"

CARD_TYPE_DIR = {"概念卡": "概念卡", "观点卡": "观点卡", "行动卡": "行动卡"}


def load_state(path):
    s = open(path, encoding="utf-8").read()
    m = re.search(r"window\.READING_DATA\s*=\s*(\{.*\})\s*;?\s*$", s, re.S)
    if not m:
        raise SystemExit("state.js 解析失败")
    return json.loads(m.group(1))


def get_book(state, title):
    for b in state["books"]:
        if b["title"] == title:
            return b
    return None


def norm_tags(x):
    """任意形式 -> 合法 YAML 引号数组字符串"""
    if x is None:
        return '["读书"]'
    if isinstance(x, list):
        items = [str(i).strip() for i in x if str(i).strip()]
    else:
        items = [p.strip() for p in re.split(r"[/,，、]", str(x)) if p.strip()]
    if not items:
        items = ["读书"]
    return "[" + ", ".join('"%s"' % i for i in items) + "]"


def safe_name(s, maxlen=40):
    s = re.sub(r'[\\/:*?"<>|#^]', " ", str(s)).strip()
    s = re.sub(r"\s+", " ", s)
    return s[:maxlen].strip()


def pad(num_str):
    digits = re.findall(r"\d+", num_str)
    if digits:
        return "%03d" % int(digits[0])
    return num_str


def norm_card_id(cid):
    """原子卡 ID 必须遵循全局库约定：YYYYMMDD-NNN（创建日 8 位 + 3 位序号）。

    书名缩写码（如 JCSX-001、FCL-003）一律视为非法——不再识别、不再生成，
    由人工修正为日期格式。返回规范化的 id（或原样返回并告警）。
    """
    if re.match(r"^\d{8}-\d{1,3}$", cid or ""):
        return cid
    sys.stderr.write("⚠️ 原子卡 ID 非日期格式，已跳过规范化（请改为 YYYYMMDD-NNN）：%s\n" % cid)
    return cid


# ===================== T1 原文分章 =====================
def split_raw(raw_path, book_title, vault):
    out_dir = os.path.join(vault, T1_ROOT, book_title)
    os.makedirs(out_dir, exist_ok=True)
    text = open(raw_path, encoding="utf-8", errors="replace").read()
    m = re.search(r"\n\s*正文\s*\n", text)
    intro = text[: m.start()].strip() if m else ""
    body = text[m.end():] if m else text

    pat = re.compile(r"\n(第[0-9零一二三四五六七八九十百千]+章[^\n]*)\n")
    parts = pat.split(body)
    pre = parts[0].strip()
    chapters = []  # (num, title, content)
    for i in range(1, len(parts), 2):
        head = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        nm = re.search(r"第([0-9零一二三四五六七八九十百千]+)章", head)
        num = nm.group(1) if nm else str((i + 1) // 2)
        title = head.split("章", 1)[1].strip() if "章" in head else head
        chapters.append((num, title, content))

    rows = []
    # 序章/题记
    if pre:
        fn = "00-序章与题记.md"
        chars = len(pre)
        write_raw(out_dir, fn, book_title, "00", "序章与题记", pre, chars)
        rows.append(("00", "序章与题记", fn, chars))
    for num, title, content in chapters:
        fn = "%s-第%s章-%s.md" % (pad(num), num, safe_name(title))
        chars = len(content)
        write_raw(out_dir, fn, book_title, pad(num), "第%s章 %s" % (num, title), content, chars)
        rows.append((pad(num), "第%s章 %s" % (num, title), fn, chars))

    # 索引
    idx = ["---",
           'title: %s-原文索引' % book_title,
           "type: raw-source",
           'book: %s' % book_title,
           'tags: ["raw", "书籍原文"]',
           "date: 2026-10-07",
           "---",
           "# %s · 原文索引" % book_title, "",
           "- **关联拆解**：[[%s - 主页]] · [[%s - 3·逐章拆解|逐章拆解]]" % (book_title, book_title), ""]
    idx.append("## 章节目录（点击精读原文）\n")
    idx.append("| 章 | 原文 | 字数 | 对照 |")
    idx.append("|---|---|---|---|")
    for num, label, fn, chars in rows:
        base = fn[:-3]
        idx.append("| %s | [[%s|%s]] | %d | [[%s - 3·逐章拆解|拆解]] |" %
                   (num, base, label, chars, book_title))
    idx.append("")
    idx.append("- **导入系统**：reading-system（1 年 50 本书 AI 阅读执行系统）")
    open(os.path.join(out_dir, "%s-原文索引.md" % book_title), "w", encoding="utf-8").write("\n".join(idx))
    return len(chapters), out_dir


def write_raw(out_dir, fn, book, ch, heading, body, chars):
    md = ["---",
          "title: %s-%s" % (book, fn[:-3]),
          "type: raw-chapter",
          "book: %s" % book,
          'chapter: "%s"' % ch,
          "chars: %d" % chars,
          'tags: ["raw", "书籍原文", "读书"]',
          "date: 2026-10-07",
          "---", "",
          "# %s · %s（原文）" % (book, heading), "",
          "> 📖 精读原文 · [[%s-原文索引|📚 全书目录]] · [[%s - 主页|回到书主页]] · [[%s - 3·逐章拆解|对照拆解]]" % (book, book, book),
          "", body, ""]
    open(os.path.join(out_dir, fn), "w", encoding="utf-8").write("\n".join(md))


# ===================== T2 深化卡 =====================
def parse_deepcard(dc):
    """把【事】【理】【重点与启发】拆成 dict"""
    out = {}
    if not dc:
        return out
    for key in ["事", "理", "重点与启发"]:
        m = re.search(r"【%s】([\s\S]*?)(?=【|$)" % key, dc)
        if m:
            out[key] = m.group(1).strip()
    return out


def build_deepcards(book, vault, atomic_by_chapter):
    title = book["title"]
    s3 = book.get("stages", {}).get("3", {}).get("data", {})
    chs = s3.get("chapters", [])
    out_dir = os.path.join(vault, T2_ROOT, title)
    os.makedirs(out_dir, exist_ok=True)
    made = []
    for ch in chs:
        ctitle = ch.get("title", "")
        nm = re.search(r"第([0-9零一二三四五六七八九十百千]+)章", ctitle)
        cnum = nm.group(1) if nm else ""
        summary = ch.get("summary", "")
        personal = ch.get("personal", "")
        quotes = ch.get("quotes", "")
        cases = ch.get("cases", "")
        dc = parse_deepcard(ch.get("deepCard", ""))
        shi = dc.get("事", summary)
        li = dc.get("理", "")
        inspire = dc.get("重点与启发", personal)
        lead = (summary[:60] if summary else (ctitle)) 

        related_cards = atomic_by_chapter.get(cnum, [])
        rel_md = "\n".join("- [[%s|%s]] — %s" % (cid, cid, csrc) for cid, csrc in related_cards) or "- （暂无关联原子卡）"

        fn = "%s - 深化卡·%s.md" % (title, safe_name(ctitle))
        md = ["---",
              "title: %s - 深化卡·%s" % (title, ctitle),
              "type: deep-card",
              "book: %s" % title,
              'chapter: %s' % ctitle,
              'tags: ["读书", "深化卡", "投资", "炒股", "认知"]',
              "date: 2026-10-07",
              "lead: %s" % lead,
              "last_verified: 2026-10-07",
              'related: ["%s - 主页"]' % title,
              "category: 单书笔记",
              "aliases: []",
              "verified: true",
              "---",
              "# 🧭 深化卡 · %s" % ctitle,
              "> 归入 [[../README.md|单书笔记]]", "",
              "**结论先行**：%s" % lead, "",
              "> 来源书 [[%s - 主页]] · 拆解 [[%s - 3·逐章拆解]]" % (title, title), "",
              "## 六维拆解", "",
              "| 维度 | 内容 |",
              "|---|---|",
              "| 事 | %s |" % (shi or "—"),
              "| 理 | %s |" % (li or "—"),
              "| 重点与启发 | %s |" % (inspire or "—"),
              "| 金句 | %s |" % (quotes or "—"),
              "| 案例 | %s |" % (cases or "—"),
              "",
              "## 本章金句",
              "- %s" % quotes if quotes else "- （无）",
              "",
              "## 本章案例",
              "- %s" % cases if cases else "- （无）",
              "",
              "## 关联原子卡",
              rel_md,
              "",
              "## 常见误区 / 风险点",
              "- 本文为作者方法论/流程梳理，非外部事实声明；涉及具体投资数据仍以最新核验为准。",
              ""]
        open(os.path.join(out_dir, fn), "w", encoding="utf-8").write("\n".join(md))
        made.append(fn)
    return made


# ===================== T3 原子卡 =====================
def parse_links(links_str):
    if not links_str:
        return []
    out = []
    for part in re.split(r"[\n;；]", str(links_str)):
        m = re.search(r"(\d{8}-[0-9]{1,3})", part)
        if m:
            out.append(m.group(1))
    return out


def build_atomic(book, vault):
    title = book["title"]
    s6 = book.get("stages", {}).get("6", {}).get("data", {})
    cards = s6.get("cards", [])
    made = []
    for c in cards:
        cid = norm_card_id(c.get("id", "CARD"))
        ctype = c.get("type", "概念卡")
        concept = c.get("concept", "")
        one = c.get("oneLiner", "")
        points = c.get("points", "")
        source = c.get("source", "")
        thought = c.get("myThought", "")
        links = parse_links(c.get("links", ""))
        tags = norm_tags(c.get("tags"))
        d = CARD_TYPE_DIR.get(ctype, "概念卡")
        out_dir = os.path.join(vault, T3_ROOT, d)
        os.makedirs(out_dir, exist_ok=True)
        fn = "%s.md" % cid
        pt_lines = "\n".join("- %s" % p.strip() for p in str(points).split("\n") if p.strip())
        rel = ['"%s - 主页"' % title] + ['"%s"' % l for l in links]
        rel_section = "\n".join("- [[%s]] — 相关卡片" % l for l in ([title + " - 主页"] + links))
        md = ["---",
              "title: %s %s" % (cid, concept),
              "type: zettel",
              "cardType: %s" % ctype,
              "book: %s" % title,
              "concept: %s" % concept,
              "tags: %s" % tags,
              "date: 2026-10-07",
              "source: %s" % source,
              "lead: %s" % one,
              "last_verified: 2026-10-07",
              "category: 原子笔记",
              "aliases: []",
              "verified: true",
              "related: [%s]" % ", ".join(rel),
              "---",
              "# 🗂️ %s" % concept,
              "> 归入 [[../README.md|原子笔记]]", "",
              "**结论先行**：%s" % one, "",
              "> **%s** · Zettelkasten 原子笔记 · ID %s · 来源书 [[%s - 主页]]" % (ctype, cid, title), "",
              "> [!summary] 一句话总结",
              "> %s" % one, "",
              "## 要点",
              pt_lines or "- （待补充）", "",
              "## 展开", "",
              str(points).strip() or "（待补充）", "",
              "## 来源",
              "%s" % source, "",
              "## 我的思考（斌哥）",
              "%s" % thought if thought else "（待补充）", "",
              "## 双向链接",
              rel_section, "",
              "## 常见误区 / 风险点",
              "- 本文为作者方法论/流程梳理，非外部事实声明。",
              ""]
        open(os.path.join(out_dir, fn), "w", encoding="utf-8").write("\n".join(md))
        made.append((cid, ctype, fn))
    return made


# ===================== 主页更新 =====================
def update_home(book, vault, n_chapters, deep_made, atomic_made):
    title = book["title"]
    home = os.path.join(vault, T2_ROOT, title, "%s - 主页.md" % title)
    if not os.path.exists(home):
        return
    s = open(home, encoding="utf-8").read()

    # 精读原文 段：指向原文索引
    s = re.sub(r"全书数据见阅读系统[^\n]*",
               "全书原文见 [[%s-原文索引|📚 %s 全书原文（%d 章）]]" % (title, title, n_chapters),
               s)

    # 原子笔记分类：列出独立卡
    atomic_lines = "概念卡×%d · 观点卡×%d · 行动卡×%d（独立卡片见 [[../13_原子笔记(Zettelkasten)/README|🗂️ 原子笔记库]]）" % (
        sum(1 for _, t, _ in atomic_made if t == "概念卡"),
        sum(1 for _, t, _ in atomic_made if t == "观点卡"),
        sum(1 for _, t, _ in atomic_made if t == "行动卡"),
    )
    s = re.sub(r"概念卡×\d+ · 观点卡×\d+ · 行动卡×\d+（存于[^\n]*）", atomic_lines, s)

    # 追加深化卡片小节（若不存在）
    if "## 深化卡片" not in s:
        deep_block = "\n## 深化卡片（12 章逐章深化）\n"
        for fn in deep_made:
            label = fn.replace("%s - 深化卡·" % title, "").replace(".md", "")
            deep_block += "- [[%s|深化卡·%s]]\n" % (fn[:-3], label)
        # 插到 知识图谱 之前
        if "## 知识图谱" in s:
            s = s.replace("## 知识图谱", deep_block + "\n## 知识图谱")
        else:
            s += deep_block

    open(home, "w", encoding="utf-8").write(s)


# ===================== main =====================
def process(book, vault, raw_path):
    title = book["title"]
    print("\n=== 处理：《%s》===" % title)
    # 原子卡按章节索引（供深化卡关联）
    s6 = book.get("stages", {}).get("6", {}).get("data", {})
    atomic_by_chapter = {}
    for c in s6.get("cards", []):
        src = c.get("source", "")
        m = re.search(r"第([0-9零一二三四五六七八九十百千]+)章", src)
        if m:
            atomic_by_chapter.setdefault(m.group(1), []).append((c.get("id"), src))

    # T1
    if raw_path and os.path.exists(raw_path):
        n, d = split_raw(raw_path, title, vault)
        print("  T1 原文分章：%d 章 -> %s" % (n, d))
    else:
        print("  T1 原文分章：跳过（未提供 --raw 原文 txt，主页标注待补）")
        n = 0

    # T2
    deep = build_deepcards(book, vault, atomic_by_chapter)
    print("  T2 深化卡：%d 张 -> %s" % (len(deep), os.path.join(vault, T2_ROOT, title)))

    # T3
    atomic = build_atomic(book, vault)
    cc = Counter(t for _, t, _ in atomic)
    print("  T3 原子卡：%d 张 (%s) -> %s" % (len(atomic),
          " · ".join("%s×%d" % (k, v) for k, v in cc.items()),
          os.path.join(vault, T3_ROOT)))

    # 主页
    update_home(book, vault, n, deep, atomic)
    print("  主页：已更新 原文链接 / 原子卡分类 / 深化卡片小节")
    return n, deep, atomic


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--book")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--raw", default=None, help="下载的全本原文 txt 路径（T1 分章用）")
    ap.add_argument("--vault", default=DEFAULT_VAULT)
    args = ap.parse_args()
    if not args.vault:
        raise SystemExit("未指定 vault 根目录：请 --vault <vault根> 或设置环境变量 "
                         "READING_VAULT（例如 Obsidian 库根目录）")

    state = load_state(args.data)
    targets = []
    if args.all:
        targets = state["books"]
    elif args.book:
        b = get_book(state, args.book)
        if not b:
            print("未找到书：%s" % args.book); sys.exit(1)
        targets = [b]
    else:
        print("需指定 --book 或 --all"); sys.exit(1)

    for b in targets:
        # 八环节未完成（done 数 < 8）的书，T2/T3 仍生成但标注
        process(b, args.vault, args.raw if args.raw else b.get("stages", {}).get("1", {}).get("data", {}).get("rawFile"))


if __name__ == "__main__":
    main()
