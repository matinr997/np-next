#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normalise quizzes to the schema lib/player-core.js ACTUALLY renders.

The renderer is the contract, not the validator in gen_quiz.py:

  mc    of[4] / oe[4] / c                 -> renders fine
  cloze blanks[bi] = {of:[3], oe:[3], c} -> dropdown with 3 options
  dnd   items[i] = {fa, en}              -> chip text
        keep = list of INDICES           -> compared against the zone indices

Some shipped quizzes were written with a flat shape:

  cloze blanks: ["کندتر", "slower"]      -> blanks[bi].of is undefined => EMPTY dropdown
  dnd   items : ["متن فارسی"]            -> it.en is undefined       => BLANK chips
  dnd   keep  : ["متن فارسی"]            -> compared against indices => ALWAYS wrong

Those questions render broken on the live site. This script repairs them with
the LLM (it has to invent distractors for cloze and the English side for dnd),
then re-validates against the renderer's real contract.

Usage:
  python3 scripts/fix_quiz_format.py            # all quizzes
  python3 scripts/fix_quiz_format.py --check     # only report
  python3 scripts/fix_quiz_format.py gYajexY55hM # one file
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUIZ_DIR = os.path.join(ROOT, "quizzes")


# ---------------------------------------------------------------- contract
def check_question(q):
    """Return a list of problems against the renderer's real expectations."""
    errs = []
    t = q.get("type")
    if t == "mc":
        of, oe, c = q.get("of"), q.get("oe"), q.get("c")
        if not isinstance(of, list) or len(of) != 4:
            errs.append("mc: of must be 4 options")
        if not isinstance(oe, list) or len(oe) != 4:
            errs.append("mc: oe must be 4 options")
        if not isinstance(c, int) or c not in (0, 1, 2, 3):
            errs.append("mc: c must be 0..3")
    elif t == "cloze":
        blanks = q.get("blanks")
        if not isinstance(blanks, list) or not blanks:
            errs.append("cloze: blanks missing")
        else:
            for bi, b in enumerate(blanks):
                if not isinstance(b, dict):
                    errs.append("cloze: blank %d is not an object (renderer needs .of/.oe/.c)" % bi)
                    continue
                if not isinstance(b.get("of"), list) or len(b.get("of")) != 3:
                    errs.append("cloze: blank %d needs 3 fa options" % bi)
                if not isinstance(b.get("oe"), list) or len(b.get("oe")) != 3:
                    errs.append("cloze: blank %d needs 3 en options" % bi)
                if not isinstance(b.get("c"), int) or b.get("c") not in (0, 1, 2):
                    errs.append("cloze: blank %d needs c 0..2" % bi)
            if "{0}" not in str(q.get("qf") or ""):
                errs.append("cloze: qf has no {0} marker")
    elif t == "dnd":
        items, keep = q.get("items"), q.get("keep")
        if not isinstance(items, list) or not (4 <= len(items) <= 6):
            errs.append("dnd: need 4-6 items")
        else:
            for i, it in enumerate(items):
                if not isinstance(it, dict):
                    errs.append("dnd: item %d is a string; renderer needs {fa, en}" % i)
                elif not it.get("fa") or not it.get("en"):
                    errs.append("dnd: item %d missing fa/en" % i)
        if not isinstance(keep, list) or not keep:
            errs.append("dnd: keep missing")
        elif any(not isinstance(k, int) for k in keep):
            errs.append("dnd: keep must be INDICES, not strings")
        elif items and any(k >= len(items) for k in keep):
            errs.append("dnd: keep index out of range")
    else:
        errs.append("unknown type %r" % t)
    return errs


def check_quiz(d):
    errs = []
    qs = d.get("questions")
    if not isinstance(qs, list) or len(qs) != 5:
        return ["need exactly 5 questions"]
    for i, q in enumerate(qs):
        for e in check_question(q):
            errs.append("q%d: %s" % (i, e))
    return errs


# ---------------------------------------------------------------- repair
FIX_PROMPT = """You repair NCLEX quiz questions so they match a strict JSON schema.

QUESTION (type: {typ}):
{question}

{extra}

Return ONLY a JSON object with these keys:
{{"blanks":[...]}}          # for cloze  — one object per blank: {{"of":[3 fa options],"oe":[3 en options],"c":0}}
{{"items":[...],"keep":[...]}}  # for dnd — items: [{{"fa":"...","en":"..."}}], keep: [indices in the correct order]

Rules:
- Keep the question wording, the learning point and the correct answer exactly as given.
- The correct option stays at index 0 in "of"/"oe" and "c" is 0.
- The two distractors must be plausible but clearly wrong.
- "keep" holds the 0-based INDICES of the items in the correct order.
- Every Persian string in Persian script, every English string in English.
- Output JSON only."""


