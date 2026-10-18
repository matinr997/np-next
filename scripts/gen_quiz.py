#!/usr/bin/env python3
"""Nurse Plus — automated quiz generator.

Pipeline (fully automatic):
  transcript subs/{id}.json + videos.json meta
    -> LLM generates 5 NCLEX-style questions (3 mc + 1 cloze + 1 dnd), bilingual
    -> schema validation (deterministic)
    -> LLM QC pass (each answer must be supported by the transcript)
    -> retry once if QC fails
    -> write quizzes/{id}.json  (served by the site)

Usage:
  python3 scripts/gen_quiz.py                 # all videos missing quizzes
  python3 scripts/gen_quiz.py --id oNEBmBtBvtw
  python3 scripts/gen_quiz.py --force --id X  # regenerate even if present
"""
import json, os, re, sys, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = "oc/mimo-v2.6-flash-free"
FALLBACK_MODELS = ["Opencode", "oc/deepseek-v4.1-flash-free", "oc/glm-5.3-flash-free", "openrouter/z-ai/glm-5.2"]
BASE_URL = "http://localhost:20128/v1/chat/completions"
KEY: str = ""
for line in open(os.path.expanduser("~/.hermes/profiles/brain-hub/.env"), encoding="utf-8"):
    if line.startswith("HERMES_CUSTOM_LOCALHOST_20128_API_KEY="):
        KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
if not KEY:
    sys.exit("router API key not found in .env")

VIDEOS = {v["id"]: v for v in json.load(open(os.path.join(ROOT, "data", "videos.json"), encoding="utf-8"))}
MAX_TRANSCRIPT_CHARS = 45000

GEN_PROMPT = """You are an expert NCLEX-style question writer for nursing/health education.
Write questions strictly from the provided video material.

VIDEO TITLE (FA): {fa}
VIDEO TITLE (EN): {en}
SUMMARY (FA): {sumfa}
SUMMARY (EN): {sumen}
CHAPTERS: {chapters}

TIMESTAMPED TRANSCRIPT (text at second S):
{transcript}

Return EXACTLY this JSON shape and nothing else (no markdown fence, no comments):
{{
  "questions": [
    {{"type":"mc","qf":"...","qe":"...","of":["4 fa options"],"oe":["4 en options"],"c":0,"wf":"why fa","we":"why en","ts":0}},
    {{"type":"mc", "... same ..."}},
    {{"type":"mc", "... same ..."}},
    {{"type":"cloze","qf":"sentence with {{0}} and maybe {{1}}","qe":"same sentence in English","blanks":[{{"of":["3 fa opts"],"oe":["3 en opts"],"c":0}}],"wf":"why fa","we":"why en","ts":0}},
    {{"type":"dnd","qf":"classification task fa","qe":"classification task en","items":[{{"fa":"...","en":"..."}}],"keep":[0,2],"wf":"why fa","we":"why en","ts":0}}
  ]
}}

STRICT RULES:
- EXACTLY 5 questions in this order: mc, mc, mc, cloze, dnd.
- mc: exactly 4 options; exactly ONE correct index `c` (0-3); distractors plausible and clearly wrong.
- cloze: 1 or 2 blanks numbered {{0}} ({{1}}); each blank has exactly 3 options; one correct index per blank; qf/qe must contain {{0}} (and {{1}} if 2 blanks).
- dnd: 5-6 items; `keep` = indices (2 or 3) of the CORRECT items only; f is a classification: "which of these belong to X".
- All text in BOTH Persian (qf/of/wf) and English (qe/oe/we); the Persian must be natural professional Persian, not literal machine translation.
- `ts` = transcript timestamp in SECONDS where the tested fact appears (integer).
- wf/we = 1-2 sentence explanation grounded in the transcript.
- Answer only from the transcript/summary; never invent facts. No "all of the above".
- Output ONLY the JSON object.
"""

QC_PROMPT = """You are a strict nursing exam QC reviewer. Below are a video transcript and 5 draft questions.
For EACH question decide if ALL of these hold:
  1) the correct answer is factually supported by the transcript,
  2) the question is unambiguous (exactly one correct option for mc),
  3) the fa/en texts are consistent (same meaning),
  4) cloze: {{0}}/{{1}} markers match blanks count; dnd: `keep` indices valid (2-3 of the items).
  5) cloze GRAMMAR: each option must fit grammatically when dropped into the marker — if the words directly around {{0}} already contain a verb (e.g. "...valves are {{0}}"), options must be bare adjectives ("closed"), NOT full verbs ("is closed"). Same for Persian: if the sentence has "هستند" after the blank, options must be "بسته" not "بسته هستند".
Return ONLY JSON: {{"pass":[0,1,2,3,4], "fail":[{{"i":0,"reason":"..."}}]}}

TRANSCRIPT (abridged, timestamps kept):
{transcript}

DRAFT QUESTIONS:
{draft}
"""


