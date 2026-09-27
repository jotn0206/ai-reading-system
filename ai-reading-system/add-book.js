#!/usr/bin/env node
/**
 * add-book.js — 向 state.js 添加一本新书（AI 阅读执行系统）
 * 用法: node add-book.js <书名> <作者> [source] [tags 逗号分隔] [emoji] [--state <state.js路径>]
 * --state 缺省为 ./data/state.js（相对当前工作目录）。
 * 写前自动备份 state.js；书名重复则拒绝。
 */
const fs = require('fs');
const path = require('path');

const rawArgs = process.argv.slice(2);
const stateFlagIdx = rawArgs.indexOf('--state');
const STATE = stateFlagIdx >= 0 ? rawArgs.splice(stateFlagIdx, 2)[1] : path.join('data', 'state.js');
const [title, author, source = 'EPUB', tagsStr = '', emoji = '📖'] = rawArgs;

if (!title || !author) {
  console.error('用法: node add-book.js <书名> <作者> [source] [tags] [emoji] [--state <state.js路径>]');
  process.exit(1);
}
if (!fs.existsSync(STATE)) {
  console.error(`✗ 找不到数据文件: ${STATE}\n  请先初始化工作台（把技能包里的 index.html 与 state.js 复制到工作目录），或用 --state 指定路径`);
  process.exit(1);
}

const PALETTE = ['#3B82F6', '#F59E0B', '#10B981', '#8B5CF6', '#EF4444', '#06B6D4', '#EC4899', '#84CC16'];

const raw = fs.readFileSync(STATE, 'utf8');
const state = JSON.parse(raw.replace(/^[\s\S]*?window\.READING_DATA\s*=\s*/, '').replace(/;\s*$/, ''));

if (state.books.some(b => b.title === title)) {
  console.error(`✗ 已存在同名书「${title}」，不重复添加`);
  process.exit(1);
}

const book = {
  id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
  title,
  author,
  coverColor: PALETTE[state.books.length % PALETTE.length],
  coverEmoji: emoji,
  addedDate: new Date().toISOString().slice(0, 10),
  source,
  tags: tagsStr.split(/[,，]/).map(s => s.trim()).filter(Boolean),
  stages: {}
};
state.books.push(book);

fs.copyFileSync(STATE, STATE + '.bak-add-' + new Date().toISOString().replace(/[:T]/g, '-').slice(0, 16));
fs.writeFileSync(STATE, '/* AI 阅读执行系统 · 数据唯一来源 */\nwindow.READING_DATA = ' + JSON.stringify(state, null, 2) + ';\n');
console.log(`✅ 已添加《${title}》（${author}），当前共 ${state.books.length} 本书`);
