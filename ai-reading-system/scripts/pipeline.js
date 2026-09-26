#!/usr/bin/env node
/**
 * pipeline.js — 一键收尾管线（AI 阅读执行系统）
 *
 * 步骤: 0 前置检查 → 1 原文校验网关（金句逐字/案例锚点回原文匹配）→ 2 页码计算+注入
 *       → 3 提取单书 state.json（供备份/再加工）
 *
 * 用法:
 *   node pipeline.js <书名> [--data <工作目录>] [--fulltext <md>] [--skip-verify] [--dry-run]
 *   --data        缺省 .（工作目录，其下应有 data/state.js 与 data/fulltext/<书名>.md）
 *   --fulltext    指定原文全文路径（缺省 <data>/data/fulltext/<书名>.md）
 *   --skip-verify 跳过金句硬网关（救急用，不建议）
 *   --dry-run     只校验+算页码，不写盘
 *
 * 前置: 新书已入库（add-book.js），环节3已产出逐章拆解（含金句/案例）。
 */
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const title = args[0];
const flag = (k) => args.includes(k);
const getOpt = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };

const DATA_DIR = getOpt('--data') || '.';
const DATA_FILE = path.join(DATA_DIR, 'data', 'state.js');
const DRY = flag('--dry-run');

if (!title) {
  console.error('用法: node pipeline.js <书名> [--data <工作目录>] [--fulltext <md>] [--skip-verify] [--dry-run]');
  process.exit(1);
}
const fulltextPath = getOpt('--fulltext') || path.join(DATA_DIR, 'data', 'fulltext', `${title}.md`);

// ---------- 数据读写（原子 + 备份） ----------
function readState() {
  const raw = fs.readFileSync(DATA_FILE, 'utf8');
  return JSON.parse(raw.replace(/^[\s\S]*?window\.READING_DATA\s*=\s*/, '').replace(/;\s*$/, ''));
}
function writeState(state) {
  if (fs.existsSync(DATA_FILE)) fs.copyFileSync(DATA_FILE, DATA_FILE + '.bak-' + new Date().toISOString().replace(/[:T]/g, '-').slice(0, 16));
  const body = '/* AI 阅读执行系统 · 数据唯一来源 —— 由 pipeline.js 回填 */\n'
    + 'window.READING_DATA = ' + JSON.stringify(state, null, 2) + ';\n';
  const tmp = DATA_FILE + '.tmp';
  fs.writeFileSync(tmp, body, 'utf8');
  fs.renameSync(tmp, DATA_FILE);
}
function loadBook(t) {
  const state = readState();
  const b = state.books.find(x => x.title.includes(t));
  if (!b) { console.error(`[0] 前置检查 FAIL: ${DATA_FILE} 中找不到「${t}」`); process.exit(1); }
  return b;
}

// ---------- 原文匹配（去空白归一） ----------
function buildIndex(raw) {
  const origIdx = []; let hay = '';
  for (let i = 0; i < raw.length; i++) {
    if (/[\s\u3000]/.test(raw[i])) continue;
    hay += raw[i]; origIdx.push(i);
  }
  const markers = [];
  const re = /\[第\s*(\d+)\s*页\]/g; let m;
  while ((m = re.exec(raw))) markers.push({ pos: m.index, page: m[1] });
  const pageAt = (normPos) => {
    const orig = origIdx[normPos]; let p = null;
    for (const mk of markers) { if (mk.pos <= orig) p = mk.page; else break; }
    return p;
  };
  const find = (text) => {
    const norm = text.replace(/[\s\u3000]/g, '');
    const i = hay.indexOf(norm);
    return i < 0 ? { found: false, page: null } : { found: true, page: pageAt(i) };
  };
  return { find };
}

