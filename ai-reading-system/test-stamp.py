# -*- coding: utf-8 -*-
"""发布版本戳回归测试（2 项）

用法: python test-stamp.py [--site <发布包目录>]

背景：在线工作台数据更新后，老访客浏览器里的 localStorage 缓存不会被刷新
（前端只在 version 变化或演示书缺字段时重播种），于是出现"线上 8 本、访客只看到 7 本"。
修法：publish-online.js 往发布包注入 buildStamp；index.html 检测到戳变化即重播种。

测试内容：
  1) 构造"上一次发布"的旧缓存（当前发布包数据去掉最后一本书 + 去掉 buildStamp）注入 localStorage，
     断言打开页面后渲染出全部书 —— 旧缓存被正确重播种
  2) 刷新后再校验：戳已一致时不重复重播种，访客在线上做的标记得以保留

踩坑固化：
  * Playwright 的 chromium 常常没下载 → executable_path 指本机 Chrome，回退 Edge
  * 用 ctx.add_init_script 注入 localStorage，才能保证在页面脚本执行前就位
"""
import argparse
import functools
import json
import os
import re
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
CHROME = os.environ.get('CHROME_PATH') or r'C:\Program Files\Google\Chrome\Application\chrome.exe'
if not os.path.exists(CHROME):
    CHROME = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

ap = argparse.ArgumentParser()
ap.add_argument('--site', default=os.path.join(ROOT, 'dist-online'))
args = ap.parse_args()
SRC = args.site

STORE_KEY = 'reading-system-v1'

state_text = open(os.path.join(SRC, 'data', 'state.js'), encoding='utf-8').read()
data = json.loads(re.sub(r'^[\s\S]*?window\.READING_DATA\s*=\s*', '', state_text).rstrip().rstrip(';'))
TOTAL = len(data['books'])
STAMP = data.get('buildStamp')
if not STAMP:
    sys.exit('❌ 发布包缺少 buildStamp —— 请先用新版 publish-online.js 重新生成发布包')
print(f'发布包: {TOTAL} 本书 | buildStamp = {STAMP}')

legacy = json.loads(json.dumps(data))
dropped = legacy['books'].pop()['title']
legacy.pop('buildStamp', None)
print(f'模拟旧缓存: {len(legacy["books"])} 本书（缺《{dropped}》）')


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=SRC))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_address[1]}/index.html'

fails = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True)
    ctx = browser.new_context()
    ctx.add_init_script(
        "try{if(!localStorage.getItem(%r))localStorage.setItem(%r,%s)}catch(e){}"
        % (STORE_KEY, STORE_KEY, json.dumps(json.dumps(legacy, ensure_ascii=False)))
    )
    page = ctx.new_page()
    errs = []
    page.on('pageerror', lambda e: errs.append(str(e)))

    def titles():
        return page.eval_on_selector_all('.book:not(.ghost) .cover .t', 'els=>els.map(e=>e.textContent)')

    page.goto(URL, wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(1200)
    got = titles()
    print(f'\n[1] 带旧缓存打开 → 渲染 {len(got)} 本')
    if len(got) == TOTAL and dropped in got:
        print(f'   ✅ 旧缓存被 buildStamp 触发重播种，已包含《{dropped}》')
    else:
        fails.append(f'应渲染 {TOTAL} 本（含《{dropped}》），实际 {len(got)} 本: {got}')

    cached = page.evaluate(
        "()=>{const v=localStorage.getItem('%s');return v?JSON.parse(v).buildStamp:null}" % STORE_KEY)
    print(f'   缓存内 buildStamp = {cached}')
    if cached == STAMP:
        print('   ✅ 重播种后缓存已带上当前版本戳')
    else:
        fails.append(f'缓存 buildStamp 应为 {STAMP}，实际 {cached}')

    page.evaluate("()=>{const s=JSON.parse(localStorage.getItem('reading-system-v1'));s.books[0].__marker='keep';localStorage.setItem('reading-system-v1',JSON.stringify(s))}")
    page.reload(wait_until='networkidle')
    page.wait_for_timeout(1000)
    marker = page.evaluate("()=>{const s=JSON.parse(localStorage.getItem('reading-system-v1'));return s.books[0].__marker||''}")
    got2 = titles()
    print(f'\n[2] 戳一致后刷新 → 渲染 {len(got2)} 本')
    if marker == 'keep':
        print('   ✅ 未重复重播种，访客线上标记被保留')
    else:
        fails.append('戳一致时不应重播种，但访客标记丢失了')

    if errs:
        fails.append(f'页面 JS 报错: {errs}')
    else:
        print('   ✅ 全程无 JS 报错')
    browser.close()

srv.shutdown()
print()
if fails:
    print('❌ 版本戳回归未通过：')
    for f in fails:
        print('   -', f)
    sys.exit(1)
print('✅ 版本戳回归全部通过')