def chat(messages, timeout=180, max_tokens=6000, temperature=0.4):
    last = None
    models = [MODEL] + FALLBACK_MODELS
    for m in models:
        try:
            b = json.dumps({"model": m, "messages": messages,
                            "max_tokens": max_tokens, "temperature": temperature}).encode()
            req = urllib.request.Request(BASE_URL, data=b,
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read())
            return d["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            last = e
            continue
    raise RuntimeError(f"all models failed: {last}")


def extract_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S).strip()
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < 0:
        raise ValueError("no JSON object in response")
    return json.loads(t[i:j + 1])


def dur_seconds(d):
    p = [int(x) for x in d.split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def build_context(vid):
    v = VIDEOS[vid]
    cues = json.load(open(os.path.join(ROOT, "subs", vid + ".json"), encoding="utf-8"))
    lines = [f"[{int(c['s'])}] {c.get('t','')}" for c in cues if c.get("t")]
    fa_lines = [c.get("fa", "") for c in cues]
    # interleave fa translation lightly: put FA after every EN line would double size;
    # instead give FA as separate sample (keep prompt bounded)
    text = "\n".join(lines)
    fa_text = " ".join(fa_lines)
    if len(text) > MAX_TRANSCRIPT_CHARS:
        step = max(1, len(lines) * len(lines[0] if lines else "") // MAX_TRANSCRIPT_CHARS)
        sampled = lines[::max(2, step)]
        text = "\n".join(sampled)
    if len(fa_text) > 15000:
        step = len(fa_text) // 15000 + 1
        fa_text = fa_text[::step]
    chapters = "; ".join(f"{c[0]} {c[1]}" for c in (v.get("ch") or [])[:30])
    fa = dict(
        fa=v["fa"], en=v["en"], sumfa=v.get("sum", ""), sumen=v.get("sum_en", ""),
        chapters=chapters, transcript=text)
    fa["transcript"] = text + "\n\nPERSIAN (for reference):\n" + fa_text
    return fa, v


def validate(draft, vid):
    v = VIDEOS[vid]
    max_ts = dur_seconds(v["dur"])
    errs = []
    qs = draft.get("questions")
    if not isinstance(qs, list) or len(qs) != 5:
        return ["need exactly 5 questions"]
    types = [q.get("type") for q in qs]
    if types != ["mc", "mc", "mc", "cloze", "dnd"]:
        errs.append(f"wrong type order: {types}")
    for i, q in enumerate(qs):
        tag = f"q{i}"
        for k in ("qf", "qe", "wf", "we", "ts"):
            if not q.get(k) and k != "ts":
                errs.append(f"{tag}: missing {k}")
        try:
            ts = int(q.get("ts", -1))
            if ts < 0 or ts > max_ts + 5:
                errs.append(f"{tag}: ts {ts} outside 0..{max_ts}")
        except Exception:
            errs.append(f"{tag}: bad ts")
        if q.get("type") == "mc":
            of, oe, c = q.get("of"), q.get("oe"), q.get("c")
            if not isinstance(of, list) or len(of) != 4:
                errs.append(f"{tag}: need 4 fa options")
            elif len(set(of)) != 4:
                errs.append(f"{tag}: duplicate fa options")
            if not isinstance(oe, list) or len(oe) != 4:
                errs.append(f"{tag}: need 4 en options")
            if not isinstance(c, int) or c not in (0, 1, 2, 3):
                errs.append(f"{tag}: bad correct index {c}")
        elif q.get("type") == "cloze":
            blanks = q.get("blanks")
            if not isinstance(blanks, list) or not (1 <= len(blanks) <= 2):
                errs.append(f"{tag}: 1-2 blanks required")
            else:
                if "{0}" not in q["qf"]:
                    errs.append(f"{tag}: qf missing {0} marker")
                if len(blanks) == 2 and "{1}" not in q["qf"]:
                    errs.append(f"{tag}: 2nd blank missing {1} marker")
                for bi, b in enumerate(blanks):
                    if not isinstance(b.get("of"), list) or len(b["of"]) != 3:
                        errs.append(f"{tag}.b{bi}: 3 fa options required")
                    if not isinstance(b.get("oe"), list) or len(b["oe"]) != 3:
                        errs.append(f"{tag}.b{bi}: 3 en options required")
                    if not isinstance(b.get("c"), int) or b["c"] not in (0, 1, 2):
                        errs.append(f"{tag}.b{bi}: bad correct index")
        elif q.get("type") == "dnd":
            items, keep = q.get("items"), q.get("keep")
            if not isinstance(items, list) or not (4 <= len(items) <= 6):
                errs.append(f"{tag}: need 4-6 items")
            else:
                for it in items:
                    if not isinstance(it, dict) or not it.get("fa") or not it.get("en"):
                        errs.append(f"{tag}: item missing fa/en")
                if not isinstance(keep, list) or not (2 <= len(keep) <= 3):
                    errs.append(f"{tag}: keep must be 2-3 indices")
                elif any(not isinstance(k, int) or k >= len(items) for k in keep):
                    errs.append(f"{tag}: keep index out of range")
    return errs


def qc(draft, ctx):
    try:
        out = chat([{"role": "user", "content": QC_PROMPT.format(
            transcript=ctx["transcript"][:30000],
            draft=json.dumps(draft, ensure_ascii=False))}], max_tokens=3000, temperature=0.1)
        verdict = extract_json(out)
        return [i for i in verdict.get("pass", []) if isinstance(i, int)], \
               verdict.get("fail", [])
    except Exception as e:  # noqa: BLE001
        # QC unavailable -> do not block pipeline; note it
        return list(range(5)), [{"i": -1, "reason": f"QC error: {e}"}]


def generate(vid, force=False):
    outp = os.path.join(ROOT, "quizzes", vid + ".json")
    if os.path.exists(outp) and not force:
        print(f"[skip] {vid}: quiz exists")
        return True
    ctx, v = build_context(vid)
    print(f"[gen ] {vid}: {v['fa'][:50]} ...")
    best = None
    for attempt in (1, 2):
        raw = chat([{"role": "user", "content": GEN_PROMPT.format(**ctx)}])
        try:
            draft = extract_json(raw)
        except Exception as e:  # noqa: BLE001
            print(f"   attempt {attempt}: JSON parse fail ({e})")
            continue
        # normalize blank markers to {0}/{1} convention (UI parses single braces)
        def _norm(t):
            return re.sub(r"\{\{(\d)\}\}", r"{\1}", t) if isinstance(t, str) else t
        for _q in draft.get("questions", []):
            _q["qf"] = _norm(_q.get("qf")); _q["qe"] = _norm(_q.get("qe"))
        errs = validate(draft, vid)
        if errs:
            print(f"   attempt {attempt}: schema errors: {errs[:4]}")
            best = best or (draft, errs)
            continue
        passed, fails = qc(draft, ctx)
        if fails:
            print(f"   attempt {attempt}: QC flagged {[f.get('i') for f in fails]}")
            best = best or (draft, [str(f) for f in fails])
            continue
        draft["video"] = vid
        draft["gen"] = {"model": MODEL, "n": len(draft["questions"])}
        os.makedirs(os.path.dirname(outp), exist_ok=True)
        json.dump(draft, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"   OK -> {os.path.relpath(outp, ROOT)}")
        return True
    # keep a flagged draft if any, with review flag, so nothing is lost
    if best:
        draft, errs = best
        try:
            draft["video"] = vid
            draft["review"] = True
            draft["review_reasons"] = [str(e) for e in errs][:8]
            os.makedirs(os.path.dirname(outp), exist_ok=True)
            json.dump(draft, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print(f"   SAVED WITH review=true ({len(errs)} issues) -> needs human check")
            return True
        except Exception:  # noqa: BLE001
            pass
    print(f"[fail] {vid}")
    return False


def main():
    args = sys.argv[1:]
    force = "--force" in args
    if "--id" in args:
        ids = [args[args.index("--id") + 1]]
    else:
        ids = [v for v in VIDEOS if not os.path.exists(os.path.join(ROOT, "quizzes", v + ".json"))] or list(VIDEOS)
    ok = sum(generate(i, force) for i in ids)
    print(f"DONE {ok}/{len(ids)}")


if __name__ == "__main__":
    main()
