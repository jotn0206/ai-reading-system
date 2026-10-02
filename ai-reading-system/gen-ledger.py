# -*- coding: utf-8 -*-
"""从 data/state.js 重新生成「1年50本进度台账.md」（进度台账；输出路径用 LEDGER_OUT 指定，笔记目录用 VAULT_NOTE_DIR 指定）
数字全部由脚本统计，不手抄——手抄必与工作台脱钩。
用法: python gen-ledger.py
"""
import json, os, io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT = os.environ.get('LEDGER_OUT') or (os.path.join(ROOT, '书单-1年50本进度台账.md'))
NOTE_DIR = os.environ.get('VAULT_NOTE_DIR','')
TARGET = 50

STAGE_NAMES = {1: '新书推荐', 2: '粗读', 3: '逐章拆解', 4: '逻辑链', 5: '重点推荐',
               6: '原子笔记', 7: '行动清单', 8: '书评'}
MARK = {'done': '✅', 'doing': '🔄', 'todo': '⬜'}


def load():
    s = open(os.path.join(ROOT, 'data/state.js'), encoding='utf-8').read()
    return json.loads(s[s.index('{'):s.rindex(';')])


def stage_of(b, i):
    return (b.get('stages') or {}).get(str(i), {}) or {}


def has_stage(b, i):
    return str(i) in (b.get('stages') or {})


def mark(st, exists=True):
    if not exists:
        return '·'                                # 环节尚未建立
    return MARK.get(st.get('status'), '⚠️')      # ⚠️ = 环节已建但 status 异常


def has_note(title):
    if not NOTE_DIR:/n        return '—'
    return '✅' if os.path.isdir(os.path.join(NOTE_DIR, title)) else '—'


def esc(t):
    return (t or '').replace('|', '\\|')


