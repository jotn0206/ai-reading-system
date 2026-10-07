# -*- coding: utf-8 -*-
"""
gen-dashboard.py · 阅读可视化看板（一页看清进度、结构与重点）

从 data/state.js + data/notes + data/kb 统计出一份**离线单文件 HTML**（无 CDN、无网络依赖，双击即开）。

看板内容：
  ① KPI 概览：在读书 / 已读透 / 年度目标进度环 / 原子卡 / 笔记洞察 / 行动执行率 / 今日待复习
  ② 年度进度：目标环 + 月度完成柱（TARGET 可改，默认 50 本/年）
  ③ 八环节完成漏斗：找出真正流失价值的环节
  ④ 每本书进度矩阵：8 格 = 8 环节，一眼看出卡在哪
  ⑤ 知识结构网络：概念/标签共现图（力导向，点节点看相关卡片）
  ⑥ 重点分布：标签 TOP、原子卡类型占比、重点章分布
  ⑦ 行动与复习：执行率、逾期、未来 7 天到期

用法：
  python gen-dashboard.py --data <工作目录> [--out <文件>] [--target 50] [--open]
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_reading as L  # noqa: E402

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>阅读看板 · 一年50本书</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#22252b;--sub:#6b7280;--line:#e6e8ec;
--red:#c0392b;--blue:#2f5fd0;--green:#2e9e6b;--amber:#d98a00;--purple:#7a4fd0}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.6 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:24px 18px 60px}
h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--sub);font-size:12px;margin-bottom:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;box-shadow:0 1px 2px rgba(0,0,0,.03)}
.card h2{font-size:15px;margin:0 0 12px;display:flex;align-items:center;gap:6px}
.card h2 small{font-weight:400;color:var(--sub);font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:14px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi .n{font-size:26px;font-weight:700;line-height:1.2}
.kpi .l{font-size:12px;color:var(--sub)}
.bar{height:8px;background:#eef0f3;border-radius:6px;overflow:hidden}
.bar>i{display:block;height:100%;border-radius:6px}
.funnel{display:flex;flex-direction:column;gap:8px}
.fn{display:grid;grid-template-columns:78px 1fr 54px;align-items:center;gap:8px;font-size:12px}
.books{display:flex;flex-direction:column;gap:10px}
.bk{display:grid;grid-template-columns:1fr auto;gap:6px 10px;align-items:center}
.bk .nm{font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mtx{display:flex;gap:3px}
.mtx i{width:14px;height:14px;border-radius:3px;background:#e6e8ec;display:inline-block}
.mtx i.on{background:var(--green)}
.mtx i.half{background:var(--amber)}
.tags{display:flex;flex-wrap:wrap;gap:6px}
.tag{background:#f1f3f7;border:1px solid var(--line);border-radius:20px;padding:2px 10px;font-size:12px}
.tag b{color:var(--red)}
svg{display:block;width:100%;height:auto}
.lg{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--sub);margin-top:8px}
.lg span{display:flex;align-items:center;gap:5px}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block}
table{width:100%;border-collapse:collapse;font-size:12px}
td,th{padding:5px 6px;border-bottom:1px solid var(--line);text-align:left}
th{color:var(--sub);font-weight:600}
.pill{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;background:#eef2ff;color:var(--blue)}
.pill.warn{background:#fff2e0;color:var(--amber)}
.pill.ok{background:#e8f7ef;color:var(--green)}
.empty{color:var(--sub);font-size:12px}
footer{color:var(--sub);font-size:11px;text-align:center;margin-top:24px}
</style></head><body><div class="wrap">
<h1>📊 阅读看板</h1>
<div class="sub" id="sub"></div>
<div class="kpis" id="kpis"></div>
<div class="grid">
  <div class="card"><h2>🎯 年度进度 <small id="yr-sub"></small></h2><div id="year"></div></div>
  <div class="card"><h2>📉 八环节完成漏斗</h2><div class="funnel" id="funnel"></div>
    <div class="lg"><span>红区=最易流失的价值环节（原子笔记/行动/书评）</span></div></div>
  <div class="card"><h2>📚 每本书进度矩阵</h2><div class="books" id="books"></div>
    <div class="lg"><span><i class="dot" style="background:var(--green)"></i>已完成</span>
    <span><i class="dot" style="background:var(--amber)"></i>进行中</span>
    <span><i class="dot" style="background:#e6e8ec"></i>未开始</span></div></div>
  <div class="card"><h2>🕸 知识结构网络 <small>点节点看相关卡</small></h2><div id="graph"></div>
    <div class="empty" id="graph-tip"></div></div>
  <div class="card"><h2>🏷 重点分布（标签 TOP）</h2><div class="tags" id="tags"></div>
    <h2 style="margin-top:16px">🗂 原子卡构成</h2><div id="cards"></div></div>
  <div class="card"><h2>✅ 行动与复习</h2><div id="ar"></div></div>
</div>
<footer>本地离线看板 · 数据源 data/state.js · 重新生成：python gen-dashboard.py --data &lt;工作目录&gt;</footer>
</div>
<script>
const D = __DATA__;
const esc=s=>String(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const pct=(a,b)=>b?Math.round(a/b*100):0;
document.getElementById('sub').textContent=`${D.books.length} 本书 · ${D.cards.total} 张原子卡 · ${D.notes.total} 条笔记洞察 · 建于 ${D.built}`;

/* KPI */
const doneBooks=D.books.filter(b=>b.done===8).length;
const kpi=[
 ['📖',D.books.length,'在读/已入库'],
 ['🏁',doneBooks,'已跑完八环节'],
 ['🎯',D.year.done+'/'+D.year.target,'年度目标'],
 ['🗂',D.cards.total,'原子卡'],
 ['💡',D.notes.total,'笔记与洞察'],
 ['✅',pct(D.actions.done,D.actions.total)+'%','行动执行率'],
 ['🔁',D.review.dueToday,'今日待复习'],
];
document.getElementById('kpis').innerHTML=kpi.map(([i,n,l])=>
 `<div class="kpi"><div class="n">${n}</div><div class="l">${i} ${l}</div></div>`).join('');

/* 年度进度 */
(function(){
 const p=pct(D.year.done,D.year.target),R=52,C=2*Math.PI*R;
 const ms=Object.entries(D.year.months).sort();
 const mx=Math.max(1,...ms.map(m=>m[1]));
 document.getElementById('yr-sub').textContent=`${D.year.done}/${D.year.target} 本 · ${p}%`;
 document.getElementById('year').innerHTML=
 `<svg viewBox="0 0 320 150"><g transform="translate(70,78)">
  <circle r="${R}" fill="none" stroke="#eef0f3" stroke-width="14"/>
  <circle r="${R}" fill="none" stroke="#2e9e6b" stroke-width="14" stroke-linecap="round"
   stroke-dasharray="${C}" stroke-dashoffset="${C*(1-p/100)}" transform="rotate(-90)"/>
  <text y="4" text-anchor="middle" font-size="22" font-weight="700">${D.year.done}</text>
  <text y="22" text-anchor="middle" font-size="11" fill="#6b7280">/ ${D.year.target} 本</text></g>
  ${ms.map(([m,v],i)=>{const x=150+i*(160/Math.max(1,ms.length)),h=v/mx*70;
   return `<rect x="${x}" y="${100-h}" width="${Math.max(8,150/ms.length-6)}" height="${h}" rx="3" fill="#2f5fd0" opacity="${0.45+0.55*v/mx}"/>
   <text x="${x}" y="118" font-size="9" fill="#6b7280">${m.slice(5)}</text>
   <text x="${x}" y="${95-h}" font-size="9" fill="#22252b">${v}</text>`}).join('')}
 </svg>`;
})();

/* 漏斗 */
document.getElementById('funnel').innerHTML=D.funnel.map(f=>{
 const p=pct(f.done,f.total);
 const red=[6,7,8].includes(f.sid);
 return `<div class="fn"><span>${f.sid} ${f.name}</span>
  <span class="bar"><i style="width:${p}%;background:${red?'var(--red)':'var(--blue)'}"></i></span>
  <span style="text-align:right;color:${red?'var(--red)':'var(--sub)'}">${f.done}/${f.total}</span></div>`;}).join('');

/* 书目矩阵 */
document.getElementById('books').innerHTML=D.books.map(b=>{
 const cells=[1,2,3,4,5,6,7,8].map(i=>`<i class="${b.stages[i-1]?'on':(b.done>0?'half':'')}"></i>`).join('');
 const p=pct(b.done,8);
 return `<div class="bk"><div class="nm">${b.emoji||'📖'} ${esc(b.title)}</div>
  <div class="mtx">${cells}</div>
  <div class="bar" style="grid-column:1/3"><i style="width:${p}%;background:${p===100?'var(--green)':'var(--blue)'}"></i></div>
  </div>`;}).join('');

/* 知识网络 */
(function(){
 const g=D.graph;
 if(!g.nodes.length){document.getElementById('graph').innerHTML='<div class="empty">还没有足够的卡片来构图（跑完环节2/6 后再生成）</div>';return;}
 const W=560,H=330,K=60;
 const n=g.nodes.map((x,i)=>({...x,x:W/2+K*Math.cos(i/g.nodes.length*6.283),
   y:H/2+K*Math.sin(i/g.nodes.length*6.283),vx:0,vy:0}));
 const idx={};n.forEach((x,i)=>idx[x.id]=i);
 const e=g.edges.map(x=>({s:idx[x.s],t:idx[x.t],w:x.w})).filter(x=>x.s!=null&&x.t!=null);
 for(let it=0;it<220;it++){
  for(let i=0;i<n.length;i++)for(let j=i+1;j<n.length;j++){
   let dx=n[i].x-n[j].x,dy=n[i].y-n[j].y,d2=dx*dx+dy*dy||1;
   const rep=1400/d2;const d=Math.sqrt(d2);
   n[i].vx+=dx/d*rep;n[i].vy+=dy/d*rep;n[j].vx-=dx/d*rep;n[j].vy-=dy/d*rep;}
  e.forEach(x=>{const a=n[x.s],b=n[x.t];let dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)||1;
   const f=(d-90)*0.008*(1+x.w*0.3);a.vx+=dx/d*f*d;a.vy+=dy/d*f*d;b.vx-=dx/d*f*d;b.vy-=dy/d*f*d;});
  n.forEach(p=>{p.vx+=(W/2-p.x)*0.006;p.vy+=(H/2-p.y)*0.006;
   p.x+=Math.max(-8,Math.min(8,p.vx));p.y+=Math.max(-8,Math.min(8,p.vy));
   p.x=Math.max(60,Math.min(W-60,p.x));p.y=Math.max(24,Math.min(H-24,p.y));p.vx*=.82;p.vy*=.82;});}
 const mx=Math.max(...n.map(x=>x.w));
 document.getElementById('graph').innerHTML=`<svg viewBox="0 0 ${W} ${H}">
  ${e.map(x=>`<line x1="${n[x.s].x}" y1="${n[x.s].y}" x2="${n[x.t].x}" y2="${n[x.t].y}"
    stroke="#c9cfda" stroke-width="${0.6+Math.min(2,x.w*0.4)}"/>`).join('')}
  ${n.map((p,i)=>`<g class="nd" data-i="${i}" style="cursor:pointer">
    <circle cx="${p.x}" cy="${p.y}" r="${5+7*p.w/mx}" fill="${p.color}" opacity=".85"/>
    <text x="${p.x}" y="${p.y+3}" text-anchor="middle" font-size="9" fill="#fff">${p.w}</text>
    <text x="${p.x}" y="${p.y+16+7*p.w/mx}" text-anchor="middle" font-size="10" fill="#22252b">${esc(p.label)}</text></g>`).join('')}
 </svg>`;
 document.querySelectorAll('.nd').forEach(el=>el.onclick=()=>{
  const p=n[+el.dataset.i];
  document.getElementById('graph-tip').innerHTML=`<b>${esc(p.label)}</b>（${p.w}）· 出现在：${esc(p.books.join('、'))}`;});
})();

/* 标签 + 卡片 */
const mxT=Math.max(1,...D.tags.map(t=>t.n));
document.getElementById('tags').innerHTML=D.tags.map(t=>
 `<span class="tag">${esc(t.tag)} <b style="font-size:${10+6*t.n/mxT}px">${t.n}</b></span>`).join('')||'<span class="empty">—</span>';
const ct=D.cards.byType, tot=Math.max(1,D.cards.total);
document.getElementById('cards').innerHTML=Object.entries(ct).map(([k,v])=>{
 const p=pct(v,tot);return `<div class="fn"><span>${k}</span>
  <span class="bar"><i style="width:${p}%;background:${k.includes('行动')?'var(--red)':k.includes('观点')?'var(--purple)':'var(--blue)'}"></i></span>
  <span style="text-align:right;color:var(--sub)">${v}</span></div>`;}).join('')
 +`<div class="lg">${Object.entries(D.cards.byBook).sort((a,b)=>b[1]-a[1]).slice(0,6)
   .map(([b,n])=>`<span>${esc(b)} <b>${n}</b></span>`).join('')}</div>`;

/* 行动与复习 */
const a=D.actions,r=D.review;
document.getElementById('ar').innerHTML=`
<table><tr><th>行动</th><th style="text-align:right">数</th></tr>
<tr><td>总计</td><td style="text-align:right">${a.total}</td></tr>
<tr><td>已完成</td><td style="text-align:right"><span class="pill ok">${a.done}</span></td></tr>
<tr><td>逾期未完成</td><td style="text-align:right"><span class="pill ${a.overdue?'warn':'ok'}">${a.overdue}</span></td></tr>
<tr><td>7 天内到期</td><td style="text-align:right">${a.dueWeek}</td></tr></table>
<h2 style="margin:14px 0 8px">🔁 复习队列（Leitner）</h2>
<table><tr><th>状态</th><th style="text-align:right">卡片</th></tr>
<tr><td>今日到期</td><td style="text-align:right"><span class="pill ${r.dueToday?'warn':'ok'}">${r.dueToday}</span></td></tr>
<tr><td>7 天内</td><td style="text-align:right">${r.dueWeek}</td></tr>
<tr><td>已进 box≥3（记住了）</td><td style="text-align:right">${r.deep}</td></tr></table>
<div class="lg"><span>执行率与复习及时率，比"读了几本"更能说明阅读是否真的产生了改变。</span></div>`;
</script></body></html>
"""


