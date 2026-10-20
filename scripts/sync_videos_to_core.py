#!/usr/bin/env python3
"""Sync the VIDEOS array inside lib/player-core.js with data/videos.json.

The player does NOT fetch videos.json at runtime — the catalogue is embedded
in player-core.js as `const VIDEOS = [...]`. Updating videos.json alone
silently shows the old list. Run this after every videos.json change.

Usage: python3 scripts/sync_videos_to_core.py
"""
import json, os, re, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(ROOT, 'lib', 'player-core.js')
DATA = os.path.join(ROOT, 'data', 'videos.json')

ORDER = ['id', 'dur', 'tr', 'cat', 'cat_en', 'src', 'views', 'publishedAt',
         'createdAt', 'fa', 'en', 'sum', 'sum_en', 'ch', 'ch_en']

START = 'const VIDEOS = [\n'
END = '\n];\n'


def build(videos):
    parts = []
    for v in videos:
        o = {k: v[k] for k in ORDER if k in v and v[k] not in (None, '', [])}
        parts.append(json.dumps(o, ensure_ascii=False))
    return START + ',\n'.join(parts) + END


def main():
    videos = json.load(open(DATA, encoding='utf-8'))
    src = open(CORE, encoding='utf-8').read()
    i = src.find(START)
    if i < 0:
        raise SystemExit('VIDEOS array start not found')
    j = src.find(END, i)
    if j < 0:
        raise SystemExit('VIDEOS array end not found')
    old = src[i:j + len(END)]
    new = build(videos)
    if old == new:
        print('player-core.js VIDEOS already in sync (%d videos)' % len(videos))
        return
    open(CORE, 'w', encoding='utf-8').write(src[:i] + new + src[j + len(END):])
    rc = subprocess.run(['node', '--check', CORE], capture_output=True, text=True)
    n_old = old.count('id:"')
    print('player-core.js VIDEOS synced: %d -> %d videos | node --check rc=%d %s'
          % (n_old, len(videos), rc.returncode, rc.stderr[:200]))


if __name__ == '__main__':
    main()