# -*- coding: utf-8 -*-
"""
tts.py · 高质量语音朗读（把书变成可以听的 mp3）

引擎优先级：
  1) edge-tts（微软神经网络语音，在线，质量最好，默认）——需要能访问微软端点
  2) SAPI（Windows 内置 System.Speech，离线，质量一般）——--engine sapi 或 edge 失败时降级

文本来源（--src）：
  fulltext  全本原文 data/fulltext/<书名>.md 按 '## ' 章节切分（真正的"听书"）
  stage     某一环节/全八环节的产出（与工作台「🔊 朗读」同源，听拆解）
  text      直接给文本文件或字符串

用法：
  python tts.py --data <工作目录> --book "韭菜修行记" --src fulltext --chapters 1-5
  python tts.py --data <dir> --book "思考，快与慢" --src stage --sid 6 --voice zh-CN-XiaoxiaoNeural
  python tts.py --data <dir> --book "金钱心理学" --src fulltext --merge        # 合成整本单文件
  python tts.py --text-file ./稿件.txt --out ./audio --voice zh-CN-YunxiNeural
  python tts.py --list-voices
  python tts.py --check              # 只体检环境

产物（默认 <data>/data/audio/<书名>/）：
  001-xxx.mp3 ...     分块音频（顺序编号，播放器按名排序即可）
  manifest.json       块索引（文本前 80 字 / 字数 / 估算时长 / 参数），用于"边听边看"与续跑
  <书名>-朗读稿.md     全文朗读稿（带块编号，便于校对）
  playlist.m3u       播放列表
  <书名>-整本.mp3     --merge 时产出（需 ffmpeg）

续跑：已存在且参数一致的块会跳过（靠 manifest 里的 hash 比对）。
"""
import argparse
import asyncio
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_reading as L  # noqa: E402

DEFAULT_VOICE = "zh-CN-YunxiNeural"
FALLBACK_VOICES = ["zh-CN-XiaoxiaoNeural", "zh-CN-YunjianNeural", "zh-CN-YunyangNeural"]
_HOME = os.path.expanduser("~")


def _venv(name):
    """受管 venv 里的解释器（不写死用户名，跨机器可用）"""
    return os.path.join(_HOME, ".workbuddy", "binaries", "python", "envs", name, "Scripts", "python.exe")


CANDIDATE_PY = [
    os.environ.get("TTS_PYTHON", ""),
    _venv("default"),
    _venv("py312"),
    os.path.join(_HOME, ".workbuddy", "binaries", "python", "versions", "3.13.12", "python.exe"),
]


# ------------------------------------------------------------ 环境问题：edge_tts 不在当前解释器就换解释器重跑
def ensure_engine():
    try:
        import edge_tts  # noqa: F401
        return True
    except Exception:
        pass
    if os.environ.get("TTS_REEXEC") == "1":
        return False
    for py in CANDIDATE_PY:
        if py and os.path.exists(py):
            env = dict(os.environ)
            env["TTS_REEXEC"] = "1"
            print("[tts] 当前解释器缺 edge-tts，改用 %s 重跑" % py)
            r = subprocess.run([py, os.path.abspath(__file__)] + sys.argv[1:], env=env)
            sys.exit(r.returncode)
    return False


def list_voices():
    import edge_tts
    vs = asyncio.run(edge_tts.list_voices())
    for v in vs:
        if v["Locale"].startswith("zh-"):
            print("%-32s %-6s %s" % (v["ShortName"], v["Gender"], v.get("VoiceTag", {}).get("VoicePersonalities") or ""))
    print("\n（常用：zh-CN-YunxiNeural 男声·稳，zh-CN-XiaoxiaoNeural 女声·柔，zh-CN-YunjianNeural 男声·浑厚解说）")


