#!/usr/bin/env python3
"""Generate admin/index.html and com/admin/index.html from one template.

The two panels are the same panel in two languages. Keeping them as two
hand-edited files means they drift apart, so both are written from one
template with a dictionary of the strings.

Usage:
    python3 scripts/gen_admin_html.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------- strings
IR = {
    'lang': 'fa', 'dir': 'rtl', 'html_lang': 'fa',
    'title': 'پنل مدیریت نرس پلاس',
    'desc': 'پنل مدیریت نرس پلاس — افزودن ویدیو به صف پایپ‌لاین، تنظیم مدل هوش مصنوعی و پیگیری وضعیت انتشار.',
    'brand': 'پنل مدیریت نرس پلاس',
    'login_title': 'ورود به پنل مدیریت',
    'login_sub': 'برای مدیریت صف پایپ‌لاین و تنظیمات مدل هوش مصنوعی وارد شوید.',
    'email': 'ایمیل', 'password': 'رمز عبور', 'login': 'ورود', 'logout': 'خروج',
    'api_missing': 'این پنل روی آدرس ایستا (GitHub Pages) باز شده و API ندارد؛ ورود فقط روی هاست یا سرور محلی ممکن است.',
    'dash': 'داشبورد', 'refresh': 'به‌روزرسانی',
    'queue': 'صف پایپ‌لاین', 'jobs': 'کار', 'queue_empty': 'هنوز کاری در صف نیست.',
    'auto': 'به‌روزرسانی خودکار',
    'add_video': 'افزودن ویدیو', 'link_count': '۰ لینک شناسایی شد',
    'add_hint': 'لینک‌های یوتیوب را هر کدام در یک خط (یا با فاصله) بچسبانید. لینک‌های تکراری پیش از افزوده‌شدن شناسایی و رد می‌شوند.',
    'both_sites': 'هر ویدیویی که از اینجا اضافه شود خودکار روی هر دو سایت فارسی (IR) و انگلیسی (COM) منتشر می‌شود.',
    'add_to_queue': 'افزودن به صف', 'clear': 'پاک کردن نتایج',
    'errors': 'مرکز خطا', 'audit': 'بررسی محتوا', 'run_audit': 'اجرای بررسی',
    'ai_title': 'تنظیمات مدل هوش مصنوعی',
    'endpoint': 'آدرس endpoint', 'api_key': 'کلید API', 'show': 'نمایش', 'hide': 'پنهان',
    'model': 'مدل', 'model_search': 'جست‌وجو در فهرست مدل‌ها…',
    'model_manual': 'یا شناسهٔ مدل را دستی وارد کنید (مثلاً gpt-4o-mini)',
    'refresh_list': 'به‌روزرسانی فهرست', 'test_conn': 'تست اتصال', 'save': 'ذخیره تنظیمات',
    'usage': 'آمار مصرف', 'usage_refresh': 'به‌روزرسانی آمار', 'requests': 'درخواست',
    'filter_model': 'مدل', 'filter_task': 'کار', 'filter_site': 'سایت',
    'all_tasks': 'همهٔ کارها', 'all_sites': 'همهٔ سایت‌ها',
    'from': 'از', 'to': 'تا',
    'videos': 'ویدیوهای اخیر', 'videos_count': '۰ ویدیو',
    'search_videos': 'جست‌وجو در عنوان یا کانال…',
    'col_id': 'شناسه', 'col_fa': 'عنوان فارسی', 'col_en': 'عنوان انگلیسی',
    'col_fa_th': '<th scope="col">عنوان فارسی</th>',
    'col_channel': 'کانال', 'col_status': 'وضعیت', 'col_added': 'زمان افزودن',
    'no_videos': 'ویدیویی برای نمایش نیست.',
}

EN = {
    'lang': 'en', 'dir': 'ltr', 'html_lang': 'en',
    'title': 'NursePlus Admin Panel',
    'desc': 'NursePlus admin panel — add videos to the pipeline queue, set the AI model and follow the publishing status.',
    'brand': 'NursePlus Admin Panel',
    'login_title': 'Sign in to the admin panel',
    'login_sub': 'Sign in to manage the pipeline queue and the AI model settings.',
    'email': 'Email', 'password': 'Password', 'login': 'Sign in', 'logout': 'Sign out',
    'api_missing': 'This panel is open on a static host (GitHub Pages) and has no API; sign-in only works on the server or on the local machine.',
    'dash': 'Dashboard', 'refresh': 'Refresh',
    'queue': 'Pipeline queue', 'jobs': 'jobs', 'queue_empty': 'There is nothing in the queue.',
    'auto': 'Auto refresh',
    'add_video': 'Add a video', 'link_count': '0 links detected',
    'add_hint': 'Paste the YouTube links, one per line (or separated by spaces). Duplicate links are detected and skipped before anything is added.',
    'both_sites': 'Every video added here is published on both sites automatically — the Persian one (IR) and the English one (COM).',
    'add_to_queue': 'Add to the queue', 'clear': 'Clear the results',
    'errors': 'Error centre', 'audit': 'Content audit', 'run_audit': 'Run the audit',
    'ai_title': 'AI model settings',
    'endpoint': 'Endpoint URL', 'api_key': 'API key', 'show': 'Show', 'hide': 'Hide',
    'model': 'Model', 'model_search': 'Search the model list…',
    'model_manual': 'or type a model id by hand (for example gpt-4o-mini)',
    'refresh_list': 'Refresh the list', 'test_conn': 'Test the connection', 'save': 'Save the settings',
    'usage': 'Model usage', 'usage_refresh': 'Refresh the usage', 'requests': 'requests',
    'filter_model': 'Model', 'filter_task': 'Task', 'filter_site': 'Site',
    'all_tasks': 'All tasks', 'all_sites': 'All sites',
    'from': 'From', 'to': 'To',
    'videos': 'Recently added videos', 'videos_count': '0 videos',
    'search_videos': 'Search the title or the channel…',
    'col_id': 'ID', 'col_fa': 'Persian title', 'col_en': 'English title',
    'col_fa_th': '',
    'col_channel': 'Channel', 'col_status': 'Status', 'col_added': 'Added',
    'no_videos': 'There is no video to show.',
}

TEMPLATE = """<!doctype html>
<html lang="{html_lang}" dir="{dir}">
<head>
<!--seo:start-->
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="noindex, nofollow">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="fa" href="{canonical_fa}">
<link rel="alternate" hreflang="en" href="{canonical_en}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="https://i.ytimg.com/vi/oNEBmBtBvtw/maxresdefault.jpg">
<meta property="og:image:width" content="1280">
<meta property="og:image:height" content="720">
<meta property="og:image:alt" content="{title}">
<meta property="og:site_name" content="NursePlus">
<meta property="og:locale" content="{og_locale}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">[]</script>
<!--seo:end-->

