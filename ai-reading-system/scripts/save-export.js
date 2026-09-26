#!/usr/bin/env node
/**
 * save-export.js — 把工作台「导出」的完整 JSON 回填为 data/state.js
 * 用法: node save-export.js <导出的.json> [--state <state.js路径>]
 *   --state 缺省 ./data/state.js（相对当前工作目录）
 * 流程: 工作台改完数据 → 工具栏「导出」得到 JSON → 本脚本校验+原子写盘（写前自动备份）
 */
const fs = require('fs');
const path = require('path');

const rawArgs = process.argv.slice(2);
const stateFlagIdx = rawArgs.indexOf('--state');
const STATE = stateFlagIdx >= 0 ? rawArgs.splice(stateFlagIdx, 2)[1] : path.join('data', 'state.js');
const input = rawArgs[0];

if (!input) { console.error('用法: node save-export.js <导出的.json> [--state <state.js路径>]'); process.exit(1); }
const raw = JSON.parse(fs.readFileSync(input, 'utf8'));

// 完整性校验（全量 state：必须含 profile 与 books 数组；空库也允许回填）
if (!raw.profile || !Array.isArray(raw.books)) {
  console.error('校验失败: 不是完整的工作台导出数据（缺 profile 或 books）');
  process.exit(1);
}
if (!fs.existsSync(path.dirname(STATE))) fs.mkdirSync(path.dirname(STATE), { recursive: true });

// 备份旧文件（防回填错误数据无法回退）
if (fs.existsSync(STATE)) {
  fs.copyFileSync(STATE, STATE + '.bak-' + new Date().toISOString().replace(/[:T]/g, '-').slice(0, 16));
}

const content = '/* AI 阅读执行系统 · 数据唯一来源 —— 由 save-export.js 从工作台导出 JSON 回填\n'
  + '   回填时间: ' + new Date().toISOString() + '  书籍数: ' + raw.books.length + ' */\n'
  + 'window.READING_DATA = ' + JSON.stringify(raw, null, 2) + ';\n';
const tmp = STATE + '.tmp';
fs.writeFileSync(tmp, content, 'utf8');
fs.renameSync(tmp, STATE);
console.log('已回填:', STATE, '| 书籍数:', raw.books.length, '| 版本:', raw.version || '(无版本字段)');
