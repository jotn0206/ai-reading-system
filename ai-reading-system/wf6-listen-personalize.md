# WF6 · 语音朗读 + 个性化闭环（听书 · 画像 · 定制）

## 一、语音朗读（tts.py）——把书和拆解变成 mp3

两种"听"的场景：
1. **听原文**（通勤/做家务时"读"完一本书）：`--src fulltext`，按 `## ` 章切分；
2. **听拆解**（复习自己八环节的产出，相当于把笔记再过一遍耳朵）：`--src stage`，与工作台「🔊 朗读」同源。

引擎：**edge-tts 微软神经网络语音**（在线，质量最好）；失败自动降级 **Windows SAPI**（离线，质量一般）。脚本会自动探测：当前解释器缺 edge-tts 时，自动改用受管 venv（`envs/default`）重跑。

```bash
P=<受管Python>

# 体检（解释器 / 网络 / ffmpeg）
$P tts.py --check
# 听某本书第 1-5 章（神经网络男声，语速 +15%）
$P tts.py --data <dir> --book "韭菜修行记" --src fulltext --chapters 1-5 --rate "+15%"
# 听环节6原子卡复习（女声）
$P tts.py --data <dir> --book "金钱心理学" --src stage --sid 6 --voice zh-CN-XiaoxiaoNeural
# 全书合成并合并单文件（需 ffmpeg）
$P tts.py --data <dir> --book "思考，快与慢" --src fulltext --merge
# 试听前 3 块 / 查语音列表 / 朗读任意文本
$P tts.py --data <dir> --book "X" --src fulltext --limit 3
$P tts.py --list-voices
$P tts.py --text-file ./稿子.txt --out ./audio
```

产物（`<dir>/data/audio/<书名>/`）：分块 mp3（`0001-xxx.mp3` 顺序编号）+ `manifest.json`（块索引/估算时长/内容 hash）+ `<书名>-朗读稿.md`（带块编号，边听边看/校对）+ `playlist.m3u` + 可选整本合并 mp3。

**续跑**：manifest 按"语音+语速+来源+引擎"判断参数是否一致，一致的已存在块按内容 hash 跳过——中断重跑不浪费。

参数：`--voice`（默认 zh-CN-YunxiNeural 男声稳；XiaoxiaoNeural 女声柔；YunjianNeural 浑厚解说）、`--rate`、`--pitch`、`--volume`、`--max-chars`（单块字数，默认 800）、`--concurrency`（默认 4）。

**踩坑**：
- 并发别调高（>4 会被微软限流，报错重试 3 次后跳过该块）；
- 大部头（百章网文）先 `--chapters 1-3 --limit 5` 试听再全量；
- 工作台内的即时朗读仍是浏览器 Web Speech API（离线可用），`tts.py` 是"导出成 mp3 长期听"的路线，两者互补；
- 网络不通时自动落 SAPI，音质明显下降——如实告知用户。

## 二、个性化闭环（personalize.py）——越用越懂你

```
行为（完成/复习/执行/笔记/思考）→ 画像 profile-learned.json → 反哺环节 5/6/8 与选书 → 新行为
```

学习信号 → 用途：

| 信号 | 学到什么 | 反哺哪里 |
|---|---|---|
| 书的完成深度 × tags | 主题权重 topics | 环节5 挑重点章、选书排序 |
| 原子卡「我的思考」反复出现的词 | 你真正在意的主题 | 环节6 卡片侧重、环节8 书评切入 |
| 行动卡/概念卡/观点卡占比 | 卡片类型偏好 | 环节6 配比建议 |
| 行动执行率、复习逾期、洞察密度 | 留存健康度 | 提醒哪环节在漏水 |
| 近 90 天读透本数 | 阅读节奏 vs 50 本/年 | 每月应跑透几本 |
| 兴趣词 - 书架覆盖 | 主题缺口 | 下一本选书方向 |

```bash
$P personalize.py --data <dir>            # 生成画像 + 可读报告（不写 state.js）
$P personalize.py --data <dir> --apply    # 把学到的 TOP 主题并回 profile.interests
$P personalize.py --data <dir> --json
```

**`--apply` 的效果链**：`profile.interests` 更新 → 工作台环节 5 的"结合身份画像生成重点"、环节 6 的"结合用户身份"、环节 8 书评的个性化全部跟着变（这三处在 WF2 就强制依赖画像）。产出的 `focusChapters`（按主题权重匹配的优先章）直接作为环节 5 重点推荐的输入。

**执行时机（agent 主动）**：
- 每本书 WF3 收尾后跑一次（报告给用户看，不 apply）；
- 每月底或用户说"最近读什么好"时 `--apply` 一次（apply 会改 state.js：先备份、提醒用户工作台导出同步）；
- 用户的"下一本读什么"问题：先跑 personalize，拿 `nextUp`（未读完 × 主题契合）和 `topicGaps`（缺口主题）回答，再给新书建议。

## 验收清单
- [ ] `tts.py --check` 全绿（edge 可用 / 网络通 / ffmpeg 可选）
- [ ] 试听块（`--limit 3`）人工确认音质与断句正常后再全量合成
- [ ] 朗读稿 md 与 mp3 块编号一致
- [ ] `personalize` 报告数字合理（执行率/逾期与工作台一致）
- [ ] `--apply` 后 profile.interests 无重复词，state.js JSON 校验通过
