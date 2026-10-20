/* NursePlus admin — dashboard, stage checklist, error centre, content audit
 * and the activity log.
 *
 * Same rules as models.js: the language comes from <html lang>, every number
 * comes from a real query, and no control is decorative.
 */
(function () {
  'use strict';

  var LANG = (document.documentElement.lang || 'fa').toLowerCase() === 'en' ? 'en' : 'fa';

  var T = {
    en: {
      dashboard: 'Dashboard', totalVideos: 'Total videos', published: 'Published',
      draft: 'Draft', withQuiz: 'With a quiz', withSubs: 'With a transcript',
      awaiting: 'Awaiting review', queued: 'Queued', running: 'Running',
      done: 'Done', failed: 'Failed', stuck: 'Stuck', aiStatus: 'AI connection status',
      reachable: 'Connected', unreachable: 'Unreachable', unknown: 'Unknown', modelCount: 'models',
      lastUpdate: 'Last updated', recentErrors: 'Recent errors', recentActions: 'Recent actions',
      checklist: 'Processing checklist', noJob: 'Select a job to see its checklist.',
      stage: 'Stage', status: 'Status', attempts: 'Attempts', started: 'Started',
      finished: 'Finished', model: 'Model', tokens: 'Tokens', retry: 'Retry',
      cancel: 'Cancel', skipped: 'Skipped', pending: 'Pending', completed: 'Completed',
      error: 'Error', retryable: 'Retryable', notRetryable: 'Not retryable',
      waiting_review: 'Awaiting review', cancelled: 'Cancelled',
      details: 'Details',
      details: 'Details',
      errorCenter: 'Error centre', fixBug: 'Fix bug', resolve: 'Resolve', ignore: 'Ignore',
      category: 'Category', severity: 'Severity', attempts2: 'Attempts', fixState: 'Fix state',
      noErrors: 'No error has been recorded.', proposed: 'Proposed', tested: 'Tested',
      testFailed: 'Test failed', approved: 'Approved', rejected: 'Rejected', applied: 'Applied',
      diff: 'The patch', noDiff: 'There is no change to show.', checks: 'Checks',
      passed: 'Passed', failed: 'Failed', propose: 'Propose a fix', risk: 'Risk',
      high: 'High', low: 'Low', forbidden: 'Forbidden', approve: 'Approve and apply',
      audit: 'Content audit', runAudit: 'Run the audit', findings: 'findings',
      evidence: 'Evidence', recommended: 'Recommended action', noIssues: 'No problem was found.',
      activity: 'Activity log', action: 'Action', target: 'Target', actor: 'Actor', time: 'Time',
      refresh: 'Refresh', nothing: 'There is nothing to show.', job: 'Job',
      fixNote: 'A proposed fix is built and tested in a separate copy; it is not applied to the live code.',
      approveNote: 'Approving this proposal applies it to the real code.'
    }
  };
  function t(k) { return (T[LANG] && T[LANG][k]) || k; }
  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function plain(n) { return Number(n || 0).toLocaleString(LANG === 'en' ? 'en-US' : 'fa-IR'); }
  function apiRoot() {
    var u = new URL(document.baseURI);
    var p = u.pathname.replace(/\/admin\/[^/]*$/, '/').replace(/\/com\/$/, '/');
    if (p.charAt(0) !== '/') p = '/' + p;
    return u.origin + p + 'api/';
  }
  var API = apiRoot();

  function api(path, body) {
    var headers = body ? { 'Content-Type': 'application/json' } : {};
    if (body && window.__npCsrf) headers['X-CSRF-Token'] = window.__npCsrf;
    return fetch(API + path, {
      method: body ? 'POST' : 'GET', credentials: 'same-origin',
      headers: headers, body: body ? JSON.stringify(body) : undefined
    }).then(function (r) {
      return r.text().then(function (txt) {
        var d = null;
        try { d = JSON.parse(txt); } catch (e) { d = null; }
        if (!r.ok || !d || d.ok === false) {
          var msg = (d && (d.message || d.error)) || ('HTTP ' + r.status);
          var err = new Error(msg);
          err.status = r.status;
          err.data = d;
          throw err;
        }
        return d;
      });
    });
  }

  var S = { dash: null, jobId: '', stages: [], errors: [], issues: [], patches: [] };

  /* ------------------------------------------------------- the dashboard */
  /* ------------------------------------------------------- the dashboard */
  function renderDash() {
    var box = document.getElementById('dashBody');
    if (!box || !S.dash) return;
    var d = S.dash, v = d.videos || {}, j = d.jobs || {}, l = d.llm || {};

    /* Small metric cards. Every number is a real count from the database. */
    var stat = function (key, val, cls) {
      return '<div class="adm-dstat' + (cls ? ' adm-dstat-' + cls : '') + '">'
        + '<span>' + esc(t(key)) + '</span><b dir="ltr">' + esc(val) + '</b></div>';
    };
    var html = '<div class="adm-dgrid">'
      + stat('totalVideos', plain(v.videos))
      + stat('published', plain(v.published), 'ok')
      + stat('draft', plain(v.draft))
      + stat('withQuiz', plain(v.with_quiz))
      + stat('withSubs', plain(v.with_transcript))
      + stat('awaiting', plain((d.review || {}).awaiting))
      + stat('queued', plain(j.queued))
      + stat('running', plain(j.running), 'run')
      + stat('done', plain(j.done), 'ok')
      + stat('failed', plain(j.failed), 'bad')
      + stat('stuck', plain((j.stuck || []).length), 'bad')
      + '</div>';

    /* The AI connection, as it actually is. A stored URL proves nothing, so
       the state comes from the last real check. */
    var conn = 'warn', label = t('unknown');
    if (l.reachable === true) { conn = 'ok'; label = t('reachable'); }
    else if (l.reachable === false) { conn = 'bad'; label = t('unreachable'); }
    var meta = [];
    if (l.model_count) meta.push(plain(l.model_count) + ' ' + t('modelCount'));
    if (l.model) meta.push(l.model);
    if (l.checked_at) meta.push(t('lastUpdate') + ': ' + l.checked_at);
    html += '<div class="adm-conn ' + conn + '"><span class="adm-dot"></span>'
      + '<b>' + esc(t('aiStatus')) + ': ' + esc(label) + '</b>'
      + '<span class="adm-conn-meta" dir="ltr">' + esc(meta.join(' · ')) + '</span></div>';
    if (l.reachable === false && l.error) {
      html += '<div class="adm-alert adm-alert-error">' + esc(l.error) + '</div>';
    }

    /* Three recent errors, newest first, and a way into the Error Centre. */
    var errs = d.recent_errors || [];
    html += '<div class="adm-dsec"><h4>' + esc(t('recentErrors')) + '</h4>';
    if (!errs.length) {
      html += '<div class="adm-dsec-empty">' + esc(t('noErrors')) + '</div>';
    } else {
      html += '<ul class="adm-dlist">' + errs.map(function (e) {
        var kind = e.severity === 'error' ? 'bad' : 'warn';
        var who = e.job_id || e.yt_id || '';
        return '<li>'
          + '<span class="adm-dl-kind ' + kind + '">' + esc(e.category || 'other') + '</span>'
          + '<span class="adm-dl-main" title="' + esc(e.message || '') + '">'
          + esc(e.stage ? e.stage + ' — ' : '') + esc(e.message || '') + '</span>'
          + '<span class="adm-dl-meta" dir="ltr">' + esc(who) + '</span>'
          + '<span class="adm-dl-meta">' + esc(fmtTime(e.created_at)) + '</span>'
          + '</li>';
      }).join('') + '</ul>';
    }
    html += '</div>';

    /* Three recent actions — the administrative history, not the errors. */
    var acts = d.recent_actions || [];
    html += '<div class="adm-dsec"><h4>' + esc(t('recentActions')) + '</h4>';
    if (!acts.length) {
      html += '<div class="adm-dsec-empty">' + esc(t('nothing')) + '</div>';
    } else {
      html += '<ul class="adm-dlist">' + acts.map(function (a) {
        return '<li>'
          + '<span class="adm-dl-kind">' + esc(a.action || '') + '</span>'
          + '<span class="adm-dl-main" title="' + esc(a.target || '') + '">'
          + esc(a.target || '') + (a.detail ? ' — ' + esc(a.detail) : '') + '</span>'
          + '<span class="adm-dl-meta">' + esc(a.actor || '') + '</span>'
          + '<span class="adm-dl-meta">' + esc(fmtTime(a.created_at)) + '</span>'
          + '</li>';
      }).join('') + '</ul>';
    }
    html += '</div>';

    box.innerHTML = html;
  }

  /* A short, local timestamp. The database stores UTC. */
  function fmtTime(s) {
    if (!s) return '';
    var d = new Date(String(s).replace(' ', 'T') + (String(s).indexOf('Z') < 0 ? 'Z' : ''));
    if (isNaN(d.getTime())) return String(s);
    /* The Gregorian calendar, in both languages: a Jalali date in one
       place and a Gregorian date in the next is worse than either one. */
    return d.toLocaleString(LANG === 'en' ? 'en-GB' : 'en-GB',
      { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  }

  function loadDash() {
    return api('dashboard.php').then(function (d) {
      S.dash = d;
      /* the AI panel reads the connection state from here */
      window.__npDash = d;
      renderDash();
    }).catch(function () { });
  }

  /* ------------------------------------------------- the stage checklist */
  var STATUS_CLASS = {
    completed: 'ok', failed: 'bad', running: 'run', skipped: 'skip',
    pending: 'wait', waiting_for_review: 'warn', cancelled: 'skip'
  };
  function stageLabel(st) {
    var m = { url_validate: 'URL validation', identify: 'Identification and metadata',
      transcript: 'Transcript acquisition', stt: 'Speech to text', cleanup: 'Transcript cleanup',
      extract_en: 'English content', translate_fa: 'Persian translation',
      title_fa: 'Persian title', title_en: 'English title', seo: 'SEO metadata',
      qc: 'Quality check', quiz: 'Quiz generation', quiz_validate: 'Quiz validation',
      terminology: 'Terminology check', persist: 'Persistence', consistency: 'Consistency check',
      publish: 'Publication' };
    if (LANG === 'en') return m[st] || st;
    
    return f[st] || st;
  }
  /* ---------------------------------------------------- the error centre */
  function renderErrors() {
    var box = document.getElementById('errorsBody');
    if (!box) return;
    if (!S.errors.length) {
      box.innerHTML = '<div class="adm-err-empty">' + esc(t('noErrors')) + '</div>';
      return;
    }
    /* One compact row per error. The technical detail — the stack trace —
       lives in its own expandable box, so a long trace never breaks the
       layout. */
    var html = '';
    S.errors.forEach(function (e) {
      var sev = e.severity === 'error' ? 'bad' : 'warn';
      var who = e.job_id || e.yt_id || '';
      html += '<div class="adm-err adm-err-' + sev + '" data-err="' + esc(e.id) + '">'
        + '<div class="adm-err-main">'
        + '<div class="adm-err-title">'
        + '<span class="adm-dl-kind ' + sev + '">' + esc(e.category || 'other') + '</span> '
        + esc(e.severity || 'error') + '</div>'
        + '<div class="adm-err-msg">' + esc(e.message || '') + '</div>'
        + '<div class="adm-err-meta">'
        + (e.stage ? esc(e.stage) + ' · ' : '')
        + (who ? '<span dir="ltr">' + esc(who) + '</span> · ' : '')
        + esc(fmtTime(e.created_at))
        + (e.fix_state && e.fix_state !== 'none' ? ' · ' + esc(e.fix_state) : '')
        + '</div>'
        + (e.detail ? '<details class="adm-err-detail"><summary>' + esc(t('details'))
            + '</summary><pre>' + esc(e.detail) + '</pre></details>' : '')
        + '</div>'
        + '<div class="adm-err-side">'
        + '<button type="button" class="adm-btn adm-btn-ghost adm-btn-sm" data-fix="' + esc(e.id) + '">'
        + esc(t('fixBug')) + '</button>'
        + '</div>'
        + '</div>';
    });
    box.innerHTML = html;
    Array.prototype.forEach.call(box.querySelectorAll('[data-fix]'), function (b) {
      b.addEventListener('click', function () { openFix(b.getAttribute('data-fix')); });
    });
  }
  function loadErrors() {
    return api('errors.php?action=list&limit=50').then(function (d) {
      S.errors = d.errors || []; renderErrors();
    }).catch(function () { });
  }

  /* ------------------------------------------------------- the fix flow */
  function openFix(errorId) {
    var box = document.getElementById('fixPanel');
    if (!box) return;
    box.hidden = false;
    box.innerHTML = '<div class="adm-empty">…</div>';
    api('errors.php?action=detail&id=' + encodeURIComponent(errorId)).then(function (d) {
      var e = d.error || {}, patches = d.patches || [];
      var html = '<div class="adm-det-head"><h3>' + esc(t('fixBug')) + '</h3>'
        + '<button type="button" class="adm-x" id="fixClose">×</button></div>'
        + '<div class="adm-fixerr">' + esc(e.message || '') + '</div>'
        + '<p class="adm-note">' + esc(t('fixNote')) + '</p>';
      if (patches.length) {
        patches.forEach(function (p) {
          var checks = {};
          try { checks = JSON.parse(p.checks || '{}'); } catch (e2) { checks = {}; }
          html += '<div class="adm-fixp"><b>' + esc(p.title) + '</b>'
            + '<span class="adm-efix">' + esc(p.status) + ' · ' + esc(t('risk')) + ': ' + esc(p.risk) + '</span>'
            + '<pre class="adm-diff">' + esc(p.diff || t('noDiff')) + '</pre>'
            + '<div class="adm-fixchecks">' + Object.keys(checks).map(function (k) {
              return '<span class="' + (checks[k] ? 'ok' : 'bad') + '">' + esc(k) + ': '
                + (checks[k] ? esc(t('passed')) : esc(t('failed'))) + '</span>';
            }).join('') + '</div>';
          if (p.status === 'tested' && p.risk !== 'high') {
            html += '<div class="adm-actions"><button type="button" class="adm-btn adm-btn-primary adm-btn-sm"'
              + ' data-approve="' + esc(p.id) + '">' + esc(t('approve')) + '</button></div>';
          }
          html += '</div>';
        });
      } else {
        html += '<div class="adm-empty">' + esc(t('noDiff')) + '</div>';
      }
      box.innerHTML = html;
      var close = document.getElementById('fixClose');
      if (close) close.addEventListener('click', function () { box.hidden = true; });
      Array.prototype.forEach.call(box.querySelectorAll('[data-approve]'), function (b) {
        b.addEventListener('click', function () {
          if (!window.confirm(t('approveNote'))) return;
          b.disabled = true;
          api('fixbug.php', { action: 'approve', id: b.getAttribute('data-approve') })
            .then(function () { return openFix(errorId); })
            .catch(function (e) { window.alert(String(e.message || e)); b.disabled = false; });
        });
      });
    }).catch(function (e) {
      box.innerHTML = '<div class="adm-alert adm-alert-error">' + esc(String(e.message || e)) + '</div>';
    });
  }

  /* ------------------------------------------------------ the content audit */
  function renderAudit() {
    var box = document.getElementById('auditBody');
    if (!box) return;
    if (!S.issues.length) {
      box.innerHTML = '<div class="adm-err-empty">' + esc(t('noIssues')) + '</div>';
      return;
    }
    /* One compact row per finding. The long recommendation text is the same
       for many findings, so it sits in an expandable box instead of being
       repeated in every row. The finding itself stays attached to its
       video. */
    var html = '';
    S.issues.forEach(function (i) {
      var sev = i.severity === 'error' ? 'bad' : 'warn';
      html += '<div class="adm-audit" data-issue="' + esc(i.id) + '">'
        + '<div class="adm-audit-main">'
        + '<div class="adm-audit-title">'
        + '<span class="adm-dl-kind ' + sev + '">' + esc(i.category || '') + '</span> '
        + esc(i.severity || '') + '</div>'
        + '<div class="adm-audit-msg">' + esc(i.evidence || '') + '</div>'
        + '<div class="adm-audit-msg" dir="ltr">' + esc(i.yt_id || i.video_id || '') + '</div>'
        + (i.recommended ? '<details class="adm-audit-why"><summary>' + esc(t('recommended'))
            + '</summary>' + esc(i.recommended) + '</details>' : '')
        + '</div>'
        + '<div class="adm-audit-side">'
        + '<button type="button" class="adm-btn adm-btn-ghost adm-btn-sm" data-resolve="' + esc(i.id) + '">'
        + esc(t('resolve')) + '</button>'
        + '</div>'
        + '</div>';
    });
    box.innerHTML = html;
    Array.prototype.forEach.call(box.querySelectorAll('[data-resolve]'), function (b) {
      b.addEventListener('click', function () {
        b.disabled = true;
        api('audit.php', { action: 'resolve', id: b.getAttribute('data-resolve') })
          .then(function () { return loadAudit(); })
          .catch(function (e) { window.alert(String(e.message || e)); b.disabled = false; });
      });
    });
  }

  function loadAudit() {
    return api('audit.php?action=list&limit=100').then(function (d) {
      S.issues = d.issues || []; renderAudit();
    }).catch(function () { });
  }

  /* ------------------------------------------------------ the activity log */
  function loadActivity() {
    return api('dashboard.php').then(function (d) {
      var box = document.getElementById('activityBody');
      if (!box) return;
      var rows = (d.recent_actions || []);
      if (!rows.length) { box.innerHTML = '<div class="adm-empty">' + esc(t('nothing')) + '</div>'; return; }
      box.innerHTML = '<div class="adm-atable">'
        + rows.map(function (a) {
          return '<div class="adm-arow"><span class="adm-aact">' + esc(a.action) + '</span>'
            + '<span class="adm-atgt" dir="ltr">' + esc(a.target || '') + '</span>'
            + '<span class="adm-aact">' + esc(a.actor || '') + '</span>'
            + '<span class="adm-atime" dir="ltr">' + esc(a.created_at || '') + '</span></div>';
        }).join('') + '</div>';
    }).catch(function () { });
  }

  /* ----------------------------------------------------------------- init */
  function init() {
    var rb = document.getElementById('dashRefresh');
    if (rb) rb.addEventListener('click', function () { loadDash(); loadActivity(); });
    var re = document.getElementById('errorsRefresh');
    if (re) re.addEventListener('click', function () { loadErrors(); });
    var ra = document.getElementById('auditRun');
    if (ra) ra.addEventListener('click', function () {
      ra.disabled = true;
      api('audit.php', { action: 'run' }).then(function () { return loadAudit(); })
        .catch(function (e) { window.alert(String(e.message || e)); })
        .then(function () { ra.disabled = false; });
    });
    var rl = document.getElementById('activityRefresh');
    if (rl) rl.addEventListener('click', function () { loadActivity(); });
    /* these need the session — the panel calls them again after the login */
    var signedIn = document.getElementById('appView') && !document.getElementById('appView').hidden;
    if (signedIn) { loadDash(); loadErrors(); loadAudit(); loadActivity(); }
    setInterval(function () { if (!document.hidden) { loadDash(); loadErrors(); } }, 20000);
  }

  /** The job list for the checklist picker. */

  /** Everything the operational modules need, after the session exists. */
  function loadAll() {
    loadDash();
    loadErrors();
    loadAudit();
    loadActivity();
  }

  window.npOps = {
    load: loadAll, loadAll: loadAll, loadErrors: loadErrors,
    loadAudit: loadAudit, loadActivity: loadActivity
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
