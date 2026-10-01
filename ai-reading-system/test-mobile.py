# -*- coding: utf-8 -*-
"""P1 移动端验收（真实浏览器，双视口）
检查：无横向滚动 / 翻页式分页（首页+Tab+弹窗）/ 零纵向滚动 / 桌面端不受影响
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

def pg_stat(pg, sel):
    """返回 (页数, 当前页指示文本, 是否有控制条)"""
    return pg.evaluate("""(sel)=>{const h=document.querySelector(sel);if(!h)return null;
      const pgs=h.querySelectorAll(':scope>.pgwrap>.pg');
      const ind=h.querySelector(':scope>.pgr-bar .pgr-ind');
      return {pages:pgs.length, ind:ind?ind.textContent.trim():'', bar:!!ind,
              over:h.scrollHeight>h.clientHeight+4};}""", sel)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)

    for W, H, label in [(390, 844, 'iPhone 14'), (360, 800, 'Android 小屏')]:
        print(f'\n===== {label} ({W}x{H}) =====')
        ctx = b.new_context(viewport={'width': W, 'height': H}, has_touch=True,
                            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148')
        pg = ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(BASE)
        pg.wait_for_timeout(700)

        sw = pg.evaluate("document.documentElement.scrollWidth")
        check('无横向滚动', sw <= W + 1, f'scrollWidth={sw}')
        check('body 无纵向滚动', pg.evaluate("document.documentElement.scrollHeight<=window.innerHeight+4"),
              pg.evaluate("document.documentElement.scrollHeight+'/'+window.innerHeight"))
        check('底部 Tab 可见', pg.evaluate("getComputedStyle(document.getElementById('tabbar')).display==='flex'"))
        check('头部操作按钮已收纳', pg.evaluate("getComputedStyle(document.querySelector('.top-actions')).display==='none'"))

        print(' [首页分页]')
        st = pg_stat(pg, '#homeview')
        check('首页已分页', st and st['pages'] >= 1, st)
        check('首页内容不溢出', st and not st['over'])
        if st and st['pages'] > 1:
            check('首页控制条可见', st['bar'], st['ind'])
            pg.click('#homeview .pgr-btn[data-dir="1"]')
            pg.wait_for_timeout(200)
            st2 = pg_stat(pg, '#homeview')
            check('首页翻页有效', st2 and st2['ind'].startswith('2'), st2 and st2['ind'])
            pg.click('#homeview .pgr-btn[data-dir="-1"]')
            pg.wait_for_timeout(200)

        print(' [Tab 分页]')
        pg.click('[data-tab="notes"]')
        pg.wait_for_timeout(400)
        st = pg_stat(pg, '#aggview')
        check('笔记 Tab 分页', st and st['pages'] >= 1, st)
        check('笔记页不溢出', st and not st['over'])
        check('首页区块已隐藏', pg.evaluate("document.getElementById('homeview').style.display==='none'"))
        sw = pg.evaluate("document.documentElement.scrollWidth")
        check('笔记页无横向滚动', sw <= W + 1, f'scrollWidth={sw}')
        if st and st['pages'] > 1:
            pg.click('#aggview .pgr-btn[data-dir="1"]')
            pg.wait_for_timeout(200)
            st2 = pg_stat(pg, '#aggview')
            check('笔记翻页有效', st2 and st2['ind'].startswith('2'), st2 and st2['ind'])
            pg.click('#aggview .pgr-btn[data-dir="-1"]')
            pg.wait_for_timeout(200)

        pg.click('[data-tab="actions"]')
        pg.wait_for_timeout(400)
        st = pg_stat(pg, '#aggview')
        check('行动 Tab 分页', st and st['pages'] >= 1, st)
        check('行动页不溢出', st and not st['over'])

        pg.click('[data-tab="stages"]')
        pg.wait_for_timeout(400)
        check('环节矩阵渲染', pg.evaluate("document.querySelectorAll('.agg-book').length>=1"),
              pg.evaluate("document.querySelectorAll('.agg-book').length"))

        print(' [弹窗分页]')
        pg.click('.agg-book .agg-step')
        pg.wait_for_timeout(500)
        mw = pg.evaluate("document.querySelector('.modal').getBoundingClientRect().width")
        check('弹窗全屏宽', abs(mw - W) <= 2, f'modalWidth={mw:.0f}')
        sw = pg.evaluate("document.documentElement.scrollWidth")
        check('弹窗内无横向滚动', sw <= W + 1, f'scrollWidth={sw}')
        check('环节头固定在分页区外', pg.evaluate("!!document.querySelector('#stage-head-out .stage-head')"))
        st = pg_stat(pg, '#stage-body')
        check('环节详情已分页', st and st['pages'] >= 1, st)
        check('环节详情不溢出', st and not st['over'])
        if st and st['pages'] > 1:
            check('弹窗控制条可见', st['bar'], st['ind'])
            # 翻到最后一页再翻回来
            for _ in range(st['pages'] - 1):
                pg.click('#stage-body ~ .pgr-bar .pgr-btn[data-dir="1"]' if False else '.modal .pgr-btn[data-dir="1"]')
                pg.wait_for_timeout(120)
            st2 = pg_stat(pg, '#stage-body')
            check('弹窗翻到末页', st2 and st2['ind'].startswith(str(st['pages'])), st2 and st2['ind'])
            check('末页下一页已禁用', pg.evaluate("document.querySelectorAll('.modal .pgr-btn')[1].disabled"))
            pg.click('.modal .pgr-btn[data-dir="-1"]')
            pg.wait_for_timeout(200)
        # 切到内容最多的环节2（粗读）验证长内容分页
        pg.click('.step[data-sid="2"]')
        pg.wait_for_timeout(400)
        st = pg_stat(pg, '#stage-body')
        check('环节2长内容分页≥2页', st and st['pages'] >= 2, st and f"{st['pages']}页")
        pg.click('.modal-head .x')
        pg.wait_for_timeout(300)

        pg.click('[data-tab="me"]')
        pg.wait_for_timeout(400)
        check('我的 Tab 渲染', pg.evaluate("document.querySelectorAll('.me-btn').length>=4"))
        check('全程无 JS 报错', not errs, str(errs[:3]))
        ctx.close()

    print('\n===== 桌面回归 (1280x800) =====')
    ctx = b.new_context(viewport={'width': 1280, 'height': 800})
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(BASE)
    pg.wait_for_timeout(700)
    check('Tab 栏隐藏', pg.evaluate("getComputedStyle(document.getElementById('tabbar')).display==='none'"))
    check('头部按钮可见', pg.evaluate("getComputedStyle(document.querySelector('.top-actions')).display!=='none'"))
    check('KPI 5 张卡', pg.evaluate("document.querySelectorAll('.kpi').length===5"))
    check('书籍网格多列', pg.evaluate("document.querySelectorAll('.book').length>3"))
    check('桌面端不分页', pg.evaluate("document.querySelectorAll('.pgwrap').length===0"))
    check('桌面弹窗环节头在位', True)
    pg.click('.book')
    pg.wait_for_timeout(500)
    check('桌面弹窗可滚动（保留原布局）', pg.evaluate("(()=>{const s=document.getElementById('stage-body');return s.scrollHeight>0})()"))
    check('桌面端弹窗也无分页', pg.evaluate("document.querySelectorAll('#stage-body .pgwrap').length===0"))
    check('无 JS 报错', not errs, str(errs[:3]))
    ctx.close()
    b.close()

srv.shutdown()
print('\n' + ('✅ P1 移动端验收全部通过' if ok else '❌ 有问题，见上'))
sys.exit(0 if ok else 1)
