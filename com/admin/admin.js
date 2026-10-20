/* =====================================================================
   NursePlus — Admin panel (Persian / RTL)
   Talks to the site API at ../api/*.php (same-origin, session cookie).
   ===================================================================== */
(function () {
  'use strict';

  var API_BASE = new URL('../../api/', document.baseURI).href;
  var POLL_MS = 4000;

  /* ------------------------------------------------------------------ */
  /* helpers                                                            */
  /* ------------------------------------------------------------------ */
  var FA_DIGITS = '0123456789';
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
    this.message = message || 'Something went wrong.';
    this.status = status || 0;
    this.data = data || null;
  }
  ApiError.prototype = Object.create(Error.prototype);

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
    }
    return fetch(API_BASE + file, init).then(function (res) {
      return res.text().then(function (text) {
        var data = null;
        if (text) {
          try { data = JSON.parse(text); } catch (e) { data = null; }
        }
        if (data === null) {
          throw new ApiError(
            res.ok ? 'The server sent an unreadable response.' : 'The server returned an error (code ' + res.status + ').',
            res.status, null
          );
        }
        if (!res.ok || data.ok === false) {
          var msg = data.message || '';
          if (!msg && file === 'auth.php' && res.status === 401) msg = 'Wrong email or password';
          if (!msg) msg = 'The request failed (code ' + res.status + ').';
          throw new ApiError(msg, res.status, data);
        }
        return data;
      });
    }).catch(function (err) {
      if (err instanceof ApiError) throw err;
      throw new ApiError('Could not reach the server. Check your connection.', 0, null);
    });
  }

  /* ------------------------------------------------------------------ */
  /* constants                                                          */
  /* ------------------------------------------------------------------ */
  var STAGE_LABEL = {
    discover: 'Discover',
    transcript: 'Transcript',
    translate: 'Translate',
    quiz: 'Quiz',
    publish: 'Publish'
  };
  var STATUS_LABEL = {
    queued: 'Queued',
    running: 'Running',
    done: 'Done',
    failed: 'Error',
    skipped: 'Duplicate',
    canceled: 'Cancelled'
  };
  var VIDEO_STATUS_LABEL = {
    published: 'Published',
    draft: 'Draft',
    pending: 'Pending',
    queued: 'Queued',
    running: 'Running',
    done: 'Done',
    failed: 'Error',
    skipped: 'Duplicate',
    canceled: 'Cancelled'
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
        errBox.textContent = 'Enter your email and password.';
        errBox.hidden = false;
        return;
      }
      btn.disabled = true;
      btn.textContent = 'Signing in…';
      api('auth.php', { method: 'POST', body: { action: 'login', email: em, password: pw } })
        .then(function (data) {
          state.user = data.user || null;
          pass.value = '';
          showApp(state.user);
          loadAll();
          toast('Welcome, ' + ((state.user && state.user.name) || state.user.email) + '!', 'ok');
        })
        .catch(function (err) {
          errBox.textContent = err.status === 401 ? 'Wrong email or password' : err.message;
          errBox.hidden = false;
        })
        .then(function () {
          btn.disabled = false;
          btn.textContent = 'Sign in';
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
          toast('Signed out.');
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
    var label = fa(uniq) + ' links detected';
    if (bad) label += ' · ' + fa(bad) + ' invalid item';
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
      toast('No links entered.', 'err');
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
            message: 'This link is a duplicate', note: 'The same link appears twice above.'
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
    btn.textContent = 'Checking…';

    Promise.all(toCheck.map(function (r) {
      return api('videos.php?check=' + encodeURIComponent(r.ytId))
        .then(function (d) {
          if (!d.duplicate) return;
          r.state = 'duplicate';
          r.message = 'This link is a duplicate';
          r.note = d.reason === 'already_queued'
            ? 'It is already in the pipeline queue.'
            : 'It is already published on the site.';
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
                r.message = 'Added to the queue';
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
                r.message = s.message || 'Not a valid YouTube link';
              } else {
                r.state = 'duplicate';
                r.message = 'This link is a duplicate';
                r.note = s.reason === 'already_queued'
                  ? 'It is already in the pipeline queue.'
                  : 'It is already published on the site.';
              }
              break;
            }
          });

          rows.forEach(function (r) {
            if (r.state === 'pending') {
              r.state = 'invalid';
              r.message = 'Not added — no valid link was detected.';
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
      btn.textContent = 'Add to queue';
    });
  }

  function renderResults(rows, summary) {
    var box = $('addResults');
    clear(box);
    var added = 0, dup = 0, bad = 0;
    rows.forEach(function (r) {
      if (r.state === 'added') {
        added++;
        box.appendChild(resultRow('ok', 'Added', r.message, r.raw !== r.url ? r.raw : r.url));
      } else if (r.state === 'duplicate') {
        dup++;
        var li = resultRow('warn', 'Duplicate', r.message, r.raw);
        if (r.note) li.querySelector('.adm-res-txt').appendChild(el('div', 'adm-res-note', r.note));
        box.appendChild(li);
      } else {
        bad++;
        box.appendChild(resultRow('err', 'Invalid', r.message, r.raw));
      }
    });
    if (rows.length) {
      summary.textContent = fa(added) + ' added · ' + fa(dup) + ' duplicate · ' + fa(bad) + ' invalid';
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
    titleBox.appendChild(el('span', 'adm-job-name'));
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

    var foot = el('div', 'adm-job-foot');
    var created = el('span', 'adm-job-time');
    foot.appendChild(created);
    var actions = el('div', 'adm-job-actions');
    var cancel = el('button', 'adm-btn adm-btn-sm adm-cancel', 'Cancel');
    cancel.type = 'button';
    cancel.setAttribute('data-cancel', job.id);
    actions.appendChild(cancel);
    foot.appendChild(actions);
    node.appendChild(foot);

    var err = el('div', 'adm-job-err');
    err.hidden = true;
    node.appendChild(err);

    node.__parts = {
      name: titleBox.querySelector('.adm-job-name'),
      url: titleBox.querySelector('.adm-job-url'),
      badge: badge,
      stage: stage,
      pct: pct,
      fill: fill,
      created: created,
      cancel: cancel,
      err: err
    };
    return node;
  }

  function updateJobNode(node, job) {
    var p = node.__parts;
    var name = job.title_en || job.title_fa || job.url || job.yt_id || job.id;
    p.name.textContent = name;
    p.url.textContent = job.url || job.yt_id || '';
    p.badge.className = statusClass(job.status);
    p.badge.textContent = STATUS_LABEL[job.status] || job.status || '—';
    p.stage.textContent = stageLabel(job.stage);
    var prog = Math.max(0, Math.min(100, parseInt(job.progress, 10) || 0));
    p.fill.style.width = prog + '%';
    p.pct.textContent = fa(prog) + '%';
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
      empty.textContent = 'Nothing in the queue yet.';
      empty.hidden = false;
    } else {
      empty.hidden = true;
    }
    $('queueCount').textContent = fa(sorted.length) + ' jobs';
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
    toast('Your session expired. Please sign in again.', 'err');
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
          toast('Job cancelled.');
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
      tr.appendChild(el('td', 'adm-c-id', v.id || '—'));
      tr.appendChild(el('td', 'adm-c-fa', v.title_fa || '—'));
      tr.appendChild(el('td', 'adm-c-en', v.title_en || '—'));
      tr.appendChild(el('td', 'adm-c-ch', v.channel || '—'));
      var td = el('td');
      var st = v.status || '';
      var badge = el('span', 'adm-badge adm-badge-other', VIDEO_STATUS_LABEL[st] || st || '—');
      td.appendChild(badge);
      tr.appendChild(td);
      body.appendChild(tr);
    });
    empty.hidden = shown > 0;
    if (!shown && state.videos.length) {
      empty.textContent = 'No video matches that search.';
    } else if (!shown) {
      empty.textContent = 'No videos to show.';
    }
    $('videosCount').textContent = fa(shown) + ' videos';
  }

  function loadVideos() {
    if (!state.user) return Promise.resolve();
    return api('videos.php').then(function (data) {
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
  function renderModelOptions() {
    var sel = $('modelSelect');
    var filter = (state.modelFilter || '').trim().toLowerCase();
    var list = state.models;
    if (filter) {
      list = list.filter(function (m) { return String(m.id).toLowerCase().indexOf(filter) !== -1; });
    }
    clear(sel);
    var frag = document.createDocumentFragment();
    /* a native <select> handles ~600 options without lag; the filter is what
       keeps the list short while the user types */
    list.forEach(function (m) {
      var opt = el('option', null, m.id);
      opt.value = m.id;
      if (m.owned_by) opt.title = m.owned_by;
      frag.appendChild(opt);
    });
    sel.appendChild(frag);
    if (!list.length) {
      var none = el('option', null, filter ? 'nothing found' : 'The model list is empty');
      none.value = '';
      sel.appendChild(none);
    }
    var total = state.models.length;
    var note = total ? fa(total) + ' model' : '';
    if (filter) note += ' · ' + fa(list.length) + ' Result';
    $('modelCount').textContent = note;
  }

  function setModels(models) {
    state.models = models || [];
    renderModelOptions();
  }

  function llmSettingsPayload() {
    var endpoint = ($('llmEndpoint').value || '').trim();
    var model = ($('llmModel').value || '').trim();
    return { endpoint: endpoint, model: model };
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
      this.textContent = showing ? 'Show' : 'Hide';
    });

    $('modelFilter').addEventListener('input', function () {
      /* Render synchronously: filling a <select> with ~600 options costs a
         couple of milliseconds, and a debounce timer is clamped to 1s in a
         backgrounded tab — which would freeze the list for the user. */
      state.modelFilter = this.value;
      renderModelOptions();
    });

    $('modelSelect').addEventListener('change', function () {
      if (this.value) $('llmModel').value = this.value;
    });

    $('testBtn').addEventListener('click', function () {
      var btn = this;
      var msg = $('llmMsg');
      var payload = llmSettingsPayload();
      btn.disabled = true;
      btn.textContent = 'Testing…';
      msg.className = 'adm-alert';
      msg.textContent = 'Connecting to the endpoint…';
      msg.hidden = false;
      api('llm.php', {
        method: 'POST',
        body: { action: 'refresh_models', endpoint: payload.endpoint, api_key: apiKeyForRequest() }
      }).then(function (data) {
        var models = data.models || [];
        setModels(models);
        msg.className = 'adm-alert adm-alert-ok';
        msg.textContent = 'Connected — ' + fa(models.length) + ' models received.';
        toast('The endpoint answered.', 'ok');
      }).catch(function (err) {
        msg.className = 'adm-alert adm-alert-error';
        msg.textContent = 'Connection failed — ' + err.message;
        toast('Connection test failed.', 'err');
      }).then(function () {
        btn.disabled = false;
        btn.textContent = 'Test connection';
      });
    });

    $('saveLlmBtn').addEventListener('click', function () {
      var btn = this;
      var msg = $('llmMsg');
      var payload = llmSettingsPayload();
      if (!payload.endpoint) {
        msg.className = 'adm-alert adm-alert-error';
        msg.textContent = 'Enter an endpoint URL.';
        msg.hidden = false;
        return;
      }
      btn.disabled = true;
      btn.textContent = 'Saving…';
      api('llm.php', { method: 'POST', body: { action: 'save', endpoint: payload.endpoint, api_key: apiKeyForRequest(), model: payload.model } })
        .then(function (data) {
          var s = data.settings || {};
          msg.className = 'adm-alert adm-alert-ok';
          msg.textContent = 'Settings saved.';
          msg.hidden = false;
          toast('Settings saved.', 'ok');
          if (s.endpoint) $('llmEndpoint').value = s.endpoint;
          if (s.model) $('llmModel').value = s.model;
          if (s.has_key) {
            state.hasKey = true;
            $('keyNote').textContent = 'A key is stored. Type a new one to change it; otherwise the stored key is kept.';
          } else {
            state.hasKey = false;
            $('keyNote').textContent = 'No key stored yet.';
          }
        })
        .catch(function (err) {
          msg.className = 'adm-alert adm-alert-error';
          msg.textContent = 'Not saved — ' + err.message;
          toast('Could not save the settings.', 'err');
        })
        .then(function () {
          btn.disabled = false;
          btn.textContent = 'Save settings';
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
        state.hasKey = !!s.has_key;
        $('keyNote').textContent = s.has_key
          ? 'A key is stored. Type a new one to change it; otherwise the stored key is kept.'
          : 'No key stored yet.';
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
  function loadAll() {
    loadJobs();
    loadVideos();
    loadLlm();
  }

  /* ------------------------------------------------------------------ */
  /* chat — the assistant                                               */
  /* ------------------------------------------------------------------ */
  /* The panel queues a chat job; scripts/pipeline_worker.py picks it up,
     runs it and writes the answer back as chat_messages. The browser only
     sends and polls — the heavy lifting never happens in the page. */
  var CHAT_POLL_MS = 1500;
  var chat = { jobId: null, seen: 0, timer: null, busy: false, file: null };

  function chatStatus(text, kind) {
    var box = $('chatStatus');
    if (!box) return;
    if (!text) { box.hidden = true; return; }
    box.hidden = false;
    box.textContent = text;
    box.className = 'adm-chat-status' + (kind ? ' ' + kind : '');
  }

  function chatScroll() {
    var log = $('chatLog');
    if (log) log.scrollTop = log.scrollHeight;
  }

  function chatBubble(role, text) {
    var box = el('div', 'adm-msg adm-msg-' + (role === 'user' ? 'user' : 'agent'));
    var head = el('div', 'adm-msg-head');
    head.appendChild(el('span', null, role === 'user' ? 'You' : 'Assistant'));
    box.appendChild(head);
    box.appendChild(el('div', 'adm-msg-body', text || ''));
    return box;
  }

  function chatRender(messages) {
    var log = $('chatLog');
    if (!log) return;
    if (!messages.length) return;
    $('chatEmpty').hidden = true;
    for (var i = chat.seen; i < messages.length; i++) {
      var m = messages[i] || {};
      var text = m.text || '';
      if (m.file_name && text.indexOf(m.file_name) === -1) {
        text = '📎 ' + m.file_name + (text ? '\n' + text : '');
      }
      log.appendChild(chatBubble(m.role, text));
    }
    chat.seen = messages.length;
    chatScroll();
  }

  function chatPoll() {
    if (!chat.jobId) return;
    api('chat.php?job_id=' + encodeURIComponent(chat.jobId)).then(function (data) {
      chatRender(data.messages || []);
      return api('jobs.php');
    }).then(function (d) {
      var job = null;
      (d.jobs || []).forEach(function (j) { if (j.id === chat.jobId) job = j; });
      if (!job) return;
      if (job.status === 'done') {
        chat.busy = false; chat.jobId = null;
        chatStatus('Done.', null);
        if (chat.timer) { clearInterval(chat.timer); chat.timer = null; }
      } else if (job.status === 'failed') {
        chat.busy = false; chat.jobId = null;
        chatStatus('Error: ' + (job.error || 'failed'), 'err');
        if (chat.timer) { clearInterval(chat.timer); chat.timer = null; }
      } else if (job.status === 'canceled') {
        chat.busy = false; chat.jobId = null;
        chatStatus('Cancelled.', 'err');
        if (chat.timer) { clearInterval(chat.timer); chat.timer = null; }
      } else {
        chatStatus('Working — stage: ' + stageLabel(job.stage) + ' (' + fa(job.progress || 0) + '%)');
      }
    }).catch(function (e) {
      chat.busy = false;
      chatStatus('Lost the connection to the server: ' + e.message, 'err');
    });
  }

  function chatSend() {
    if (chat.busy) { toast('A job is already running; give it a moment.', 'warn'); return; }
    var input = $('chatInput');
    var text = (input.value || '').trim();
    var file = chat.file;
    if (!text && !file) { toast('A message or a file is required.', 'warn'); return; }

    chat.busy = true;
    chat.seen = 0;
    chat.jobId = null;
    chatStatus('Sending…');

    var p;
    if (file) {
      var fd = new FormData();
      fd.append('file', file);
      if (text) fd.append('message', text);
      p = fetch(API_BASE + 'chat.php', {
        method: 'POST', credentials: 'same-origin', body: fd
      }).then(function (res) {
        return res.text().then(function (t) {
          var data = null;
          try { data = JSON.parse(t); } catch (e) { data = null; }
          if (!data || data.ok === false) {
            throw new ApiError((data && data.message) || 'The upload failed.', res.status, data);
          }
          return data;
        });
      });
    } else {
      p = api('chat.php', { method: 'POST', body: { action: 'send', message: text } });
    }

    p.then(function (d) {
      chat.jobId = d.job_id;
      input.value = '';
      chat.file = null;
      $('chatFileName').textContent = '';
      clear($('chatLog'));
      chatScroll();
      chatPoll();
      if (chat.timer) clearInterval(chat.timer);
      chat.timer = setInterval(chatPoll, CHAT_POLL_MS);
    }).catch(function (e) {
      chat.busy = false;
      chatStatus('Could not send: ' + e.message, 'err');
      toast('Could not send: ' + e.message, 'error');
    });
  }

  function chatSetFile(file) {
    if (!file) return;
    chat.file = file;
    $('chatFileName').textContent = '📎 ' + file.name + ' (' + Math.max(1, Math.round(file.size / 1024)) + ' KB)';
  }

  function initChat() {
    var input = $('chatInput');
    var drop = $('chatDrop');
    var picker = $('chatFile');
    if (!input || !drop || !picker) return;

    $('chatSend').addEventListener('click', chatSend);
    input.addEventListener('keydown', function (e) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); chatSend(); }
    });

    $('chatPick').addEventListener('click', function () { picker.click(); });
    picker.addEventListener('change', function () { chatSetFile(picker.files && picker.files[0]); });

    ['dragenter', 'dragover'].forEach(function (ev) {
      drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add('over'); });
    });
    ['dragleave', 'drop'].forEach(function (ev) {
      drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove('over'); });
    });
    drop.addEventListener('drop', function (e) {
      var dt = e.dataTransfer;
      if (dt && dt.files && dt.files.length) {
        chatSetFile(dt.files[0]);
        /* the browser must not navigate to the dropped file */
        e.preventDefault();
      }
    });
  }

  function init() {
    initLogin();
    initLogout();
    initJobs();
    initLlm();
    initChat();

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
