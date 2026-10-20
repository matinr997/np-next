/* =====================================================================
   NursePlus — Admin panel (Persian / RTL)
   Talks to the site API at ../api/*.php (same-origin, session cookie).
   ===================================================================== */
(function () {
  'use strict';

  var API_BASE = new URL('../api/', document.baseURI).href;
  var POLL_MS = 4000;

  /* ------------------------------------------------------------------ */
  /* helpers                                                            */
  /* ------------------------------------------------------------------ */
  var FA_DIGITS = '۰۱۲۳۴۵۶۷۸۹';
  function fa(value) {
    if (value === null || value === undefined) return '';
    return String(value).replace(/[0-9]/g, function (d) { return FA_DIGITS.charAt(+d); });
  }
  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }
  function clear(node) { while (node && node.firstChild) node.removeChild(node.firstChild); }

  /* ------------------------------------------------------------------ */
  /* toast                                                              */
  /* ------------------------------------------------------------------ */
  var toastTimer = null;
  function toast(message, kind) {
    var t = $('toast');
    if (!t) return;
    t.textContent = message;
    t.className = 'adm-toast' + (kind ? ' ' + kind : '');
    /* force reflow so the transition replays */
    void t.offsetWidth;
    t.classList.add('show');
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.remove('show'); }, 4200);
  }

  /* ------------------------------------------------------------------ */
  /* api                                                                */
  /* ------------------------------------------------------------------ */
  function ApiError(message, status, data) {
    this.name = 'ApiError';
    this.message = message || 'خطای نامشخصی رخ داد';
    this.status = status || 0;
    this.data = data || null;
  }
  ApiError.prototype = Object.create(Error.prototype);

  /* The CSRF token for writes. The server hands it out with the login and
   with GET /api/auth.php; it is refreshed whenever a write is refused. */
var CSRF = '';

function setCsrf(token) {
  if (token) {
    CSRF = token;
    /* models.js is a separate file and needs the same token */
    window.__npCsrf = token;
  }
}

/* ------------------------------------------------------------------ */
  /* is the API actually there?                                          */
  /*                                                                     */
  /* GitHub Pages serves the panel as static files, so a POST to         */
  /* ../api/auth.php comes back 405 and the login can never work.        */
  /* Detect it once and say so plainly instead of showing a raw code.   */
  /* ------------------------------------------------------------------ */
  var API_MISSING = false;
  function apiMissingMessage() {
    return 'این پنل روی آدرس ایستا (GitHub Pages) باز شده و API ندارد؛ ورود فقط روی هاست یا سرور محلی ممکن است. آدرس محلی: http://127.0.0.1:8131/admin/ — یا پنل را روی نتفراز نصب کنید.';
  }
  function checkApi() {
    return fetch(API_BASE + 'auth.php?action=csrf', { credentials: 'same-origin' })
      .then(function (res) {
        if (res.status === 405 || res.status === 404) { API_MISSING = true; }
        return res.text().then(function (t) {
          try { return JSON.parse(t); } catch (e) { return null; }
        });
      })
      .catch(function () { /* the network is down; the real error shows later */ });
  }