<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<link rel="stylesheet" href="{root}assets/globals.css">
<link rel="stylesheet" href="admin.css">
<link rel="stylesheet" href="models.css">
<link rel="stylesheet" href="ops.css">
<link rel="stylesheet" href="compact.css">
</head>
<body class="adm">

<!-- ============================ LOGIN ============================ -->
<div class="adm-login" id="loginView">
  <form class="adm-card adm-login-card" id="loginForm" novalidate>
    <div class="adm-login-brand"><span class="adm-dot"></span> {brand}</div>
    <h1 class="adm-login-title">{login_title}</h1>
    <p class="adm-sub">{login_sub}</p>

    <label class="adm-field">
      <span class="adm-label">{email}</span>
      <input type="email" id="loginEmail" dir="ltr" autocomplete="username" placeholder="admin@example.com" spellcheck="false">
    </label>

    <label class="adm-field">
      <span class="adm-label">{password}</span>
      <input type="password" id="loginPass" dir="ltr" autocomplete="current-password" placeholder="••••••••">
    </label>

    <div class="adm-alert adm-alert-error" id="loginError" role="alert" hidden></div>

    <button class="adm-btn adm-btn-primary adm-btn-block" id="loginBtn" type="submit">{login}</button>
  </form>
    <p class="adm-api-missing" id="apiMissing" hidden>{api_missing}</p>
</div>

