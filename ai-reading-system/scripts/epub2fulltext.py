#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
epub2fulltext.py — EPUB → 全文 markdown（AI 阅读执行系统 · 新书入库用）

产出: <outdir>/<书名>.md
  - 按 spine 顺序拼接正文，章节标题映射为 `## `（供 split_fulltext.js 切章）
  - 跳过 <1000 字符的封面/版权/目录分件
  - 篇级标题（上篇/下篇）降级为 `# `，不产生切章段
  - EPUB 无真实页码，不生成 [第 N 页] 标记（校验网关会如实报告，不编页码）

用法: python epub2fulltext.py <book.epub> <书名> [outdir]
  outdir 缺省为 ./data/fulltext
"""
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path

class XhtmlToMd(HTMLParser):
    BLOCK_SKIP = {'style', 'script', 'head', 'svg', 'img', 'image'}
    HEAD_MAP = {'h1': '## ', 'h2': '### ', 'h3': '#### ', 'h4': '##### '}

    def __init__(self):
        super().__init__()
        self.out = []
        self.skip = 0
        self.buf = ''

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCK_SKIP:
            self.skip += 1
        elif tag in self.HEAD_MAP:
            self._flush()
            self.buf = self.HEAD_MAP[tag]
        elif tag == 'li':
            self._flush()
            self.buf = '- '
        elif tag == 'blockquote':
            self._flush()
            self.buf = '> '
        elif tag == 'br':
            self.buf += ' '

    def handle_endtag(self, tag):
        if tag in self.BLOCK_SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in self.HEAD_MAP or tag in ('p', 'li', 'blockquote', 'div', 'tr'):
            self._flush()

    def handle_data(self, data):
        if not self.skip:
            self.buf += data

    def _flush(self):
        text = re.sub(r'\s+', ' ', self.buf).strip()
        if text:
            self.out.append(text)
        self.buf = ''


def extract_xhtml_text(raw: str) -> str:
    p = XhtmlToMd()
    p.feed(raw)
    p._flush()
    return '\n\n'.join(p.out)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    epub_path, title = sys.argv[1], sys.argv[2]
    outdir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path('data') / 'fulltext'
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f'{title}.md'

    z = zipfile.ZipFile(epub_path)
    opf_name = next(n for n in z.namelist() if n.endswith('.opf'))
    opf = z.read(opf_name).decode('utf-8')
    base = opf_name.rsplit('/', 1)[0]

    items = {}
    for m in re.finditer(r'<item\b[^>]*/?>', opf):
        tag = m.group(0)
        i = re.search(r'id="([^"]+)"', tag)
        h = re.search(r'href="([^"]+)"', tag)
        if i and h:
            href = h.group(1)
            items[i.group(1)] = f'{base}/{href}' if base and not href.startswith('/') else href.lstrip('/')

    spine = re.findall(r'<itemref[^>]*idref="([^"]+)"', opf)
    parts = []
    for sid in spine:
        path = items.get(sid)
        if not path or not re.search(r'\.(xhtml|html?)$', path, re.I):
            continue
        try:
            raw = z.read(path).decode('utf-8')
        except KeyError:
            continue
        text = extract_xhtml_text(raw)
        heads = [l for l in text.split('\n') if re.match(r'^#{2,4} ', l)]
        if heads and re.search(r'目\s*录', heads[0]):
            continue  # 目录页
        if not heads and len(text) < 1000:
            continue  # 封面/版权/篇级隔页等无标题小件
        parts.append(text)

    # 篇级标题（上篇/下篇/第X篇）降级为 '# '，避免被切章脚本当成章节
    def demote(line):
        if line.startswith('## ') and re.match(r'##\s*(上篇|下篇|第[一二三四五六七八九十]+篇)', line):
            return '#' + line[2:]
        return line

    body = '\n\n'.join(
        '\n'.join(demote(l) for l in part.split('\n')) for part in parts
    )
    header = f'# {title}\n\n> 来源: EPUB 直转（epub2fulltext.py，无真实页码）\n\n'
    out.write_text(header + body + '\n', encoding='utf-8')
    chars = len(body)
    secs = len(re.findall(r'^## ', body, re.M))
    print(f'✅ {out}  共 {len(parts)} 个分件, {secs} 个章节标题, {chars} 字符')


if __name__ == '__main__':
    main()