def check_env():
    ok = False
    try:
        import edge_tts  # noqa: F401
        ok = True
    except Exception:
        pass
    print("edge-tts :", "可用" if ok else "不可用（当前解释器）")
    for py in CANDIDATE_PY:
        if py and os.path.exists(py):
            try:
                r = subprocess.run([py, "-c", "import edge_tts;print(edge_tts.__version__)"],
                                   capture_output=True, text=True, timeout=30)
                print("  %s -> %s" % (py, r.stdout.strip() or "缺"))
            except Exception as e:
                print("  %s -> 检测失败 %s" % (py, e))
    ff = "ffmpeg" if find_ffmpeg() else None
    print("ffmpeg   :", ff or "未找到（--merge 不可用，可 --ffmpeg 指定路径）")
    if ok:
        import edge_tts
        ping = os.path.join(os.environ.get("TEMP", "."), "_tts_ping.mp3")
        try:
            asyncio.run(edge_tts.Communicate("连通性测试。", DEFAULT_VOICE).save(ping))
            print("网络连通 : 正常（微软端点可达）")
        except Exception as e:
            print("网络连通 : 失败 ->", e)
        finally:
            try:
                os.remove(ping)
            except Exception:
                pass
    return ok


def find_ffmpeg(cli=None):
    if cli:
        return cli if os.path.exists(cli) else None
    from shutil import which
    return which("ffmpeg")


# ------------------------------------------------------------ 文本准备
def build_sections(args, data, book):
    """→ [(章名, [段落...]), ...]"""
    if args.src == "text":
        raw = ""
        if args.text_file:
            raw = open(args.text_file, encoding="utf-8", errors="ignore").read()
        elif args.text:
            raw = args.text
        else:
            sys.exit("需要 --text 或 --text-file")
        paras = [x.strip() for x in raw.split("\n") if x.strip()]
        return [("文本", paras)]
    if args.src == "fulltext":
        secs = L.fulltext_sections(args.data, book)
        if not secs:
            sys.exit("找不到全文文件：%s（--src fulltext 需要 data/fulltext/<书名>.md）" % L.fulltext_path(args.data, book))
    else:  # stage
        if args.sid:
            secs = L.readable_sections(book, int(args.sid))
            if not secs:
                sys.exit("环节 %s 暂无可读内容" % args.sid)
        else:
            secs = L.readable_book(book)
            if not secs:
                sys.exit("该书八个环节都还没有内容")
    # 章节筛选（1-based，支持 1-5,8）
    if args.chapters:
        want = set()
        for part in args.chapters.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                want.update(range(int(a), int(b) + 1))
            else:
                want.add(int(part))
        secs = [s for i, s in enumerate(secs, 1) if i in want]
    return secs


def blocks_from_sections(secs, max_chars):
    """→ [(章名, 块序号, 文本)]"""
    out, idx = [], 0
    for title, paras in secs:
        for blk in L.split_blocks(paras, max_chars=max_chars):
            idx += 1
            out.append((title, idx, blk))
    return out


# ------------------------------------------------------------ 合成
async def synth_edge(blocks, out_dir, voice, rate, pitch, volume, conc, manifest):
    import edge_tts
    sem = asyncio.Semaphore(conc)
    done = 0

    async def one(i, title, text, fp):
        nonlocal done
        async with sem:
            for attempt in range(3):
                try:
                    c = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
                    await c.save(fp)
                    done += 1
                    if done % 10 == 0 or done == len(blocks):
                        print("  合成进度 %d/%d" % (done, len(blocks)))
                    return True
                except Exception as e:
                    if attempt == 2:
                        print("  [失败] 第 %d 块: %s" % (i, e))
                        return False
                    await asyncio.sleep(1.5 * (attempt + 1))
        return False

    tasks = []
    for title, i, text in blocks:
        fp = os.path.join(out_dir, "%04d-%s.mp3" % (i, L.slug(title)[:20]))
        if manifest.get("blocks") and i <= len(manifest["blocks"]):
            old = manifest["blocks"][i - 1]
            if old.get("hash") == L.sha1(text) and os.path.exists(os.path.join(out_dir, old.get("file", ""))):
                done += 1
                continue
        tasks.append(one(i, title, text, fp))
    res = await asyncio.gather(*tasks)
    return sum(1 for r in res if r)


