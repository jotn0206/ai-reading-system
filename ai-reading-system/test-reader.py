# -*- coding: utf-8 -*-
"""P2 阅读体验改造验收（真实浏览器，双端）
覆盖：朗读引擎（分段/状态/跳段/语速/高亮）/ 阅读视图（渲染/进度/字号/位置记忆）/
      环节8流程卡 / 吸底操作栏 / 阅读进度条
用法: python tools/test-reader.py
"""
import os, sys, threading, functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

# 用桩替代 speechSynthesis：headless Chrome 无声卡，speak 不会真发声也不会触发 onend
TTS_STUB = """
if(!window.__ttsStubbed){window.__ttsStubbed=true;
window.__spoken=[];
speechSynthesis.speak=function(u){window.__spoken.push(u.text);window.__utter=u;
  setTimeout(()=>{if(u.onstart)u.onstart();},10);};
speechSynthesis.cancel=function(){};
speechSynthesis.pause=function(){};
speechSynthesis.resume=function(){};
speechSynthesis.getVoices=function(){return[];};
Object.defineProperty(speechSynthesis,'paused',{get:()=>false,configurable:true});
Object.defineProperty(speechSynthesis,'speaking',{get:()=>false,configurable:true});
}
window.__spoken.length=0;
"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)

    # ================= 桌面端 =================
    print('\n===== 桌面端 (1280x800) =====')
    ctx = b.new_context(viewport={'width': 1280, 'height': 800})
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(BASE)
    pg.wait_for_timeout(600)

    print(' [环节8 流程卡]')
    pg.click('.book')
    pg.wait_for_timeout(400)
    pg.click('.step[data-sid="8"]')
    pg.wait_for_timeout(400)
    check('流程卡渲染 6 步', pg.evaluate("document.querySelectorAll('.f8-step').length===6"),
          pg.evaluate("document.querySelectorAll('.f8-step').length"))
    check('首步「撰写书评」存在', pg.evaluate("[...document.querySelectorAll('.f8-step .f8-t')].some(x=>x.textContent.includes('撰写书评'))"))
    check('存在进行中/待开始状态', pg.evaluate("document.querySelectorAll('.f8-step.doing,.f8-step:not(.done)').length>=1"))
    # 点击「去AI味」卡片标记完成
    before = pg.evaluate("[...document.querySelectorAll('.f8-step')].filter(x=>x.classList.contains('done')).length")
    pg.click('.f8-step[data-k="humanizer"]')
    pg.wait_for_timeout(300)
    after = pg.evaluate("[...document.querySelectorAll('.f8-step')].filter(x=>x.classList.contains('done')).length")
    check('点卡片标记完成', after == before + 1, f'{before}→{after}')
    check('折叠详情存在（草稿/网关/评分）', pg.evaluate("document.querySelectorAll('.f8-detail').length>=3"),
          pg.evaluate("document.querySelectorAll('.f8-detail').length"))

    print(' [阅读视图]')
    pg.click('.step[data-sid="2"]')
    pg.wait_for_timeout(300)
    check('环节头有「阅读」入口', pg.evaluate("!!document.querySelector('[data-action=\"rd-open\"]')"))
    pg.click('[data-action="rd-open"]')
    pg.wait_for_timeout(400)
    check('阅读视图打开', pg.evaluate("document.getElementById('reader').classList.contains('show')"))
    segs = pg.evaluate("document.querySelectorAll('#rd-inner .tts-seg').length")
    check('阅读视图有分段', segs >= 3, f'{segs} 段')
    check('有小节标题', pg.evaluate("document.querySelectorAll('#rd-inner .rs-t').length>=1"))
    check('吸底操作栏存在', pg.evaluate("!!document.querySelector('.rd-foot')"))
    # 朗读条应已载入
    check('朗读条已显示', pg.evaluate("document.getElementById('tts-bar').classList.contains('show')"))

    print(' [朗读引擎]')
    pg.evaluate(TTS_STUB)
    n_segs = pg.evaluate("TTS.segs.length")
    check('TTS 分段就绪', n_segs >= 3, f'{n_segs} 段')
    pg.click('#rd-playbtn')
    pg.wait_for_timeout(200)
    check('播放后开始朗读', pg.evaluate("window.__spoken.length>=1"), pg.evaluate("window.__spoken.length"))
    check('首段高亮同步', pg.evaluate("!!document.querySelector('#rd-inner .tts-cur')"))
    check('播放中状态文案', pg.evaluate("document.getElementById('tts-info').textContent.includes('朗读中')"),
          pg.evaluate("document.getElementById('tts-info').textContent"))
    # 跳段
    pg.click('[data-action="tts-next"]')
    pg.wait_for_timeout(150)
    check('下一段跳转', pg.evaluate("TTS.idx===1"), pg.evaluate("TTS.idx"))
    # 语速
    r0 = pg.evaluate("TTS.rate")
    pg.click('[data-action="tts-rate"]')
    pg.wait_for_timeout(100)
    check('语速调节', pg.evaluate("TTS.rate") != r0, f"{r0}→{pg.evaluate('TTS.rate')}")
    # 暂停
    pg.click('#tts-playbtn')
    pg.wait_for_timeout(100)
    check('暂停', pg.evaluate("TTS.playing===false"))
    # 停止
    pg.click('[data-action="tts-stop"]')
    pg.wait_for_timeout(100)
    check('停止后朗读条隐藏', pg.evaluate("!document.getElementById('tts-bar').classList.contains('show')"))
    # 点段落从该处朗读
    pg.evaluate(TTS_STUB)
    pg.evaluate("TTS.load(TTS.segs)")
    pg.click('#rd-inner .tts-seg >> nth=2')
    pg.wait_for_timeout(200)
    check('点段落从该处朗读', pg.evaluate("TTS.idx===2"), pg.evaluate("TTS.idx"))

    print(' [字号与位置记忆]')
    fs0 = pg.evaluate("getComputedStyle(document.getElementById('rd-body')).fontSize")
    pg.click('[data-action="rd-font"][data-d="1"]')
    pg.wait_for_timeout(100)
    fs1 = pg.evaluate("getComputedStyle(document.getElementById('rd-body')).fontSize")
    check('A+ 放大字号', float(fs1[:-2]) > float(fs0[:-2]), f'{fs0}→{fs1}')
    # 滚动后关闭重开恢复位置
    pg.evaluate("document.getElementById('rd-body').scrollTop=300")
    pg.wait_for_timeout(400)  # 等 _saveScroll 防抖
    saved = pg.evaluate("localStorage.getItem('rd_pos_'+Reader.book.id+'_stage_2')")
    check('滚动位置已记忆', saved and float(saved) > 100, saved)
    pg.click('[data-action="rd-close"]')
    pg.wait_for_timeout(200)
    check('阅读视图关闭', pg.evaluate("!document.getElementById('reader').classList.contains('show')"))
    pg.click('[data-action="rd-open"]')
    pg.wait_for_timeout(300)
    restored = pg.evaluate("document.getElementById('rd-body').scrollTop")
    check('重开恢复阅读位置', restored > 100, f'scrollTop={restored}')
    pg.click('[data-action="rd-close"]')
    pg.wait_for_timeout(150)

    print(' [阅读进度条]')
    check('弹窗有进度条', pg.evaluate("!!document.querySelector('#read-prog')"))
    check('全程无 JS 报错', not errs, str(errs[:3]))
    ctx.close()

    # ================= 移动端 =================
    print('\n===== 移动端 (390x844) =====')
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, has_touch=True,
                        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148')
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(BASE)
    pg.wait_for_timeout(700)

    print(' [弹窗吸底操作栏]')
    pg.evaluate("openBook(state.books[0].id)")   # 移动端首页分页，.book 可能不在当前页，直接调函数
    pg.evaluate("currentStage=1;renderModal()")  # 固定到环节1，保证 foot-prev 禁用 / foot-next 可用
    pg.wait_for_timeout(500)
    check('吸底栏显示', pg.evaluate("getComputedStyle(document.getElementById('stage-foot')).display==='flex'"))
    check('首环节「上一环节」禁用', pg.evaluate("document.querySelector('[data-action=\"foot-prev\"]').disabled"))
    # 下一环节
    cur0 = pg.evaluate("currentStage")
    pg.click('[data-action="foot-next"]')
    pg.wait_for_timeout(300)
    check('下一环节', pg.evaluate("currentStage") == cur0 + 1, f'{cur0}→{pg.evaluate("currentStage")}')
    pg.click('[data-action="foot-prev"]')
    pg.wait_for_timeout(300)
    check('上一环节', pg.evaluate("currentStage") == cur0)
    # 标完成（先确保当前环节未完成）
    pg.evaluate("bookStage(getBook(),currentStage).status='todo';save();renderStage()")
    pg.wait_for_timeout(200)
    st0 = pg.evaluate("bookStage(getBook(),currentStage).status")
    pg.click('[data-action="foot-done"]')
    pg.wait_for_timeout(300)
    check('标完成', pg.evaluate("bookStage(getBook(),currentStage).status==='done'"), f'{st0}→done')
    # 🔊 朗读入口
    pg.evaluate(TTS_STUB)
    pg.click('[data-action="tts-open"]')
    pg.wait_for_timeout(300)
    check('吸底栏🔊触发朗读', pg.evaluate("window.__spoken.length>=1"), pg.evaluate("window.__spoken.length"))

    print(' [移动端流程卡 2 列]')
    pg.click('.step[data-sid="8"]')
    pg.wait_for_timeout(300)
    cols = pg.evaluate("getComputedStyle(document.querySelector('.flow8')).gridTemplateColumns.split(' ').length")
    check('流程卡收敛为 2 列', cols == 2, f'{cols} 列')
    check('无横向滚动', pg.evaluate("document.documentElement.scrollWidth<=391"))
    pg.click('.modal-head .x')
    pg.wait_for_timeout(200)
    check('全程无 JS 报错', not errs, str(errs[:3]))
    ctx.close()
    b.close()

srv.shutdown()
print('\n' + ('✅ P2 阅读体验改造验收全部通过' if ok else '❌ 有问题，见上'))
sys.exit(0 if ok else 1)
