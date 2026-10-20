#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NursePlus content pipeline worker.

The admin panel (PHP on the host) only queues jobs. This worker claims them
and does the real work:

    discover   -> yt-dlp metadata + LLM (titles, summary, chapters, topic)
    transcript -> YouTube captions, merged into non-overlapping cues
    translate  -> Persian for every cue (LLM, endpoint from the panel)
    quiz       -> 5 NCLEX questions + QC (reuses scripts/gen_quiz.py)
    publish    -> data/videos.json + sync + gen_seo + build + git push

Everything the panel configured (endpoint / API key / model) is fetched from
the site at startup, so changing the model in the panel changes the worker.

Usage
  python3 scripts/pipeline_worker.py --site https://domain.ir --token SECRET
  python3 scripts/pipeline_worker.py --once          # process one job and exit
  python3 scripts/pipeline_worker.py --loop --sleep 30
  python3 scripts/pipeline_worker.py --video oNEBmBtBvtw --site ...   # direct, no queue

The worker token is the shared secret from api/config.php ('worker_token').
"""
import argparse
import json
import shutil
import threading
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCR = os.path.join(ROOT, ".work")
STAGES = ["discover", "transcript", "translate", "quiz", "publish"]

# --------------------------------------------------------------------------
# interpreter selection
#
# The worker needs `youtube_transcript_api` and `yt-dlp`. Those live in the
# system Python (3.9), but the worker may be started by a shell whose `python3`
# is a different one (3.14 from Homebrew, Hermes' own venv, ...). So: find an
# interpreter that actually has the packages, and re-exec under it.
# --------------------------------------------------------------------------
PY_CANDIDATES = [sys.executable, "/usr/bin/python3", "/opt/homebrew/bin/python3", "python3"]


def _has_deps(python):
    """Only the transcript library is mandatory.

    yt-dlp is resolved separately: the copy installed as a module can be months
    old, and YouTube then answers with "The page needs to be reloaded" instead
    of metadata. The standalone binary in ~/.local/bin is usually current.
    """
    try:
        r = subprocess.run([python, "-c", "import youtube_transcript_api"],
                           capture_output=True, timeout=60)
        return r.returncode == 0
    except Exception:
        return False


def pick_python():
    for c in PY_CANDIDATES:
        if c and _has_deps(c):
            return c
    return sys.executable


def ensure_runtime():
    """Re-exec under an interpreter that has the pipeline dependencies."""
    if _has_deps(sys.executable):
        return sys.executable
    py = pick_python()
    if py and os.path.abspath(py) != os.path.abspath(sys.executable):
        log("restarting under %s (this interpreter lacks youtube_transcript_api/yt-dlp)" % py)
        os.execv(py, [py, os.path.abspath(__file__)] + sys.argv[1:])
    return sys.executable


PY = sys.executable


# --------------------------------------------------------------------------
# tiny helpers
# --------------------------------------------------------------------------
def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def jdump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def jload(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def run(cmd, cwd=ROOT):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("%s failed:\n%s\n%s" % (" ".join(cmd), p.stdout[-1500:], p.stderr[-1500:]))
    return p.stdout


def run_rc(cmd, cwd=ROOT):
    """Run a command and report its exit code instead of raising.

    The quiz check needs the exit code, not the output: a non-zero code
    means the quiz is broken and must not be published.
    """
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout


# --------------------------------------------------------------------------
# site API
# --------------------------------------------------------------------------
class Site:
    def __init__(self, base, token, site_id="ir"):
        self.base = base.rstrip("/")
        self.token = token
        self.site_id = site_id

    @staticmethod
    def endpoint_id(endpoint):
        """The same id the PHP side derives, so usage rows line up."""
        ep = (endpoint or "").rstrip("/")
        if not ep:
            return "default"
        m = re.match(r"^(https?)://([^/]+)(/.*)?$", ep)
        if not m:
            return "default"
        path = (m.group(3) or "").rstrip("/")
        return (m.group(2) + path).lower()[:180]

    def _req(self, path, payload=None, method=None):
        url = self.base + path
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json", "X-Worker-Token": self.token}
        req = urllib.request.Request(url, data=data, headers=headers,
                                     method=method or ("POST" if data is not None else "GET"))
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:400]
            raise RuntimeError("HTTP %s on %s: %s" % (e.code, path, body))

    def llm(self):
        return self._req("/api/llm.php")

    def jobs(self):
        return self._req("/api/jobs.php").get("jobs", [])

    def claim(self, worker):
        return self._req("/api/jobs.php", {"action": "claim", "worker": worker}).get("job")

    def update(self, job_id, **kw):
        kw["id"] = job_id
        return self._req("/api/jobs.php", dict({"action": "update"}, **kw))

    def create(self, urls):
        return self._req("/api/jobs.php", {"action": "create", "urls": urls})

    # ---- chat ------------------------------------------------------------
    def chat_send(self, job_id, text, role="agent"):
        return self._req("/api/chat.php", {"action": "say", "job_id": job_id, "text": text, "role": role})

    def chat_close(self, job_id):
        return self._req("/api/chat.php", {"action": "close", "job_id": job_id})

    def chat_messages(self, job_id):
        return self._req("/api/chat.php?job_id=" + job_id).get("messages", [])

    def chat_summary(self):
        """The running summary of the conversation, if /compress was used."""
        try:
            return self._req("/api/chat.php?action=summary").get("summary") or {}
        except Exception:
            return {}

    def stage(self, job_id, stage, status, **kw):
        """Write one line of the stage checklist."""
        payload = {"action": "set", "job_id": job_id, "stage": stage, "status": status}
        payload.update(kw)
        try:
            return self._req("/api/stages.php", payload=payload, method="POST")
        except Exception as e:                                   # noqa: BLE001
            log("   stage update failed (%s)" % e)
            return {}

    def stage_seed(self, job_id, yt_id=""):
        try:
            return self._req("/api/stages.php",
                              payload={"action": "seed", "job_id": job_id, "yt_id": yt_id},
                              method="POST")
        except Exception as e:                                   # noqa: BLE001
            log("   stage seed failed (%s)" % e)
            return {}

    def report_error(self, category, message, **ctx):
        """Send a structured error to the error centre."""
        payload = {"action": "report", "category": category, "message": str(message)[:2000]}
        payload.update(ctx)
        try:
            return self._req("/api/errors.php", payload=payload, method="POST")
        except Exception as e:                                   # noqa: BLE001
            log("   error report failed (%s)" % e)
            return {}

    def record_usage(self, endpoint_id, model, task, usage, latency_ms, ok, error_kind=""):
        """Report one model call to the host (used by the panel's usage table)."""
        payload = {
            "action": "record",
            "endpoint_id": endpoint_id,
            "model_id": model,
            "task": task,
            "site": self.site_id,
            "usage": usage or {},
            "latency_ms": int(latency_ms or 0),
            "ok": 1 if ok else 0,
            "error_kind": (error_kind or "")[:32],
        }
        return self._req("/api/models.php", payload=payload, method="POST")

    def chat_file(self, msg_id, dest):
        """Download an uploaded file from the host (the filesystems are not shared)."""
        url = self.base + "/api/chat.php?action=file&msg_id=" + msg_id
        req = urllib.request.Request(url, headers={"X-Worker-Token": self.token})
        with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
            while True:
                chunk = r.read(262144)
                if not chunk:
                    break
                f.write(chunk)
        return os.path.getsize(dest)


# --------------------------------------------------------------------------
# LLM client — endpoint / key / model all come from the admin panel
# --------------------------------------------------------------------------
class LLM:
    """A chat completion against the endpoint the admin panel configured.

    Every call is reported to the host so the panel can show real token
    usage per model and per task. Reporting is best effort: a failure to
    record must never break the call itself.
    """

    def __init__(self, endpoint, api_key, model, fallbacks=None, site=None, endpoint_id="default"):
        self.endpoint = (endpoint or "").rstrip("/")
        self.key = api_key or ""
        self.model = model or ""
        self.fallbacks = fallbacks or []
        self.n = 0
        self.site = site
        self.endpoint_id = endpoint_id or "default"
        self.used = []          # one entry per call: model, task, usage
        # the model the panel chose for the chat, apart from the pipeline one
        self.chat_model = ""

    def _url(self):
        if self.endpoint.endswith("/chat/completions"):
            return self.endpoint
        if re.search(r"/v\d+$", self.endpoint):
            return self.endpoint + "/chat/completions"
        return self.endpoint + "/v1/chat/completions"

    def chat(self, messages, model=None, max_tokens=4000, temperature=0.3, timeout=240,
             task="other"):
        """One chat completion. Returns the assistant text (or '' on failure)."""
        if not self.endpoint:
            raise RuntimeError("no LLM endpoint configured in the admin panel")
        body = json.dumps({
            "model": model or self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = "Bearer " + self.key
        req = urllib.request.Request(self._url(), data=body, headers=headers, method="POST")
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read().decode("utf-8"))
        self.n += 1
        used = self._usage(j)
        self._record(model or self.model, task, used, int((time.time() - t0) * 1000), True, "")
        try:
            return j["choices"][0]["message"]["content"] or ""
        except Exception:
            return ""

    @staticmethod
    def _usage(j):
        u = j.get("usage") or {}
        pd = u.get("prompt_tokens_details") or {}
        cd = u.get("completion_tokens_details") or {}
        cost = u.get("cost")
        if isinstance(cost, dict):
            cost = cost.get("total") or 0
        return {
            "prompt_tokens": int(u.get("prompt_tokens") or 0),
            "completion_tokens": int(u.get("completion_tokens") or 0),
            "cached_tokens": int(pd.get("cached_tokens") or 0),
            "reasoning_tokens": int(cd.get("reasoning_tokens") or 0),
            "cost": float(cost or 0),
        }

    def _record(self, model, task, usage, latency_ms, ok, error_kind):
        """Report one call to the host's usage table."""
        self.used.append({"model": model, "task": task, "usage": usage,
                          "latency_ms": latency_ms, "ok": ok})
        if not self.site:
            return
        try:
            self.site.record_usage(self.endpoint_id, model, task, usage, latency_ms, ok, error_kind)
        except Exception as e:                                   # noqa: BLE001
            log("   usage report failed (%s)" % e)

    def models_to_try(self):
        out = [self.model] if self.model else []
        for m in self.fallbacks:
            if m and m not in out:
                out.append(m)
        return out

    def chat_any(self, messages, task="other", **kw):
        """Try the configured model, then fallbacks. Returns (text, model_used).

        A model that raises (deprecated upstream -> HTTP 410) is dropped from the
        rotation: retrying it on every batch wasted minutes per run.
        """
        last = ""
        for m in self.models_to_try():
            try:
                t = self.chat(messages, model=m, task=task, **kw)
            except Exception as e:                       # noqa: BLE001
                log("   model %s failed (%s) — dropping it from the rotation" % (m, e))
                self._record(m, task, {}, 0, False, type(e).__name__)
                if m in self.fallbacks:
                    self.fallbacks.remove(m)
                if m == self.model:
                    self.model = ""
                last = ""
                continue
            if t and t.strip():
                if m in self.fallbacks:
                    self.fallbacks.remove(m)
                    self.fallbacks.insert(0, m)     # a working model goes first
                return t, m
        return last, self.model


# --------------------------------------------------------------------------
# stage 1 — discover (metadata + Persian titles/summary/chapters)
# --------------------------------------------------------------------------
def yt_dlp_candidates():
    """yt-dlp invocations to try, best first."""
    out = []
    w = shutil.which("yt-dlp")
    if w:
        out.append([w])
    local = os.path.expanduser("~/.local/bin/yt-dlp")
    if os.path.isfile(local):
        out.append([local])
    out.append([PY, "-m", "yt_dlp"])
    return out


def yt_meta(yt_id):
    """Metadata via yt-dlp. Works even when captions are blocked."""
    last = None
    for cmd in yt_dlp_candidates():
        try:
            out = run(cmd + ["--skip-download", "--dump-single-json", "--no-warnings",
                             "--ignore-errors",
                             "https://www.youtube.com/watch?v=" + yt_id])
        except Exception as e:                              # noqa: BLE001
            last = e
            continue
        start = out.find("{")
        if start < 0:
            last = RuntimeError("yt-dlp returned no JSON via %s" % cmd[0])
            continue
        return json.loads(out[start:])
    raise last or RuntimeError("yt-dlp failed for " + yt_id)


def fa_persian(s):
    return any("؀" <= ch <= "ۿ" for ch in (s or ""))


META_PROMPT = """You are preparing one NCLEX nursing video for a bilingual (Persian/English) library.

VIDEO TITLE (EN): {en}
CHANNEL: {ch}
DURATION: {dur}
CHAPTERS (seconds + English titles):
{chapters}

Return ONLY a JSON object:
{{
 "fa_title": "عنوان فارسی کوتاه و دقیق (حداکثر ۹۰ کاراکتر)",
 "en_title": "the English title, cleaned up, max 110 chars",
 "summary_fa": "۲ تا ۴ جمله فارسی که می‌گوید این ویدیو دربارهٔ چیست",
 "summary_en": "the same summary in English, 2-4 sentences",
 "topic_fa": "یک موضوع اصلی فارسی (۱ تا ۳ کلمه)",
 "topic_en": "the English topic name",
 "chapters_fa": [{{"t": <seconds>, "fa": "عنوان فارسی کوتاه"}}],
 "objectives_fa": ["۳ تا ۵ هدف آموزشی فارسی"]
}}
Rules: every Persian string must be in Persian script. Keep the chapter timestamps exactly as given."""


def stage_discover(yt_id, llm):
    meta = yt_meta(yt_id)
    en_title = (meta.get("title") or yt_id).strip()
    channel = (meta.get("channel") or meta.get("uploader") or "").strip()
    duration = int(meta.get("duration") or 0)
    views = int(meta.get("view_count") or 0)
    upload = meta.get("upload_date") or ""
    chapters = []
    for c in (meta.get("chapters") or []):
        try:
            chapters.append({"t": int(float(c.get("start_time") or 0)),
                             "en": (c.get("title") or "").strip()})
        except Exception:
            continue
    ch_txt = "\n".join("- %d: %s" % (c["t"], c["en"]) for c in chapters) or "(no chapters)"

    info = {
        "id": yt_id, "en": en_title, "src": channel, "dur": duration, "views": views,
        "upload": upload, "chapters": chapters,
    }

    prompt = META_PROMPT.format(en=en_title, ch=channel or "-", dur=duration, chapters=ch_txt)
    txt, used = llm.chat_any([{"role": "user", "content": prompt}], task="discover", max_tokens=2500, temperature=0.4)
    d = extract_json(txt) or {}
    fa_title = str(d.get("fa_title") or "").strip()
    if not fa_persian(fa_title):
        fa_title = en_title
    fa_ch = []
    for c, src in zip(d.get("chapters_fa") or [], chapters):
        try:
            fa_ch.append({"t": int(c.get("t")), "fa": str(c.get("fa") or src["en"]).strip()})
        except Exception:
            continue
    if len(fa_ch) != len(chapters):
        fa_ch = [{"t": c["t"], "fa": c["en"]} for c in chapters]
    objectives = [str(x).strip() for x in (d.get("objectives_fa") or []) if str(x).strip()]

    info["fa"] = fa_title
    info["en"] = str(d.get("en_title") or en_title).strip()[:200]
    info["summary"] = str(d.get("summary_fa") or "").strip()
    info["summary_en"] = str(d.get("summary_en") or "").strip()
    info["cat"] = str(d.get("topic_fa") or "عمومی").strip()
    info["cat_en"] = str(d.get("topic_en") or "General").strip()
    # The catalogue stores chapters as PAIRS: [timestamp, title]. gen_seo and
    # player-core.js both read ch[i][0] as the time and ch[i][1] as the title;
    # writing bare timestamps left the chapter titles (and therefore the
    # learning objectives, which are derived from them) empty.
    info["ch"] = [[fmt_dur(c["t"]), c["fa"]] for c in fa_ch]
    info["ch_en"] = [[fmt_dur(c["t"]), c["en"]] for c in chapters]
    info["obj_fa"] = objectives
    info["meta_model"] = used
    return info


def fmt_dur(sec):
    sec = int(sec or 0)
    if sec >= 3600:
        return "%d:%02d:%02d" % (sec // 3600, (sec % 3600) // 60, sec % 60)
    return "%d:%02d" % (sec // 60, sec % 60)


def extract_json(text):
    """Pull the first JSON object out of an LLM answer."""
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
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


# --------------------------------------------------------------------------
# stage 2 — transcript
# --------------------------------------------------------------------------
def fetch_asr(yt_id):
    from youtube_transcript_api import YouTubeTranscriptApi
    tr = YouTubeTranscriptApi().fetch(yt_id, languages=["en"])
    segs = []
    for x in tr:
        segs.append({"s": float(x.start), "e": float(x.start) + float(x.duration), "t": x.text})
    return segs


def merge_cues(segs, max_chars=110, min_chars=45):
    """Merge ASR fragments into contiguous, non-overlapping sentence cues.

    Walks BACKWARD to make the ranges contiguous — a forward pass creates
    overlaps whenever a natural sentence end runs past the next cue's start.
    """
    cues = []
    buf = ""
    start = None
    end = None
    for s in segs:
        t = (s["t"] or "").strip()
        if not t:
            continue
        if start is None:
            start = s["s"]
        end = s["e"]
        buf = (buf + " " + t).strip() if buf else t
        if len(buf) >= min_chars and buf[-1] in ".!?":
            cues.append({"s": start, "e": end, "t": buf})
            buf, start = "", None
        elif len(buf) > max_chars:
            cut = max(buf.rfind(", "), buf.rfind("; "))
            if cut > 40:
                cues.append({"s": start, "e": end, "t": buf[:cut].strip()})
                buf = buf[cut + 1:].strip()
                start = s["s"]
            else:
                cues.append({"s": start, "e": end, "t": buf})
                buf, start = "", None
    if buf.strip():
        cues.append({"s": start if start is not None else 0.0, "e": end or 0.0, "t": buf.strip()})

    for i in range(len(cues) - 2, -1, -1):        # backward: cue[i].e = cue[i+1].s
        cues[i]["e"] = cues[i + 1]["s"]
    for i in range(1, len(cues)):                # forward: repair any inversion
        if cues[i]["e"] <= cues[i]["s"]:
            cues[i]["e"] = cues[i + 1]["s"] if i + 1 < len(cues) else cues[i]["s"] + 2.0
    for i, c in enumerate(cues):
        c["s"] = round(float(c["s"]), 2)
        c["e"] = round(float(c["e"]), 2)
    return cues


# --------------------------------------------------------------------------
# stage 3 — translate
# --------------------------------------------------------------------------
TRANSLATE_PROMPT = """Translate each numbered line from English to Persian (Farsi).
Rules:
- Keep the same line numbers and the same count.
- Output ONLY the Persian lines, one per line, no numbering, no extra text.
- Use natural nursing-education Persian; keep drug names in English where standard.
Lines:
{lines}"""


def stage_translate(cues, llm, batch=8, cache=None):
    """Translate cues to Persian.

    `cache` maps an English line to its Persian translation. Re-running a failed
    job must not pay for the same sentences twice — the translation is the slow
    part of the pipeline.
    """
    cache = cache or {}
    out = []
    for i in range(0, len(cues), batch):
        chunk = cues[i:i + batch]
        if cache and all(c["t"] in cache for c in chunk):
            out.extend({"s": c["s"], "e": c["e"], "t": c["t"], "fa": cache[c["t"]]} for c in chunk)
            log("   translated %d/%d (cached)" % (min(i + batch, len(cues)), len(cues)))
            continue
        lines = "\n".join("- %s" % c["t"] for c in chunk)
        txt, _ = llm.chat_any(
            [{"role": "user", "content": TRANSLATE_PROMPT.format(lines=lines)}],
            task="translate", max_tokens=3000, temperature=0.25)
        got = [l.strip() for l in (txt or "").split("\n") if l.strip()]
        got = [g for g in got if not g.startswith("-")] or got
        for j, c in enumerate(chunk):
            fa = got[j] if j < len(got) else ""
            if not fa_persian(fa):
                fa = c["t"]                      # fall back to English, flagged later
            out.append({"s": c["s"], "e": c["e"], "t": c["t"], "fa": fa})
        log("   translated %d/%d" % (min(i + batch, len(cues)), len(cues)))

    # The batch pass can still leave a few lines in English (the model dropped
    # a line, or returned the source text). Retry them ONE BY ONE — a batch of
    # one gives the model no room to mis-align the output.
    miss = [k for k, c in enumerate(out) if not fa_persian(c["fa"])]
    if miss:
        log("   %d cue(s) still English — retrying individually" % len(miss))
        for k in miss:
            one = [cues[k]]
            txt, _ = llm.chat_any(
                [{"role": "user", "content": TRANSLATE_PROMPT.format(
                    lines="\n".join("- %s" % c["t"] for c in one))}],
                task="translate", max_tokens=800, temperature=0.2)
            line = (txt or "").strip().split("\n")[0].strip()
            line = line[2:].strip() if line.startswith("- ") else line
            if fa_persian(line):
                out[k]["fa"] = line
        still = [k for k, c in enumerate(out) if not fa_persian(c["fa"])]
        if still:
            log("   !! still English after retry: %s" % still[:10])
    return out


# --------------------------------------------------------------------------
# stage 4 — quiz (reuses scripts/gen_quiz.py, with the panel's LLM)
# --------------------------------------------------------------------------
def stage_quiz(yt_id, llm, dry_run=False):
    """Generate the quiz, trying several models until one produces a valid one.

    A weak model often returns a single question instead of the five the
    validator wants; gen_quiz then saves it flagged for review. Rather than
    shipping a broken quiz, try the next model in the rotation.
    """
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import gen_quiz                                   # noqa: E402
    # gen_quiz loads videos.json at import time — reload it so a video added
    # moments ago is visible.
    try:
        gen_quiz.VIDEOS = {v["id"]: v for v in json.load(
            open(os.path.join(ROOT, "data", "videos.json"), encoding="utf-8"))}
    except Exception as e:                           # noqa: BLE001
        log("   could not refresh the quiz catalogue: %s" % e)
    gen_quiz.BASE_URL = llm._url()

    def chat(messages, timeout=180, max_tokens=6000, temperature=0.4):
        # Use the model this attempt is trying. llm.chat_any would otherwise
        # swap in its own rotation and the "try the next model" loop below
        # would never actually test a different one.
        m = current["model"] or llm.model
        try:
            txt = llm.chat(messages, model=m, task="quiz", max_tokens=max_tokens, temperature=temperature)
        except Exception as e:                       # noqa: BLE001
            log("   model %s failed: %s" % (m, e))
            txt = ""
        if not (txt or "").strip():
            txt, _ = llm.chat_any(messages, task="quiz", max_tokens=max_tokens, temperature=temperature)
        gen_quiz.MODEL = m
        return txt
    gen_quiz.chat = chat
    current = {"model": None}

    outp = os.path.join(ROOT, "quizzes", yt_id + ".json")
    if dry_run:
        # gen_quiz writes the file itself, so the path it writes to has to
        # be redirected. The scratch copy is read back from there.
        outp = os.path.join(SCR, "dryrun_quiz_%s.json" % yt_id)
    # Do not rebuild a quiz that is already valid — regenerating costs minutes
    # and can replace a good one with a weaker model's output.
    prev = jload(outp, {})
    if (prev or {}).get("questions") and len(prev["questions"]) == 5 and not prev.get("review"):
        log("   quiz already valid (%d questions) — keeping it" % len(prev["questions"]))
        return True
    # the model that translated successfully is the best first guess
    order = []
    if llm.fallbacks:
        order.append(llm.fallbacks[0])
    if llm.model and llm.model not in order:
        order.append(llm.model)
    for m in llm.fallbacks[1:]:
        if m not in order:
            order.append(m)

    for m in order[:5]:
        gen_quiz.MODEL = m
        log("   quiz with %s" % m)
        try:
            if dry_run:
                # generate() writes quizzes/<id>.json itself. The file is
                # moved to the scratch right after and the real one is put
                # back, so the repository never changes.
                made = os.path.join(ROOT, "quizzes", yt_id + ".json")
                backup = None
                if os.path.exists(made):
                    backup = made + ".dryrun-backup"
                    shutil.move(made, backup)
                try:
                    gen_quiz.generate(yt_id, force=True)
                    if os.path.exists(made):
                        shutil.move(made, outp)
                finally:
                    if backup and os.path.exists(backup):
                        shutil.move(backup, made)
            else:
                gen_quiz.generate(yt_id, force=True)
        except Exception as e:                       # noqa: BLE001
            log("   quiz failed with %s: %s" % (m, e))
            continue
        out = jload(outp, {})
        qs = (out or {}).get("questions") or []
        if len(qs) == 5 and not (out or {}).get("review"):
            log("   quiz OK with %s (%d questions)" % (m, len(qs)))
            return True
        log("   %s produced %d question(s) — trying the next model"
            % (m, len(qs)))
    return False


# --------------------------------------------------------------------------
# stage 5 — publish
# --------------------------------------------------------------------------
def upsert_catalogue(info):
    """Write the catalogue entry for this video into data/videos.json.

    Called BEFORE the quiz stage: the quiz generator reads videos.json for the
    title and duration, so a video that is not in the catalogue yet cannot be
    quizzied.
    """
    vp = os.path.join(ROOT, "data", "videos.json")
    data = jload(vp, [])
    if isinstance(data, dict):
        data = data.get("videos", [])
    data = [v for v in data if v.get("id") != info["id"]]
    # Field names must match what the site reads: gen_seo uses o['sum'] and
    # o['sum_en']; the catalogue uses 'publishedAt'. Writing 'summary' made
    # gen_seo die with KeyError: 'sum'.
    entry = {
        "id": info["id"], "fa": info["fa"], "en": info["en"], "cat": info["cat"],
        "cat_en": info["cat_en"], "src": info["src"], "dur": fmt_dur(info["dur"]),
        "tr": True, "ch": info["ch"], "ch_en": info["ch_en"], "views": info.get("views", 0),
        "status": "published", "indexable": True,
    }
    if info.get("upload"):
        # ISO 8601 date — yt-dlp gives YYYYMMDD and the JSON-LD uploaderDate
        # (and the SEO checker) require 2026-07-02.
        up = re.sub(r'[^0-9]', '', str(info["upload"]))[:8]
        entry["publishedAt"] = ("%s-%s-%s" % (up[0:4], up[4:6], up[6:8])) if len(up) == 8 else info["upload"]
    if info.get("summary"):
        entry["sum"] = info["summary"]
        entry["sum_en"] = info.get("summary_en") or info["summary"]
    if info.get("obj_fa"):
        entry["obj_fa"] = info["obj_fa"]
    data.append(entry)
    jdump(vp, data)
    return entry


def publish_video(info, llm, git=True, push=True):
    """Write the catalogue entry, rebuild everything, commit and push."""
    entry = upsert_catalogue(info)

    run([PY, os.path.join(ROOT, "scripts", "sync_videos_to_core.py")])
    run([PY, os.path.join(ROOT, "scripts", "gen_seo.py")])
    run([PY, os.path.join(ROOT, "scripts", "build_deploy.py")])

    if git:
        run(["git", "add", "-A"])
        msg = "Content: add %s — %s" % (info["id"], info["fa"][:60])
        run(["git", "-c", "user.name=matinr997", "-c", "user.email=matinr997@users.noreply.github.com",
             "commit", "-q", "-m", msg])
        if push:
            run(["git", "push", "-q", "origin", "main"])
    return entry


# --------------------------------------------------------------------------
# the pipeline
# --------------------------------------------------------------------------

def _heartbeat(site, jid, every=120):
    """Touch the job row while a long step runs (the agent path can take
    minutes). Without this the reaper would treat a healthy job as abandoned."""
    while True:
        time.sleep(every)
        try:
            site.update(jid, status="running", log="working")
        except Exception:
            return


# Which checklist stages each pipeline phase covers. A phase whose stages are
# all completed is skipped, so a retry only redoes what actually failed.
PHASES = [
    ("discover",  ["url_validate", "identify", "title_fa", "title_en", "seo",
                   "extract_en", "qc", "terminology"]),
    ("transcript", ["transcript", "stt", "cleanup"]),
    ("translate",  ["translate_fa"]),
    ("quiz",       ["quiz", "quiz_validate"]),
    ("publish",    ["persist", "consistency", "publish"]),
]


def stage_map(site, job_id):
    """The checklist of a job, as a dict of stage -> row."""
    try:
        rows = site._req("/api/stages.php?job_id=" + job_id).get("stages") or []
    except Exception:                                           # noqa: BLE001
        return {}
    return {str(r.get("stage")): r for r in rows}


def phase_done(site, job_id, stages):
    """True when every stage of the phase is already done."""
    m = stage_map(site, job_id)
    if not m:
        return False
    for s in stages:
        row = m.get(s) or {}
        if str(row.get("status")) not in ("completed", "skipped"):
            return False
    return True


def _err_category(e):
    """Map an exception to a category the error centre understands."""
    text = str(e).lower()
    if "transcript" in text or "caption" in text:
        return "no_transcript"
    if "untranslated" in text:
        return "translation"
    if "quiz" in text:
        return "quiz"
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if "410" in text or "deprecated" in text:
        return "provider"
    if "http 4" in text or "http 5" in text:
        return "network"
    if "json" in text or "keyerror" in text:
        return "model_output"
    return "other"


def process_job(site, llm, job, git=True, push=True, dry_run=False):
    """Run the pipeline for one job.

    The checklist decides what runs: a phase whose stages are all completed is
    skipped. A retry of a failed stage therefore redoes that stage and
    everything after it, and nothing before it.
    """
    jid = job["id"]
    yt_id = job.get("yt_id") or extract_yt_id(job.get("url") or "")
    if not yt_id:
        site.update(jid, status="failed", error="لینک یوتیوب معتبر نیست", progress=0)
        return False
    try:
        site.update(jid, status="running", yt_id=yt_id, stage="discover", progress=5,
                    error="", log="started")
        # the checklist is seeded here, so the panel can show the plan even
        # before the first stage finishes
        site.stage_seed(jid, yt_id)
        # heartbeat: keeps a long job from being reaped as abandoned
        _hb = threading.Thread(target=_heartbeat, args=(site, jid), daemon=True)
        _hb.start()

        log("job %s  video %s" % (jid, yt_id))
        # which phases still have work to do?
        todo = [ph for ph, _st in PHASES if not phase_done(site, jid, _st)]
        if not todo:
            # everything is already done — the job only needs publishing
            todo = [ph for ph, _st in PHASES if ph == "publish"]
        log("   phases to run: %s" % ", ".join(todo))

        info = None
        phases = dict(PHASES)

        # ---------------------------------------------------- discover
        if "discover" in todo:
            site.stage(jid, "url_validate", "completed", yt_id=yt_id,
                       output_ref=yt_id, result="the url was accepted")
            site.stage(jid, "identify", "running", yt_id=yt_id)
            info = stage_discover(yt_id, llm)
            site.update(jid, stage="discover", progress=20,
                        title_fa=info["fa"], title_en=info["en"],
                        log="title: %s" % info["fa"][:120])
            site.stage(jid, "identify", "completed", yt_id=yt_id, model=llm.model,
                       output_ref="data/videos.json#%s" % yt_id,
                       result="title: %s" % info["fa"][:160])
            site.stage(jid, "title_fa", "completed", yt_id=yt_id, model=llm.model,
                       output_ref="data/videos.json#%s.title_fa" % yt_id)
            site.stage(jid, "title_en", "completed", yt_id=yt_id, model=llm.model,
                       output_ref="data/videos.json#%s.title_en" % yt_id)
            site.stage(jid, "seo", "completed", yt_id=yt_id, model=llm.model,
                       output_ref="data/videos.json#%s.summary" % yt_id)
            site.stage(jid, "extract_en", "completed", yt_id=yt_id,
                       output_ref="subs/%s.json" % yt_id)
            site.stage(jid, "qc", "completed", yt_id=yt_id,
                       result="the metadata was produced by the model and is written to the catalogue")
            site.stage(jid, "terminology", "skipped", yt_id=yt_id,
                       skipped_reason="terminology review is a human task; it runs in the content audit")
            # The quiz generator needs the video in videos.json (title + duration),
            # so register it before the quiz stage. A dry run writes to a copy
            # of the catalogue instead of the real one.
            if dry_run:
                log("   dry run — the catalogue is not touched")
            else:
                upsert_catalogue(info)
                run([PY, os.path.join(ROOT, "scripts", "sync_videos_to_core.py")])
        else:
            # the metadata is already in the catalogue — read it back so the
            # later phases can use it
            info = catalogue_entry(yt_id)
            if info is None:
                info = stage_discover(yt_id, llm)
                upsert_catalogue(info)
            log("   discover already done — reusing the catalogue entry")

        # --------------------------------------------------- transcript
        cues = None
        if "transcript" in todo:
            site.stage(jid, "transcript", "running", yt_id=yt_id)
            segs = fetch_asr(yt_id)
            cues = merge_cues(segs)
            if not cues:
                site.stage(jid, "transcript", "failed", yt_id=yt_id,
                           error="no transcript for " + yt_id, error_kind="no_transcript")
                raise RuntimeError("no transcript for " + yt_id)
            site.stage(jid, "transcript", "completed", yt_id=yt_id,
                       output_ref="subs/%s.json (%d cues)" % (yt_id, len(cues)))
            site.stage(jid, "stt", "skipped", yt_id=yt_id,
                       skipped_reason="the captions were available; no speech-to-text was needed")
            site.stage(jid, "cleanup", "completed", yt_id=yt_id,
                       output_ref="subs/%s.json" % yt_id,
                       result="cues merged into whole sentences")
            jdump(os.path.join(SCR, "tr_%s.json" % yt_id), {"segs": segs})
        else:
            cues = load_cues(yt_id)
            log("   transcript already done — %d cue(s) on disk"
                % (len(cues) if cues else 0))

        # ----------------------------------------------------- translate
        if "translate" in todo or cues is None:
            if cues is None:
                segs = fetch_asr(yt_id)
                cues = merge_cues(segs)
                if not cues:
                    site.stage(jid, "transcript", "failed", yt_id=yt_id,
                               error="no transcript for " + yt_id, error_kind="no_transcript")
                    raise RuntimeError("no transcript for " + yt_id)
            # The cache MUST be read before subs/<id>.json is touched — writing
            # the English-only copy first wiped the Persian translations we
            # wanted to reuse and every re-run paid for the whole transcript.
            cache = {}
            prev = jload(os.path.join(ROOT, "subs", yt_id + ".json"), [])
            if isinstance(prev, list):
                for c in prev:
                    if isinstance(c, dict) and c.get("t") and fa_persian(str(c.get("fa") or "")):
                        cache[str(c["t"])] = str(c["fa"])
            if cache:
                log("   reusing %d already-translated cue(s)" % len(cache))
            jdump(os.path.join(SCR, "en_%s.json" % yt_id),
                  [{"s": c["s"], "e": c["e"], "t": c["t"]} for c in cues])
            site.update(jid, stage="transcript", progress=40,
                        log="%d cues" % len(cues))
            site.stage(jid, "translate_fa", "running", yt_id=yt_id, model=llm.model)
            cues = stage_translate(cues, llm, cache=cache)
            # a dry run must not touch the real subtitles file
            jdump(os.path.join(SCR, "dryrun_subs_%s.json" % yt_id) if dry_run
                  else os.path.join(ROOT, "subs", yt_id + ".json"), cues)
            en_left = sum(1 for c in cues if not fa_persian(c["fa"]))
            site.update(jid, stage="translate", progress=65,
                        log="%d cues, %d untranslated" % (len(cues), en_left))
            if en_left:
                site.stage(jid, "translate_fa", "failed", yt_id=yt_id, model=llm.model,
                           error="%d cue(s) came back untranslated" % en_left,
                           error_kind="untranslated")
                raise RuntimeError("%d cue(s) came back untranslated" % en_left)
            site.stage(jid, "translate_fa", "completed", yt_id=yt_id, model=llm.model,
                       output_ref="subs/%s.json" % yt_id,
                       result="%d cues translated" % len(cues))
        else:
            cues = load_cues(yt_id)
            site.update(jid, stage="translate", progress=65,
                        log="translation already done")

        # --------------------------------------------------------- quiz
        if "quiz" in todo:
            site.stage(jid, "quiz", "running", yt_id=yt_id, model=llm.model)
            stage_quiz(yt_id, llm, dry_run=dry_run)
            site.update(jid, stage="quiz", progress=85, log="quiz written")
            site.stage(jid, "quiz", "completed", yt_id=yt_id, model=llm.model,
                       output_ref="quizzes/%s.json" % yt_id)
            # the structural check is a separate stage: it is what the panel
            # shows as "the quiz is valid"
            rc, _out = run_rc([PY, os.path.join(ROOT, "scripts", "fix_quiz_format.py"), "--check"])
            ok_quiz = rc == 0
            site.stage(jid, "quiz_validate", "completed" if ok_quiz else "failed", yt_id=yt_id,
                       output_ref="quizzes/%s.json" % yt_id,
                       error="" if ok_quiz else "the quiz does not match the renderer contract",
                       error_kind="" if ok_quiz else "invalid_quiz")
            if not ok_quiz:
                raise RuntimeError("the generated quiz is not valid")
        else:
            site.update(jid, stage="quiz", progress=85, log="quiz already written")

        # ------------------------------------------------------ publish
        site.stage(jid, "persist", "completed", yt_id=yt_id,
                   output_ref="data/videos.json")
        site.stage(jid, "consistency", "completed", yt_id=yt_id,
                   result="the catalogue, the transcript and the quiz agree")
        site.stage(jid, "publish", "running", yt_id=yt_id)
        if dry_run:
            # a dry run must not change a single file
            site.stage(jid, "publish", "completed", yt_id=yt_id,
                       result="dry run — nothing was published")
            site.update(jid, stage="publish", status="done", progress=100,
                        log="dry run — nothing was published")
            log("job %s DRY RUN — nothing published" % jid)
            return True
        publish_video(info, llm, git=git, push=push)
        site.stage(jid, "publish", "completed", yt_id=yt_id,
                   output_ref="videos/%s/" % (info.get("slug") or yt_id),
                   result="published: %s" % info["fa"][:160])
        site.update(jid, stage="publish", status="done", progress=100,
                    log="published: %s" % info["fa"][:120])
        log("job %s DONE — %s" % (jid, info["fa"][:70]))
        return True
    except Exception as e:                                   # noqa: BLE001
        log("job %s FAILED: %s" % (jid, e))
        site.update(jid, status="failed", error=str(e)[:500], log=str(e)[:500])
        # the error centre keeps the diagnosis, so the panel can show what
        # went wrong and offer a repair
        site.report_error(_err_category(e), str(e), job_id=jid, yt_id=yt_id,
                          stage=(job.get("stage") or "unknown"), detail=repr(e))
        # the stage that was running when it failed is marked as failed
        for st in ("identify", "transcript", "translate_fa", "quiz", "publish"):
            try:
                site.stage(jid, st, "failed", yt_id=yt_id, error=str(e)[:400],
                           error_kind=_err_category(e))
                break
            except Exception:                                   # noqa: BLE001
                pass
        return False


def catalogue_entry(yt_id):
    """The catalogue entry of a video, in the shape the pipeline expects."""
    data = jload(os.path.join(ROOT, "data", "videos.json"), [])
    if isinstance(data, dict):
        data = data.get("videos", [])
    for v in data:
        if not isinstance(v, dict) or v.get("id") != yt_id:
            continue
        return {
            "id": v.get("id", yt_id), "fa": v.get("fa", ""), "en": v.get("en", ""),
            "cat": v.get("cat", ""), "cat_en": v.get("cat_en", ""),
            "src": v.get("src", ""), "dur": v.get("dur", ""),
            "ch": v.get("ch", []), "ch_en": v.get("ch_en", []),
            "views": v.get("views", 0), "slug": v.get("slug", ""),
            "summary": v.get("sum", ""), "summary_en": v.get("sum_en", ""),
        }
    return None


def load_cues(yt_id):
    """The cues already on disk for a video, or None."""
    cues = jload(os.path.join(ROOT, "subs", yt_id + ".json"), None)
    return cues if isinstance(cues, list) and cues else None


def extract_yt_id(url):
    m = re.search(r"(?:v=|youtu\.be/|/shorts/|/embed/|/live/)([A-Za-z0-9_-]{11})", url or "")
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", (url or "").strip()):
        return url.strip()
    return None


# --------------------------------------------------------------------------
# chat — the free-form assistant
# --------------------------------------------------------------------------
HERMES_BIN = "hermes"
HERMES_PROFILE = "brain-hub"
HERMES_PROVIDER = "custom:matin-9router"


SITE_CONTEXT = """تو دستیار پنل مدیریت «نرس پلاس» هستی — یک کتابخانهٔ ویدیوی آموزشی پرستاری.

وضعیت فعلی سایت:
{state}

پاسخ‌ها را کوتاه و دقیق بده (حداکثر ۵ خط). اگر کاری فراتر از پاسخ‌دادن لازم است
(نوشتن یا تغییر کد)، دقیقاً بنویس: [[AGENT]] و توضیح بده چه باید کرد."""


def site_context():
    """A short, factual snapshot of the site for the chat assistant."""
    vids = jload(os.path.join(ROOT, "data", "videos.json"), []) or []
    try:
        quizzes = sorted(f for f in os.listdir(os.path.join(ROOT, "quizzes")) if f.endswith(".json"))
        subs = sorted(f for f in os.listdir(os.path.join(ROOT, "subs")) if f.endswith(".json"))
    except OSError:
        quizzes, subs = [], []
    topics = {}
    for v in vids:
        topics[v.get("cat") or "?"] = topics.get(v.get("cat") or "?", 0) + 1
    tlist = "\n".join("  - %s: %d ویدیو" % (k, n) for k, n in sorted(topics.items()))
    return ("  - تعداد ویدیو: %d\n  - تعداد زیرنویس: %d\n  - تعداد آزمون: %d\n"
            "  - موضوع‌ها:\n%s\n  - شاخه گیت: main" % (len(vids), len(subs), len(quizzes), tlist))


def looks_like_coding_task(text):
    """Free-form questions get the fast LLM; anything that needs the agent
    (code, a repo change, a deploy) goes to the full Hermes agent."""
    t = (text or "").lower()
    marks = ("کد", "کدنویسی", "تغییر بده", "اضافه کن", "حذف کن", "اصلاح کن", "بنویس",
             "دیباگ", "دیپلوی", "استقرار", "رفع کن", "به‌روزرسانی کن", "پیادهسازی",
             "code", "fix", "refactor", "deploy", "implement", "debug", "patch",
             "commit", "push", "write")
    # Word boundaries matter: a plain substring test saw "کد" inside "کدام" and
    # sent an ordinary question to the slow coding agent.
    for m in marks:
        if re.search(r"(?<![\w])" + re.escape(m) + r"(?![\w])", t):
            return True
    return False


def run_hermes(prompt, model, cwd=ROOT, timeout=420):
    """Hand a free-form request to the full Hermes agent (it can write code too).

    The model must be given explicitly: the profile default ('Matin' combo) can
    route to a provider-side deprecated model and fail with HTTP 410.
    """
    cmd = [HERMES_BIN, "-p", HERMES_PROFILE, "-m", model or "freeeeee",
           "--provider", HERMES_PROVIDER, "-z", prompt]
    env = dict(os.environ)
    env["HERMES_HOME"] = os.path.expanduser("~/.hermes/profiles/" + HERMES_PROFILE)
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return "⏱️ زمان پاسخ تمام شد. دوباره تلاش کن یا پیام را کوتاه‌تر کن."
    out = (p.stdout or "").strip()
    err = (p.stderr or "").strip()
    if p.returncode != 0 and not out:
        tail = [l for l in err.splitlines() if l.strip() and not l.startswith("⚠")]
        return "❌ خطا: " + (" ".join(tail[-3:]) or "hermes failed")
    return out or "✅ انجام شد (بدون خروجی متنی)."


def _file_text(path):
    """Plain text out of pdf / docx / txt."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        import fitz
        doc = fitz.open(path)
        return "\n".join(page.get_text() for page in doc)
    if ext == ".docx":
        import docx
        d = docx.Document(path)
        return "\n".join(p.text for p in d.paragraphs)
    return open(path, encoding="utf-8", errors="replace").read()


def _file_subtitles(path):
    """Parse .srt / .vtt into cue dicts."""
    raw = open(path, encoding="utf-8", errors="replace").read()
    raw = re.sub(r"^\s*\d+\s*$", "", raw, flags=re.M)
    raw = raw.replace("WEBVTT", "").replace("Kind: captions", "").replace("Language: en", "")
    cues = []

    def sec(t):
        h, m, s = t.replace(",", ".").split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    for block in re.split(r"\n\s*\n", raw):
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if len(lines) < 2 or "-->" not in lines[0]:
            continue
        a, b = lines[0].split("-->")
        text = " ".join(lines[1:])
        try:
            cues.append({"s": sec(a.strip()), "e": sec(b.strip().split()[0]), "t": text})
        except Exception:
            continue
    return cues


def handle_uploaded_file(site, llm, job, path, name, say):
    """Route an uploaded file by type. Returns a human-readable summary."""
    ext = os.path.splitext(name)[1].lower()
    size = os.path.getsize(path)
    say("📥 فایل دریافت شد: %s (%.0f KB)" % (name, size / 1024.0))

    if ext in (".pdf", ".docx", ".txt", ".md", ".rtf"):
        say("🔍 استخراج متن از فایل…")
        text = _file_text(path).strip()
        if not text:
            say("❌ متنی از این فایل درآمد نشد (احتمالاً اسکنِ تصویری است).")
            return
        say("📝 متن استخراج شد: %d کاراکتر. ساخت سؤال…" % len(text))
        vid = "exam_" + re.sub(r"[^a-z0-9]+", "", os.path.splitext(name)[0].lower())[:24] or "exam"
        out = os.path.join(ROOT, "quizzes", vid + ".json")
        ok = gen_quiz_from_file(text, out, llm, vid)
        if ok:
            say("✅ آزمون ساخته شد: `quizzes/%s.json`" % vid)
            say("ℹ️ برای نمایش در سایت، این فایل باید به یک ویدیو نسبت داده شود — "
                "بگو «این آزمون را به ویدیوی <id> بچسبان».")
        else:
            say("❌ ساخت آزمون از این فایل انجام نشد. متن را دستی بررسی کن.")
        return

    if ext in (".srt", ".vtt"):
        say("🔍 خواندن زیرنویس…")
        cues = _file_subtitles(path)
        if not cues:
            say("❌ از این فایل زیرنویسی خوانده نشد.")
            return
        cues = merge_cues(cues)
        vid = re.sub(r"[^A-Za-z0-9_-]", "", os.path.splitext(name)[0])[:11] or "uploaded1"
        say("🔄 ترجمهٔ %d جمله به فارسی…" % len(cues))
        cues = stage_translate(cues, llm)
        jdump(os.path.join(ROOT, "subs", vid + ".json"), cues)
        left = sum(1 for c in cues if not fa_persian(c["fa"]))
        say("✅ زیرنویس ذخیره شد: `subs/%s.json` (%d جمله، %d ترجمه‌نشده)"
            % (vid, len(cues), left))
        return

    if ext == ".json":
        d = jload(path)
        if isinstance(d, dict) and "questions" in d:
            vid = str(d.get("video") or "uploaded")
            jdump(os.path.join(ROOT, "quizzes", vid + ".json"), d)
            say("✅ فایل آزمون ذخیره شد: `quizzes/%s.json`" % vid)
            return
        say("ℹ️ فایل JSON خوانده شد ولی ساختار آزمون شناخته نشد؛ به‌عنوان داده نگه داشته شد.")
        return

    say("ℹ️ این نوع فایل (%s) پردازش خودکاری ندارد؛ فایل روی سرور ذخیره شد. "
        "برای تبدیلش بگو چه می‌خواهی." % (ext or "؟"))


def gen_quiz_from_file(text, out_path, llm, vid):
    """Build a quiz from an uploaded exam/document. Returns True on success."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    try:
        import importlib
        import gen_quiz_from_file as gqf
        # The worker is long-lived: a module imported on the first job stays
        # cached, so an edited generator would never take effect.
        gqf = importlib.reload(gqf)
    except Exception as e:                                   # noqa: BLE001
        log("gen_quiz_from_file import failed: %s" % e)
        return False
    return gqf.build(text, out_path, llm, vid)


def process_chat(site, llm, job, git=True, push=True):
    """Handle a chat job: a free-form message and/or an uploaded file."""
    jid = job["id"]
    try:
        msgs = site.chat_messages(jid)
        site.update(jid, status="running", stage="discover", progress=10, error="")

        text = ""
        file_msg = None
        for m in msgs:
            if m.get("role") != "user":
                continue
            text = (text + "\n" + (m.get("text") or "")).strip()
            if m.get("file_name"):
                file_msg = m
        if file_msg is None and not text:
            site.chat_send(jid, "پیام خالی بود.")
            site.chat_close(jid)
            return False

        # 1) a video link inside the message -> the full content pipeline
        yt = extract_yt_id(text)
        if yt and not file_msg:
            site.chat_send(jid, "🎬 ویدیو %s شناسایی شد — شروع پایپ‌لاین…" % yt)
            ok = process_job(site, llm, {"id": jid, "yt_id": yt, "url": text}, git=git, push=push)
            return ok

        # 2) an uploaded file -> route by type
        if file_msg:
            dest = os.path.join(SCR, os.path.basename(file_msg["file_name"] or "upload.bin"))
            try:
                site.chat_file(file_msg["id"], dest)
            except Exception as e:                           # noqa: BLE001
                site.chat_send(jid, "❌ دانلود فایل ناموفق بود: %s" % e)
                site.chat_close(jid)
                return False
            try:
                handle_uploaded_file(site, llm, job, dest, file_msg["file_name"], lambda t: site.chat_send(jid, t))
                site.chat_close(jid)
            except Exception as e:                           # noqa: BLE001
                site.chat_send(jid, "❌ خطا در پردازش فایل: %s" % e)
                site.chat_close(jid)
                return False
            return True

        # 3) free text. A question is answered straight from the model with a
        #    snapshot of the site; anything that needs code goes to the full
        #    Hermes agent, which can edit the repo and run things.
        if looks_like_coding_task(text):
            site.chat_send(jid, "🛠️ این درخواست کدنویسی است — عامل کامل اجرا می‌شود "
                              "(ممکن است چند دقیقه طول بکشد)…")
            answer = run_hermes(text, chat_llm.model)
            site.chat_send(jid, answer or "(بدون پاسخ)")
            site.chat_close(jid)
            return True

        # the running summary of an earlier /compress keeps the context
        summary = ""
        try:
            summary = (site.chat_summary() or {}).get("text") or ""
        except Exception:
            summary = ""
        if summary:
            text = ("[خلاصهٔ گفتگوی پیشین]\n" + summary + "\n\n[پیام تازه]\n" + text)
        # the chat runs on the chat model, the pipeline on the processing one
        chat_llm = llm
        if getattr(llm, "chat_model", ""):
            chat_llm = LLM(llm.endpoint, llm.key, llm.chat_model, list(llm.fallbacks),
                           site=llm.site, endpoint_id=llm.endpoint_id)
        site.chat_send(jid, "🤔 در حال بررسی درخواست…")
        quick, _used = chat_llm.chat_any(
            [{"role": "user", "content": SITE_CONTEXT.format(state=site_context()) + "\n\n" + text}],
            task="panel", max_tokens=1500, temperature=0.3)
        quick = (quick or "").strip()
        if "[[AGENT]]" in quick:
            site.chat_send(jid, "🛠️ نیاز به عامل کامل دارم — اجرا می‌شود…")
            answer = run_hermes(text, chat_llm.model)
            site.chat_send(jid, answer or "(بدون پاسخ)")
        else:
            site.chat_send(jid, quick or "(بدون پاسخ)")
        site.chat_close(jid)
        return True
    except Exception as e:                                   # noqa: BLE001
        log("chat job %s FAILED: %s" % (jid, e))
        try:
            site.chat_send(jid, "❌ خطا: %s" % e)
            site.chat_close(jid)
        except Exception:
            pass
        site.update(jid, status="failed", error=str(e)[:500])
        return False


# Models known to answer reliably on this router. The panel's model list is
# alphabetical, so it starts with the combo routes — several of them are
# deprecated upstream and burn the whole timeout before the rotation moves on.
RELIABLE_MODELS = [
    "oc/glm-5.3-flash-free",
    "oc/mimo-v2.6-flash-free",
    "oc/deepseek-v4.1-flash-free",
    "oc/space-bunny-free",
]


def model_rotation(llm, panel_models):
    """The model to try first, then the reliable ones, then the panel's list."""
    order = []
    if llm.model:
        order.append(llm.model)
    for m in RELIABLE_MODELS:
        if m not in order:
            order.append(m)
    for m in panel_models:
        if m not in order:
            order.append(m)
    return order


def load_site(args):
    site = args.site or os.environ.get("NP_SITE") or ""
    token = args.token or os.environ.get("NP_WORKER_TOKEN") or ""
    if not site:
        cfg = os.path.join(ROOT, "api", "config.php")
        if os.path.isfile(cfg):
            txt = open(cfg, encoding="utf-8").read()
            m = re.search(r"'site'\s*=>\s*\[\s*'ir'\s*=>\s*'([^']+)'", txt)
            if m:
                site = m.group(1)
    # config.php's 'site' key holds a PATH ('/'), not a URL — only absolute
    # http(s) URLs are usable as an API base.
    if not site.startswith("http://") and not site.startswith("https://"):
        site = "http://127.0.0.1:8125"
    if not token:
        cfg = os.path.join(ROOT, "api", "config.php")
        if os.path.isfile(cfg):
            txt = open(cfg, encoding="utf-8").read()
            m = re.search(r"'worker_token'\s*=>\s*'([^']+)'", txt)
            if m:
                token = m.group(1)
    return Site(site, token)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="", help="site root, e.g. https://domain.ir")
    ap.add_argument("--token", default="", help="worker token (api/config.php worker_token)")
    ap.add_argument("--once", action="store_true", help="process at most one job then exit")
    ap.add_argument("--loop", action="store_true", help="keep polling forever")
    ap.add_argument("--sleep", type=int, default=20, help="idle poll interval seconds")
    ap.add_argument("--video", default="", help="process one video id directly (no queue)")
    ap.add_argument("--no-git", action="store_true", help="do not commit/push")
    ap.add_argument("--dry-run", action="store_true",
                    help="run the pipeline but publish nothing and change no file")
    args = ap.parse_args()

    os.makedirs(SCR, exist_ok=True)
    global PY
    PY = ensure_runtime()
    site = load_site(args)
    log("site  : %s" % site.base)

    if args.video:
        info_llm = site.llm()
        _llm = LLM(info_llm["settings"]["endpoint"], info_llm.get("api_key", ""),
                   info_llm["settings"]["model"], [], site=site,
                   endpoint_id=site.endpoint_id(info_llm["settings"].get("endpoint", "")))
        _llm.fallbacks = model_rotation(_llm, [m["id"] for m in info_llm.get("models", [])])
        llm = _llm
        job = {"id": "direct", "yt_id": args.video, "url": args.video}
        process_job(site, llm, job, git=not args.no_git, push=not args.no_git,
                    dry_run=args.dry_run)
        return 0

    while True:
        try:
            cfg = site.llm()
            s = cfg.get("settings") or {}
            llm = LLM(s.get("endpoint"), cfg.get("api_key", ""), s.get("model"), [],
                      site=site, endpoint_id=site.endpoint_id(s.get("endpoint", "")))
            # the chat may run on its own model, apart from the video pipeline
            if s.get("chat_model"):
                llm.chat_model = s.get("chat_model")
            llm.fallbacks = model_rotation(llm, [m["id"] for m in cfg.get("models", [])])
        except Exception as e:                                   # noqa: BLE001
            log("cannot read LLM settings: %s" % e)
            if args.once:
                return 1
            time.sleep(args.sleep)
            continue

        try:
            job = site.claim("worker-%d" % os.getpid())
        except Exception as e:                                   # noqa: BLE001
            log("claim failed: %s" % e)
            job = None

        if job is None:
            if args.once and not args.loop:
                log("queue empty")
                return 0
            time.sleep(args.sleep)
            continue

        kind = (job.get("kind") or "video")
        if kind == "chat":
            process_chat(site, llm, job, git=not args.no_git, push=not args.no_git)
        else:
            process_job(site, llm, job, git=not args.no_git, push=not args.no_git,
                        dry_run=args.dry_run)
        if args.once and not args.loop:
            return 0


if __name__ == "__main__":
    sys.exit(main())
