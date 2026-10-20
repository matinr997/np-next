#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a bilingual NCLEX quiz from an uploaded document (PDF / DOCX / text).

This is the file-upload path of the admin chat: the user drops an exam PDF or
a lecture note and gets a quiz in exactly the shape the player renders.

The question schema is the one lib/player-core.js actually consumes:

  mc    -> of[4] / oe[4] / c (index 0..3)
  cloze -> qf contains "{0}" and blanks[] each with of[3] / oe[3] / c
  dnd   -> items[] are {fa, en} objects and keep[] are INDICES into items
           (the renderer compares sorted zone indices against sorted keep)

Usage:
  python3 scripts/gen_quiz_from_file.py <text-file> <out.json> [videoId]
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROMPT = """You are an expert NCLEX-style question writer for a Persian+English nursing education platform.

Read the SOURCE MATERIAL below and write {n} multiple-choice questions that are strictly answerable from it.

SOURCE MATERIAL:
---
{text}
---

Return ONLY a JSON object:
{"questions":[ ... ]}

Each question is one of:

A) multiple choice
{"type":"mc",
 "qf":"سؤال فارسی",
 "qe":"the English question",
 "of":["گزینهٔ فارسی ۱","۲","۳","۴"],
 "oe":["English option 1","2","3","4"],
 "c":0,
 "wf":"توضیح فارسی چرا این گزینه درست است",
 "we":"English explanation"}

B) cloze (fill the blank)
{"type":"cloze",
 "qf":"جملهٔ فارسی با {0} و جای خالی",
 "qe":"English sentence with {0}",
 "blanks":[{"of":["گزینهٔ فارسی ۱","۲","۳"],"oe":["English 1","2","3"],"c":0}],
 "wf":"...","we":"..."}

C) drag and drop (ordering)
{"type":"dnd",
 "qf":"سؤال فارسی برای چیدن موارد به ترتیب درست",
 "qe":"English question",
 "items":[{"fa":"مورد فارسی ۱","en":"item 1"},{"fa":"مورد فارسی ۲","en":"item 2"},{"fa":"مورد فارسی ۳","en":"item 3"},{"fa":"مورد فارسی ۴","en":"item 4"}],
 "keep":[0,2,1],
 "wf":"...","we":"..."}

Rules:
- Every Persian field must be in Persian script; every English field in English.
- Exactly {n} questions, in the order: 3 mc, then 1 cloze, then 1 dnd.
- The correct answer must be supported by the source material. Never invent a fact.
- 4 distinct options for mc, 3 distinct options for each cloze blank.
- For dnd, "keep" holds 2 or 3 of the INDICES of the items, in the correct order (0-based).
- Do not include "ts". Output JSON only."""


