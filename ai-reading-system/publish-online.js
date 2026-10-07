/* 生成在线工作台发布包（默认 dist-online/）
 * 用法: node publish-online.js --data <工作目录> [--out <发布包目录>]
 *   例: node publish-online.js --data ../reading-system
 *       node publish-online.js --data D:/work/reading-data --out D:/work/dist-online
 *
 * 规则（2026-09-27 事故固化，别破坏）:
 *   1. index.html 一律取自源码 index.html —— 口令门等改动只改源码，杜绝手工改发布包
 *   2. 发布包只带 index.html + data/state.js
 *   3. 版权红线: 包内不得出现 data/fulltext/ 与任何书全文
 *   4. 发布前自检: state.js JSON 合法 + 口令门存在 + 八环节齐全
 */
const fs = require('fs');
const path = require('path');

function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : def;
}

const WORKDIR = path.resolve(arg('data', '.'));
const DIST = path.resolve(arg('out', path.join(WORKDIR, 'dist-online')));
const TITLE_HINT = arg('title', '');   /* 可选：只检查书名为子串的那本，默认全部检查 */

if (!fs.existsSync(path.join(WORKDIR, 'index.html'))) {
  console.error('❌ 工作目录里找不到 index.html：' + WORKDIR);
  process.exit(1);
}

const src = fs.readFileSync(path.join(WORKDIR, 'index.html'), 'utf8');
const statePath = path.join(WORKDIR, 'data', 'state.js');
if (!fs.existsSync(statePath)) {
  console.error('❌ 工作目录里找不到 data/state.js：' + statePath);
  process.exit(1);
}
const state = fs.readFileSync(statePath, 'utf8');

let s;
try {
  s = JSON.parse(state.replace(/^[\s\S]*?window\.READING_DATA\s*=\s*/, '').replace(/;\s*$/, ''));
} catch (e) {
  console.error('❌ state.js 不是合法 JSON:', e.message);
  process.exit(1);
}
console.log('state.js JSON 自检 ✅ | 书数:', s.books.length);

/* —— 口令门自检 —— */
const gateOk = /__gateUnlock/.test(src) && /id="gate"/.test(src) && /data-locked/.test(src);
if (!gateOk) {
  console.error('❌ 口令门缺失，请检查 index.html（应是源码里的 DOMContentLoaded + #gate + data-locked）');
  process.exit(1);
}
const m = /var\s+PASS\s*=\s*['"]([^'"]+)['"]/.exec(src);
console.log('口令门自检 ✅ | 当前口令:', m ? m[1] : '(未提取到)');

/* —— 版权红线 —— */
const fulltextDir = path.join(WORKDIR, 'data', 'fulltext');
const fulltextFiles = fs.existsSync(fulltextDir) ? fs.readdirSync(fulltextDir).length : 0;
if (fulltextFiles) {
  console.log('⚠️  本地 data/fulltext/ 有 ' + fulltextFiles + ' 个文件，但不进发布包（仅本地用）');
}
if (/data\/fulltext/.test(src)) {
  console.error('❌ index.html 里出现 data/fulltext 引用，请确认未把全文路径打进页面');
  process.exit(1);
}

/* —— 八环节齐全检查 —— */
let bad = 0;
const books = TITLE_HINT ? s.books.filter(b => (b.title || '').includes(TITLE_HINT)) : s.books;
books.forEach(b => {
  const n = Object.keys(b.stages || {}).length;
  if (n !== 8) { console.log('  ⚠️ ' + (b.title || '(无标题)') + ' 环节数 ' + n + '（非 8）'); bad++; }
});
console.log(books.length + ' 本书环节检查完毕' + (bad ? '，' + bad + ' 本异常' : '，全部 8 环节齐全 ✅'));
/* 环节不全必须在“写包之前”拦（2026-10-08 修正：原先先写包再报错，留下一个看着可发的被拒包）。
   但“正在读的书”本来就没跑满 8 环节，属于正常态 → 显式加 --allow-partial 才能带病发布。 */