<!-- ============================ APP ============================ -->
<div class="adm-shell" id="appView" hidden>

  <header class="adm-top">
    <div class="adm-top-in">
      <div class="adm-top-brand"><span class="adm-dot"></span> {brand}</div>
      <div class="adm-top-side">
        <span class="adm-user" id="userName"></span>
        <button class="adm-btn adm-btn-ghost adm-btn-sm" id="logoutBtn" type="button">{logout}</button>
      </div>
    </div>
  </header>

  <div class="adm-grid">

    <!-- ---------- the main workspace ---------- -->
    <div class="adm-main">

      <!-- ---------- dashboard ---------- -->
      <section class="adm-card adm-area-dash">
        <div class="adm-card-head">
          <h2 class="adm-card-title">{dash}</h2>
          <button class="adm-btn adm-btn-ghost adm-btn-sm" id="dashRefresh" type="button">{refresh}</button>
        </div>
        <div id="dashBody"></div>
      </section>

      <!-- ---------- the pipeline queue ---------- -->
      <section class="adm-card adm-area-queue">
        <div class="adm-card-head">
          <h2 class="adm-card-title">{queue}</h2>
          <span class="adm-count" id="queueCount">۰ {jobs}</span>
          <span class="adm-hint adm-hint-tight adm-auto">{auto}</span>
        </div>
        <div class="adm-jobs" id="jobsList"></div>
        <div class="adm-empty" id="jobsEmpty">{queue_empty}</div>
      </section>

      <!-- ---------- add a video ---------- -->
      <section class="adm-card adm-area-add">
        <div class="adm-card-head">
          <h2 class="adm-card-title">{add_video}</h2>
          <span class="adm-count" id="linkCount">{link_count}</span>
        </div>
        <p class="adm-hint">{add_hint}</p>
        <p class="adm-bothsites"><span class="adm-dot"></span>{both_sites}</p>

        <textarea class="adm-textarea" id="urlInput" rows="4" spellcheck="false"
          placeholder="https://www.youtube.com/watch?v=..."></textarea>

        <div class="adm-detected" id="detected"></div>

        <div class="adm-actions">
          <button class="adm-btn adm-btn-primary" id="addBtn" type="button">{add_to_queue}</button>
          <button class="adm-btn adm-btn-ghost" id="clearBtn" type="button">{clear}</button>
        </div>

        <div class="adm-result-summary" id="addSummary" hidden></div>
        <ul class="adm-results" id="addResults" aria-live="polite"></ul>
      </section>

      <!-- ---------- the error centre ---------- -->
      <section class="adm-card adm-area-errors">
        <div class="adm-card-head">
          <h2 class="adm-card-title">{errors}</h2>
          <button class="adm-btn adm-btn-ghost adm-btn-sm" id="errorsRefresh" type="button">{refresh}</button>
        </div>
        <div id="errorsBody"></div>
        <div class="adm-fixpanel" id="fixPanel" hidden></div>
      </section>

      <!-- ---------- the content audit ---------- -->
      <section class="adm-card adm-area-audit">
        <div class="adm-card-head">
          <h2 class="adm-card-title">{audit}</h2>
          <button class="adm-btn adm-btn-primary adm-btn-sm" id="auditRun" type="button">{run_audit}</button>
        </div>
        <div id="auditBody"></div>
      </section>

      <!-- ---------- the model usage ---------- -->
      <section class="adm-card adm-area-usage">
        <div class="adm-card-head">
          <h2 class="adm-card-title">{usage}</h2>
          <span class="adm-count" id="usageCount">۰ {requests}</span>
          <button class="adm-btn adm-btn-ghost adm-btn-sm" id="usageRefresh" type="button">{usage_refresh}</button>
        </div>
        <div class="adm-toolbar adm-usage-filters">
          <select id="usageModel" aria-label="{filter_model}"></select>
          <select id="usageTask" aria-label="{filter_task}">
            <option value="">{all_tasks}</option>
            <option value="panel">{panel}</option>
            <option value="discover">discover</option>
            <option value="translate">translate</option>
            <option value="quiz">quiz</option>
            <option value="compress">compress</option>
            <option value="other">other</option>
          </select>
          <select id="usageSite" aria-label="{filter_site}">
            <option value="">{all_sites}</option>
            <option value="ir">IR</option>
            <option value="com">COM</option>
          </select>
          <input type="date" id="usageFrom" aria-label="{from}">
          <input type="date" id="usageTo" aria-label="{to}">
        </div>
        <div id="usageBody"></div>
      </section>

      <!-- ---------- the recently added videos ---------- -->
      <section class="adm-card adm-area-videos">
        <div class="adm-card-head">
          <h2 class="adm-card-title">{videos}</h2>
          <span class="adm-count" id="videosCount">{videos_count}</span>
        </div>

        <div class="adm-toolbar">
          <input type="search" id="videoSearch" placeholder="{search_videos}" spellcheck="false">
        </div>

        <div class="adm-table-wrap">
          <table class="adm-table">
            <thead>
              <tr>
                <th scope="col">{col_id}</th>
                {col_fa_th}
                <th scope="col">{col_en}</th>
                <th scope="col">{col_channel}</th>
                <th scope="col">{col_status}</th>
                <th scope="col">{col_added}</th>
              </tr>
            </thead>
            <tbody id="videosBody"></tbody>
          </table>
        </div>
        <div class="adm-empty" id="videosEmpty">{no_videos}</div>
      </section>

    </div>

    <!-- ---------- the AI panel, on the right ---------- -->
    <div class="adm-side">
      <section class="adm-card adm-card-ai adm-area-side">
        <div class="adm-card-head">
          <h2 class="adm-card-title">{ai_title}</h2>
          <span class="adm-ai-pill">AI</span>
        </div>

        <div class="adm-conn" id="connState">
          <span class="adm-dot"></span>
          <b id="connLabel">—</b>
          <span class="adm-conn-meta" id="connMeta"></span>
        </div>

        <label class="adm-field">
          <span class="adm-label">{endpoint}</span>
          <input type="text" id="llmEndpoint" dir="ltr" spellcheck="false" placeholder="http://localhost:20128/v1">
        </label>

        <label class="adm-field">
          <span class="adm-label">{api_key}</span>
          <div class="adm-in-row">
            <input type="password" id="llmKey" dir="ltr" autocomplete="off" spellcheck="false" placeholder="••••••••">
            <button class="adm-btn adm-btn-ghost adm-btn-sm adm-btn-noflex" id="toggleKey" type="button">{show}</button>
          </div>
          <span class="adm-note" id="keyNote"></span>
        </label>

        <label class="adm-field">
          <span class="adm-label">{model}</span>
          <div class="adm-model-picker">
            <input type="search" id="modelFilter" dir="ltr" placeholder="{model_search}" spellcheck="false">
            <div class="adm-capfilters" id="capFilters"></div>
            <div class="adm-modellist" id="modelList" role="listbox" aria-label="{model_search}"></div>
            <span class="adm-note" id="modelCount"></span>
          </div>
          <input type="text" id="llmModel" dir="ltr" spellcheck="false" placeholder="{model_manual}">
          <div class="adm-msum" id="modelSummary" hidden></div>
          <div class="adm-actions">
            <button class="adm-btn adm-btn-ghost adm-btn-sm" id="modelsRefresh" type="button">{refresh_list}</button>
          </div>
        </label>

        <!-- the model detail lives inside the AI panel now -->
        <div class="adm-modeldetail" id="modelDetail" hidden></div>

        <div class="adm-actions">
          <button class="adm-btn adm-btn-ghost" id="testBtn" type="button">{test_conn}</button>
          <button class="adm-btn adm-btn-primary" id="saveLlmBtn" type="button">{save}</button>
        </div>

        <div class="adm-alert" id="llmMsg" role="status" hidden></div>
      </section>
    </div>

  </div>