def main():
    j = load()
    books = j['books']
    rows = []
    for b in books:
        st = {i: stage_of(b, i) for i in range(1, 9)}
        done = sum(1 for i in range(1, 9) if st[i].get('status') == 'done')
        doing = [i for i in range(1, 9) if st[i].get('status') == 'doing']
        unmark = [i for i in range(1, 9) if has_stage(b, i) and not st[i].get('status')]
        absent = [i for i in range(1, 9) if not has_stage(b, i)]
        d6 = st[6].get('data', {}) or {}
        d7 = st[7].get('data', {}) or {}
        d5 = st[5].get('data', {}) or {}
        d8 = st[8].get('data', {}) or {}
        cards = len(d6.get('cards', []) or [])
        acts = len(d7.get('actions', []) or [])
        done_acts = sum(1 for a in (d7.get('actions') or []) if a.get('done'))
        rec = d5.get('recommended') or []
        key_ch = len(rec)                      # 环节5 产出的重点章节条目数
        key_flag = sum(1 for r in rec if r.get('isKey'))   # 其中被勾为「必读」的
        hit = str(d8.get('hitScore') or '').strip()
        pub_raw = (d8.get('publishStatus') or '').strip()
        pub = pub_raw.split('（')[0].split('(')[0].strip() or '—'   # 去掉长说明，只留状态词
        media = (d8.get('mediaId') or '').strip()
        # 占位假数据识别：示例值 / test / 短横线
        fake = bool(media) and (len(media) < 25 or media.lower().startswith(('media_', 'test', 'demo', 'xxx')))
        rows.append(dict(b=b, done=done, doing=doing, unmark=unmark, absent=absent,
                         cards=cards, acts=acts, done_acts=done_acts,
                         key_ch=key_ch, key_flag=key_flag,
                         hit=hit, pub=pub, media=media, fake_media=fake,
                         note=has_note(b['title'])))

    full = [r for r in rows if r['done'] == 8]
    partial = [r for r in rows if 0 < r['done'] < 8]
    untouched = len(books) - len(full) - len(partial)
    total_cards = sum(r['cards'] for r in rows)
    total_acts = sum(r['acts'] for r in rows)
    total_done_acts = sum(r['done_acts'] for r in rows)
    total_key = sum(r['key_ch'] for r in rows)
    total_keyflag = sum(r['key_flag'] for r in rows)
    scored = [r for r in rows if str(r['hit']).isdigit()]
    published = [r for r in rows if r['pub'] == '已发布']
    fake_media = [r for r in rows if r['fake_media']]
    missing_note = [r for r in rows if r['note'] == '—']

    L = []
    A = L.append
    A('---')
    A('title: 书单-1年50本进度台账')
    A('type: ledger')
    A('tags: ["读书", "台账"]')
    A('date: %s' % j.get('generated', '2026-10-02'))
    A('---')
    A('# 📋 1年50本 阅读进度台账')
    A('')
    A('> **本文件由 `reading-system/tools/gen-ledger.py` 从工作台 `data/state.js` 自动生成，别手改。**')
    A('> 手改会在下次同步时被覆盖；要改数据请改工作台，再重跑脚本。')
    A('> 在线工作台：https://ai-reading-system.app.workbuddy.host/ （数据口径以此为准）')
    A('')
    A('## 一、总览')
    A('')
    A('| 指标 | 数值 |')
    A('| --- | --- |')
    A('| 年度目标 | %d 本 |' % TARGET)
    A('| 已入库 | **%d 本**（占目标 %d%%） |' % (len(books), round(len(books) * 100 / TARGET)))
    A('| 八环节全跑通 | **%d 本** |' % len(full))
    A('| 跑了一半 | %d 本 |' % len(partial))
    A('| 原子卡累计 | %d 张 |' % total_cards)
    A('| 行动项累计 | %d 项（已打勾 %d 项） |' % (total_acts, total_done_acts))
    A('| 重点章节累计 | %d 章（其中标记必读 %d 章） |' % (total_key, total_keyflag))
    A('| 爆款评分已过线 | %d 本 |' % len(scored))
    A('| 书评已发布 | %d 本 |' % len(published))
    if fake_media:
        A('| ⚠️ media_id 疑似占位 | %d 本 |' % len(fake_media))
    A('')
    A('### 环节分布（各环节处于什么状态的书数）')
    A('')
    A('| 环节 | ' + ' | '.join('%d %s' % (i, STAGE_NAMES[i]) for i in range(1, 9)) + ' |')
    A('| --- |' + ' --- |' * 8)
    A('| ✅完成 | ' + ' | '.join(
        str(sum(1 for r in rows if stage_of(r['b'], i).get('status') == 'done')) for i in range(1, 9)) + ' |')
    A('| 🔄进行中 | ' + ' | '.join(
        str(sum(1 for r in rows if stage_of(r['b'], i).get('status') == 'doing')) for i in range(1, 9)) + ' |')
    A('| ⬜已建未开始 | ' + ' | '.join(
        str(sum(1 for r in rows if has_stage(r['b'], i) and stage_of(r['b'], i).get('status') in (None, 'todo')))
        for i in range(1, 9)) + ' |')
    A('| · 未建环节 | ' + ' | '.join(
        str(sum(1 for r in rows if i in r['absent'])) for i in range(1, 9)) + ' |')
    A('')
    A('> 图例：✅完成 / 🔄进行中 / ⬜已建未开始 / `·` 该环节在数据里还不存在（书还没推进到那一步）。')
    A('')
    A('## 二、主进度表')
    A('')
    A('| # | 书名 | 作者 | 来源 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 完成度 | 当前卡点 |')
    A('| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |')
    for n, r in enumerate(rows, 1):
        b = r['b']
        st = {i: stage_of(b, i) for i in range(1, 9)}     # 每行必须重算，别复用上一轮
        if r['done'] == 8:
            stuck = '✅ 全流程跑通'
        elif r['doing']:
            stuck = '🔄 环节%d %s' % (r['doing'][0], STAGE_NAMES[r['doing'][0]])
        elif r['unmark']:
            stuck = '⚠️ 环节%d 状态异常' % r['unmark'][0]
        else:
            stuck = '从环节%d %s 开始' % (r['absent'][0], STAGE_NAMES[r['absent'][0]])
        A('| %d | [[%s]] | %s | %s | %s | 完成 %d/8 | %s |' % (
            n, esc(b['title']), esc(b.get('author', '—')), esc(b.get('source', '—')[:10]),
            ' | '.join(mark(st[i], has_stage(b, i)) for i in range(1, 9)), r['done'], stuck))
    A('')
    A('## 三、产出台账')
    A('')
    A('| # | 书名 | 原子卡 | 行动项 | 重点章节 | 爆款分 | 书评状态 | 笔记 |')
    A('| --- | --- | --- | --- | --- | --- | --- | --- |')
    for n, r in enumerate(rows, 1):
        pub = r['pub']
        if r['media']:
            pub += '（media_id 已回填）'
        A('| %d | %s | %d | %d%s | %d | %s | %s | %s |' % (
            n, esc(r['b']['title']), r['cards'],
            r['acts'], '（✅%d）' % r['done_acts'] if r['done_acts'] else '',
            r['key_ch'], r['hit'] or '未评', pub, r['note']))
    A('')
    A('## 四、待续清单（按卡点排序）')
    A('')
    todo = sorted([r for r in rows if r['done'] < 8], key=lambda r: -r['done'])
    if not todo:
        A('全部 books 八环节已跑通。')
    else:
        A('| 优先级 | 书名 | 从哪继续 | 缺什么 |')
        A('| --- | --- | --- | --- |')
        for r in todo:
            if r['doing']:
                nxt = '环节%d %s' % (r['doing'][0], STAGE_NAMES[r['doing'][0]])
            elif r['unmark']:
                nxt = '环节%d %s（状态异常，先回标）' % (r['unmark'][0], STAGE_NAMES[r['unmark'][0]])
            else:
                nxt = '环节%d %s' % (r['absent'][0], STAGE_NAMES[r['absent'][0]])
            miss = ['%d.%s' % (i, STAGE_NAMES[i]) for i in range(1, 9)
                    if stage_of(r['b'], i).get('status') != 'done']
            A('| P%d | %s | %s | %s |' % (
                1 if r['done'] >= 5 else 2, esc(r['b']['title']), nxt,
                '、'.join(miss) if miss else '—'))
    A('')
    A('## 五、发布状态')
    A('')
    for r in rows:
        if r['pub'] == '已发布':
            tag = '（media_id 疑似占位，需核对）' if r['fake_media'] else ('（media_id 已回填）' if r['media'] else '')
            A('- ✅ **%s** — 已发布%s' % (r['b']['title'], tag))
    pend = [r for r in rows if r['pub'] != '已发布']
    if pend:
        A('')
        A('待发布 / 草稿：')
        for r in pend:
            extra = '｜⚠️ 有 media_id 但状态未回标' if (r['media'] and not r['fake_media']) else ''
            A('- %s — %s（爆款分 %s）%s' % (r['b']['title'], r['pub'], r['hit'] or '未评', extra))
    A('')
    A('## 六、数据质量问题（脚本自动检出）')
    A('')
    issues = []
    for r in rows:
        if r['fake_media']:
            issues.append('- ⚠️ **%s**：media_id = `%s` 疑似示例/占位值，若已真发布请回填真实 id，若未发布则清空。'
                          % (r['b']['title'], r['media']))
        if r['media'] and not r['fake_media'] and r['pub'] != '已发布':
            issues.append('- ⚠️ **%s**：已有 media_id 但 publishStatus 仍为「%s」，发布状态没回标。'
                          % (r['b']['title'], r['pub']))
        if r['unmark']:
            issues.append('- ⚠️ **%s**：环节 %s 存在但 status 为空（非合法枚举值），工作台上状态点不亮。'
                          % (r['b']['title'], '、'.join(str(i) for i in r['unmark'])))
        if r['done'] == 8 and not r['hit']:
            issues.append('- ℹ️ **%s**：八环节已跑通但爆款分未评（环节8 若要发布必须补评）。' % r['b']['title'])
        if r['done'] < 8 and r['cards'] == 0 and r['done'] >= 3:
            issues.append('- ℹ️ **%s**：已推进到 %d 环节但原子卡为 0，环节6 尚未真正开工。'
                          % (r['b']['title'], r['done']))
    if not issues:
        A('无。')
    else:
        L.extend(issues)
    A('')
    A('## 七、笔记沉淀缺口')
    A('')
    if missing_note:
        A('以下 %d 本在笔记目录（VAULT_NOTE_DIR 指定）没有目录（跑完你的笔记同步脚本补）：' % len(missing_note))
        for r in missing_note:
            A('- %s（完成 %d/8）' % (r['b']['title'], r['done']))
    else:
        A('全部已沉淀。')
    A('')
    A('---')
    A('')
    A('## 附：口径说明')
    A('')
    A('- **完成度** = 八环节中 status 为 `done` 的数量，满格 8/8。')
    A('- **⚠️ 未标状态** = 该环节在数据里存在但 status 字段为空/异常，通常是环节8 书评写完后忘了回标，需要人工确认。')
    A('- **爆款分** = 环节8 的 `hitScore`，空 = 未评（不许拿初评冒充过线）。')
    A('- **笔记** = 笔记目录（VAULT_NOTE_DIR）下是否有该书目录；为 `—` 表示还没沉淀。')
    A('- 台账只沉淀**已入库**的书；目标 50 本的空位由工作台 ghost 卡占位。')
    A('')

    with io.open(VAULT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))
    print('✅ 台账已生成:', VAULT)
    print('   入库 %d 本 / 全跑通 %d 本 / 卡 %d 本' % (len(books), len(full), len(partial)))
    print('   原子卡 %d · 行动 %d(✅%d) · 重点章 %d · 过线 %d · 已发布 %d'
          % (total_cards, total_acts, total_done_acts, total_key, len(scored), len(published)))


if __name__ == '__main__':
    main()
