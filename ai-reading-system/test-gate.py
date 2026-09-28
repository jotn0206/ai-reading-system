# -*- coding: utf-8 -*-
"""口令门回归测试（本地起 http 服务 + 真实浏览器，7 项）

用法: python test-gate.py [--site <发布包目录>] [--pass <口令>]

原理：本地/127.0.0.1 打开时源码会判为 "不设门"，所以测试副本里把 local 判断
改写成 false，模拟线上（非本地 host）的真实行为。

踩坑固化：
  * Playwright 的 chromium 常常没下载 → 用 executable_path 指本机 Chrome，回退 Edge
  * b.new_page() 每个页都是独立 context、localStorage 不共享
    → 必须 ctx = b.new_context(); pg = ctx.new_page()
  * __gateLock() 会 location.reload()，紧跟的 evaluate 会撞上导航销毁
    → evaluate 后 sleep 700ms 再 wait_for_load_state
"""
import os, re, shutil, sys, tempfile, threading, functools, argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
CHROME = os.environ.get('CHROME_PATH') or r'C:\Program Files\Google\Chrome\Application\chrome.exe'
if not os.path.exists(CHROME):
    CHROME = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

ap = argparse.ArgumentParser()
ap.add_argument('--site', default=os.path.join(ROOT, 'dist-online'))
ap.add_argument('--pass', dest='pass_', default=None)
args = ap.parse_args()

SRC = os.path.abspath(args.site)
if not os.path.isdir(SRC):
    sys.exit('❌ 找不到发布包目录：' + SRC)

html0 = open(os.path.join(SRC, 'index.html'), encoding='utf-8').read()
PASS = args.pass_ or (re.search(r"var\s+PASS\s*=\s*['\"]([^'\"]+)['\"]", html0) or [None, 'AIREAD2026'])[1]
if PASS.startswith('AIREAD2026') and args.pass_ is None:
    print('ℹ️  未在发布包里读到口令，用占位口令 ' + PASS + '（模板默认，部署前记得改）')

PATCH = ("var local=location.protocol==='file:'||location.hostname==='localhost'"
         "||location.hostname==='127.0.0.1';")
assert PATCH in html0, 'local 判断语句未找到，测试前提失效（源码结构变了？）'
tmp = tempfile.mkdtemp(prefix='gate-test-')
testdir = os.path.join(tmp, 'site')
shutil.copytree(SRC, testdir)
p = os.path.join(testdir, 'index.html')
open(p, 'w', encoding='utf-8').write(html0.replace(PATCH, 'var local=false;'))

handler = functools.partial(SimpleHTTPRequestHandler, directory=testdir)
srv = ThreadingHTTPServer(('127.0.0.1', 0), handler)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = 'http://127.0.0.1:%d/' % port

ok = True
def check(name, cond, extra=''):
    global ok
    print(('  ✅ ' if cond else '  ❌ ') + name + (' | ' + extra if extra else ''))
    if not cond: ok = False

def state_of(page):
    return page.evaluate("""() => ({
      locked: document.documentElement.hasAttribute('data-locked'),
      gateVisible: (()=>{const g=document.getElementById('gate');
        return g? getComputedStyle(g).display!=='none' : false;})(),
      headerVisible: (()=>{const h=document.querySelector('header.top');
        return h? getComputedStyle(h).display!=='none' : false;})(),
      err: (document.getElementById('gate-err')||{}).textContent||'',
      ls: localStorage.getItem('reading_gate_v1')
    })""")

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    ctx = b.new_context()            # 自建 context，localStorage 才在页间共享
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(BASE)

    print('\n[1] 首次访问：应上锁')
    s = state_of(pg)
    check('data-locked 存在', s['locked'])
    check('口令框可见', s['gateVisible'])
    check('正文被隐藏', not s['headerVisible'])
    check('无 JS 报错', not errs, str(errs[:2]))

    print('\n[2] 错误口令 → 回车提交')
    pg.fill('#gate-input', 'WRONG-PASS')
    pg.press('#gate-input', 'Enter')
    s = state_of(pg)
    check('提示口令不正确', '口令不正确' in s['err'], s['err'])
    check('仍上锁', s['locked'])

    print('\n[3] 正确口令（小写+前后空格）→ 回车提交')
    pg.fill('#gate-input', '  ' + PASS.lower() + '  ')
    pg.press('#gate-input', 'Enter')
    s = state_of(pg)
    check('已解锁', not s['locked'])
    check('口令框隐藏', not s['gateVisible'])
    check('正文可见', s['headerVisible'])
    check('localStorage 已记 ok', s['ls'] == 'ok')
    check('锁定条出现', pg.evaluate("!!document.getElementById('lockbar')"))

    print('\n[4] 点「锁定」→ 回到上锁')
    pg.evaluate("try{__gateLock()}catch(e){}")
    pg.wait_for_timeout(700)          # 等 reload 完成，否则 evaluate 撞上导航
    pg.wait_for_load_state('load')
    s = state_of(pg)
    check('重新上锁', s['locked'] and s['gateVisible'])

    print('\n[5] 正确口令 → 点按钮进入')
    pg.fill('#gate-input', PASS)
    pg.click('.gate-box button')
    s = state_of(pg)
    check('已解锁', not s['locked'])
    check('正文可见', s['headerVisible'])

    print('\n[6] 二次访问（localStorage 已 ok）→ 直接进')
    pg2 = ctx.new_page(); pg2.on('pageerror', lambda e: errs.append(str(e)))  # 同 context 才共享 localStorage
    pg2.goto(BASE)
    s = state_of(pg2)
    check('不重复上锁', not s['locked'])
    check('正文可见', s['headerVisible'])

    print('\n[7] 忘记口令兜底：地址栏带 #口令')
    pg3 = ctx.new_page()
    pg3.goto(BASE + '#' + PASS)
    s = state_of(pg3)
    check('带 hash 直接打开', not s['locked'] and s['headerVisible'])

    check('全程无 JS 报错', not errs, str(errs[:3]))
    b.close()

srv.shutdown(); shutil.rmtree(tmp, ignore_errors=True)
print('\n' + ('✅ 口令门 7 项全部通过' if ok else '❌ 有问题，见上'))
sys.exit(0 if ok else 1)