def month_key(s):
    return str(s or "")[:7]


def build_payload(data_dir, target):
    data = L.load_state(L.state_file(data_dir))
    books = data.get("books", [])
    today = L.today()
    # 书
    bks = []
    for b in books:
        done = sum(1 for i in range(1, 9) if L.stage_done(b, i))
        stages = [1 if L.stage_done(b, i) else 0 for i in range(1, 9)]
        fin = ""
        for i in (8, 7, 6, 5, 4, 3, 2, 1):
            st = L.stage_obj(b, i)
            if st.get("doneAt"):
                fin = st["doneAt"]
                break
        bks.append({"title": b.get("title", ""), "done": done, "stages": stages,
                    "emoji": b.get("coverEmoji") or "📖", "finishedAt": fin,
                    "tags": b.get("tags") or []})
    finished = [b for b in bks if b["done"] == 8]
    months = Counter(month_key(b["finishedAt"]) for b in finished if b["finishedAt"])
    if not months:
        months = Counter(month_key(b.get("addedDate")) for b in books)
    # 漏斗
    funnel = []
    for sid in range(1, 9):
        n = sum(1 for b in books if L.stage_done(b, sid))
        funnel.append({"sid": sid, "name": L.STAGE_NAMES[sid], "done": n, "total": len(books)})
    # 原子卡
    cards_all = []
    for b in books:
        for c in L.stage_data(b, 6).get("cards") or []:
            cards_all.append((b.get("title", ""), c))
    by_type = Counter(c.get("type") or "概念卡" for _, c in cards_all)
    by_book = Counter(t for t, _ in cards_all)
    # 行动
    acts = []
    for b in books:
        for a in L.stage_data(b, 7).get("actions") or []:
            acts.append(a)
    act_done = sum(1 for a in acts if a.get("done"))
    overdue = sum(1 for a in acts if not a.get("done") and a.get("due") and str(a["due"]) < today)
    due_week = sum(1 for a in acts if not a.get("done") and a.get("due")
                   and today <= str(a["due"]) <= L.add_days(today, 7))
    # 复习
    due_today = due_wk = deep = 0
    for _, c in cards_all:
        rv = c.get("review") or {}
        nxt = rv.get("next")
        if nxt:
            if str(nxt) <= today:
                due_today += 1
            elif str(nxt) <= L.add_days(today, 7):
                due_wk += 1
        if int(rv.get("box") or 0) >= 3:
            deep += 1
    # 笔记
    notes = L.read_notes(data_dir)
    # 知识网络：以书的标签 + 原子卡概念关键词为节点，共现为边
    tag_books = defaultdict(set)
    for b in bks:
        for t in b["tags"]:
            tag_books[t].add(b["title"])
    concept_books = defaultdict(set)
    card_of = defaultdict(list)
    for t, c in cards_all:
        key = (c.get("concept") or "").strip()
        if not key:
            continue
        key = re.split(r"[（(，,：:。/]|——", key)[0].strip() or key
        if len(key) > 12:
            key = key[:12]
        concept_books[key].add(t)
        card_of[key].append("%s·%s" % (t, c.get("id") or ""))
    nodes_src = []
    for k, v in tag_books.items():
        nodes_src.append((k, len(v), sorted(v), "tag"))
    for k, v in concept_books.items():
        nodes_src.append((k, len(v), sorted(v), "concept"))
    nodes_src.sort(key=lambda x: -x[1])
    nodes_src = nodes_src[:26]
    names = [x[0] for x in nodes_src]
    palette = ["#2f5fd0", "#c0392b", "#2e9e6b", "#7a4fd0", "#d98a00", "#0e8ea6"]
    nodes = [{"id": n, "label": (n if len(n) <= 8 else n[:8] + "…"), "w": w,
              "books": bs, "color": palette[i % len(palette)]}
             for i, (n, w, bs, _k) in enumerate(nodes_src)]
    cooc = Counter()
    for b in bks:
        ts = [t for t in b["tags"] if t in names]
        cs = [k for k, v in concept_books.items() if b["title"] in v and k in names]
        pool = ts + cs
        for i in range(len(pool)):
            for j in range(i + 1, len(pool)):
                if pool[i] != pool[j]:
                    cooc[tuple(sorted((pool[i], pool[j])))] += 1
    edges = [{"s": a, "t": b, "w": w} for (a, b), w in cooc.most_common(90)]
    tags = Counter()
    for b in bks:
        for t in b["tags"]:
            tags[t] += 1
    for n in notes:
        for t in (n.get("tags") or []):
            tags[t] += 0.6

    return {
        "built": L.now_iso(),
        "books": bks,
        "year": {"target": target, "done": len(finished),
                 "months": dict(sorted(months.items()))},
        "funnel": funnel,
        "graph": {"nodes": nodes, "edges": edges},
        "cards": {"total": len(cards_all), "byType": dict(by_type), "byBook": dict(by_book)},
        "actions": {"total": len(acts), "done": act_done, "overdue": overdue, "dueWeek": due_week},
        "review": {"dueToday": due_today, "dueWeek": due_wk, "deep": deep},
        "notes": {"total": len(notes), "byKind": dict(Counter(n.get("kind") for n in notes))},
        "tags": [{"tag": t, "n": round(v, 1)} for t, v in tags.most_common(24)],
    }


def main():
    ap = argparse.ArgumentParser(description="阅读系统 · 可视化看板")
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", help="输出 HTML，默认 <data>/data/kb/dashboard.html")
    ap.add_argument("--target", type=int, default=int(os.environ.get("TARGET", 50)))
    ap.add_argument("--open", action="store_true", help="生成后用默认浏览器打开")
    args = ap.parse_args()
    payload = build_payload(args.data, args.target)
    out = args.out or os.path.join(args.data, "data", "kb", "dashboard.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    html = HTML.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("看板已生成：%s" % out)
    print("  书目 %d ｜ 已跑透 %d ｜ 原子卡 %d ｜ 行动 %d（执行 %d）｜ 今日复习 %d ｜ 笔记 %d"
          % (len(payload["books"]), payload["year"]["done"], payload["cards"]["total"],
             payload["actions"]["total"], payload["actions"]["done"],
             payload["review"]["dueToday"], payload["notes"]["total"]))
    if args.open:
        try:
            os.startfile(out)
        except Exception:
            pass


if __name__ == "__main__":
    main()