// ---------- 解析金句/案例行 ----------
function parseQuotes(q) {
  return (q || '').split('\n').map(l => l.trim()).filter(Boolean)
    .map(line => {
      // 分层提取引文：直引号对优先（外层引文），再退弯引号对，最后取内层弯引号首段
      const text = (line.match(/"([^"]+)"/) || line.match(/“([^”]+)”/) || line.match(/["“]([^"”]+)["”]/) || [])[1] || null;
      return { line, text };
    })
    .filter(x => x.text);
}
function parseCases(c) {
  return (c || '').split('\n').map(l => l.trim()).filter(Boolean)
    .map(line => {
      const name = (line.match(/【([^】]+)】/) || [])[1] || null;
      // 校验/页码锚点：案例名常为概括标签，取描述中 ≥6 字的连续片段做原文匹配
      const desc = line.replace(/【[^】]*】/, '').replace(/（P\d+）/g, '');
      const segs = desc.split(/[，。；：、！？"""\s（）——]+/).map(s => s.trim()).filter(s => s.length >= 6);
      return { line, name, segs };
    })
    .filter(x => x.name);
}
const hasPageMark = (s, key) => new RegExp(`${key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*（P\\d+）`).test(s);
const hasPageMarkLoose = (s, key) => s.includes(key) && new RegExp(`${key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}["”']?\\s*（P\\d+）`).test(s);

// 案例校验/定位：名称逐字命中优先，否则用描述片段（防概括名误杀，仍能拦截凭空编造）
function locateCase(c) {
  const byName = idx.find(c.name);
  if (byName.found) return { found: true, page: byName.page, via: 'name' };
  for (const seg of c.segs) {
    const r = idx.find(seg);
    if (r.found) return { found: true, page: r.page, via: 'desc' };
  }
  return { found: false, page: null, via: 'none' };
}

// ================= 主流程 =================
const book = loadBook(title);
console.log(`[0] 前置检查: 「${book.title}」 · 数据: ${DATA_FILE} · 原文: ${fulltextPath} · dry-run=${DRY}`);
if (!fs.existsSync(fulltextPath)) {
  console.error(`    FAIL: 找不到原文全文。请先放置 ${path.join(DATA_DIR, 'data', 'fulltext', title + '.md')} 或用 --fulltext 指定`);
  process.exit(1);
}
const raw = fs.readFileSync(fulltextPath, 'utf8');
const idx = buildIndex(raw);
const chapters = (book.stages[3] && book.stages[3].data && book.stages[3].data.chapters) || [];
if (!chapters.length) {
  console.error('[0] 前置检查 FAIL: 环节3「逐章拆解」还没有章节与金句/案例数据，先完成环节3');
  process.exit(1);
}

// ---- 步骤1: 原文校验网关 ----
// 金句=硬网关（金句承诺逐字摘录，未命中=疑似编造，必须打回）
// 案例=软网关（案例允许忠实转述，自动定位不到的列入人工复核清单，留痕不拦截）
console.log('[1] 原文校验网关（金句逐字 / 案例锚点）');
let vOk = 0; const vFail = [], caseReview = [];
chapters.forEach(ch => {
  parseQuotes(ch.quotes).forEach(q => {
    if (idx.find(q.text).found) vOk++; else vFail.push(`金句: ${q.text.slice(0, 30)}…`);
  });
  parseCases(ch.cases).forEach(c => {
    const r = locateCase(c);
    if (r.found) vOk++; else caseReview.push(`${c.name}  ← 转述案例，请人工确认原文依据`);
  });
});
console.log(`    自动命中 ${vOk} 条（金句逐字 + 案例锚点）`);
if (vFail.length) {
  console.log(`    金句未命中 ${vFail.length} 条（硬网关打回）:`);
  vFail.forEach(f => console.log('      ✗ ' + f));
}
if (caseReview.length) {
  console.log(`    案例人工复核 ${caseReview.length} 条（转述，无法自动定位，不拦截）:`);
  caseReview.forEach(f => console.log('      ? ' + f));
}
if (vFail.length && !flag('--skip-verify')) {
  console.error('[1] 校验网关不通过 —— 请在工作台/数据中修正金句后重跑（倔强跳过请加 --skip-verify）');
  process.exit(1);
}
if (vFail.length) console.log('    ⚠ 已按 --skip-verify 放行');

// ---- 步骤2: 页码计算 + 注入 state ----
console.log('[2] 页码计算与注入（金句 "…"（P页）/ 案例 【…】（P页））');
let injQ = 0, injC = 0, already = 0; const noPage = [];
chapters.forEach(ch => {
  parseQuotes(ch.quotes).forEach(q => {
    if (hasPageMarkLoose(ch.quotes, q.text)) { already++; return; }
    const r = idx.find(q.text);
    if (!r.page) { noPage.push('金句: ' + q.text.slice(0, 20)); return; }
    const from = `"${q.text}"`, to = `"${q.text}"（P${r.page}）`;
    if (!ch.quotes.includes(from)) { noPage.push('金句(引号不匹配): ' + q.text.slice(0, 20)); return; }
    ch.quotes = ch.quotes.replace(from, to);
    if (ch.quotes.includes(to)) injQ++; else noPage.push('金句(替换未生效): ' + q.text.slice(0, 20));
  });
  parseCases(ch.cases).forEach(c => {
    if (hasPageMark(ch.cases.split('\n').find(l => l.includes(c.name)) || '', `【${c.name}】`)) { already++; return; }
    const r = locateCase(c);
    if (!r.page) { noPage.push('案例(原文未定位): ' + c.name); return; }
    const from = `【${c.name}】`, to = `【${c.name}】（P${r.page}）`;
    if (!ch.cases.includes(from)) { noPage.push('案例(不匹配): ' + c.name); return; }
    ch.cases = ch.cases.replace(from, to);
    if (ch.cases.includes(to)) injC++; else noPage.push('案例(替换未生效): ' + c.name);
  });
});
console.log(`    新注入 金句${injQ} / 案例${injC}，已有页码 ${already} 条${noPage.length ? `，原文无页码标记 ${noPage.length} 条` : ''}`);
noPage.forEach(f => console.log('      ? ' + f));

// ---- 步骤3: 回写 + 提取单书 state.json ----
if (!DRY) {
  const state = readState();
  const target = state.books.find(x => x.id === book.id || x.title === book.title);
  if (target) { target.stages = book.stages; writeState(state); console.log(`[3] state.js 已回写（含新页码，旧版已备份）`); }
  const out = { profile: state.profile, books: [book] };
  const outFile = path.join(DATA_DIR, 'data', `state-${book.id}.json`);
  fs.writeFileSync(outFile, JSON.stringify(out, null, 2), 'utf8');
  console.log(`[3] 单书数据已提取 → ${outFile} — ${book.title} · ${Object.keys(book.stages).length} 环节`);
} else {
  console.log('[3] dry-run 跳过写盘');
}

console.log(`\n✅ 管线完成: ${book.title}${DRY ? '（dry-run）' : ''} — 校验${vOk}命中/页码+${injQ + injC}条`);