function api(file, opts) {
    opts = opts || {};
    var init = {
      method: opts.method || 'GET',
      credentials: 'same-origin',
      headers: { 'Accept': 'application/json' }
    };
    if (opts.body !== undefined) {
      init.headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(opts.body);
      if (CSRF) init.headers['X-CSRF-Token'] = CSRF;
    }
    return fetch(API_BASE + file, init).then(function (res) {
      if (res.status === 403 && init.method === 'POST') {
        /* the token expired — fetch a new one so the next attempt works */
        fetch(API_BASE + 'auth.php?action=csrf', { credentials: 'same-origin' })
          .then(function (r) { return r.json(); })
          .then(function (d) { setCsrf(d && d.csrf); })
          .catch(function () { });
      }
      return res.text().then(function (text) {
        var data = null;
        if (text) {
          try { data = JSON.parse(text); } catch (e) { data = null; }
        }
        if (data === null) {
          if (res.status === 405 || res.status === 404) { API_MISSING = true; }
          throw new ApiError(
            API_MISSING ? apiMissingMessage() : (res.ok ? 'پاسخ سرور قابل خواندن نبود.' : 'سرور خطا برگرداند (کد ' + res.status + ').'),
            res.status, null
          );
        }
        if (!res.ok || data.ok === false) {
          var msg = data.message || '';
          if (!msg && file === 'auth.php' && res.status === 401) msg = 'ایمیل یا رمز اشتباه است';
          if (!msg) msg = 'درخواست ناموفق بود (کد ' + res.status + ').';
          throw new ApiError(msg, res.status, data);
        }
        return data;
      });
    }).catch(function (err) {
      if (err instanceof ApiError) throw err;
      throw new ApiError('ارتباط با سرور برقرار نشد. اتصال اینترنت را بررسی کنید.', 0, null);
    });
  }

  /* ------------------------------------------------------------------ */
  /* constants                                                          */
  /* ------------------------------------------------------------------ */
  var STAGE_LABEL = {
    discover: 'کشف',
    transcript: 'زیرنویس',
    translate: 'ترجمه',
    quiz: 'آزمون',
    publish: 'انتشار'
  };
  var STATUS_LABEL = {
    queued: 'در صف',
    running: 'در حال اجرا',
    done: 'انجام شد',
    failed: 'خطا',
    skipped: 'تکراری',
    canceled: 'لغو شد'
  };
  /* The language of this panel, and the labels that differ. */
  var FA = (document.documentElement.lang || 'fa').toLowerCase() === 'fa';
  var VIDEO_EMPTY_SEARCH = 'ویدیویی با این عبارت پیدا نشد.';
  var VIDEO_EMPTY = 'ویدیویی برای نمایش نیست.';
  var VIDEOS_COUNT_LABEL = 'ویدیو';

  var VIDEO_STATUS_LABEL = {
    published: 'منتشر شده',
    draft: 'پیش‌نویس',
    pending: 'در انتظار',
    queued: 'در صف',
    running: 'در حال اجرا',
    done: 'انجام شد',
    failed: 'خطا',
    skipped: 'تکراری',
    canceled: 'لغو شد'
  };

  /* ------------------------------------------------------------------ */
  /* session / view state                                               */
  /* ------------------------------------------------------------------ */
  var state = {
    user: null,
    jobs: [],
    jobNodes: {},
    videos: [],
    models: [],
    modelFilter: '',
    hasKey: false,
    pollTimer: null,
    polling: false,
    busy: false
  };

  function showLogin() {
    $('loginView').hidden = false;
    $('appView').hidden = true;
    stopPolling();
  }
  function showApp(user) {
    state.user = user || state.user;
    $('loginView').hidden = true;
    $('appView').hidden = false;
    $('userName').textContent = state.user
      ? (state.user.name || state.user.email)
      : '';
    startPolling();
  }

  /* ------------------------------------------------------------------ */
  /* login                                                              */
  /* ------------------------------------------------------------------ */
  function initLogin() {
    var form = $('loginForm');
    var email = $('loginEmail');
    var pass = $('loginPass');
    var btn = $('loginBtn');
    var errBox = $('loginError');

    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      errBox.hidden = true;
      var em = (email.value || '').trim();
      var pw = pass.value || '';
      if (!em || !pw) {
        errBox.textContent = 'ایمیل و رمز را وارد کنید.';
        errBox.hidden = false;
        return;
      }
      btn.disabled = true;
      btn.textContent = 'در حال ورود…';
      api('auth.php', { method: 'POST', body: { action: 'login', email: em, password: pw } })
        .then(function (data) {
          state.user = data.user || null;
          setCsrf(data.csrf);
          pass.value = '';
          showApp(state.user);
          loadAll();
          toast('خوش آمدید، ' + ((state.user && state.user.name) || state.user.email) + '!', 'ok');
        })
        .catch(function (err) {
          errBox.textContent = err.status === 401 ? 'ایمیل یا رمز اشتباه است' : err.message;
          errBox.hidden = false;
        })
        .then(function () {
          btn.disabled = false;
          btn.textContent = 'ورود';
        });
    });
  }

  function initLogout() {
    $('logoutBtn').addEventListener('click', function () {
      api('auth.php', { method: 'POST', body: { action: 'logout' } })
        .catch(function () { /* ignore — the local session is dropped anyway */ })
        .then(function () {
          state.user = null;
          state.jobs = [];
          state.jobNodes = {};
          state.videos = [];
          state.models = [];
          $('loginPassword') && ($('loginPassword').value = '');
          $('loginPass').value = '';
          showLogin();
          toast('از پنل خارج شدید.');
        });
    });
  }

  /* ------------------------------------------------------------------ */
  /* YouTube link parsing                                               */
  /* ------------------------------------------------------------------ */
  var YT_RE = /(?:youtube(?:-nocookie)?\.com\/watch\?(?:[^\s]*&)?v=|youtu\.be\/|youtube(?:-nocookie)?\.com\/(?:shorts|embed|live)\/)([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])/i;
  var BARE_ID_RE = /^[A-Za-z0-9_-]{11}$/;
  var URLISH_RE = /^(?:https?:\/\/|www\.)/i;

  /* Split the pasted blob into candidates.
     valid   → a YouTube id could be extracted (sent to the API as a canonical watch URL)
     invalid → looks like a link but is not a usable YouTube link (the API confirms with
               reason:'invalid', so the user still sees exactly which one was rejected) */
  function parseLinks(text) {
    var out = [];
    var raw = String(text || '');
    if (!raw.trim()) return out;
    var tokens = raw.split(/[\s\u200c,;،]+/);
    for (var i = 0; i < tokens.length; i++) {
      var tok = tokens[i];
      if (!tok) continue;
      var m = YT_RE.exec(tok);
      if (m) {
        out.push({
          raw: tok,
          ytId: m[1],
          url: 'https://www.youtube.com/watch?v=' + m[1],
          valid: true
        });
        continue;
      }
      if (BARE_ID_RE.test(tok)) {
        out.push({
          raw: tok,
          ytId: tok,
          url: 'https://www.youtube.com/watch?v=' + tok,
          valid: true
        });
        continue;
      }
      if (URLISH_RE.test(tok) || /youtu/i.test(tok)) {
        out.push({ raw: tok, ytId: null, url: tok, valid: false });
      }
      /* anything else is prose, not a link — ignored on purpose */
    }
    return out;
  }

  /* live counter + chips under the textarea */
  function renderDetected() {
    var links = parseLinks($('urlInput').value);
    var ids = {}, uniq = 0, bad = 0;
    links.forEach(function (l) {
      if (l.valid) { if (!ids[l.ytId]) { ids[l.ytId] = 1; uniq++; } }
      else bad++;
    });
    var label = fa(uniq) + ' لینک شناسایی شد';
    if (bad) label += ' · ' + fa(bad) + ' مورد نامعتبر';
    $('linkCount').textContent = label;

    var box = $('detected');
    clear(box);
    links.forEach(function (l) {
      if (!l.valid) return;
      var chip = el('span', 'adm-chip');
      chip.appendChild(el('b', null, 'YouTube'));
      chip.appendChild(el('span', null, l.ytId));
      box.appendChild(chip);
    });
  }

  /* ------------------------------------------------------------------ */
  /* add videos                                                         */
  /* ------------------------------------------------------------------ */
  function resultRow(stateName, badge, message, link) {
    var li = el('li', 'adm-res adm-res-' + stateName);
    li.appendChild(el('span', 'adm-res-badge', badge));
    var txt = el('div', 'adm-res-txt');
    txt.appendChild(el('div', null, message));
    if (link) txt.appendChild(el('span', 'adm-res-link', link));
    li.appendChild(txt);
    return li;
  }

  function addToQueue() {
    if (state.busy) return;
    var box = $('addResults');
    var summary = $('addSummary');
    var btn = $('addBtn');
    clear(box);
    summary.hidden = true;

    var links = parseLinks($('urlInput').value);
    if (!links.length) {
      toast('هیچ لینکی وارد نشده است.', 'err');
      return;
    }

    /* de-duplicate identical ids inside the paste, keep the first */
    var seen = {};
    var rows = [];
    links.forEach(function (l) {
      if (l.valid) {
        if (seen[l.ytId]) {
          rows.push({
            raw: l.raw, ytId: l.ytId, url: l.url, state: 'duplicate',
            message: 'این لینک تکراری است', note: 'همین لینک در پیام بالا تکرار شده بود.'
          });
          return;
        }
        seen[l.ytId] = 1;
        rows.push({ raw: l.raw, ytId: l.ytId, url: l.url, state: 'pending' });
      } else {
        /* sent to the API as-is so the server is the one that says 'invalid' */
        rows.push({ raw: l.raw, ytId: null, url: l.raw, state: 'pending' });
      }
    });

    var toCheck = rows.filter(function (r) { return r.state === 'pending' && r.ytId; });
    if (!rows.length) { renderResults(rows, summary); return; }

    state.busy = true;
    btn.disabled = true;
    btn.textContent = 'در حال بررسی…';

    Promise.all(toCheck.map(function (r) {
      return api('videos.php?check=' + encodeURIComponent(r.ytId))
        .then(function (d) {
          if (!d.duplicate) return;
          r.state = 'duplicate';
          r.message = 'این لینک تکراری است';
          r.note = d.reason === 'already_queued'
            ? 'همین حالا در صف پایپ‌لاین قرار دارد.'
            : 'قبلاً روی سایت منتشر شده است.';
        })
        .catch(function () {
          /* a failed pre-check must not block the submission */
        });
    })).then(function () {
      var send = rows.filter(function (r) { return r.state === 'pending'; });
      if (!send.length) { renderResults(rows, summary); return null; }
      return api('jobs.php', { method: 'POST', body: { action: 'create', urls: send.map(function (r) { return r.url; }) } })
        .then(function (data) {
          var created = data.created || [];
          var skipped = data.skipped || [];

          created.forEach(function (c) {
            for (var i = 0; i < rows.length; i++) {
              var r = rows[i];
              if (r.state !== 'pending') continue;
              if (r.ytId && c.yt_id && r.ytId === c.yt_id) {
                r.state = 'added';
                r.message = 'به صف اضافه شد';
                r.jobId = c.id;
                break;
              }
            }
          });

          skipped.forEach(function (s) {
            for (var i = 0; i < rows.length; i++) {
              var r = rows[i];
              if (r.state !== 'pending') continue;
              var sameId = (s.yt_id && r.ytId && s.yt_id === r.ytId);
              var sameUrl = s.url === r.url;
              if (!sameId && !sameUrl) continue;
              if (s.reason === 'invalid') {
                r.state = 'invalid';
                r.message = s.message || 'لینک یوتیوب معتبر نیست';
              } else {
                r.state = 'duplicate';
                r.message = 'این لینک تکراری است';
                r.note = s.reason === 'already_queued'
                  ? 'همین حالا در صف پایپ‌لاین قرار دارد.'
                  : 'قبلاً روی سایت منتشر شده است.';
              }
              break;
            }
          });

          rows.forEach(function (r) {
            if (r.state === 'pending') {
              r.state = 'invalid';
              r.message = 'ثبت نشد — لینک معتبر شناسایی نشد.';
            }
          });
          renderResults(rows, summary);
          loadJobs();
          return null;
        });
    }).catch(function (err) {
      toast(err.message, 'err');
      renderResults(rows, summary);
    }).then(function () {
      state.busy = false;
      btn.disabled = false;
      btn.textContent = 'افزودن به صف';
    });
  }

  function renderResults(rows, summary) {
    var box = $('addResults');
    clear(box);
    var added = 0, dup = 0, bad = 0;
    rows.forEach(function (r) {
      if (r.state === 'added') {
        added++;
        box.appendChild(resultRow('ok', 'افزوده شد', r.message, r.raw !== r.url ? r.raw : r.url));
      } else if (r.state === 'duplicate') {
        dup++;
        var li = resultRow('warn', 'تکراری', r.message, r.raw);
        if (r.note) li.querySelector('.adm-res-txt').appendChild(el('div', 'adm-res-note', r.note));
        box.appendChild(li);
      } else {
        bad++;
        box.appendChild(resultRow('err', 'نامعتبر', r.message, r.raw));
      }
    });
    if (rows.length) {
      summary.textContent = fa(added) + ' افزوده شد · ' + fa(dup) + ' تکراری · ' + fa(bad) + ' نامعتبر';
      summary.hidden = false;
    }
  }

  /* ------------------------------------------------------------------ */
  /* jobs                                                               */
  /* ------------------------------------------------------------------ */
  function stageLabel(stage) {
    return STAGE_LABEL[stage] || stage || '—';
  }
  function statusClass(status) {
    return 'adm-badge adm-badge-' + (STATUS_LABEL[status] ? status : 'other');
  }

  function buildJobNode(job) {
    var node = el('div', 'adm-job');
    node.setAttribute('data-id', job.id);

    var top = el('div', 'adm-job-top');
    var titleBox = el('div', 'adm-job-title');
    /* the title opens the video on YouTube */
    var link = el('a', 'adm-job-name');
    link.setAttribute('target', '_blank');
    link.setAttribute('rel', 'noopener');
    titleBox.appendChild(link);
    titleBox.appendChild(el('span', 'adm-job-url'));
    top.appendChild(titleBox);
    var badge = el('span', 'adm-badge');
    top.appendChild(badge);
    node.appendChild(top);

    var meta = el('div', 'adm-job-meta');
    var stage = el('span', 'adm-stage');
    meta.appendChild(stage);
    var pct = el('span', 'adm-pct');
    meta.appendChild(pct);
    node.appendChild(meta);

    var track = el('div', 'adm-track');
    var fill = el('div', 'adm-fill');
    track.appendChild(fill);
    node.appendChild(track);

    /* the checklist as a strip of stages */
    var strip = el('div', 'adm-stages');
    node.appendChild(strip);

    var foot = el('div', 'adm-job-foot');
    var created = el('span', 'adm-job-time');
    foot.appendChild(created);
    var actions = el('div', 'adm-job-actions');
    var cancel = el('button', 'adm-btn adm-btn-sm adm-cancel', 'لغو');
    cancel.type = 'button';
    cancel.setAttribute('data-cancel', job.id);
    actions.appendChild(cancel);
    foot.appendChild(actions);
    node.appendChild(foot);

    var err = el('div', 'adm-job-err');
    err.hidden = true;
    node.appendChild(err);

    node.__parts = {
      name: link,
      url: titleBox.querySelector('.adm-job-url'),
      badge: badge,
      stage: stage,
      pct: pct,
      fill: fill,
      created: created,
      cancel: cancel,
      err: err,
      strip: strip
    };
    return node;
  }

  /* The checklist as a strip of stages.
   * done -> a green tick, running -> a blue spinner, failed -> a red
   * warning, waiting -> an empty circle. */
  function stageMark(status) {
    if (status === 'completed') return { cls: 'done', glyph: '\u2713', label: 'کامل' };
    if (status === 'running') return { cls: 'run', glyph: '', label: 'در حال اجرا' };
    if (status === 'failed') return { cls: 'bad', glyph: '\u26A0', label: 'خطا' };
    if (status === 'skipped') return { cls: 'skip', glyph: '\u2013', label: 'رد شد' };
    if (status === 'waiting_for_review') return { cls: 'wait', glyph: '?', label: 'در انتظار بررسی' };
    if (status === 'cancelled') return { cls: 'skip', glyph: '\u2715', label: 'لغو شد' };
    return { cls: 'todo', glyph: '', label: 'در انتظار' };
  }

  function renderStageStrip(node, job) {
    var strip = node.__parts.strip;
    if (!strip) return;
    var stages = job.stages || [];
    if (!stages.length) { strip.hidden = true; return; }
    strip.hidden = false;
    clear(strip);
    stages.forEach(function (st) {
      var m = stageMark(st.status);
      var item = el('span', 'adm-stg adm-stg-' + m.cls);
      item.title = st.label_fa + ' — ' + m.label;
      item.setAttribute('aria-label', st.label_fa + ' — ' + m.label);
      if (m.cls === 'run') {
        var sp = el('i', 'adm-spin');
        item.appendChild(sp);
      } else {
        item.appendChild(el('b', null, m.glyph));
      }
      /* a failed stage can be retried on its own */
      if (m.cls === 'bad') {
        item.className += ' adm-stg-click';
        item.setAttribute('data-retry-stage', st.stage);
        item.setAttribute('data-retry-job', job.id);
        item.setAttribute('role', 'button');
        item.setAttribute('tabindex', '0');
      }
      strip.appendChild(item);
    });
    /* a failed stage: click it to retry that stage */
    Array.prototype.forEach.call(strip.querySelectorAll('[data-retry-stage]'), function (it) {
      var go = function () {
        var jobId = it.getAttribute('data-retry-job');
        var stage = it.getAttribute('data-retry-stage');
        api('stages.php', { method: 'POST',
                            body: { action: 'retry', job_id: jobId, stage: stage } })
          .then(function () { return loadJobs(); })
          .catch(function (e) { toast(String(e.message || e), 'err'); });
      };
      it.addEventListener('click', go);
      it.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); }
      });
    });
  }

  function updateJobNode(node, job) {
    var p = node.__parts;
    var name = job.title_fa || job.title_en || job.yt_id || job.id;
    p.name.textContent = name;
    /* the title opens the video on YouTube */
    p.name.href = job.watch_url || (job.yt_id ? 'https://www.youtube.com/watch?v=' + job.yt_id : '#');
    p.name.title = job.watch_url ? 'Open the video on YouTube' : '';
    p.url.textContent = job.yt_id ? ('youtube.com/watch?v=' + job.yt_id) : (job.url || '');
    p.badge.className = statusClass(job.status);
    p.badge.textContent = STATUS_LABEL[job.status] || job.status || '—';
    p.stage.textContent = stageLabel(job.stage);
    /* the checklist decides the percentage, not the rough job progress */
    var prog = job.pct;
    if (prog === undefined || prog === null) {
      prog = Math.max(0, Math.min(100, parseInt(job.progress, 10) || 0));
    }
    p.fill.style.width = prog + '%';
    p.pct.textContent = fa(prog) + '٪';
    renderStageStrip(node, job);
    p.created.textContent = job.created_at ? String(job.created_at).replace('T', ' ').slice(0, 16) : '';
    var cancellable = job.status === 'queued' || job.status === 'running';
    p.cancel.hidden = !cancellable;
    if (job.error) {
      p.err.textContent = job.error;
      p.err.hidden = false;
    } else {
      p.err.hidden = true;
    }
  }

  function renderJobs(jobs) {
    var list = $('jobsList');
    var empty = $('jobsEmpty');
    state.jobs = jobs || [];

    /* sort: active first, then newest first */
    var rank = { running: 0, queued: 1, failed: 2, done: 3, canceled: 4, skipped: 5 };
    var sorted = state.jobs.slice().sort(function (a, b) {
      var ra = rank[a.status] === undefined ? 9 : rank[a.status];
      var rb = rank[b.status] === undefined ? 9 : rank[b.status];
      if (ra !== rb) return ra - rb;
      return String(b.created_at || '').localeCompare(String(a.created_at || ''));
    });

    var seen = {};
    sorted.forEach(function (job) {
      seen[job.id] = 1;
      var node = state.jobNodes[job.id];
      if (!node) {
        node = buildJobNode(job);
        state.jobNodes[job.id] = node;
      }
      updateJobNode(node, job);
    });

    /* reconcile order + removals without re-creating nodes (no flicker) */
    Object.keys(state.jobNodes).forEach(function (id) {
      if (!seen[id]) {
        var n = state.jobNodes[id];
        if (n && n.parentNode) n.parentNode.removeChild(n);
        delete state.jobNodes[id];
      }
    });
    var frag = document.createDocumentFragment();
    sorted.forEach(function (job) {
      var node = state.jobNodes[job.id];
      if (node) frag.appendChild(node);
    });
    list.appendChild(frag);

    if (!sorted.length) {
      empty.textContent = 'هنوز کاری در صف نیست.';
      empty.hidden = false;
    } else {
      empty.hidden = true;
    }
    $('queueCount').textContent = fa(sorted.length) + ' کار';
  }

  function loadJobs() {
    if (!state.user) return Promise.resolve();
    return api('jobs.php').then(function (data) {
      renderJobs(data.jobs || []);
    }).catch(function (err) {
      if (err.status === 401) { handleSessionLost(); return; }
      /* keep the last good list; a transient poll failure is not worth a toast storm */
      console.warn('jobs poll failed:', err.message);
    });
  }

  function handleSessionLost() {
    state.user = null;
    showLogin();
    toast('نشست شما منقضی شده است. دوباره وارد شوید.', 'err');
  }

  function startPolling() {
    stopPolling();
    state.pollTimer = setInterval(function () {
      if (state.polling) return;
      if (document.hidden) return;
      state.polling = true;
      loadJobs().then(function () { state.polling = false; }, function () { state.polling = false; });
    }, POLL_MS);
  }
  function stopPolling() {
    if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
  }

  function initJobs() {
    $('jobsList').addEventListener('click', function (ev) {
      var btn = ev.target.closest ? ev.target.closest('[data-cancel]') : null;
      if (!btn) return;
      var id = btn.getAttribute('data-cancel');
      btn.disabled = true;
      api('jobs.php', { method: 'POST', body: { action: 'cancel', id: id } })
        .then(function () {
          toast('کار لغو شد.');
          loadJobs();
        })
        .catch(function (err) {
          btn.disabled = false;
          toast(err.message, 'err');
        });
    });
  }

  /* ------------------------------------------------------------------ */
  /* videos                                                             */
  /* ------------------------------------------------------------------ */
  /* The recently added videos.
   *
   * The order comes from the server: the newest record first, by the real
   * creation time. The table shows ten of them, and the search filters what
   * is already on the screen. */
  function renderVideos() {
    var body = $('videosBody');
    var empty = $('videosEmpty');
    var q = ($('videoSearch').value || '').trim().toLowerCase();
    clear(body);
    var shown = 0;
    state.videos.forEach(function (v) {
      var hay = [v.id, v.title_fa, v.title_en, v.channel].join(' ').toLowerCase();
      if (q && hay.indexOf(q) === -1) return;
      shown++;
      var tr = el('tr');
      tr.appendChild(el('td', 'adm-cell-id', v.id || '—'));
      /* The Persian panel shows both titles; the English panel shows only
         the English one — no Persian text is allowed on the .com side. */
      if (FA) {
        var tdFa = el('td', 'adm-cell-title');
        tdFa.title = v.title_fa || '';
        if (v.id) {
          var a = el('a', null, v.title_fa || '—');
          a.href = 'https://www.youtube.com/watch?v=' + encodeURIComponent(v.id);
          a.target = '_blank';
          a.rel = 'noopener noreferrer';
          tdFa.appendChild(a);
        } else {
          tdFa.appendChild(document.createTextNode(v.title_fa || '—'));
        }
        tr.appendChild(tdFa);
      }
      var tdEn = el('td', 'adm-cell-title');
      tdEn.title = v.title_en || '';
      tdEn.appendChild(document.createTextNode(v.title_en || '—'));
      tr.appendChild(tdEn);
      tr.appendChild(el('td', 'adm-c-ch', v.channel || '—'));
      var td = el('td');
      var st = v.status || '';
      td.appendChild(el('span', 'adm-badge adm-badge-other', VIDEO_STATUS_LABEL[st] || st || '—'));
      tr.appendChild(td);
      tr.appendChild(el('td', 'adm-cell-time', fmtStamp(v.created_at)));
      body.appendChild(tr);
    });
    empty.hidden = shown > 0;
    if (!shown && state.videos.length) {
      empty.textContent = VIDEO_EMPTY_SEARCH;
    } else if (!shown) {
      empty.textContent = VIDEO_EMPTY;
    }
    $('videosCount').textContent = fa(shown) + ' ' + VIDEOS_COUNT_LABEL;
  }

  /* A short timestamp. The database stores UTC. */
  function fmtStamp(s) {
    if (!s) return '—';
    var d = new Date(String(s).replace(' ', 'T') + (String(s).indexOf('Z') < 0 ? 'Z' : ''));
    if (isNaN(d.getTime())) return String(s);
    /* the Gregorian calendar in both languages, for the same reason */
    return d.toLocaleDateString('en-GB',
      { year: 'numeric', month: '2-digit', day: '2-digit' });
  }

  function loadVideos() {
    if (!state.user) return Promise.resolve();
    /* The server does the sorting and sends only the newest records. */
    return api('videos.php?recent=10').then(function (data) {
      state.videos = data.videos || [];
      renderVideos();
    }).catch(function (err) {
      if (err.status === 401) { handleSessionLost(); return; }
      toast(err.message, 'err');
    });
  }

  /* ------------------------------------------------------------------ */
  /* LLM settings                                                       */
  /* ------------------------------------------------------------------ */
  /* The model picker is drawn by models.js: it shows the capability icons,
     the context window and the usage of every model, which a native
     <select> cannot do. The list of ids is still kept here for the
     connection test. */
  function renderModelOptions() {
    if (window.npModels && window.npModels.render) window.npModels.render();
  }

  function setModels(models) {
    state.models = models || [];
    renderModelOptions();
  }

  function llmSettingsPayload() {
    var endpoint = ($('llmEndpoint').value || '').trim();
    var model = ($('llmModel').value || '').trim();
    var chatModel = ($('chatModel') ? ($('chatModel').value || '').trim() : '');
    return { endpoint: endpoint, model: model, chat_model: chatModel };
  }

  /* An untouched key field must never overwrite the stored key: the API treats
     an empty api_key as "keep what is stored". Only a newly typed key is sent. */
  function apiKeyForRequest() {
    return ($('llmKey').value || '').trim();
  }

  function initLlm() {
    $('toggleKey').addEventListener('click', function () {
      var input = $('llmKey');
      var showing = input.type === 'text';
      input.type = showing ? 'password' : 'text';
      this.textContent = showing ? 'نمایش' : 'پنهان';
    });

    /* The filter input is shared with models.js, which owns the list.
       Keep the raw value here for the connection test. */
    $('modelFilter').addEventListener('input', function () {
      state.modelFilter = this.value;
    });



    $('testBtn').addEventListener('click', function () {
      var btn = this;
      var msg = $('llmMsg');
      var payload = llmSettingsPayload();
      btn.disabled = true;
      btn.textContent = 'در حال تست…';
      msg.className = 'adm-alert';
      msg.textContent = 'در حال اتصال به endpoint…';
      msg.hidden = false;
      api('llm.php', {
        method: 'POST',
        body: { action: 'refresh_models', endpoint: payload.endpoint, api_key: apiKeyForRequest() }
      }).then(function (data) {
        var models = data.models || [];
        setModels(models);
        /* the capability metadata lives in its own table — read it again so
           the icons and the context sizes are the provider's, not stale */
        return api('models.php', { method: 'POST', body: { action: 'refresh' } })
          .then(function () { return data; });
        msg.className = 'adm-alert adm-alert-ok';
        msg.textContent = 'اتصال برقرار است — ' + fa(models.length) + ' مدل دریافت شد.';
        toast('اتصال به endpoint موفق بود.', 'ok');
      }).catch(function (err) {
        msg.className = 'adm-alert adm-alert-error';
        msg.textContent = 'اتصال ناموفق بود — ' + err.message;
        toast('تست اتصال ناموفق بود.', 'err');
      }).then(function () {
        btn.disabled = false;
        btn.textContent = 'تست اتصال';
      });
    });

    $('saveLlmBtn').addEventListener('click', function () {
      var btn = this;
      var msg = $('llmMsg');
      var payload = llmSettingsPayload();
      if (!payload.endpoint) {
        msg.className = 'adm-alert adm-alert-error';
        msg.textContent = 'آدرس endpoint را وارد کنید.';
        msg.hidden = false;
        return;
      }
      btn.disabled = true;
      btn.textContent = 'در حال ذخیره…';
      api('llm.php', { method: 'POST', body: { action: 'save', endpoint: payload.endpoint, api_key: apiKeyForRequest(), model: payload.model } })
        .then(function (data) {
          var s = data.settings || {};
          msg.className = 'adm-alert adm-alert-ok';
          msg.textContent = 'تنظیمات ذخیره شد.';
          msg.hidden = false;
          toast('تنظیمات ذخیره شد.', 'ok');
          if (s.endpoint) $('llmEndpoint').value = s.endpoint;
          if (s.model) $('llmModel').value = s.model;
    if (s.chat_model && $('chatModel')) $('chatModel').value = s.chat_model;
          if (s.has_key) {
            state.hasKey = true;
            $('keyNote').textContent = 'یک کلید ذخیره شده است. برای تغییر، کلید جدید را بنویسید؛ در غیر این صورت کلید قبلی حفظ می‌شود.';
          } else {
            state.hasKey = false;
            $('keyNote').textContent = 'کلیدی ذخیره نشده است.';
          }
        })
        .catch(function (err) {
          msg.className = 'adm-alert adm-alert-error';
          msg.textContent = 'ذخیره نشد — ' + err.message;
          toast('ذخیره تنظیمات ناموفق بود.', 'err');
        })
        .then(function () {
          btn.disabled = false;
          btn.textContent = 'ذخیره تنظیمات';
        });
    });
  }

  function loadLlm() {
    if (!state.user) return Promise.resolve();
    return api('llm.php').then(function (data) {
      var s = data.settings;
      if (s) {
        $('llmEndpoint').value = s.endpoint || 'http://localhost:20128/v1';
        if (s.model) $('llmModel').value = s.model;
    if (s.chat_model && $('chatModel')) $('chatModel').value = s.chat_model;
        state.hasKey = !!s.has_key;
        $('keyNote').textContent = s.has_key
          ? 'یک کلید ذخیره شده است. برای تغییر، کلید جدید را بنویسید؛ در غیر این صورت کلید قبلی حفظ می‌شود.'
          : 'کلیدی ذخیره نشده است.';
      } else {
        $('llmEndpoint').value = $('llmEndpoint').value || 'http://localhost:20128/v1';
      }
      if (data.models && data.models.length) setModels(data.models);
    }).catch(function (err) {
      if (err.status === 401) { handleSessionLost(); return; }
      toast(err.message, 'err');
    });
  }

  /* ------------------------------------------------------------------ */
  /* boot                                                               */
  /* ------------------------------------------------------------------ */
  /* The AI panel draws the connection state; models.js owns that panel. */
  function loadConn() {
    if (window.npModels && typeof window.npModels.renderConn === 'function') {
      window.npModels.renderConn(window.__npDash);
    }
  }

  function loadAll() {
    /* an already signed-in session still needs a token for the writes */
    api('auth.php?action=csrf').then(function (d) { setCsrf(d.csrf); }).catch(function () { });
    loadJobs();
    loadVideos();
    loadLlm();
    /* the operational modules need the session, so they load after the
       login — not on DOMContentLoaded */
    if (window.npOps) {
      window.npOps.load();
      window.npOps.loadErrors();
    }
    if (window.npModels) window.npModels.load();
  }

  /* ------------------------------------------------------------------ */
  /* ------------------------------------------------------------------ */
  var CHAT_POLL_MS = 1500;

  /* ---- /compress: summarise the session, keep the key points ---- */
  function init() {
    initLogin();
    initLogout();
    initJobs();
    initLlm();

    $('urlInput').addEventListener('input', renderDetected);
    $('addBtn').addEventListener('click', addToQueue);
    $('clearBtn').addEventListener('click', function () {
      clear($('addResults'));
      $('addSummary').hidden = true;
      $('urlInput').value = '';
      renderDetected();
    });
    $('videoSearch').addEventListener('input', renderVideos);

    renderDetected();
    $('llmEndpoint').value = 'http://localhost:20128/v1';

    /* is there an API at all? A static host answers 405 and the panel
       must say so plainly instead of failing with a raw code. */
    checkApi().then(function () {
      if (API_MISSING) {
        var box = document.getElementById('apiMissing');
        if (box) { box.textContent = apiMissingMessage(); box.hidden = false; }
      }
    });

    /* restore the session if the cookie is still alive */
    api('auth.php').then(function (data) {
      if (data.user) {
        state.user = data.user;
        showApp(data.user);
        loadAll();
      } else {
        showLogin();
      }
    }).catch(function () {
      showLogin();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
