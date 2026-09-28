#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
幂等推送技能包到 GitHub（走 REST API，不依赖 git remote）
本机代理只通 api.github.com，不通 github.com，所以不走 git push。

用法: python push-gh.py            # 干跑（只看会改什么）
      python push-gh.py --apply    # 真正提交

流程: 本地文件 → blobs → tree → commit → 更新 main ref
坑位备忘:
  * 必须先把 base_tree 写进 JSON body；别用 -f base_tree= 与 --input 同用（body 被忽略）
  * tree 删除条目必须带 mode/type/sha:null，否则 422 invalid tree.mode
  * /tmp 是 Git Bash 的虚拟路径，Python 读不到 → 用仓库内固定临时目录
"""
import base64
import json
import os
import subprocess
import sys
import urllib.request

REPO = 'jotn0206/ai-reading-system'
BRANCH = 'main'
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ai-reading-system')
TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.push-tmp')
API = 'https://api.github.com'
SKIP_SUFFIX = ('.tmp', '.log')
# 不参与同步的本地目录（构建产物 / 工具缓存）
SKIP_DIRS = {'.git', '.push-tmp', 'dist', '__pycache__', 'node_modules'}


def gh(method, path, body=None):
    url = f'{API}/repos/{REPO}/{path}'
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', 'Bearer ' + (os.environ.get('GH_TOKEN') or subprocess.run(
        ['gh', 'auth', 'token'], capture_output=True, text=True).stdout.strip()))
    req.add_header('Accept', 'application/vnd.github+json')
    req.add_header('Content-Type', 'application/json')
    req.add_header('User-Agent', 'skill-push')
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f'❌ {method} {path} → HTTP {e.code}')
        print(e.read().decode()[:600])
        raise


def main():
    apply_ = '--apply' in sys.argv
    os.makedirs(TMP, exist_ok=True)

    print('📖 读取远端 tree ...')
    remote = gh('GET', f'git/trees/{BRANCH}?recursive=1')
    remote_files = {i['path']: i['sha'] for i in remote['tree'] if i['type'] == 'blob'}

    # 本地期望存在于远端的文件：仓库根文件（README/build.py/...，不带前缀）
    # + 技能包平铺文件（ai-reading-system/xxx，带前缀）
    repo_root = os.path.dirname(os.path.abspath(__file__))
    local = {}
    for f in sorted(os.listdir(repo_root)):
        full = os.path.join(repo_root, f)
        if os.path.isdir(full):
            if f in SKIP_DIRS:
                continue
            if f == 'ai-reading-system':        # 技能包单独特地处理
                continue
            if any(os.path.join(full, d) for d in SKIP_DIRS if os.path.isdir(os.path.join(full, d))):
                continue
        elif f in ('.git', '.github') or f.endswith(SKIP_SUFFIX):
            continue
        if os.path.isfile(full):
            local[f] = full
    for root, _dirs, files in os.walk(SRC):
        for f in files:
            if f.endswith(SKIP_SUFFIX):
                continue
            full = os.path.join(root, f)
            rel = 'ai-reading-system/' + os.path.relpath(full, SRC).replace('\\', '/')
            local[rel] = full

    added, modified, deleted, unchanged = [], [], [], []
    for rel, full in sorted(local.items()):
        blob = base64.b64encode(open(full, 'rb').read()).decode()
        sha = gh('POST', 'git/blobs', {'content': blob, 'encoding': 'base64'})['sha']
        if rel not in remote_files:
            added.append((rel, sha))
        elif remote_files[rel] != sha:
            modified.append((rel, sha))
        else:
            unchanged.append(rel)

    # 远端有、本地没有的 → 视为删除（包内文件只增不删时为空）
    keep = set(local)
    to_delete = [{'path': p, 'mode': '100644', 'type': 'blob', 'sha': None}
                 for p in sorted(remote_files) if p not in keep]

    print(f'\n📊 变更概览: 新增 {len(added)} / 修改 {len(modified)} / 删除 {len(to_delete)} / 不变 {len(unchanged)}')
    for p, _ in added:
        print('   ➕ ' + p)
    for p, _ in modified:
        print('   ✏️  ' + p)
    for d in to_delete:
        print('   🗑️  ' + d['path'])

    if not (added or modified or to_delete):
        print('\n✅ 远端已是最新，无需推送')
        return

    if not apply_:
        print('\n🔍 干跑结束（--apply 才真正提交）')
        return

    newblobs = [{'path': p, 'mode': '100644', 'type': 'blob', 'sha': sha} for p, sha in added + modified]
    tree = gh('POST', 'git/trees', {'base_tree': remote['sha'], 'tree': newblobs + to_delete})
    commit = gh('POST', 'git/commits', {
        'message': 'chore(skill): v1.1.0 同步在线工作台发布链路与口令门修复\n\n'
                   '- index.html 同步源码（口令门进源码 + 事件绑进 DOMContentLoaded）\n'
                   '- 新增 publish-online.js（从源码生成发布包 + 版权红线自检）\n'
                   '- 新增 test-gate.py（口令门真实浏览器 7 项回归）\n'
                   '- 新增 wf4-online-workbench.md\n'
                   '- 口令改占位符 AIREAD2026；build.py 加占位符/盘符/版权三道闸',
        'tree': tree['sha'],
        'parents': [remote['sha']],
    })
    gh('PATCH', f'git/refs/heads/{BRANCH}', {'sha': commit['sha'], 'force': False})
    print('\n✅ 已推送: ' + commit['html_url'])
    import shutil
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == '__main__':
    main()