def synth_sapi(blocks, out_dir, voice_name, rate):
    """离线降级：Windows SAPI → wav。rate: -10..10"""
    ok = 0
    for title, i, text in blocks:
        fp = os.path.join(out_dir, "%04d-%s.wav" % (i, L.slug(title)[:20]))
        txt_fp = os.path.join(out_dir, "_in.txt")
        with open(txt_fp, "w", encoding="utf-8") as f:
            f.write(text)
        ps = (
            "Add-Type -AssemblyName System.Speech;"
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            "$s.Rate=%d;" % rate
            + ("try{$s.SelectVoice('%s')}catch{}" % voice_name if voice_name else "")
            + "$s.SetOutputToWaveFile('%s');" % fp.replace("\\", "\\\\")
            + "$t=Get-Content -Raw -Encoding UTF8 '%s';" % txt_fp.replace("\\", "\\\\")
            + "$s.Speak($t);$s.Dispose();"
        )
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                           capture_output=True)
        if r.returncode == 0 and os.path.exists(fp):
            ok += 1
        else:
            print("  [失败] 第 %d 块: %s" % (i, (r.stderr or b"").decode("gbk", errors="replace")[:200]))
    try:
        os.remove(os.path.join(out_dir, "_in.txt"))
    except Exception:
        pass
    return ok


def merge_audio(out_dir, files, target, ffmpeg, ext):
    list_fp = os.path.join(out_dir, "_concat.txt")
    with open(list_fp, "w", encoding="utf-8") as f:
        for fn in files:
            f.write("file '%s'\n" % os.path.join(out_dir, fn).replace("\\", "/"))
    cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_fp,
           "-c", "copy", target]
    r = subprocess.run(cmd, capture_output=True)
    try:
        os.remove(list_fp)
    except Exception:
        pass
    if r.returncode != 0:
        print("合并失败：", (r.stderr or b"").decode("utf-8", errors="replace")[:300])
        return None
    return target


