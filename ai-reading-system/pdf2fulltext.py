#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf2fulltext.py — PDF → 全文 markdown（AI 阅读执行系统 · WF1 新书入库用）

策略:
  - 优先用 PDF 书签(outline)确定章节切分；无书签时回退到标题正则
  - 每页末尾插入 [第 N 页] 标记（优先取页面上的印刷页码，封面页偏移自动对齐）
  - 去掉页眉页码行、重复的章标题行
  - 章标题映射为 `## `（供 split_fulltext.js 切章），小节标题 `1.2 …` 保持正文

用法: python pdf2fulltext.py <book.pdf> <书名> [outdir]
  outdir 缺省为 ./data/fulltext
"""
import re
import sys
from pathlib import Path

from pypdf import PdfReader


def flat_outline(reader: PdfReader):
    out = []
    try:
        items = reader.outline
    except Exception:
        return out
    def walk(ol, level):
        for it in ol:
            if isinstance(it, list):
                walk(it, level + 1)
            else:
                try:
                    page = reader.get_destination_page_number(it) + 1
                    out.append((level, it.title.strip(), page))
                except Exception:
                    pass
    walk(items, 0)
    return out


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    pdf_path, title = sys.argv[1], sys.argv[2]
    outdir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path('data') / 'fulltext'
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f'{title}.md'

    reader = PdfReader(pdf_path)
    total = len(reader.pages)
    chapters = [c for c in flat_outline(reader) if c[0] == 0]
    # 只保留章级（第X章/前言/序/附录等），从版权页之后开始
    chapters = [c for c in chapters if re.match(r'^(第\s*\S+\s*章|前言|序言|序|附录|写给|内容提要|致谢)', c[1]) or re.match(r'^第\S+章', c[1].replace(' ', ''))]

    # 归一化（去空白）索引：用于剔除正文里重复出现的章标题行
    norm = lambda s: re.sub(r'\s+', '', s)
    chap_norms = {norm(c[1]): c[1] for c in chapters}

    # 章页区间
    ranges = []
    for i, (_, t, p) in enumerate(chapters):
        end = chapters[i + 1][2] - 1 if i + 1 < len(chapters) else total
        ranges.append((t, p, end))

    body_parts = []
    kept_pages = 0
    for chap_title, p_start, p_end in ranges:
        body_parts.append(f'\n\n## {chap_title}\n')
        for p in range(p_start, min(p_end, total) + 1):
            text = (reader.pages[p - 1].extract_text() or '').strip()
            if not text:
                text = '（本页为图片或无文本层）'
            lines = []
            printed = None
            for ln in text.split('\n'):
                s = ln.strip()
                if not s:
                    continue
                if printed is None and re.fullmatch(r'\d{1,3}', s):
                    printed = int(s)  # 页码行（通常是页首/页尾）
                    continue
                if norm(s) in chap_norms:
                    continue  # 正文里重复的章标题
                lines.append(s)
            page_label = printed if printed else p
            body_parts.append('\n'.join(lines) + f'\n[第 {page_label} 页]\n')
            kept_pages += 1

    header = f'# {title}\n\n> 来源: PDF 直转（pdf2fulltext.py，含 [第 N 页] 页码标记）\n\n'
    out.write_text(header + ''.join(body_parts), encoding='utf-8')
    chars = len(''.join(body_parts))
    secs = len(ranges)
    print(f'✅ {out}')
    print(f'   共 {secs} 个章节, {kept_pages}/{total} 页提取, {chars} 字符')
    if secs == 0:
        print('   ⚠ 未识别到书签章级标题——请检查 PDF 是否有目录书签')


if __name__ == '__main__':
    main()
