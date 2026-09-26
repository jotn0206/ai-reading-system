#!/usr/bin/env node
/**
 * split_fulltext.js — 把书籍全文 markdown 按章节拆分为独立章节笔记
 *
 * 用法: node split_fulltext.js <全文.md> <书名> [--out <目录>] [--manifest <json路径>]
 *   --out       缺省 ./chapters/<书名>/
 *   --manifest  缺省 <out>/../chapters_manifest.json（记录每章序号/标题/字数）
 *
 * 产出: 每章一个 md（frontmatter + 原文正文 + 前后章导航），文件名 NN-章名.md
 * 切章规则: 一级章节 = 全文中的 `## ` 标题行；前言/序合并为 00；附录归 99。
 */
const fs = require('fs');
const path = require('path');

const rawArgs = process.argv.slice(2);
const getOpt = (k) => { const i = rawArgs.indexOf(k); return i >= 0 ? rawArgs[i + 1] : null; };
const flag = (k) => rawArgs.includes(k);
const SRC = rawArgs[0];
const TITLE = rawArgs[1];
if (!SRC || !TITLE) {
  console.error('用法: node split_fulltext.js <全文.md> <书名> [--out <目录>] [--manifest <json路径>]');
  process.exit(1);
}
const OUT = getOpt('--out') || path.join('chapters', TITLE);
const MANIFEST = getOpt('--manifest') || path.join(path.dirname(OUT), 'chapters_manifest.json');
const TODAY = new Date().toISOString().slice(0, 10);

// ---------- 中文数字 → 两位序号 ----------
const CN = { '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9 };
function cnNum(str) {
  if (str === '十') return 10;
  if (str.startsWith('十')) return 10 + CN[str[1]];
  if (str.includes('十')) { const m = str.split('十'); return CN[m[0]] * 10 + (m[1] ? CN[m[1]] : 0); }
  return CN[str] || 0;
}
function chapterNo(title) {
  const m = title.match(/^第(.+?)章/);
  if (m) return String(cnNum(m[1])).padStart(2, '0');
  if (/^(前言|序)/.test(title)) return '00';
  return '99'; // 致谢等附录
}

// ---------- 解析全文 ----------
const text = fs.readFileSync(SRC, 'utf8');
const lines = text.split(/\r?\n/);
const sections = [];
let cur = null, preamble = [];
for (const line of lines) {
  if (/^## /.test(line)) { cur = { title: line.replace(/^## /, '').trim(), body: [] }; sections.push(cur); }
  else if (cur) cur.body.push(line);
  else if (!/^\s*$/.test(line)) preamble.push(line);
}
preamble = preamble.filter(l => !/^#\s/.test(l) && !/^>\s*来源/.test(l) && !/^>\s*用途/.test(l)).join('\n').trim();
console.log(`解析到 ${sections.length} 个章节段落：`);
sections.forEach(s => console.log(`  ${chapterNo(s.title)} — ${s.title} (${s.body.join('\n').length} 字符)`));

// 前言 + 序 合并为一篇
const merged = [];
for (let i = 0; i < sections.length; i++) {
  const s = sections[i];
  const nxt = sections[i + 1];
  if (chapterNo(s.title) === '00' && nxt && chapterNo(nxt.title) === '00') {
    merged.push({ title: '前言与序', body: [...s.body, '', '---', '', `## ${nxt.title}`, ...nxt.body] });
    i++;
    continue;
  }
  merged.push(s);
}
console.log(`\n合并后 ${merged.length} 篇，开始生成。`);

// ---------- 生成章笔记 ----------
fs.mkdirSync(OUT, { recursive: true });
const built = merged.map((s, idx) => {
  const no = chapterNo(s.title);
  const fname = `${no}-${s.title.replace(/\s+/g, '-')}`;
  const body = s.body.join('\n').trim();

  let md = `---\ntitle: ${TITLE}-${fname}\ntype: book-chapter\nbook: ${TITLE}\nchapter: "${no}"\nchars: ${body.length}\ndate: ${TODAY}\n---\n`;
  md += `\n# ${TITLE} · ${s.title}（原文）\n`;
  if (no === '00' && preamble) md += `\n> [!info] 卷首\n${preamble.split('\n').map(l => '> ' + l).join('\n')}\n`;
  md += `\n${body}\n`;
  const prev = merged[idx - 1], nxt = merged[idx + 1];
  md += `\n---\n`;
  md += prev ? `⬅️ 上一章: ${chapterNo(prev.title)}-${prev.title.replace(/\s+/g, '-')} · ` : '⬅️ 已是开篇 · ';
  md += nxt ? `下一章: ${chapterNo(nxt.title)}-${nxt.title.replace(/\s+/g, '-')} ➡️` : '➡️ 全书完\n';

  fs.writeFileSync(path.join(OUT, fname + '.md'), md, 'utf8');
  console.log(`  ✓ ${fname}.md (${body.length} 字符)`);
  return { no, title: s.title, fname, chars: body.length };
});

// ---------- 输出章节清单 ----------
const all = {};
all[TITLE] = built;
let old = {};
if (fs.existsSync(MANIFEST)) { try { old = JSON.parse(fs.readFileSync(MANIFEST, 'utf8')); } catch (e) {} }
fs.writeFileSync(MANIFEST, JSON.stringify({ ...old, ...all }, null, 2), 'utf8');
console.log(`\n✅ 完成：${built.length} 篇章节笔记 → ${OUT}`);
console.log(`   章节清单已更新 → ${MANIFEST}`);