# ------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description="阅读系统 · 高质量语音朗读")
    ap.add_argument("--data", help="工作目录（含 data/state.js）")
    ap.add_argument("--book", help="书名")
    ap.add_argument("--src", default="fulltext", choices=["fulltext", "stage", "text"], help="文本来源")
    ap.add_argument("--sid", help="--src stage 时指定环节 1-8；不指定=全八环节")
    ap.add_argument("--chapters", help="只朗读第几章，如 1-5,8（1-based）")
    ap.add_argument("--voice", default=DEFAULT_VOICE, help="语音（--list-voices 查看）")
    ap.add_argument("--rate", default="+8%", help="语速，如 +20% / -10%")
    ap.add_argument("--pitch", default="+0Hz", help="音调")
    ap.add_argument("--volume", default="+0%", help="音量")
    ap.add_argument("--out", help="输出目录，默认 <data>/data/audio/<书名>/")
    ap.add_argument("--max-chars", type=int, default=800, help="单块字数上限（默认 800）")
    ap.add_argument("--limit", type=int, default=0, help="只合成前 N 块（试听用）")
    ap.add_argument("--concurrency", type=int, default=4, help="并发数（默认 4，太高会被限流）")
    ap.add_argument("--merge", action="store_true", help="合并为单个 mp3（需 ffmpeg）")
    ap.add_argument("--ffmpeg", help="ffmpeg 路径")
    ap.add_argument("--engine", default="edge", choices=["edge", "sapi"], help="合成引擎")
    ap.add_argument("--list-voices", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--text")
    ap.add_argument("--text-file")
    args = ap.parse_args()

    if args.list_voices:
        ensure_engine()
        list_voices()
        return
    if args.check:
        ensure_engine()
        check_env()
        return

    if args.engine == "edge" and not ensure_engine():
        print("[tts] edge-tts 不可用，自动降级到 SAPI（离线，质量一般）")
        args.engine = "sapi"

    if not args.data and args.src != "text":
        sys.exit("需要 --data")
    data = L.load_state(L.state_file(args.data)) if args.data else {"books": []}
    book = L.find_book(data, args.book) if args.book else None
    if args.src != "text" and not book:
        sys.exit("找不到这本书：%s" % args.book)
    title = (book or {}).get("title") or "文本"

    out_dir = args.out or os.path.join(args.data or ".", "data", "audio", L.slug(title))
    os.makedirs(out_dir, exist_ok=True)

    secs = build_sections(args, data, book)
    blocks = blocks_from_sections(secs, args.max_chars)
    if args.limit:
        blocks = blocks[:args.limit]
    total_chars = sum(len(t) for _, _, t in blocks)
    print("书目：%s ｜ 来源：%s ｜ 章节 %d ｜ 块 %d ｜ 约 %d 字"
          % (title, args.src, len(secs), len(blocks), total_chars))

    mf_path = os.path.join(out_dir, "manifest.json")
    manifest = {}
    if os.path.exists(mf_path):
        try:
            manifest = json.load(open(mf_path, encoding="utf-8"))
        except Exception:
            manifest = {}
    same = (manifest.get("voice") == args.voice and manifest.get("rate") == args.rate
            and manifest.get("src") == args.src and manifest.get("engine") == args.engine)
    if not same:
        manifest = {}

    if args.engine == "edge":
        n = asyncio.run(synth_edge(blocks, out_dir, args.voice, args.rate, args.pitch,
                                   args.volume, args.concurrency, manifest))
        ext = ".mp3"
    else:
        n = synth_sapi(blocks, out_dir, args.voice if args.voice.startswith("Microsoft") else "", 2)
        ext = ".wav"
    print("合成完成：%d/%d 块" % (n, len(blocks)))

    # manifest + 朗读稿 + 播放列表
    files, blocks_meta = [], []
    for fn in sorted(os.listdir(out_dir)):
        if fn.endswith(ext) and re.match(r"^\d{4}-", fn):
            files.append(fn)
    for title_, i, text in blocks:
        fn = "%04d-%s%s" % (i, L.slug(title_)[:20], ext)
        blocks_meta.append({
            "i": i, "file": fn, "chapter": title_, "chars": len(text),
            "seconds": round(len(text) / 4.6 / (1 + float(args.rate.replace("%", "").replace("+", "")) / 100.0), 1),
            "hash": L.sha1(text), "text": text[:80],
        })
    mf = {
        "book": title, "src": args.src, "sid": args.sid, "engine": args.engine,
        "voice": args.voice, "rate": args.rate, "pitch": args.pitch, "volume": args.volume,
        "built": L.now_iso(), "chars": total_chars,
        "est_minutes": round(sum(b["seconds"] for b in blocks_meta) / 60.0, 1),
        "blocks": blocks_meta,
    }
    with open(mf_path, "w", encoding="utf-8") as f:
        json.dump(mf, f, ensure_ascii=False, indent=1)

    script_md = ["# %s · 朗读稿\n", "> 语音：%s ｜ 语速：%s ｜ 引擎：%s ｜ 共 %d 块，约 %.1f 分钟\n"
                 % (args.voice, args.rate, args.engine, len(blocks), mf["est_minutes"])]
    cur = None
    for b in blocks_meta:
        if b["chapter"] != cur:
            cur = b["chapter"]
            script_md.append("\n## %s\n" % cur)
        script_md.append("**[%d]** %s\n" % (b["i"], b["text"] + ("…" if len(b["text"]) >= 80 else "")))
    with open(os.path.join(out_dir, "%s-朗读稿.md" % L.slug(title)), "w", encoding="utf-8") as f:
        f.write("\n".join(script_md))

    with open(os.path.join(out_dir, "playlist.m3u"), "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for fn in files:
            f.write("#EXTINF:-1,%s\n%s\n" % (fn[:-4], fn))

    print("产物目录：%s" % out_dir)
    print("  manifest.json（%d 块，约 %.1f 分钟）" % (len(blocks_meta), mf["est_minutes"]))
    print("  %s-朗读稿.md（边听边看 / 校对用）" % L.slug(title))
    print("  playlist.m3u")

    if args.merge:
        ff = find_ffmpeg(args.ffmpeg)
        if not ff:
            print("未找到 ffmpeg，跳过合并（可用 --ffmpeg 指定路径）")
        else:
            target = os.path.join(out_dir, "%s-整本%s" % (L.slug(title), ext))
            got = merge_audio(out_dir, files, target, ff, ext)
            if got:
                print("  已合并：%s（%.1f MB）" % (got, os.path.getsize(got) / 1024 / 1024))


if __name__ == "__main__":
    main()
