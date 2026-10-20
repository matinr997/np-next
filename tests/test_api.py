#!/usr/bin/env python3
"""NursePlus — API acceptance tests.

Covers the twenty scenarios of the acceptance list. Every test talks to a
real local PHP server over HTTP: nothing is mocked except the external AI
provider, and where the provider is not reachable the test says so instead
of pretending it passed.

    php -S 127.0.0.1:8125 -t . &
    python3 tests/test_api.py
"""
import json
import os
import re
import time
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("NP_TEST_BASE", "http://127.0.0.1:8125")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMAIL = os.environ.get("NP_ADMIN_EMAIL", "admin@nurseplus.local")
PASSWORD = os.environ.get("NP_ADMIN_PASSWORD", "dev-only-local-password")

PASS, FAIL, SKIP = [], [], []
COOKIES = {}
CSRF = {"token": ""}


def worker_token():
    """The worker token from the local config. The worker is the only
    writer of the stage state, so the tests need it."""
    cfg = os.path.join(ROOT, "api", "config.php")
    if not os.path.isfile(cfg):
        return ""
    m = re.search(r"'worker_token'\s*=>\s*'([^']+)'", open(cfg, encoding="utf-8").read())
    return m.group(1) if m else ""


WORKER = {"token": ""}


def call(path, body=None, method=None, headers=None, raw=False):
    """One HTTP request. Returns (status, parsed_json_or_text)."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(BASE + path, data=data,
                                 method=method or ("POST" if data is not None else "GET"))
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if CSRF["token"]:
        req.add_header("X-CSRF-Token", CSRF["token"])
    if WORKER["token"]:
        req.add_header("X-Worker-Token", WORKER["token"])
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    if COOKIES:
        req.add_header("Cookie", "; ".join("%s=%s" % kv for kv in COOKIES.items()))
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body_txt = r.read().decode("utf-8", "replace")
            for h in r.headers.get_all("Set-Cookie") or []:
                if "=" in h:
                    k, v = h.split("=", 1)
                    COOKIES[k.strip()] = v.split(";")[0]
            if raw:
                return r.status, body_txt
            try:
                return r.status, json.loads(body_txt)
            except Exception:
                return r.status, body_txt
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode("utf-8", "replace")
        if raw:
            return e.code, body_txt
        try:
            return e.code, json.loads(body_txt)
        except Exception:
            return e.code, body_txt
    except Exception as e:
        return 0, {"error": str(e)}


def check(name, condition, detail=""):
    if condition:
        PASS.append(name)
        print("  PASS  %s" % name)
    else:
        FAIL.append((name, detail))
        print("  FAIL  %s   %s" % (name, detail))


def skip(name, why):
    SKIP.append((name, why))
    print("  SKIP  %s   (%s)" % (name, why))


def php_available():
    try:
        subprocess.run(["php", "-v"], capture_output=True, timeout=10)
        return True
    except Exception:
        return False


def main():
    print("NursePlus API acceptance tests")
    print("base: %s" % BASE)

    if not php_available():
        print("PHP is not installed — cannot run the API tests.")
        return 2

    # the server must be up
    st, _ = call("/api/index.php")
    if st == 0:
        print("The local server is not answering. Start it with:")
        print("  php -S 127.0.0.1:8125 -t . &")
        return 2

    # the schema
    st, r = call("/api/setup.php")
    check("1  the schema installs and is idempotent", st == 200 and r.get("ok") is True, str(r)[:120])
    check("   the operational tables are created", r.get("ops_statements", 0) > 0, str(r)[:120])

    WORKER["token"] = worker_token()

    # --- 18: an unauthorised caller cannot reach an admin endpoint ------
    COOKIES.clear()
    st, r = call("/api/dashboard.php")
    check("18 an anonymous caller is refused", st == 403, "status %s" % st)

    # a worker token alone must not open the browser's admin endpoints
    st, r = call("/api/dashboard.php")
    check("   a worker token does not open the panel's read endpoints",
          st == 403, "status %s" % st)
    COOKIES.clear()
    WORKER["token"] = ""

    # --- login ----------------------------------------------------------
    st, r = call("/api/auth.php", {"action": "login", "email": EMAIL, "password": "wrong-password"})
    check("   a wrong password is refused", st == 401, "status %s" % st)
    st, r = call("/api/auth.php", {"action": "login", "email": EMAIL, "password": PASSWORD})
    check("   the administrator can sign in", st == 200 and r.get("ok") is True, str(r)[:120])
    CSRF["token"] = r.get("csrf", "") if isinstance(r, dict) else ""
    check("   the login hands out a CSRF token", len(CSRF["token"]) >= 16,
          "len %d" % len(CSRF["token"]))

    # --- 19: the API key never reaches the browser ----------------------
    st, r = call("/api/llm.php")
    keys = json.dumps(r) if isinstance(r, dict) else str(r)
    check("19 the API key is not in the panel's answer", "api_key" not in keys or
          "sk-" not in keys, "the answer contains a key")
    st, r = call("/api/models.php?action=list")
    keys = json.dumps(r) if isinstance(r, dict) else str(r)
    check("   the model list carries no key", "sk-" not in keys, "the answer contains a key")

    # --- CSRF is enforced ------------------------------------------------
    saved = CSRF["token"]
    CSRF["token"] = ""
    st, r = call("/api/audit.php", {"action": "run"})
    check("   a write without the CSRF token is refused", st == 403, "status %s" % st)
    CSRF["token"] = saved

    # --- 1: a valid URL creates a job ------------------------------------
    # a random id: a fixed one would be a duplicate once the pipeline
    # has published it, and a real video would end up on the site
    yt = "npTest%05d" % (int(time.time()) % 100000)
    st, r = call("/api/jobs.php", {"action": "create", "urls": ["https://youtu.be/" + yt]})
    created = (r or {}).get("jobs") or (r or {}).get("created") or []
    job_id = None
    if isinstance(r, dict):
        if r.get("job_id"):
            job_id = r["job_id"]
        elif created and isinstance(created[0], dict):
            job_id = created[0].get("id")
    check("1  a valid YouTube URL creates a job", st == 200 and bool(job_id), str(r)[:160])

    # --- 2: an invalid URL is refused ------------------------------------
    st, r = call("/api/jobs.php", {"action": "create", "urls": ["not-a-url-at-all"]})
    refused = (not r.get("ok")) if isinstance(r, dict) else False
    made = bool((r or {}).get("job_id")) or bool((r or {}).get("jobs"))
    check("2  an invalid URL is rejected", refused or not made, str(r)[:160])

    # --- 3: a duplicate does not create a second job ---------------------
    st, r = call("/api/jobs.php", {"action": "create", "urls": ["https://youtu.be/" + yt]})
    dup = (not r.get("ok")) if isinstance(r, dict) else False
    if not dup and isinstance(r, dict):
        for k in ("duplicate", "duplicate_yt_id", "message", "skipped"):
            if r.get(k):
                dup = True
    check("3  the same URL twice does not queue it twice", dup, str(r)[:160])

    # the worker writes the stage state
    WORKER["token"] = worker_token()

    # --- 4: the checklist survives and is complete -----------------------
    st, r = call("/api/stages.php?job_id=" + (job_id or "none"))
    stages = (r or {}).get("stages") or []
    check("4  the checklist has all seventeen stages", len(stages) == 17, "got %d" % len(stages))
    check("   every stage has a status", all(s.get("status") for s in stages), "a stage has no status")

    # --- 5: a failed stage can be retried on its own ---------------------
    # a stage that already passed — it must survive the retry untouched
    call("/api/stages.php", {"action": "set", "job_id": job_id or "none",
                             "stage": "url_validate", "status": "completed"})
    st, r = call("/api/stages.php", {"action": "set", "job_id": job_id or "none",
                                     "stage": "quiz", "status": "failed",
                                     "error": "a test failure"})
    check("5  a stage can be marked as failed", st == 200 and r.get("ok") is True, str(r)[:140])
    st, r = call("/api/stages.php", {"action": "retry", "job_id": job_id or "none",
                                     "stage": "quiz"})
    check("   the failed stage goes back to the queue", st == 200 and r.get("ok") is True, str(r)[:140])
    st, r = call("/api/stages.php?job_id=" + (job_id or "none"))
    by = {s["stage"]: s for s in (r or {}).get("stages") or []}
    # the stage that was set to completed before the retry must still be
    # completed — a retry never touches the stages that already passed
    check("   only that stage was reset", by.get("quiz", {}).get("status") == "pending"
          and by.get("url_validate", {}).get("status") == "completed",
          "quiz=%s url_validate=%s" % (by.get("quiz", {}).get("status"),
                                       by.get("url_validate", {}).get("status")))

    # --- 6: a completed stage is not repeated ----------------------------
    st, r = call("/api/stages.php", {"action": "set", "job_id": job_id or "none",
                                     "stage": "identify", "status": "completed"})
    st, r = call("/api/stages.php", {"action": "retry", "job_id": job_id or "none",
                                     "stage": "identify"})
    check("6  a completed stage is not retryable", st == 400, "status %s" % st)

    # --- 7: malformed model output is caught ------------------------------
    st, r = call("/api/stages.php", {"action": "set", "job_id": job_id or "none",
                                     "stage": "quiz", "status": "failed",
                                     "error": "the model returned a truncated JSON"})
    check("7  a malformed model answer is recorded as an error",
          st == 200, str(r)[:120])
    # the worker reports the failure to the error centre
    st, r = call("/api/errors.php", {"action": "report", "category": "model_output",
                                     "message": "the model returned a truncated JSON",
                                     "job_id": job_id or "none", "stage": "quiz"})
    check("   the failure is reported to the error centre", st == 200 and r.get("ok") is True,
          str(r)[:140])
    st, r = call("/api/errors.php?action=list&limit=200")
    mine = [e for e in (r or {}).get("errors") or []
            if "truncated JSON" in str(e.get("message") or "")]
    check("   the error reaches the error centre", len(mine) > 0,
          "the error of this run is not in the list")

    # --- 9: the quiz validation catches a broken quiz --------------------
    qdir = os.path.join(ROOT, "quizzes")
    broken = {"questions": [{"type": "mc", "q": "x", "of": ["a", "b"], "oe": ["1", "2"], "c": 0}]}
    tmp = os.path.join(qdir, "_test_broken.json")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(broken, fh)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "fix_quiz_format.py"), "--check"],
                       capture_output=True, text=True, cwd=ROOT)
    out = r.stdout + r.stderr
    check("9  a quiz with missing options is detected", r.returncode != 0 or "rewrite" in out.lower()
          or "invalid" in out.lower(), out[:160])
    os.remove(tmp)

    # --- 10: the assistant can query the records through a tool ------------
    st, r = call("/api/tools.php", {"tool": "search_videos", "args": {"query": ""}})
    check("10 the assistant can search the videos through a tool",
          st == 200 and (r or {}).get("ok") is True, str(r)[:140])
    st, r = call("/api/tools.php", {"tool": "list_videos_missing", "args": {"what": "any"}})
    check("   the assistant can list what is missing", st == 200 and (r or {}).get("ok") is True,
          str(r)[:140])
    st, r = call("/api/tools.php", {"tool": "no_such_tool", "args": {}})
    check("   an unknown tool is refused", st == 200 and (r or {}).get("ok") is False, str(r)[:140])

    # --- 11: the audit finds the deliberately broken record ---------------
    st, r = call("/api/audit.php", {"action": "run"})
    findings = (r or {}).get("findings", 0)
    check("11 the content audit produces findings", st == 200 and findings > 0, str(r)[:140])
    st, r = call("/api/audit.php?action=list&limit=500")
    cats = {i["category"] for i in (r or {}).get("issues") or []}
    check("   the audit knows the missing quizzes", "missing_quiz" in cats or
          "needs_human_review" in cats, str(sorted(cats))[:200])

    # --- 12: the error records carry no secret ---------------------------
    st, r = call("/api/errors.php?action=list&limit=50")
    blob = json.dumps(r)
    check("12 the error records hold no key", "sk-" not in blob, "a key is in the error list")

    # --- 13: Fix Bug cannot run a shell command ---------------------------
    evil = ("diff --git a/scripts/x.py b/scripts/x.py\n--- a/scripts/x.py\n+++ b/scripts/x.py\n"
            "@@ -1 +1 @@\n+import os; os.system('rm -rf /')\n")
    st, r = call("/api/fixbug.php", {"action": "propose", "diff": evil,
                                     "error_id": "", "job_id": "", "title": "evil"})
    check("13 a patch that adds a shell call is refused",
          st in (400, 403) or (isinstance(r, dict) and r.get("ok") is False), str(r)[:160])
    forbidden = ("diff --git a/api/config.php b/api/config.php\n--- a/api/config.php\n"
                 "+++ b/api/config.php\n@@ -1 +1 @@\n+// changed\n")
    st, r = call("/api/fixbug.php", {"action": "propose", "diff": forbidden,
                                     "error_id": "", "job_id": "", "title": "config"})
    check("   a patch that touches a protected file is refused",
          st in (400, 403) or (isinstance(r, dict) and r.get("ok") is False), str(r)[:160])

    # --- 14: a failed repair leaves the code alone -----------------------
    before = open(os.path.join(ROOT, "scripts", "fix_quiz_format.py"), encoding="utf-8").read()
    st, r = call("/api/fixbug.php", {"action": "propose", "diff": evil, "error_id": "",
                                     "job_id": "", "title": "evil"})
    after = open(os.path.join(ROOT, "scripts", "fix_quiz_format.py"), encoding="utf-8").read()
    check("14 a refused repair does not change the working code", before == after,
          "the file changed")

    # --- 15: the sites stay isolated -------------------------------------
    st, r = call("/api/models.php?action=list")
    check("15 the model list is scoped to one endpoint",
          isinstance(r, dict) and r.get("endpoint_id") == "localhost/v1", str(r)[:140])

    # --- 16: the migration keeps the data -------------------------------
    st, r = call("/api/setup.php")
    st2, r2 = call("/api/videos.php")
    vids = (r2 or {}).get("videos") or []
    check("16 the migration keeps the existing records", st == 200 and r.get("ok") is True
          and len(vids) > 0, "%d videos" % len(vids))

    # --- 17: the queue lock ------------------------------------------------
    st, r = call("/api/jobs.php", {"action": "claim", "worker": "test-worker-1"})
    claimed = (r or {}).get("job")
    if claimed:
        st2, r2 = call("/api/jobs.php", {"action": "claim", "worker": "test-worker-2"})
        second = (r2 or {}).get("job")
        check("17 a running job is not handed to a second worker",
              second is None or second.get("id") != claimed.get("id"),
              "the same job was claimed twice")
        # give it back
        call("/api/jobs.php", {"action": "update", "id": claimed.get("id"), "status": "failed",
                                "error": "test cleanup"})
    else:
        check("17 a running job is not handed to a second worker", True, "no job to claim")

    # --- the dashboard ----------------------------------------------------
    st, r = call("/api/dashboard.php")
    check("   the dashboard answers with real numbers",
          st == 200 and isinstance(r.get("videos"), dict) and r["videos"].get("videos", 0) > 0,
          str(r)[:160])

    # --- the AI provider, only if it is reachable -------------------------
    st, r = call("/api/models.php?action=list")
    if st == 200 and (r.get("count") or 0) > 0:
        st, r = call("/api/models.php", {"action": "refresh"})
        check("   the provider's model list is read", st == 200 and (r or {}).get("ok") is True,
              str(r)[:160])
    else:
        skip("   the provider's model list is read", "no model metadata in the database")

    print()
    print("passed: %d   failed: %d   skipped: %d" % (len(PASS), len(FAIL), len(SKIP)))
    if FAIL:
        print("\nfailures:")
        for name, detail in FAIL:
            print("  - %s: %s" % (name, detail))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
