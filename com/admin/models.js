/* NursePlus admin — model capability indicators, context window and usage.
 *
 * One file, two languages: the panel is rendered in Persian on the IR
 * deployment and in English on COM, so every string comes from the table
 * below and the language is read from <html lang>.
 *
 * The rules this file follows:
 *   - a capability icon is only shown as "supported" when the provider
 *     said so; anything else is drawn as "not supported" or "unknown"
 *   - a token count that was computed locally is always labelled as an
 *     estimate; only the provider's own usage block is called actual
 *   - the API key is never read here and never shown
 */
(function () {
  'use strict';

  var LANG = (document.documentElement.lang || 'fa').toLowerCase() === 'en' ? 'en' : 'fa';

  var T = {
    fa: {
      models: 'مدل‌ها', modelsCount: 'مدل', refresh: 'به‌روزرسانی فهرست',
      search: 'جست‌وجو در نام مدل…', allModels: 'همه',
      vision: 'بینایی', reasoning: 'استدلال', tools: 'ابزار', image_gen: 'تولید تصویر', audio: 'صدا',
      yes: 'پشتیبانی می‌شود', no: 'پشتیبانی نمی‌شود', unknown: 'نامشخص — تأییدنشده',
      context: 'پنجرهٔ متن', maxOut: 'حداکثر خروجی', provider: 'ارائه‌دهنده',
      source: 'منبع metadata', sourceProvider: 'اعلام ارائه‌دهنده', sourceNone: 'بدون metadata',
      sourceManual: 'دستی', verified: 'تأییدشده', unverified: 'تأییدنشده',
      usage: 'آمار مصرف', usageTitle: 'آمار مصرف مدل', refreshUsage: 'به‌روزرسانی آمار',
      requests: 'درخواست', failures: 'خطا', promptTok: 'توکن ورودی', completionTok: 'توکن خروجی',
      cachedTok: 'توکن کش‌شده', reasoningTok: 'توکن استدلال', cost: 'هزینه', latency: 'تأخیر',
      lastUsed: 'آخرین استفاده', model: 'مدل', task: 'کار', site: 'سایت', time: 'زمان',
      noUsage: 'هنوز درخواستی ثبت نشده است.', noModels: 'مدلی پیدا نشد.',
      details: 'جزئیات مدل', close: 'بستن', override: 'بازنویسی دستی',
      overrideHint: 'بازنویسی‌ها جدا از metadata خودکار ذخیره می‌شوند و با به‌روزرسانی پاک نمی‌شوند.',
      save: 'ذخیره', reset: 'بازگشت به مقدار ارائه‌دهنده', saved: 'ذخیره شد.',
      auto: 'خودکار', total: 'مجموع', byModel: 'بر اساس مدل', byTask: 'بر اساس کار',
      ctxUsed: 'استفاده‌شده', ctxFree: 'باقی‌مانده', estimated: 'تخمینی', actual: 'واقعی',
      allTasks: 'همهٔ کارها', allSites: 'همهٔ سایت‌ها', from: 'از', to: 'تا',
      lastRequest: 'آخرین درخواست', of: 'از', selectModel: 'مدل را انتخاب کن',
      filterCaps: 'فیلتر قابلیت', detailsOf: 'جزئیات', usageOf: 'آمار',
      warnContext: 'متن گفتگو به سقف context نزدیک می‌شود.',
      lastUpdated: 'آخرین به‌روزرسانی', refreshNeeded: 'فهرست مدل‌ها هنوز به‌روز نشده — دکمهٔ به‌روزرسانی را بزن.'
    },
    en: {
      models: 'Models', modelsCount: 'models', refresh: 'Refresh the list',
      search: 'Search the model name…', allModels: 'All',
      vision: 'Vision', reasoning: 'Reasoning', tools: 'Tool calling', image_gen: 'Image generation', audio: 'Audio',
      yes: 'supported', no: 'not supported', unknown: 'unknown — unverified',
      context: 'Context window', maxOut: 'Max output', provider: 'Provider',
      source: 'Metadata source', sourceProvider: 'declared by the provider', sourceNone: 'no metadata',
      sourceManual: 'manual', verified: 'verified', unverified: 'unverified',
      usage: 'Usage', usageTitle: 'Model usage', refreshUsage: 'Refresh the statistics',
      requests: 'Requests', failures: 'Failures', promptTok: 'Input tokens', completionTok: 'Output tokens',
      cachedTok: 'Cached tokens', reasoningTok: 'Reasoning tokens', cost: 'Cost', latency: 'Latency',
      lastUsed: 'Last used', model: 'Model', task: 'Task', site: 'Site', time: 'Time',
      noUsage: 'No request has been recorded yet.', noModels: 'No model found.',
      details: 'Model details', close: 'Close', override: 'Manual override',
      overrideHint: 'Overrides are stored apart from the automatic metadata and survive a refresh.',
      save: 'Save', reset: 'Back to the provider value', saved: 'Saved.',
      auto: 'auto', total: 'Total', byModel: 'By model', byTask: 'By task',
      ctxUsed: 'used', ctxFree: 'free', estimated: 'estimated', actual: 'actual',
      allTasks: 'All tasks', allSites: 'All sites', from: 'From', to: 'To',
      lastRequest: 'Last request', of: 'of', selectModel: 'Select a model',
      filterCaps: 'Filter by capability', detailsOf: 'Details', usageOf: 'Usage',
      warnContext: 'The conversation is approaching the context limit.',
      lastUpdated: 'Last updated', refreshNeeded: 'The model list has not been refreshed yet — press refresh.'
    }
  };
  function t(k) { return (T[LANG] && T[LANG][k]) || k; }

  /* ---------------------------------------------------------------- icons
   * Inline SVG, one visual language: 14px, 1.6 stroke, round caps. */
  function svg(paths) {
    return '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" ' +
      'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + paths + '</svg>';
  }
  var ICON = {
    vision: svg('<path d="M2 12s3.6-6 10-6 10 6 10 6-3.6 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="2.6"/>'),
    reasoning: svg('<path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-1.6 5.3A3 3 0 0 0 6 17a3 3 0 0 0 3 3h1V4Z"/>' +
      '<path d="M15 4a3 3 0 0 1 3 3 3 3 0 0 1 1.6 5.3A3 3 0 0 1 18 17a3 3 0 0 1-3 3h-1V4Z"/>'),
    tools: svg('<path d="M14.7 6.3a4 4 0 0 0 5 5l-9.2 9.2a2.1 2.1 0 0 1-3-3Z"/><path d="M6 6 8 8"/>'),
    image_gen: svg('<rect x="3" y="4" width="18" height="16" rx="2.5"/><circle cx="8.5" cy="9.5" r="1.6"/>' +
      '<path d="m4 17 5-5 4 4 3-2.5 4 3.5"/>'),
    audio: svg('<path d="M4 9v6h4l5 4V5L8 9Z"/><path d="M17 8.5a5 5 0 0 1 0 7"/>')
  };
  var CAPS = ['vision', 'reasoning', 'tools', 'image_gen', 'audio'];

  function capIcon(field, state) {
    var cls = 'adm-ic adm-ic-' + state;
    var label = t(field) + ' — ' + t(state === 'yes' ? 'yes' : state === 'no' ? 'no' : 'unknown');
    if (state === 'unknown') {
      return '<span class="' + cls + '" title="' + esc(label) + '" aria-label="' + esc(label) + '" role="img">?</span>';
    }
    return '<span class="' + cls + '" title="' + esc(label) + '" aria-label="' + esc(label) + '" role="img">'
      + ICON[field] + '</span>';
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function nfmt(n) {
    n = Number(n || 0);
    if (n >= 1e9) return (n / 1e9).toFixed(n >= 1e10 ? 0 : 1) + 'B';
    if (n >= 1e6) return (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(n >= 1e4 ? 0 : 1) + 'K';
    return String(n);
  }
  function plain(n) { return Number(n || 0).toLocaleString(LANG === 'en' ? 'en-US' : 'fa-IR'); }

  /* ------------------------------------------------------------- state */
  var S = {
    models: [], prefs: {}, q: '', caps: {}, selected: '',
    usage: null, detail: null, lastContext: null, loaded: false
  };
  /* The API always lives at the site root — the COM deployment shares it.
   * The panel sits at /admin/ on IR and at /com/admin/ on COM, so the depth
   * is worked out from the path instead of being hard-coded. */
  function apiRoot() {
    var u = new URL(document.baseURI);
    var p = u.pathname.replace(/\/admin\/[^/]*$/, '/').replace(/\/com\/$/, '/');
    if (p.charAt(0) !== '/') p = '/' + p;
    return u.origin + p + 'api/';
  }
  var API = apiRoot();

  function api(path, body) {
    var headers = body ? { 'Content-Type': 'application/json' } : {};
    /* the same CSRF token the rest of the panel uses */
    if (body && window.__npCsrf) headers['X-CSRF-Token'] = window.__npCsrf;
    return fetch(API + path, {
      method: body ? 'POST' : 'GET',
      credentials: 'same-origin',
      headers: headers,
      body: body ? JSON.stringify(body) : undefined
    }).then(function (r) {
      return r.text().then(function (txt) {
        var d = null;
        try { d = JSON.parse(txt); } catch (e) { d = null; }
        if (!r.ok || !d || d.ok === false) {
          var msg = (d && (d.message || d.error)) || ('HTTP ' + r.status);
          throw new Error(msg);
        }
        return d;
      });
    });
  }

  /* ------------------------------------------------- capability filters */
  function renderFilters() {
    var box = document.getElementById('capFilters');
    if (!box) return;
    var html = '<span class="adm-flabel">' + esc(t('filterCaps')) + '</span>';
    CAPS.forEach(function (f) {
      var on = !!S.caps[f];
      html += '<button type="button" class="adm-chip' + (on ? ' on' : '') + '" data-cap="' + f + '"'
        + ' aria-pressed="' + (on ? 'true' : 'false') + '">'
        + capIcon(f, on ? 'yes' : 'unknown') + '<span>' + esc(t(f)) + '</span></button>';
    });
    box.innerHTML = html;
    Array.prototype.forEach.call(box.querySelectorAll('.adm-chip'), function (b) {
      b.addEventListener('click', function () {
        var f = b.getAttribute('data-cap');
        S.caps[f] = !S.caps[f];
        renderFilters();
        renderList();
      });
    });
  }

  /* -------------------------------------------------------- the list */
  function visible() {
    var q = S.q.trim().toLowerCase();
    return S.models.filter(function (m) {
      if (q && String(m.id).toLowerCase().indexOf(q) === -1
        && String(m.provider || '').toLowerCase().indexOf(q) === -1) return false;
      var caps = Object.keys(S.caps);
      for (var i = 0; i < caps.length; i++) {
        if (S.caps[caps[i]] && m.caps[caps[i]] !== 'yes') return false;
      }
      return true;
    });
  }

  function renderList() {
    var box = document.getElementById('modelList');
    if (!box) return;
    var rows = visible();
    if (!S.models.length) {
      box.innerHTML = '<div class="adm-empty">' + esc(t('refreshNeeded')) + '</div>';
    } else if (!rows.length) {
      box.innerHTML = '<div class="adm-empty">' + esc(t('noModels')) + '</div>';
    } else {
      var html = '';
      rows.slice(0, 300).forEach(function (m) {
        var sel = m.id === S.selected ? ' sel' : '';
        html += '<button type="button" class="adm-mrow' + sel + '" data-model="' + esc(m.id) + '" role="option"'
          + ' aria-selected="' + (m.id === S.selected ? 'true' : 'false') + '">'
          + '<span class="adm-mname" dir="ltr">' + esc(m.id) + '</span>'
          + '<span class="adm-mcaps">'
          + CAPS.map(function (f) { return capIcon(f, m.caps[f] || 'unknown'); }).join('')
          + '</span>'
          + '<span class="adm-mctx" dir="ltr">' + (m.ctx_max ? nfmt(m.ctx_max) : '—') + '</span>'
          + '</button>';
      });
      if (rows.length > 300) {
        html += '<div class="adm-mmore">+' + (rows.length - 300) + '</div>';
      }
      box.innerHTML = html;
      Array.prototype.forEach.call(box.querySelectorAll('.adm-mrow'), function (b) {
        b.addEventListener('click', function () { pick(b.getAttribute('data-model')); });
      });
    }
    var c = document.getElementById('modelCount');
    if (c) c.textContent = plain(rows.length) + ' / ' + plain(S.models.length) + ' ' + t('modelsCount');
  }

  /* ----------------------------------------------- the selected model */
  function byId(id) {
    for (var i = 0; i < S.models.length; i++) if (S.models[i].id === id) return S.models[i];
    return null;
  }
  function pick(id) {
    S.selected = id;
    var inp = document.getElementById('llmModel');
    if (inp) inp.value = id;
    renderList();
    renderSummary();
    loadDetail(id);
  }
  function pct(p) { return Math.max(0, Math.min(100, Number(p) || 0)); }
  function barClass(p) {
    if (p < 60) return 'ok';
    if (p < 80) return 'warn';
    if (p < 90) return 'hot';
    return 'crit';
  }
  function renderSummary() {
    var box = document.getElementById('modelSummary');
    if (!box) return;
    var m = byId(S.selected);
    if (!m) { box.innerHTML = ''; box.hidden = true; return; }
    box.hidden = false;
    var ctx = S.lastContext && S.lastContext.model === m.id ? S.lastContext : null;
    var used = ctx ? pct(ctx.pct) : 0;
    var html = '<div class="adm-sum-head">'
      + '<span class="adm-mname" dir="ltr">' + esc(m.id) + '</span>'
      + '<span class="adm-mcaps">'
      + CAPS.map(function (f) { return capIcon(f, m.caps[f] || 'unknown'); }).join('') + '</span>'
      + '</div>';
    html += '<div class="adm-sum-grid">'
      + '<div><span class="adm-sum-k">' + esc(t('context')) + '</span><b dir="ltr">'
      + (m.ctx_max ? plain(m.ctx_max) : '—') + '</b></div>'
      + '<div><span class="adm-sum-k">' + esc(t('maxOut')) + '</span><b dir="ltr">'
      + (m.out_max ? plain(m.out_max) : '—') + '</b></div>'
      + '<div><span class="adm-sum-k">' + esc(t('provider')) + '</span><b dir="ltr">'
      + esc(m.provider || '—') + '</b></div>'
      + '<div><span class="adm-sum-k">' + esc(t('requests')) + '</span><b dir="ltr">'
      + plain(m.usage.requests) + '</b></div>'
      + '</div>';
    if (ctx && ctx.ctx_max) {
      html += '<div class="adm-ctx">'
        + '<div class="adm-ctx-top"><span>' + esc(t('lastRequest')) + '</span>'
        + '<span dir="ltr">' + plain(ctx.actual_prompt || ctx.est) + ' / ' + plain(ctx.ctx_max)
        + ' · ' + (ctx.pct || 0).toFixed(1) + '% · ' + esc(ctx.source === 'actual' ? t('actual') : t('estimated'))
        + '</span></div>'
        + '<div class="adm-ctx-bar"><i class="' + barClass(used) + '" style="width:' + used.toFixed(1) + '%"></i></div>'
        + '</div>';
    }
    box.innerHTML = html;
  }

  /* --------------------------------------------------- the details panel */
  function loadDetail(id) {
    if (!id) return;
    api('models.php?action=detail&model=' + encodeURIComponent(id)).then(function (d) {
      S.detail = d;
      renderDetail();
    }).catch(function () { S.detail = null; renderDetail(); });
  }

  function renderDetail() {
    var box = document.getElementById('modelDetail');
    if (!box) return;
    var d = S.detail;
    if (!d || !d.model) { box.innerHTML = ''; box.hidden = true; return; }
    box.hidden = false;
    var m = d.model;
    var u = m.usage;
    var src = m.source === 'provider' ? t('sourceProvider') : m.source === 'manual' ? t('sourceManual') : t('sourceNone');
    var ver = m.verify === 'confirmed' ? t('verified') : t('unverified');

    var html = '<div class="adm-det-head"><h3>' + esc(t('details')) + '</h3>'
      + '<button type="button" class="adm-x" id="modelDetailClose" aria-label="' + esc(t('close')) + '">×</button></div>';
    html += '<div class="adm-det-model" dir="ltr">' + esc(m.id) + '</div>';
    html += '<div class="adm-det-caps">' + CAPS.map(function (f) {
      var st = m.caps[f] || 'unknown';
      return '<span class="adm-det-cap ' + st + '">' + capIcon(f, st) + '<span>' + esc(t(f))
        + '</span><em>' + esc(t(st === 'yes' ? 'yes' : st === 'no' ? 'no' : 'unknown')) + '</em></span>';
    }).join('') + '</div>';
    html += '<dl class="adm-det-kv">'
      + '<dt>' + esc(t('context')) + '</dt><dd dir="ltr">' + (m.ctx_max ? plain(m.ctx_max) : '—') + '</dd>'
      + '<dt>' + esc(t('maxOut')) + '</dt><dd dir="ltr">' + (m.out_max ? plain(m.out_max) : '—') + '</dd>'
      + '<dt>' + esc(t('provider')) + '</dt><dd dir="ltr">' + esc(m.provider || '—') + '</dd>'
      + '<dt>' + esc(t('source')) + '</dt><dd>' + esc(src) + '</dd>'
      + '<dt>' + esc(t('verified')) + '</dt><dd>' + esc(ver) + '</dd>'
      + '<dt>' + esc(t('lastUpdated')) + '</dt><dd dir="ltr">' + esc(m.refreshed_at || '—') + '</dd>'
      + '</dl>';

    html += '<div class="adm-det-usage"><h4>' + esc(t('usage')) + '</h4><dl class="adm-det-kv">'
      + '<dt>' + esc(t('requests')) + '</dt><dd dir="ltr">' + plain(u.requests) + '</dd>'
      + '<dt>' + esc(t('promptTok')) + '</dt><dd dir="ltr">' + plain(u.prompt_tokens) + '</dd>'
      + '<dt>' + esc(t('completionTok')) + '</dt><dd dir="ltr">' + plain(u.completion_tokens) + '</dd>'
      + '<dt>' + esc(t('cachedTok')) + '</dt><dd dir="ltr">' + plain(u.cached_tokens) + '</dd>'
      + '<dt>' + esc(t('reasoningTok')) + '</dt><dd dir="ltr">' + plain(u.reasoning_tokens) + '</dd>'
      + '<dt>' + esc(t('failures')) + '</dt><dd dir="ltr">' + plain(u.failures) + '</dd>'
      + '<dt>' + esc(t('latency')) + '</dt><dd dir="ltr">' + plain(u.avg_latency_ms) + ' ms</dd>'
      + '<dt>' + esc(t('lastUsed')) + '</dt><dd dir="ltr">' + esc(u.last_used || '—') + '</dd>'
      + '</dl></div>';

    // manual overrides
    html += '<details class="adm-ovr"><summary>' + esc(t('override')) + '</summary>'
      + '<p class="adm-note">' + esc(t('overrideHint')) + '</p><div class="adm-ovr-grid">';
    CAPS.forEach(function (f) {
      var cur = m.caps[f] || 'unknown';
      html += '<label class="adm-ovr-item"><span>' + esc(t(f)) + '</span><select data-ovr="' + f + '">'
        + '<option value="">' + esc(t('auto')) + '</option>'
        + '<option value="yes"' + (cur === 'yes' ? ' selected' : '') + '>' + esc(t('yes')) + '</option>'
        + '<option value="no"' + (cur === 'no' ? ' selected' : '') + '>' + esc(t('no')) + '</option>'
        + '<option value="unknown"' + (cur === 'unknown' ? ' selected' : '') + '>' + esc(t('unknown')) + '</option>'
        + '</select></label>';
    });
    html += '<label class="adm-ovr-item"><span>' + esc(t('context')) + '</span>'
      + '<input type="number" min="0" step="1024" data-ovr="ctx_max" value="'
      + (m.overridden && m.overridden.indexOf('ctx_max') > -1 ? m.ctx_max : '') + '" placeholder="' + esc(t('auto')) + '"></label>';
    html += '<label class="adm-ovr-item"><span>' + esc(t('maxOut')) + '</span>'
      + '<input type="number" min="0" step="1024" data-ovr="out_max" value="'
      + (m.overridden && m.overridden.indexOf('out_max') > -1 ? m.out_max : '') + '" placeholder="' + esc(t('auto')) + '"></label>';
    html += '</div><div class="adm-actions">'
      + '<button type="button" class="adm-btn adm-btn-primary adm-btn-sm" id="ovrSave">' + esc(t('save')) + '</button>'
      + '<button type="button" class="adm-btn adm-btn-ghost adm-btn-sm" id="ovrReset">' + esc(t('reset')) + '</button>'
      + '</div></details>';

    box.innerHTML = html;
    var close = document.getElementById('modelDetailClose');
    if (close) close.addEventListener('click', function () { box.hidden = true; });
    var save = document.getElementById('ovrSave');
    if (save) save.addEventListener('click', function () {
      var body = { action: 'override', endpoint_id: S.endpointId, model_id: m.id };
      Array.prototype.forEach.call(box.querySelectorAll('[data-ovr]'), function (el) {
        body[el.getAttribute('data-ovr')] = el.value;
      });
      api('models.php', body).then(function () {
        loadModels(); loadDetail(m.id);
      }).catch(function (e) { window.alert(String(e.message || e)); });
    });
    var reset = document.getElementById('ovrReset');
    if (reset) reset.addEventListener('click', function () {
      api('models.php', { action: 'clear_override', endpoint_id: S.endpointId, model_id: m.id })
        .then(function () { loadModels(); loadDetail(m.id); })
        .catch(function (e) { window.alert(String(e.message || e)); });
    });
  }

  /* ------------------------------------------------------ usage dashboard */
  function loadUsage() {
    var f = usageFilters();
    var q = 'models.php?action=usage&limit=200';
    if (f.model) q += '&model=' + encodeURIComponent(f.model);
    if (f.task) q += '&task=' + encodeURIComponent(f.task);
    if (f.site) q += '&site=' + encodeURIComponent(f.site);
    if (f.from) q += '&from=' + encodeURIComponent(f.from);
    if (f.to) q += '&to=' + encodeURIComponent(f.to);
    return api(q).then(function (d) { S.usage = d; renderUsage(); }).catch(function () { });
  }
  function usageFilters() {
    var g = function (id) { var e = document.getElementById(id); return e ? e.value : ''; };
    return { model: g('usageModel'), task: g('usageTask'), site: g('usageSite'),
             from: g('usageFrom'), to: g('usageTo') };
  }
  function renderUsage() {
    var box = document.getElementById('usageBody');
    if (!box || !S.usage) return;
    var d = S.usage;
    var tot = d.totals || {};
    var head = '<div class="adm-usg-tot">'
      + stat(t('requests'), plain(tot.requests || 0))
      + stat(t('promptTok'), plain(tot.prompt_tokens || 0))
      + stat(t('completionTok'), plain(tot.completion_tokens || 0))
      + stat(t('cachedTok'), plain(tot.cached_tokens || 0))
      + stat(t('reasoningTok'), plain(tot.reasoning_tokens || 0))
      + stat(t('failures'), plain(tot.failures || 0))
      + stat(t('latency'), plain(tot.avg_latency_ms || 0) + ' ms')
      + '</div>';
    var rows = d.rows || [];
    var body = rows.length ? '<div class="adm-table-wrap"><table class="adm-table">'
      + '<thead><tr><th>' + esc(t('time')) + '</th><th>' + esc(t('model')) + '</th><th>' + esc(t('task'))
      + '</th><th>' + esc(t('site')) + '</th><th>' + esc(t('promptTok')) + '</th><th>' + esc(t('completionTok'))
      + '</th><th>' + esc(t('cachedTok')) + '</th><th>' + esc(t('reasoningTok')) + '</th><th>' + esc(t('latency'))
      + '</th><th>' + esc(t('failures')) + '</th></tr></thead><tbody>'
      + rows.map(function (r) {
        return '<tr><td dir="ltr">' + esc(r.created_at) + '</td><td dir="ltr">' + esc(r.model_id)
          + '</td><td dir="ltr">' + esc(r.task) + '</td><td dir="ltr">' + esc(r.site)
          + '</td><td dir="ltr">' + plain(r.prompt_tokens) + '</td><td dir="ltr">' + plain(r.completion_tokens)
          + '</td><td dir="ltr">' + plain(r.cached_tokens) + '</td><td dir="ltr">' + plain(r.reasoning_tokens)
          + '</td><td dir="ltr">' + plain(r.latency_ms) + ' ms</td><td>' + (r.ok ? '—' : '⚠') + '</td></tr>';
      }).join('') + '</tbody></table></div>'
      : '<div class="adm-empty">' + esc(t('noUsage')) + '</div>';

    var br = '<div class="adm-usg-break">'
      + '<div><h4>' + esc(t('byModel')) + '</h4><table class="adm-mini"><tbody>'
      + (d.by_model || []).slice(0, 12).map(function (r) {
        return '<tr><td dir="ltr">' + esc(r.model_id) + '</td><td dir="ltr">' + plain(r.requests)
          + '</td><td dir="ltr">' + plain(r.prompt_tokens) + '</td><td dir="ltr">' + plain(r.completion_tokens) + '</td></tr>';
      }).join('') + '</tbody></table></div>'
      + '<div><h4>' + esc(t('byTask')) + '</h4><table class="adm-mini"><tbody>'
      + (d.by_task || []).map(function (r) {
        return '<tr><td dir="ltr">' + esc(r.task) + '</td><td dir="ltr">' + plain(r.requests)
          + '</td><td dir="ltr">' + plain(r.prompt_tokens) + '</td><td dir="ltr">' + plain(r.completion_tokens) + '</td></tr>';
      }).join('') + '</tbody></table></div></div>';

    box.innerHTML = head + body + br;
    var c = document.getElementById('usageCount');
    if (c) c.textContent = plain(tot.requests || 0) + ' ' + t('requests');
  }
  function stat(k, v) {
    return '<div class="adm-usg-stat"><span>' + esc(k) + '</span><b dir="ltr">' + esc(v) + '</b></div>';
  }

  /* ----------------------------------------------------------- loading */
  function loadModels() {
    return api('models.php?action=list').then(function (d) {
      S.models = d.models || [];
      S.prefs = d.prefs || {};
      S.endpointId = d.endpoint_id || 'default';
      S.loaded = true;
      var sel = document.getElementById('llmModel');
      if (sel && sel.value) S.selected = sel.value;
      if (!S.selected && S.models.length) S.selected = S.models[0].id;
      renderFilters();
      renderList();
      renderSummary();
      fillUsageFilters();
      return loadUsage();
    }).catch(function () { });
  }
  function fillUsageFilters() {
    var sel = document.getElementById('usageModel');
    if (sel && sel.options.length <= 1) {
      var used = {};
      (S.usage && S.usage.by_model || []).forEach(function (r) { used[r.model_id] = 1; });
      S.models.forEach(function (m) { if (used[m.id] || m.id === S.selected) used[m.id] = 1; });
      var ids = Object.keys(used);
      ids.sort();
      sel.innerHTML = '<option value="">' + esc(t('allModels')) + '</option>'
        + ids.map(function (id) { return '<option value="' + esc(id) + '" dir="ltr">' + esc(id) + '</option>'; }).join('');
    }
  }

  /* ------------------------------------------------------------- init */
  function init() {
    var f = document.getElementById('modelFilter');
    if (f) {
      f.addEventListener('input', function () { S.q = f.value || ''; renderList(); });
    }
    var rf = document.getElementById('modelsRefresh');
    if (rf) rf.addEventListener('click', function () {
      rf.disabled = true;
      api('models.php', { action: 'refresh' }).then(function () {
        return loadModels();
      }).catch(function (e) {
        window.alert(String(e.message || e));
      }).then(function () { rf.disabled = false; });
    });
    var ru = document.getElementById('usageRefresh');
    if (ru) ru.addEventListener('click', function () { loadUsage(); });
    Array.prototype.forEach.call(document.querySelectorAll('[id^="usageModel"],[id^="usageTask"],[id^="usageSite"],[id^="usageFrom"],[id^="usageTo"]'), function (el) {
      el.addEventListener('change', function () { loadUsage(); });
    });
    var mi = document.getElementById('llmModel');
    if (mi) {
      mi.addEventListener('change', function () { pick(mi.value.trim()); });
    }
    /* the catalogue needs the session — the panel calls load() again once
       the administrator is signed in */
    if (document.getElementById('appView') && !document.getElementById('appView').hidden) loadModels();
    // keep the list fresh if the panel is open for a long time
    setInterval(function () { if (!document.hidden) loadUsage(); }, 30000);
  }

  // expose a tiny hook so the main panel script can report the context of
  // the last request it made
  window.npModels = {
    render: function () { renderFilters(); renderList(); renderSummary(); },
    setContext: function (ctx) { S.lastContext = ctx; renderSummary(); },
    selected: function () { return S.selected; },
    load: loadModels
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
