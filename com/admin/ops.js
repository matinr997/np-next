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
    fa: {
      dashboard: 'داشبورد', totalVideos: 'کل ویدیوها', published: 'منتشرشده',
      draft: 'پیش‌نویس', withQuiz: 'دارای آزمون', withSubs: 'دارای زیرنویس',
      awaiting: 'در انتظار بررسی', queued: 'در صف', running: 'در حال اجرا',
      done: 'انجام‌شده', failed: 'ناموفق', stuck: 'گیرکرده', aiStatus: 'وضعیت اتصال هوش مصنوعی',
      reachable: 'متصل', unreachable: 'قطع', unknown: 'نامشخص', modelCount: 'مدل',
      lastUpdate: 'آخرین به‌روزرسانی', recentErrors: 'خطاهای اخیر', recentActions: 'اقدامات اخیر',
      checklist: 'چک‌لیست پردازش', noJob: 'کاری را انتخاب کنید تا چک‌لیست آن را ببینید.',
      stage: 'مرحله', status: 'وضعیت', attempts: 'تعداد تلاش', started: 'شروع',
      finished: 'پایان', model: 'مدل', tokens: 'توکن', retry: 'تلاش دوباره',
      cancel: 'لغو', skipped: 'رد شد', pending: 'در انتظار', completed: 'کامل',
      error: 'خطا', retryable: 'قابل تلاش', notRetryable: 'غیرقابل تلاش',
      waiting_review: 'در انتظار بررسی', cancelled: 'لغو شد',
      errorCenter: 'مرکز خطا', fixBug: 'رفع باگ', resolve: 'حل‌شده', ignore: 'نادیده',
      category: 'دسته', severity: 'شدت', attempts2: 'تلاش‌ها', fixState: 'وضعیت رفع',
      noErrors: 'خطایی ثبت نشده است.', proposed: 'پیشنهاد شده', tested: 'تست‌شده',
      testFailed: 'تست ناموفق', approved: 'تأییدشده', rejected: 'ردشده', applied: 'اعمال‌شد',
      diff: 'تغییرات', noDiff: 'تغییری برای نمایش نیست.', checks: 'بررسی‌ها',
      passed: 'قبول', failed: 'مردود', propose: 'ساخت پیشنهاد', risk: 'ریسک',
      high: 'بالا', low: 'پایین', forbidden: 'ممنوع', approve: 'تأیید و اعمال',
      audit: 'بررسی محتوا', runAudit: 'اجرای بررسی', findings: 'یافته',
      evidence: 'شاهد', recommended: 'اقدام پیشنهادی', noIssues: 'مشکلی پیدا نشد.',
      activity: 'گزارش فعالیت', action: 'اقدام', target: 'هدف', actor: 'کاربر', time: 'زمان',
      refresh: 'به‌روزرسانی', nothing: 'چیزی برای نمایش نیست.', job: 'کار',
      fixNote: 'پیشنهاد رفع باگ در یک کپی جداگانه ساخته و تست می‌شود؛ روی سایت اصلی اعمال نمی‌شود.',
      approveNote: 'تأیید این پیشنهاد باعث اعمال آن روی کد اصلی می‌شود.'
    },
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
  function renderDash() {
    var box = document.getElementById('dashBody');
    if (!box || !S.dash) return;
    var d = S.dash, v = d.videos || {}, j = d.jobs || {}, l = d.llm || {};
    var stat = function (k, val, sub) {
      return '<div class="adm-dstat"><span>' + esc(k) + '</span><b dir="ltr">' + esc(val) + '</b>'
        + (sub ? '<em>' + esc(sub) + '</em>' : '') + '</div>';
    };
    var html = '<div class="adm-dgrid">'
      + stat(t('totalVideos'), plain(v.videos))
      + stat(t('published'), plain(v.published))
      + stat(t('draft'), plain(v.draft))
      + stat(t('withQuiz'), plain(v.with_quiz))
      + stat(t('withSubs'), plain(v.with_transcript))
      + stat(t('awaiting'), plain((d.review || {}).awaiting))
      + stat(t('queued'), plain(j.queued))
      + stat(t('running'), plain(j.running))
      + stat(t('done'), plain(j.done))
      + stat(t('failed'), plain(j.failed))
      + stat(t('stuck'), plain((j.stuck || []).length))
      + '</div>';
    // the AI connection, as it actually is
    var llmState = l.reachable === true ? t('reachable') : (l.reachable === false ? t('unreachable') : t('unknown'));
    var llmClass = l.reachable === true ? 'ok' : (l.reachable === false ? 'bad' : 'warn');
    html += '<div class="adm-dllm ' + llmClass + '"><span class="adm-ai-pill">AI</span>'
      + '<b>' + esc(t('aiStatus')) + ': ' + esc(llmState) + '</b>'
      + '<span dir="ltr">' + esc(l.model || '—') + ' · ' + plain(l.model_count) + ' ' + esc(t('modelCount')) + '</span>'
      + '<em>' + esc(t('lastUpdate')) + ': ' + esc(d.generated_at || '') + '</em></div>';

    if ((d.recent_errors || []).length) {
      html += '<div class="adm-dsec"><h4>' + esc(t('recentErrors')) + '</h4><ul class="adm-dlist">'
        + d.recent_errors.slice(0, 6).map(function (e) {
          return '<li><b>' + esc(e.category) + '</b> ' + esc(e.stage || '') + ' — ' + esc(e.message || '') + '</li>';
        }).join('') + '</ul></div>';
    }
    if ((d.recent_actions || []).length) {
      html += '<div class="adm-dsec"><h4>' + esc(t('recentActions')) + '</h4><ul class="adm-dlist">'
        + d.recent_actions.slice(0, 8).map(function (a) {
          return '<li><b>' + esc(a.action) + '</b> ' + esc(a.target || '') + ' — ' + esc(a.actor || '') + '</li>';
        }).join('') + '</ul></div>';
    }
    box.innerHTML = html;
  }

  function loadDash() {
    return api('dashboard.php').then(function (d) { S.dash = d; renderDash(); }).catch(function () { });
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
    var f = { url_validate: 'اعتبارسنجی لینک', identify: 'شناسایی و اطلاعات',
      transcript: 'دریافت زیرنویس', stt: 'گفتار به متن', cleanup: 'پاک‌سازی متن',
      extract_en: 'استخراج انگلیسی', translate_fa: 'ترجمهٔ فارسی', title_fa: 'عنوان فارسی',
      title_en: 'عنوان انگلیسی', seo: 'سئو', qc: 'کنترل کیفیت', quiz: 'ساخت آزمون',
      quiz_validate: 'اعتبارسنجی آزمون', terminology: 'اصطلاحات پزشکی', persist: 'ذخیره',
      consistency: 'کنترل سازگاری', publish: 'انتشار' };
    return f[st] || st;
  }
  function renderStages() {
    var box = document.getElementById('checklistBody');
    if (!box) return;
    if (!S.jobId) { box.innerHTML = '<div class="adm-empty">' + esc(t('noJob')) + '</div>'; return; }
    if (!S.stages.length) { box.innerHTML = '<div class="adm-empty">' + esc(t('noJob')) + '</div>'; return; }
    var html = '<div class="adm-cl">';
    S.stages.forEach(function (s) {
      var cls = STATUS_CLASS[s.status] || 'wait';
      html += '<div class="adm-clrow ' + cls + '">'
        + '<span class="adm-clseq">' + s.seq + '</span>'
        + '<span class="adm-clname">' + esc(stageLabel(s.stage)) + '</span>'
        + '<span class="adm-clst">' + esc(t(s.status)) + '</span>'
        + '<span class="adm-clmeta" dir="ltr">' + esc(s.attempts || 0) + '×'
        + (s.model ? ' · ' + esc(s.model) : '')
        + (s.tokens ? ' · ' + plain(s.tokens) + ' tok' : '') + '</span>'
        + (s.skipped_reason ? '<span class="adm-clwhy">' + esc(s.skipped_reason) + '</span>' : '')
        + (s.error ? '<span class="adm-clerr">' + esc(s.error) + '</span>' : '')
        + (s.status === 'failed' && s.retryable
            ? '<button type="button" class="adm-btn adm-btn-ghost adm-btn-sm adm-clretry"'
              + ' data-job="' + esc(s.job_id || S.jobId) + '" data-stage="' + esc(s.stage) + '">'
              + esc(t('retry')) + '</button>' : '')
        + '</div>';
    });
    html += '</div>';
    box.innerHTML = html;
    Array.prototype.forEach.call(box.querySelectorAll('.adm-clretry'), function (b) {
      b.addEventListener('click', function () {
        b.disabled = true;
        api('stages.php', { action: 'retry', job_id: b.getAttribute('data-job'),
                            stage: b.getAttribute('data-stage') })
          .then(function () { return loadStages(S.jobId); })
          .catch(function (e) { window.alert(String(e.message || e)); b.disabled = false; });
      });
    });
  }
  function loadStages(jobId) {
    S.jobId = jobId || '';
    if (!S.jobId) { renderStages(); return Promise.resolve(); }
    return api('stages.php?job_id=' + encodeURIComponent(S.jobId))
      .then(function (d) { S.stages = d.stages || []; renderStages(); })
      .catch(function () { S.stages = []; renderStages(); });
  }

  /* ---------------------------------------------------- the error centre */
  function renderErrors() {
    var box = document.getElementById('errorsBody');
    if (!box) return;
    if (!S.errors.length) { box.innerHTML = '<div class="adm-empty">' + esc(t('noErrors')) + '</div>'; return; }
    var html = '<div class="adm-etable">';
    S.errors.forEach(function (e) {
      html += '<div class="adm-erow" data-err="' + esc(e.id) + '">'
        + '<span class="adm-esev ' + esc(e.severity) + '">' + esc(e.severity) + '</span>'
        + '<span class="adm-ecat">' + esc(e.category) + '</span>'
        + '<span class="adm-emsg">' + esc(e.message || '') + '</span>'
        + '<span class="adm-emeta" dir="ltr">' + esc(e.stage || '') + ' · ' + esc(e.created_at || '') + '</span>'
        + '<span class="adm-efix">' + esc(e.fix_state || 'none') + '</span>'
        + '<button type="button" class="adm-btn adm-btn-ghost adm-btn-sm" data-fix="' + esc(e.id) + '">'
        + esc(t('fixBug')) + '</button>'
        + '</div>';
    });
    html += '</div>';
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
    if (!S.issues.length) { box.innerHTML = '<div class="adm-empty">' + esc(t('noIssues')) + '</div>'; return; }
    var html = '<div class="adm-itable">';
    S.issues.forEach(function (i) {
      html += '<div class="adm-irow">'
        + '<span class="adm-isev ' + esc(i.severity) + '">' + esc(i.severity) + '</span>'
        + '<span class="adm-icat">' + esc(i.category) + '</span>'
        + '<span class="adm-iid" dir="ltr">' + esc(i.yt_id || i.video_id) + '</span>'
        + '<span class="adm-iev">' + esc(i.evidence || '') + '</span>'
        + '<span class="adm-irec">' + esc(i.recommended || '') + '</span>'
        + '<button type="button" class="adm-btn adm-btn-ghost adm-btn-sm" data-resolve="' + esc(i.id) + '">'
        + esc(t('resolve')) + '</button>'
        + '</div>';
    });
    html += '</div>';
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
    var jobSel = document.getElementById('checklistJob');
    if (jobSel) {
      jobSel.addEventListener('change', function () { loadStages(jobSel.value); });
    }
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
  function loadJobList() {
    var jobSel = document.getElementById('checklistJob');
    if (!jobSel) return Promise.resolve();
    return api('jobs.php').then(function (d) {
      var jobs = d.jobs || [];
      jobSel.innerHTML = '<option value="">\u2014</option>' + jobs.map(function (j) {
        return '<option value="' + esc(j.id) + '" dir="ltr">' + esc(j.yt_id || j.id)
          + ' (' + esc(j.status) + ')</option>';
      }).join('');
      if (jobs.length && !S.jobId) { jobSel.value = jobs[0].id; loadStages(jobs[0].id); }
    }).catch(function () { });
  }

  /** Everything the operational modules need, after the session exists. */
  function loadAll() {
    loadDash();
    loadErrors();
    loadAudit();
    loadActivity();
    loadJobList();
  }

  window.npOps = {
    load: loadAll, loadAll: loadAll, loadStages: loadStages, loadErrors: loadErrors,
    loadAudit: loadAudit, loadActivity: loadActivity
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