def repair_with_llm(q, llm):
    """Ask the model to re-shape one question. Returns the new question or None."""
    typ = q.get("type")
    if typ == "cloze":
        blanks = q.get("blanks") or []
        flat = []
        for b in blanks:
            if isinstance(b, dict):
                flat.append({"fa": (b.get("of") or [""])[b.get("c", 0)] if b.get("of") else "",
                             "en": (b.get("oe") or [""])[b.get("c", 0)] if b.get("oe") else ""})
            elif isinstance(b, (list, tuple)) and len(b) >= 2:
                flat.append({"fa": b[0], "en": b[1]})
            elif isinstance(b, str):
                flat.append({"fa": b, "en": ""})
        extra = ("The correct answer for each blank (already known, keep it):\n"
                 + json.dumps(flat, ensure_ascii=False))
        prompt = FIX_PROMPT.format(typ=typ, question=json.dumps(q, ensure_ascii=False), extra=extra)
        raw, _ = llm.chat_any([{"role": "user", "content": prompt}], max_tokens=2500, temperature=0.2)
        d = extract_json(raw) or {}
        new = dict(q)
        new["blanks"] = d.get("blanks") or []
        return new
    if typ == "dnd":
        items = q.get("items") or []
        flat = [{"fa": (it.get("fa") if isinstance(it, dict) else str(it)),
                 "en": (it.get("en") if isinstance(it, dict) else "")} for it in items]
        keep_fa = []
        keep = q.get("keep") or []
        for k in keep:
            if isinstance(k, int) and 0 <= k < len(flat):
                keep_fa.append(flat[k]["fa"])
            elif isinstance(k, str):
                keep_fa.append(k)
        extra = ("Items (fa, en — en may be empty):\n" + json.dumps(flat, ensure_ascii=False)
                 + "\n\nThe correct ORDER, as Persian strings:\n" + json.dumps(keep_fa, ensure_ascii=False))
        prompt = FIX_PROMPT.format(typ=typ, question=json.dumps(q, ensure_ascii=False), extra=extra)
        raw, _ = llm.chat_any([{"role": "user", "content": prompt}], max_tokens=3000, temperature=0.2)
        d = extract_json(raw) or {}
        new = dict(q)
        new["items"] = d.get("items") or []
        new["keep"] = d.get("keep") or []
        return new
    return None


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


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check_only = "--check" in sys.argv
    targets = [a for a in args if a.endswith(".json")] or \
              [f for f in sorted(os.listdir(QUIZ_DIR)) if f.endswith(".json")]

    llm = None
    if not check_only:
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        from pipeline_worker import LLM, load_site      # noqa: E402
        site = load_site(type("A", (), {"site": "", "token": ""})())
        cfg = site.llm()
        s = cfg.get("settings") or {}
        llm = LLM(s.get("endpoint"), cfg.get("api_key", ""), s.get("model"),
                  [m["id"] for m in cfg.get("models", [])][:40])

    changed = 0
    bad = []
    for name in targets:
        path = os.path.join(QUIZ_DIR, name)
        if not os.path.isfile(path):
            continue
        d = json.load(open(path, encoding="utf-8"))
        errs = check_quiz(d)
        if not errs:
            print("%-22s OK" % name)
            continue
        print("%-22s %d problem(s):" % (name, len(errs)))
        for e in errs:
            print("    - %s" % e)
        bad.append(name)
        if check_only or llm is None:
            continue
        for i, q in enumerate(d.get("questions", [])):
            if not check_question(q):
                continue
            print("    repairing q%d (%s)…" % (i, q.get("type")))
            new = repair_with_llm(q, llm)
            if not new:
                continue
            still = check_question(new)
            if still:
                print("      still broken: %s" % still[:3])
                continue
            d["questions"][i] = new
        after = check_quiz(d)
        if after:
            print("    -> NOT fixed, remaining: %s" % after[:5])
            continue
        json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("    -> FIXED")
        changed += 1
    print("\n%d quiz file(s) rewritten" % changed)
    # --check must fail the process when something is wrong, otherwise the
    # pipeline's quiz_validate stage would always look like a pass.
    if bad:
        print("%d quiz file(s) need attention" % len(bad))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
