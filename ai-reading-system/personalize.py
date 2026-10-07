# -*- coding: utf-8 -*-
"""
personalize.py · 阅读画像与个性化引擎（让系统越用越懂你）

从你的真实行为里学习偏好，反哺八个环节的生成：
  环节5（重点推荐）→ 按 topics 权重挑重点章
  环节6（原子笔记）→ 按卡片类型偏好建议配比
  选书          → 按主题缺口 + 未读完优先级给下一本建议

学习信号：
  · 书的完成深度（8 环节跑完 = 强信号）× 书 tags → 主题权重
  · 原子卡「我的思考」里反复出现的主题 → 加权（你在意什么，看得见）
  · 笔记/洞察的 tags 与密度
  · 行动执行率 / 复习及时率 → 留存健康度
  · 近 90 天完成速度 → 阅读节奏与 50 本/年目标的差距

用法：
  python personalize.py --data <dir>                 # 生成画像 + 报告
  python personalize.py --data <dir> --apply         # 把学到的主题并回 profile.interests（影响环节5/6/8）
  python personalize.py --data <dir> --json          # 输出 JSON
产物：<data>/data/profile-learned.json
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_reading as L  # noqa: E402

RED = [6, 7, 8]  # 最易流失环节


def learn(data, data_dir):
    today = L.today()
    profile = data.get("profile") or {}
    books = data.get("books", [])

    # ---- 主题权重
    topics = Counter()
    book_topics = {}
    for b in books:
        depth = sum(1 for i in range(1, 9) if L.stage_done(b, i)) / 8.0
        w = 1.0 if depth >= 1 else (0.6 if depth > 0 else 0.25)
        for t in b.get("tags") or []:
            topics[t] += w
        book_topics[b.get("title", "")] = set(b.get("tags") or [])
    # 原子卡「我的思考」里出现的主题词
    interests = [x for x in (profile.get("interests") or []) if x]
    cards_all = []
    for b in books:
        for c in L.stage_data(b, 6).get("cards") or []:
            cards_all.append((b.get("title", ""), c))
    thought_text = "\n".join(str(c.get("myThought") or "") for _, c in cards_all)
    for t in interests:
        n = thought_text.count(t)
        if n:
            topics[t] += n * 0.5
    for n in L.read_notes(data_dir):
        for t in (n.get("tags") or []):
            topics[t] += 1.2

    # ---- 卡片类型偏好
    by_type = Counter(c.get("type") or "概念卡" for _, c in cards_all)

    # ---- 行为健康度
    acts = [a for b in books for a in L.stage_data(b, 7).get("actions") or []]
    act_rate = (sum(1 for a in acts if a.get("done")) / len(acts)) if acts else 0
    rv_total = overdue = 0
    for _, c in cards_all:
        rv = c.get("review") or {}
        if rv.get("next"):
            rv_total += 1
            if str(rv["next"]) < today and int(rv.get("box") or 0) == 0:
                overdue += 1
    review_health = 1 - (overdue / rv_total) if rv_total else 1.0
    notes = L.read_notes(data_dir)
    funnel = {sid: sum(1 for b in books if L.stage_done(b, sid)) for sid in range(1, 9)}
    leak = sorted(RED, key=lambda s: funnel.get(s, 0))[0] if books else 7

    # ---- 节奏
    recent = 0
    for b in books:
        st8 = L.stage_obj(b, 8).get("doneAt") or ""
        if st8 and L.days_between(st8, today) is not None and -90 <= L.days_between(st8, today) <= 90:
            recent += 1
    pace_year = recent / 90.0 * 365
    weeks_left_books = max(0, 50 - sum(1 for b in books if sum(1 for i in range(1, 9) if L.stage_done(b, i)) == 8))
    per_month_needed = weeks_left_books / 12.0

    # ---- 推荐：未读完优先级
    tops = [t for t, _ in topics.most_common(12)]
    unfinished = []
    for b in books:
        done = sum(1 for i in range(1, 9) if L.stage_done(b, i))
        if done < 8:
            match = sum(1 for t in (b.get("tags") or []) if t in tops)
            unfinished.append({"title": b.get("title", ""), "done": done, "match": match,
                               "why": "主题契合（%s）+ 已完成 %d/8" % (
                                   "、".join(t for t in (b.get("tags") or []) if t in tops[:6]) or "一般", done)})
    unfinished.sort(key=lambda x: (-x["match"], -x["done"]))

    # ---- 重点定制：未完书里与主题词匹配的章
    focus = {}
    for b in books:
        done = sum(1 for i in range(1, 9) if L.stage_done(b, i))
        if done >= 8:
            continue
        chs = (L.stage_data(b, 3).get("chapters")
               or L.stage_data(b, 1).get("chapters") or [])
        scored = []
        for c in chs:
            title = str(c.get("title") or "")
            hit = [t for t in tops if t and t in title]
            if hit:
                scored.append({"chapter": title, "hit": hit})
        if scored:
            focus[b.get("title", "")] = scored[:5]

    # ---- 主题缺口（书架没覆盖的兴趣词）
    covered = set(topics.keys())
    gaps = [t for t in interests if t not in covered]

    result = {
        "built": L.now_iso(),
        "topics": dict(topics.most_common(30)),
        "topTopics": tops[:8],
        "cardTypePref": dict(by_type),
        "cardTypeAdvice": advice_cards(by_type),
        "health": {
            "actionRate": round(act_rate, 3),
            "reviewOverdue": overdue,
            "reviewHealth": round(review_health, 3),
            "insightPerBook": round(len(notes) / max(1, len(books)), 2),
            "leakStage": leak,
            "leakStageName": L.STAGE_NAMES[leak],
        },
        "pace": {
            "finishedLast90d": recent,
            "extrapolatedYear": round(pace_year, 1),
            "target": 50,
            "remaining": weeks_left_books,
            "perMonthNeeded": round(per_month_needed, 1),
        },
        "nextUp": unfinished[:5],
        "focusChapters": focus,
        "topicGaps": gaps,
    }
    return result, profile


def advice_cards(by_type):
    tot = sum(by_type.values()) or 1
    act = by_type.get("行动卡", 0) / tot
    if act < 0.2:
        return "行动卡占比偏低（%d%%）：环节 6 每次多沉淀 1-2 张「马上能做」的行动卡，别只存概念" % round(act * 100)
    if act > 0.5:
        return "行动卡偏多（%d%%）：概念提炼不足，长期会缺理论骨架；环节 6 补概念卡" % round(act * 100)
    return "卡片类型配比健康（行动卡 %d%%），保持" % round(act * 100)


def report(r, profile):
    h, p = r["health"], r["pace"]
    print("=" * 62)
    print("阅读画像 · %s" % r["built"])
    print("=" * 62)
    print("你在意什么（主题权重 TOP8）：")
    print("  " + "  ".join("%s %.1f" % (t, r["topics"][t]) for t in r["topTopics"]))
    print("卡片类型： %s" % r["cardTypeAdvice"])
    print("留存健康： 行动执行率 %d%% ｜ 复习逾期 %d 张 ｜ 每书洞察 %.1f 条" % (
        h["actionRate"] * 100, h["reviewOverdue"], h["insightPerBook"]))
    print("最易流失环节： 环节%d %s —— 下本书优先保住它" % (h["leakStage"], h["leakStageName"]))
    print("节奏： 近90天读透 %d 本 → 外推全年 %.0f 本（目标 50）" % (
        p["finishedLast90d"], p["extrapolatedYear"]))
    if p["extrapolatedYear"] < p["target"]:
        print("  ⚠ 要达标 50 本/年，还差 %d 本，每月需跑透 %.1f 本（约每周 %.1f 个环节）"
              % (p["remaining"], p["perMonthNeeded"], p["perMonthNeeded"] * 8 / 4.3))
    print("\n接下来读（未读完 × 主题契合度）：")
    for u in r["nextUp"]:
        print("  ▸ %s（%d/8）—— %s" % (u["title"], u["done"], u["why"]))
    if r["focusChapters"]:
        print("\n重点定制（结合你的主题权重，这些书该优先啃的章）：")
        for t, chs in list(r["focusChapters"].items())[:5]:
            print("  《%s》" % t)
            for c in chs:
                print("    · %s ← 命中 %s" % (c["chapter"], "、".join(c["hit"])))
    if r["topicGaps"]:
        print("\n主题缺口（画像里写了兴趣但书架没覆盖）： %s" % "、".join(r["topicGaps"]))


def main():
    ap = argparse.ArgumentParser(description="阅读系统 · 个性化画像")
    ap.add_argument("--data", required=True)
    ap.add_argument("--apply", action="store_true", help="把学到的主题并回 profile.interests")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    data = L.load_state(L.state_file(args.data))
    r, profile = learn(data, args.data)

    out = os.path.join(args.data, "data", "profile-learned.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return
    report(r, profile)
    print("\n画像已写入：%s" % out)

    if args.apply:
        merged = list(profile.get("interests") or [])
        added = [t for t in r["topTopics"] if t not in merged]
        merged += added[:10]
        profile["interests"] = merged
        data["profile"] = profile
        bak = L.backup(L.state_file(args.data))
        with open(L.state_file(args.data), "w", encoding="utf-8") as f:
            f.write(L.dump_state(data))
        print("已并回 profile.interests（+%d：%s）；备份 %s" % (
            len(added), "、".join(added), bak))
        print("⚠ 记得在工作台「导出」同步，且重新发布线上包时 buildStamp 会自动刷新。")


if __name__ == "__main__":
    main()
