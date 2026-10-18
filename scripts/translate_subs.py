#!/usr/bin/env python3
"""Turn LevelUpRN ASR transcripts into the site's cue format (EN) + Persian (FA).

YouTube ASR returns short overlapping fragments; the player expects
non-overlapping sentence cues. This merges fragments into sentences, then
translates each sentence to Persian via the local LLM router.

Usage: python3 scripts/translate_subs.py <videoId> [...]
Writes: subs/<videoId>.json  ->  [{s,e,t,fa}, ...]
"""
import json, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCR = '/Users/matin/.hermes/profiles/brain-hub/cache/scratch'
KEYFILE = os.path.expanduser('~/.hermes/profiles/brain-hub/.env')

env = dict(os.environ)
for line in open(KEYFILE):
    if '=' in line and not line.startswith('#'):
        k, v = line.strip().split('=', 1)
        env[k] = v.strip().strip('"').strip("'")
KEY = env.get('HERMES_CUSTOM_LOCALHOST_20128_API_KEY', '')

MODELS = ['oc/glm-5.3-flash-free', 'oc/mimo-v2.6-flash-free',
          'oc/deepseek-v4.1-flash-free', 'oc/space-bunny-free']

SYS = ("شما مترجم حرفه‌ای پرستاری هستید. جملات آموزشی پرستاری را به فارسی روان، حرفه‌ای و "
       "دقیق ترجمه کنید؛ همان سبکی که در آزمون‌های پرستاری ایران به کار می‌رود. اصطلاحات "
       "بالینی استاندارد فارسی را به‌کار ببرید و از ترجمهٔ ماشینیِ تحت‌اللفظی پرهیز کنید. "
       "فقط و فقط یک آرایهٔ JSON از رشته‌ها برگردانید؛ طول و ترتیب آرایه دقیقاً مثل ورودی باشد. "
       "هیچ توضیحی ننویسید.")


def merge(segments, max_chars=110, min_chars=45):
    """Merge overlapping ASR fragments into contiguous, non-overlapping sentences."""
    cues = []
    buf, start = '', None
    for seg in segments:
        txt = seg['t'].strip()
        if not txt:
            continue
        if start is None:
            start = seg['s']
        buf = (buf + ' ' + txt).strip() if buf else txt
        ends_sentence = bool(re.search(r'[.!?]\s*$', buf))
        long_enough = len(buf) >= max_chars
        if ends_sentence and len(buf) >= min_chars:
            cues.append([start, seg['e'], buf])
            buf, start = '', None
        elif long_enough:
            # cut at the last clause boundary to avoid mid-word splits
            cut = max(buf.rfind(', '), buf.rfind('; '))
            if cut > min_chars:
                head, rest = buf[:cut + 1].strip(), buf[cut + 1:].strip()
                cues.append([start, seg['e'], head])
                buf, start = rest, seg['e']
    if buf:
        cues.append([start, cues[-1][1] if cues else segments[-1]['e'], buf])

    # contiguous, non-overlapping ranges: walk BACKWARD so each cue ends exactly
    # where the next one starts (forward walking can create overlaps when a
    # natural end runs past the next cue's start).
    last_end = max(cues[-1][1], cues[-1][0] + 1.0)
    cues[-1][1] = round(last_end, 2)
    for i in range(len(cues) - 2, -1, -1):
        nxt_s = cues[i + 1][0]
        end = min(cues[i][1], nxt_s)
        cues[i][1] = round(max(end, cues[i][0] + 0.6), 2)
    # forward pass: repair any residual inversion
    for i in range(1, len(cues)):
        if cues[i][0] < cues[i - 1][1]:
            cues[i][0] = round(cues[i - 1][1], 2)
    return [{'s': round(c[0], 2), 'e': c[1], 't': c[2]} for c in cues]


def ask(model, texts):
    payload = {"model": model, "temperature": 0.2,
               "messages": [{"role": "system", "content": SYS},
                            {"role": "user", "content": json.dumps(texts, ensure_ascii=False)}]}
    open('/tmp/_tr_req.json', 'w').write(json.dumps(payload))
    r = subprocess.run(['curl', '-s', '--max-time', '120', '-X', 'POST',
                        'http://localhost:20128/v1/chat/completions',
                        '-H', 'Content-Type: application/json',
                        '-H', 'Authorization: Bearer ' + KEY,
                        '-d', '@/tmp/_tr_req.json'], capture_output=True, text=True, env=env)
    try:
        raw = json.loads(r.stdout)['choices'][0]['message']['content']
    except Exception:
        return None
    s = raw.strip()
    if s.startswith('```'):
        s = s.split('```')[1]
        s = s[s.find('['):]
    a, b = s.find('['), s.rfind(']')
    if a < 0 or b < 0:
        return None
    try:
        out = json.loads(s[a:b + 1])
    except Exception:
        return None
    return out if isinstance(out, list) and len(out) == len(texts) else None


def build(vid):
    segs = json.load(open(SCR + '/tr_%s.json' % vid, encoding='utf-8'))['segs']
    cues = merge(segs)
    print('%s: %d ASR fragments -> %d cues' % (vid, len(segs), len(cues)))

    texts = [c['t'] for c in cues]
    fa = [None] * len(texts)
    B = 8
    for i in range(0, len(texts), B):
        chunk = texts[i:i + B]
        got = None
        for m in MODELS:
            got = ask(m, chunk)
            if got:
                break
            time.sleep(1)
        if not got:
            got = chunk
            print('   !! batch %d FAILED on all models, kept EN' % i, flush=True)
        for j in range(len(chunk)):
            fa[i + j] = got[j]
        print('   %d/%d' % (min(i + B, len(texts)), len(texts)), flush=True)
        time.sleep(0.3)

    miss = [k for k, v in enumerate(fa) if not any('\u0600' <= c <= '\u06ff' for c in v)]
    if miss:
        print('   !! %d cue(s) still English: %s' % (len(miss), miss[:12]))
    out = [{'s': c['s'], 'e': c['e'], 't': c['t'], 'fa': fa[k]} for k, c in enumerate(cues)]
    os.makedirs(os.path.join(ROOT, 'subs'), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, 'subs', vid + '.json'), 'w', encoding='utf-8'),
              ensure_ascii=False)
    ov = sum(1 for a, b in zip(out, out[1:]) if b['s'] < a['e'])
    print('%s -> subs/%s.json (%d cues, %d overlaps)' % (vid, vid, len(out), ov))


if __name__ == '__main__':
    for v in sys.argv[1:]:
        build(v)