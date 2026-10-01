# -*- coding: utf-8 -*-
"""P0 移动端验收（真实浏览器，双视口）
检查：无横向滚动 / Tab 切换渲染 / 弹窗全屏 / 桌面端不受影响
用法: python tools/test-mobile.py
"""
import os, sys, threading, functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))  # 平铺结构：脚本与工作目录同级
CHROME = os.environ.get('CHROME_PATH') or r'C:\Program Files\Google\Chrome\Application\chrome.exe'
if not os.path.exists(CHROME):
    CHROME = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

handler = functools.partial(SimpleHTTPRequestHandler, directory=ROOT)
srv = ThreadingHTTPServer(('127.0.0.1', 0), handler)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = 'http://127.0.0.1:%d/' % port

ok = True
def check(name, cond, extra=''):
    global ok
    print(('  ✅ ' if cond else '  ❌ ') + name + (' | ' + str(extra) if extra else ''))
    if not cond: ok = False

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)

    for W, H, label in [(390, 844, 'iPhone 14'), (360, 800, 'Android 小屏')]:
        print(f'\n===== {label} ({W}x{H}) =====')
        ctx = b.new_context(viewport={'width': W, 'height': H},
                            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148')
        pg = ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(BASE)
        pg.wait_for_timeout(600)

        sw = pg.evaluate("document.documentElement.scrollWidth")
        check('无横向滚动', sw <= W + 1, f'scrollWidth={sw}')
        check('底部 Tab 可见', pg.evaluate("getComputedStyle(document.getElementById('tabbar')).display==='flex'"))
        check('头部操作按钮已收纳', pg.evaluate("getComputedStyle(document.querySelector('.top-actions')).display==='none'"))

        print(' [Tab 切换]')
        pg.click('[data-tab="notes"]')
        pg.wait_for_timeout(300)
        check('笔记 Tab 渲染', pg.evaluate("document.getElementById('aggview').innerHTML.length>100"))
        check('首页区块已隐藏', pg.evaluate("document.getElementById('grid').style.display==='none'"))
        sw = pg.evaluate("document.documentElement.scrollWidth")
        check('笔记页无横向滚动', sw <= W + 1, f'scrollWidth={sw}')

        pg.click('[data-tab="actions"]')
        pg.wait_for_timeout(300)
        check('行动 Tab 渲染', pg.evaluate("document.getElementById('aggview').innerHTML.length>50"))
        sw = pg.evaluate("document.documentElement.scrollWidth")
        check('行动页无横向滚动', sw <= W + 1, f'scrollWidth={sw}')

        pg.click('[data-tab="stages"]')
        pg.wait_for_timeout(300)
        check('环节矩阵渲染', pg.evaluate("document.querySelectorAll('.agg-book').length>=1"),
              pg.evaluate("document.querySelectorAll('.agg-book').length"))

        # 打开第一本书 → 弹窗应全屏
        pg.click('.agg-book .agg-step')
        pg.wait_for_timeout(400)
        mw = pg.evaluate("document.querySelector('.modal').getBoundingClientRect().width")
        check('弹窗全屏宽', abs(mw - W) <= 2, f'modalWidth={mw:.0f}')
        sw = pg.evaluate("document.documentElement.scrollWidth")
        check('弹窗内无横向滚动', sw <= W + 1, f'scrollWidth={sw}')
        stepper_overflow = pg.evaluate("""(()=>{const s=document.querySelector('.stepper');
          return s.scrollWidth>s.clientWidth? '可横滑(预期)' : '无溢出'})()""")
        print('   环节条:', stepper_overflow)
        pg.click('.modal-head .x')
        pg.wait_for_timeout(300)

        pg.click('[data-tab="me"]')
        pg.wait_for_timeout(300)
        check('我的 Tab 渲染', pg.evaluate("document.querySelectorAll('.me-btn').length>=4"))
        check('全程无 JS 报错', not errs, str(errs[:3]))
        ctx.close()

    print('\n===== 桌面回归 (1280x800) =====')
    ctx = b.new_context(viewport={'width': 1280, 'height': 800})
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(BASE)
    pg.wait_for_timeout(600)
    check('Tab 栏隐藏', pg.evaluate("getComputedStyle(document.getElementById('tabbar')).display==='none'"))
    check('头部按钮可见', pg.evaluate("getComputedStyle(document.querySelector('.top-actions')).display!=='none'"))
    check('KPI 5 张卡', pg.evaluate("document.querySelectorAll('.kpi').length===5"))
    check('书籍网格多列', pg.evaluate("document.querySelectorAll('.book').length>3"))
    check('无 JS 报错', not errs, str(errs[:3]))
    ctx.close()
    b.close()

srv.shutdown()
print('\n' + ('✅ P0 移动端验收全部通过' if ok else '❌ 有问题，见上'))
sys.exit(0 if ok else 1)