</div>

<div class="adm-toast" id="toast" role="status" aria-live="polite"></div>

<!-- The modules first: admin.js drives them, so they must be defined
     before it runs. Each one is self-contained and waits for the session. -->
<script src="models.js"></script>
<script src="ops.js"></script>
<script src="admin.js"></script>
</body>
</html>
"""

CANON = {
    'ir': {
        'canonical': 'https://matinr997.github.io/np-next/admin/',
        'canonical_fa': 'https://matinr997.github.io/np-next/admin/',
        'canonical_en': 'https://matinr997.github.io/np-next/com/admin/',
        'og_locale': 'fa_IR', 'root': '../', 'out': 'admin/index.html',
    },
    'en': {
        'canonical': 'https://matinr997.github.io/np-next/com/admin/',
        'canonical_fa': 'https://matinr997.github.io/np-next/admin/',
        'canonical_en': 'https://matinr997.github.io/np-next/com/admin/',
        'og_locale': 'en_US', 'root': '../../', 'out': 'com/admin/index.html',
    },
}


def main():
    for key, strings, which in (('fa', IR, 'ir'), ('en', EN, 'en')):
        data = dict(strings)
        data.update(CANON[which])
        # the "panel" task name is the same in both
        data['panel'] = 'پنل' if key == 'fa' else 'panel'
        out = os.path.join(ROOT, CANON[which]['out'])
        html = TEMPLATE.format(**data)
        with open(out, 'w', encoding='utf-8') as f:
            f.write(html)
        print('%s  %d lines' % (CANON[which]['out'], html.count('\n') + 1))


if __name__ == '__main__':
    main()