def extract_json(text):
    if not text:
        return None
    t = re.sub(r"^```(?:json)?\s*", "", text.strip())
    t = re.sub(r"\s*```$", "", t)
    try:
        return json.loads(t)
    except Exception:
        pass
    start = t.find("{")
    while start >= 0:
        depth = 0
        for i in range(start, len(t)):
            if t[i] == "{":
                depth += 1
            elif t[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(t[start:i + 1])
                    except Exception:
                        break
        start = t.find("{", start + 1)
    return None


def validate(draft, want=5):
    """Shape check only — there is no video, so 'ts' is not checked."""
    errs = []
    qs = draft.get("questions") if isinstance(draft, dict) else None
    if not isinstance(qs, list) or len(qs) != want:
        return ["need exactly %d questions" % want]
    for i, q in enumerate(qs):
        tag = "q%d" % i
        for k in ("qf", "qe", "wf", "we"):
            if not str(q.get(k) or "").strip():
                errs.append("%s: missing %s" % (tag, k))
        t = q.get("type")
        if t == "mc":
            of, oe, c = q.get("of"), q.get("oe"), q.get("c")
            if not isinstance(of, list) or len(of) != 4:
                errs.append("%s: need 4 fa options" % tag)
            elif len(set(map(str, of))) != 4:
                errs.append("%s: duplicate fa options" % tag)
            if not isinstance(oe, list) or len(oe) != 4:
                errs.append("%s: need 4 en options" % tag)
            if not isinstance(c, int) or c not in (0, 1, 2, 3):
                errs.append("%s: bad correct index" % tag)
        elif t == "cloze":
            blanks = q.get("blanks")
            if not isinstance(blanks, list) or not (1 <= len(blanks) <= 2):
                errs.append("%s: 1-2 blanks required" % tag)
            else:
                if "{0}" not in str(q.get("qf") or ""):
                    errs.append("%s: qf missing {0}" % tag)
                for bi, b in enumerate(blanks):
                    if not isinstance(b.get("of"), list) or len(b["of"]) != 3:
                        errs.append("%s.b%d: 3 fa options required" % (tag, bi))
                    if not isinstance(b.get("oe"), list) or len(b["oe"]) != 3:
                        errs.append("%s.b%d: 3 en options required" % (tag, bi))
                    if not isinstance(b.get("c"), int) or b.get("c") not in (0, 1, 2):
                        errs.append("%s.b%d: bad correct index" % (tag, bi))
        elif t == "dnd":
            items, keep = q.get("items"), q.get("keep")
            if not isinstance(items, list) or not (4 <= len(items) <= 6):
                errs.append("%s: need 4-6 items" % tag)
            else:
                for it in items:
                    if not isinstance(it, dict) or not it.get("fa") or not it.get("en"):
                        errs.append("%s: item must be {fa, en}" % tag)
            if not isinstance(keep, list) or not (2 <= len(keep) <= max(2, len(items or []))):
                errs.append("%s: keep must hold 2..%d indices" % (tag, max(2, len(items or []))))
            elif any(not isinstance(k, int) or k >= len(items or []) for k in keep):
                errs.append("%s: keep index out of range" % tag)
        else:
            errs.append("%s: unknown type %r" % (tag, t))
    return errs


def _fa(s):
    return any("؀" <= ch <= "ۿ" for ch in (s or ""))


def build(text, out_path, llm, vid, want=5):
    """Generate and write a quiz. Returns True on success."""
    text = (text or "").strip()
    if not text:
        return False
    # keep the prompt inside the model's context
    if len(text) > 40000:
        text = text[:40000]
    # .format() would resolve the cloze marker {0} inside the JSON examples.
    prompt = PROMPT.replace("{n}", str(want)).replace("{text}", text)
    draft = None
    for attempt in (1, 2):
        raw, _used = llm.chat_any([{"role": "user", "content": prompt}],
                                  max_tokens=6000, temperature=0.4)
        cand = extract_json(raw)
        if not cand:
            print("   attempt %d: no JSON" % attempt)
            continue
        errs = validate(cand, want)
        if errs:
            print("   attempt %d: %s" % (attempt, errs[:5]))
            # feed the errors back so the next attempt can fix them
            prompt = prompt + "\n\nPrevious attempt failed validation with: %s\nFix exactly these and return the full JSON again." % "; ".join(errs[:8])
            draft = cand
            continue
        draft = cand
        break
    if not draft:
        return False
    errs = validate(draft, want)
    if errs:
        print("   final validation errors: %s" % errs[:8])
        return False
    # a quiz whose Persian is actually English is worse than no quiz
    fa_ok = sum(1 for q in draft["questions"] if _fa(q.get("qf")))
    if fa_ok < len(draft["questions"]):
        print("   only %d/%d questions have Persian text" % (fa_ok, len(draft["questions"])))
        return False
    for q in draft["questions"]:
        q.pop("ts", None)
        q["ts"] = 0
    out = {"video": vid, "gen": "uploaded", "questions": draft["questions"]}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return True


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else None
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    vid = sys.argv[3] if len(sys.argv) > 3 else "uploaded"
    if not src or not dst:
        print(__doc__)
        sys.exit(1)
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from pipeline_worker import LLM, load_site   # noqa: E402
    site = load_site(type("A", (), {"site": "", "token": ""})())
    cfg = site.llm()
    s = cfg.get("settings") or {}
    llm = LLM(s.get("endpoint"), cfg.get("api_key", ""), s.get("model"),
              [m["id"] for m in cfg.get("models", [])][:40])
    txt = open(src, encoding="utf-8", errors="replace").read()
    ok = build(txt, dst, llm, vid)
    print("OK" if ok else "FAILED")
    sys.exit(0 if ok else 1)