if (bad) {
  if (!process.argv.includes('--allow-partial')) {
    console.error('\n❌ 有 ' + bad + ' 本书环节不全（<8）。');
    console.error('   若是正常在读书、确实要发：重跑一次并加 --allow-partial');
    console.error('   否则先补齐环节再发布。（只想检查某一本：加 --title "<书名片段>"）');
    process.exit(1);
  }
  console.log('⚠️  --allow-partial 已指定：' + bad + ' 本在读书（环节<8）照常进包');
}

/* —— 落盘（注入发布版本戳 buildStamp）——
   前端凭它判断"线上数据已更新"，让老访客浏览器里的旧 localStorage 缓存自动重播种。
   只用内容哈希（不含时间）：内容没变就不打扰访客在线上做的勾选/批注。 */
const crypto = require('crypto');
const stamp = crypto.createHash('sha1')
  .update(JSON.stringify(s.books) + JSON.stringify(s.profile || {}))
  .digest('hex').slice(0, 12);
const stateOut = '/* AI 阅读执行系统 · 发布包（自动生成，勿手改）\n'
  + '   改数据请改源码 data/state.js 后重跑 publish-online.js */\n'
  + 'window.READING_DATA = ' + JSON.stringify(Object.assign({}, s, { buildStamp: stamp })) + ';\n';
console.log('发布版本戳 buildStamp:', stamp, '（数据一旦变化，访客浏览器会自动重读）');
fs.mkdirSync(path.join(DIST, 'data'), { recursive: true });
fs.writeFileSync(path.join(DIST, 'index.html'), src);
fs.writeFileSync(path.join(DIST, 'data', 'state.js'), stateOut);

/* —— 可选：知识看板（WF5 产物）存在则一起进包 —— */
const kbSrc = path.join(WORKDIR, 'data', 'kb', 'dashboard.html');
if (fs.existsSync(kbSrc)) {
  fs.mkdirSync(path.join(DIST, 'data', 'kb'), { recursive: true });
  fs.writeFileSync(path.join(DIST, 'data', 'kb', 'dashboard.html'), fs.readFileSync(kbSrc));
  console.log('知识看板进包 ✅  data/kb/dashboard.html');
} else {
  console.log('ℹ️  未找到 data/kb/dashboard.html（gen-dashboard.py 生成），线上点「📈 知识看板」会提示未生成');
}

/* —— 复核发布包 —— */
const out = fs.readFileSync(path.join(DIST, 'index.html'), 'utf8');
JSON.parse(fs.readFileSync(path.join(DIST, 'data', 'state.js'), 'utf8')
  .replace(/^[\s\S]*?window\.READING_DATA\s*=\s*/, '').replace(/;\s*$/, ''));
console.log('发布包 JSON 复核 ✅');
console.log('fulltext 未进包:', fs.existsSync(path.join(DIST, 'data', 'fulltext')) ? '❌ 存在' : '✅ 不存在');
/* 真正的版权红线：state.js 里不得内嵌书全文（章节原文）。
   判据：扫描连续 ≥500 汉字的片段——正常笔记/书评远达不到，整章原文会超。 */
const strips = (stateOut.replace(/^[\s\S]*?window\.READING_DATA\s*=\s*/, '').match(/[一-鿿]{500,}/g) || []);
if (strips.length) {
  console.error('❌ state.js 内嵌了疑似书全文的连续长段（' + strips.length + ' 处，最长 ' +
    Math.max(...strips.map(t => t.length)) + ' 字）—— 全文应只留在 data/fulltext/ 不进包');
  process.exit(1);
}
console.log('发布包书全文特征: ✅ 无 ≥500 字连续中文片段');
console.log('发布包内容: ' +
  fs.statSync(path.join(DIST, 'index.html')).size + ' B index.html + ' +
  fs.statSync(path.join(DIST, 'data', 'state.js')).size + ' B state.js');
console.log('\n✅ ' + DIST + ' 已就绪，下一步: 跑 test-gate.py 回归 → 部署');
