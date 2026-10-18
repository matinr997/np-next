/* NursePlus — Account Dashboard UI layer (shared ir/com; RTL comes from <html dir>) */
// per-deployment config: ir uses config-ir.js, com uses config-com.js (set by entry)
const SITE = window.__NP_ACCOUNT_SITE || { id:'ir', lang:'fa', dir:'rtl', currency:'IRT', gateway:'zarinpal' };
import { IS_COM, BASE, FA, L, esc, fmtInt, pct, getUser, getStats, getVideos } from './account-core.js';
import { initShell } from './shell.js';

/* ---------------- i18n ---------------- */
const S = {
  account:      ['حساب کاربری', 'Account'],
  manage:       ['پروفایل خود را مدیریت کنید', 'Manage your profile'],
  profile:      ['پروفایل', 'Profile'],
  billing:      ['صورتحساب', 'Billing'],
  settings:     ['تنظیمات', 'Settings'],
  analytics:    ['آمار من', 'My Analytics'],
  cme:          ['دوره‌های CME', 'CME'],
  signout:      ['خروج', 'Sign out'],
  personalInfo: ['اطلاعات شخصی', 'Personal Info'],
  education:    ['اطلاعات تحصیلی', 'Education Information'],
  extraBenefits:['مزایای تکمیلی', 'Extra Benefits'],
  fullName:     ['نام و نام خانوادگی', 'Full name'],
  email:        ['ایمیل', 'Email address'],
  password:     ['رمز عبور', 'Password'],
  credentialsNote:['مدیریت اطلاعات ورود از تنظیمات پروفایل انجام می‌شود.',
                   'Sign-in details are managed from your profile settings.'],
  fieldYear:    ['رشته و سال فارغ‌التحصیلی', 'Field and Year'],
  faculty:      ['دانشکده یا تخصص', 'Faculty or specialty'],
  timezone:     ['منطقهٔ زمانی', 'Timezone'],
  customize:    ['شخصی‌سازی', 'Customize'],
  linkedin:     ['لینکدین', 'LinkedIn'],
  birthday:     ['تاریخ تولد', 'Birthday'],
  addInfo:      ['افزودن اطلاعات', 'Add your information'],
  optionalNote: ['این بخش کاملاً اختیاری است و برای استفادهٔ پایه لازم نیست.',
                 'Entirely optional — not required for basic access.'],
  billingDetails:['جزئیات صورتحساب', 'Billing details'],
  terms:        ['قوانین و شرایط', 'Terms and Conditions'],
  package:      ['بسته', 'Package'],
  status:       ['وضعیت', 'Status'],
  changePkg:    ['تغییر بسته', 'Change Package'],
  active:       ['فعال', 'Active'],
  free:         ['رایگان', 'Free'],
  expires:      ['انقضا', 'Expires'],
  notSet:       ['ثبت نشده', 'Not set'],
  gatewayNote:  ['پرداخت واقعی پس از اتصال به درگاه انجام می‌شود؛ وضعیت نهایی را سرور تأیید می‌کند.',
                 'Live payments activate once the gateway is connected; the server verifies final status.'],
  learningSet:  ['تنظیمات یادگیری', 'Learning settings'],
  videos:       ['ویدیوها', 'Videos'],
  videosDesc:   ['تنظیم پخش خودکار ویدیوی بعدی', 'Autoplay behaviour for the next video'],
  autoplay:     ['پخش خودکار', 'Autoplay'],
  schedules:    ['برنامهٔ مطالعه', 'Study schedules'],
  schedulesDesc:['مدیریت یا بایگانی برنامه‌های مطالعه', 'Manage or archive your study plans'],
  openSched:    ['باز کردن', 'Open'],
  access:       ['دسترسی حساب', 'Account access'],
  accessDesc:   ['نشست‌های فعال این دستگاه', 'Active session on this device'],
  daily:        ['تمرین روزانه', 'Daily practice'],
  dailyDesc:    ['تعداد سؤال آزمون و یادآور مطالعه', 'Quiz length and study reminder'],
  qLen:         ['طول آزمون', 'Quiz length'],
  reminder:     ['یادآور مطالعه', 'Study reminder'],
  off:          ['خاموش', 'Off'],
  on:           ['روشن', 'On'],
  help:         ['راهنما', 'Help'],
  helpText:     ['برای هر سؤالی دربارهٔ ویدیوها، آزمون یا اشتراک کمک می‌خواهید؟',
                 'Need help with videos, quizzes or your subscription?'],
  helpCenter:   ['مرکز راهنمایی', 'Help Center'],
  overview:     ['نمای کلی داده', 'Overview Data'],
  reports:      ['گزارش‌ها', 'Reports'],
  archNote:     ['داده‌ها بر اساس فعالیت ثبت‌شده در همین دستگاه محاسبه می‌شود.',
                 'Figures are calculated from activity recorded on this device.'],
  startDate:    ['از تاریخ', 'Start Date'],
  endDate:      ['تا تاریخ', 'End Date'],
  groupBy:      ['گروه‌بندی', 'Group by'],
  day:          ['روز', 'Day'], week:['هفته','Week'], month:['ماه','Month'], quarter:['فصل','Quarter'],
  sessions:     ['نشست‌ها', 'Sessions'],
  sessionsNote: ['روزهایی که در آن وارد حساب شدید', 'Days you signed in'],
  export:       ['خروجی CSV', 'Export CSV'],
  videosWatched:['ویدیوهای تماشاشده', 'Videos Watched'],
  allTime:      ['از ابتدا', 'All-time'],
  watchedNote:  ['ویدیوهایی که حداقل ۸۰٪ آن‌ها تماشا شده', 'Videos watched at least 80%'],
  watchVideo:   ['تماشای ویدیو', 'Watch a video'],
  noActivity:   ['هنوز فعالیتی ثبت نشده است', 'No activity recorded yet'],
  questions:    ['سؤالات پاسخ‌داده', 'Questions Answered'],
  qNote:        ['مجموع سؤال‌هایی که پاسخ داده‌اید', 'Total questions you have answered'],
  takeQuiz:     ['شرکت در آزمون', 'Take a quiz'],
  library:      ['کتابخانه', 'Library'],
  selectTopics: ['انتخاب موضوعات', 'Select topics'],
  videoTopics:  ['موضوعات ویدیو', 'Video Topics'],
  apply:        ['اعمال', 'Apply'], cancel:['انصراف','Cancel'],
  noReports:    ['برای این بازه و موضوعات داده‌ای موجود نیست', 'No data for this range and topic selection'],
  cmeTitle:     ['دوره‌های CME', 'CME courses'],
  cmeEmpty:     ['هنوز دورهٔ CME فعالی وجود ندارد. به‌محض اضافه شدن، اینجا نمایش داده می‌شود.',
                 'No CME activity is available yet — it will appear here once published.'],
  backTo:       ['بازگشت به ویدیوها', 'Back to videos'],
  comingSoon:   ['به‌زودی', 'Coming soon'],
  devMode:      ['حالت توسعه — داده‌ها از همین مرورگر خوانده می‌شود؛ پس از اتصال PHP/MySQL داده‌های واقعی نمایش داده می‌شود.',
                 'Development mode — data is read from this browser; real data appears once PHP/MySQL is connected.'],
};

/* ---------------- topics (from the real videos.json taxonomy) -------- */
function topicGroups(videos){
  /* classify on the English key (stable), display the localized label */
  const bodyRe = /(Cardio|Respir|Endocr|GI|Neuro|Anatom|Physiol|Micro|Path|Epidem|OB|Gyn)/i;
  const seen = new Map();
  videos.forEach(v => {
    const key = v.cat_en || v.cat;
    const lbl = FA ? (v.cat || v.cat_en) : key;
    if (!seen.has(key)) seen.set(key, lbl);
  });
  const groups = { body: [], courses: [] };
  seen.forEach((lbl, key) => { (bodyRe.test(key) ? groups.body : groups.courses).push({ key, lbl }); });
  return [
    { h: L('دوره‌های پرستاری', 'Nursing courses'), items: groups.courses },
    { h: L('دستگاه‌ها و علوم پایه', 'Body systems & sciences'), items: groups.body },
  ];
}

/* ============================ render ============================ */
const I = FA ? 0 : 1;   // S[key][I] -> fa when FA, else en
const $ = (s, r = document) => r.querySelector(s);
const el = (h) => { const d = document.createElement('div'); d.innerHTML = h.trim(); return d.firstElementChild; };

function row(label, value, action){
  return `<div class="arow">
    <div class="arow-l"><div class="alab">${label}</div><div class="aval">${value}</div></div>
    ${action || ''}
  </div>`;
}
function disabledBtn(label){ return `<button class="abtn ghost" disabled title="${esc(L('پس از اتصال به سرور فعال می‌شود','Enabled once the backend is connected'))}">${label}</button>`; }
function linkBtn(href, label, cls){ return `<a class="abtn ${cls || ''}" href="${href}">${label}</a>`; }

function avatar(user, big){
  const ini = (user.name || '?').trim().split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase();
  return `<div class="avatar ${big ? 'big' : ''}">${esc(ini)}</div>`;
}

async function render(){
  const [user, stats, videos] = await Promise.all([getUser(), getStats(), getVideos()]);
  const wrap = $('#accMain');
  $('#accUser').innerHTML = avatar(user) + `<div><div class="aname">${esc(user.name)}</div>
    <div class="amail">${esc(user.email || L('ایمیل ثبت نشده','No email on file'))}</div></div>`;

  const groups = topicGroups(videos);

  wrap.innerHTML = `
    <div class="acc-page" data-p="profile"></div>
    <div class="acc-page" data-p="billing"></div>
    <div class="acc-page" data-p="settings"></div>
    <div class="acc-page" data-p="analytics"></div>
    <div class="acc-page" data-p="cme"></div>`;

  /* ---------- PROFILE ---------- */
  wrap.querySelector('[data-p=profile]').innerHTML = `
    <h1 class="atitle">${S.personalInfo[I]}</h1>
    <div class="acard">
      ${row(S.fullName[I], esc(user.name) || '—', disabledBtn(L('ویرایش','Edit')))}
      ${row(S.email[I], esc(user.email) || '<span class="muted">—</span>', disabledBtn(L('ویرایش','Edit')))}
      ${row(S.password[I], '<span class="masked">••••••••••</span>', '')}
      <div class="anote">${S.credentialsNote[I]}</div>
    </div>
    <h1 class="atitle sm">${S.education[I]}</h1>
    <div class="acard">
      ${row(S.fieldYear[I], `<span class="muted">${S.notSet[I]}</span>`, disabledBtn(S.customize[I]))}
      ${row(S.faculty[I],   `<span class="muted">${S.notSet[I]}</span>`, disabledBtn(S.customize[I]))}
      ${row(S.timezone[I],  `<span class="muted">${esc(Intl.DateTimeFormat().resolvedOptions().timeZone || '—')}</span>`, '')}
    </div>
    <h1 class="atitle sm">${S.extraBenefits[I]}</h1>
    <div class="acard">
      ${row(S.linkedin[I], `<span class="muted">${S.addInfo[I]}</span><div class="ahint">${L('برای معرفی حرفه‌ای خود','For your professional profile')}</div>`, '')}
      ${row(S.birthday[I], `<span class="muted">${S.addInfo[I]}</span>`, '')}
      <div class="anote">${S.optionalNote[I]}</div>
    </div>`;

  /* ---------- BILLING ---------- */
  const plan = user.plan === 'premium' ? L('Premium', 'Premium') : L('رایگان', 'Free');
  wrap.querySelector('[data-p=billing]').innerHTML = `
    <h1 class="atitle">${S.billingDetails[I]} <a class="aterms" href="#">${S.terms[I]}</a></h1>
    <div class="acard">
      ${row(S.package[I], `<b>${esc(plan)}</b>`, linkBtn(BASE + 'premium.html', S.changePkg[I], 'blue'))}
      ${row(S.status[I], `<span class="pill ${user.plan === 'premium' ? 'ok' : ''}">${user.plan === 'premium' ? S.active[I] : S.free[I]}</span>`, '')}
      ${row(S.expires[I], user.planExpires ? esc(user.planExpires) : `<span class="muted">—</span>`, '')}
      <div class="anote">${S.gatewayNote[I]}</div>
    </div>`;

  /* ---------- SETTINGS ---------- */
  wrap.querySelector('[data-p=settings]').innerHTML = `
    <div class="acol">
      <div class="acard">
        <h2 class="acard-h">${S.learningSet[I]}</h2>
        ${row(S.videos[I] + ' — ' + S.videosDesc[I], '', `<label class="sw"><input type="checkbox" id="setAuto"><span></span></label>`)}
        ${row(S.schedules[I] + ' — ' + S.schedulesDesc[I], '', linkBtn(BASE + 'schedule.html', S.openSched[I], 'blue'))}
        ${row(S.daily[I] + ' — ' + S.qLen[I],
          `<select class="asel" id="setQLen"><option>3</option><option>5</option><option>10</option></select>`, '')}
        ${row(S.daily[I] + ' — ' + S.reminder[I],
          '', `<label class="sw"><input type="checkbox" id="setRem"><span></span></label>`)}
      </div>
      <div class="acard help">
        <div class="helpill">🩺</div>
        <h2 class="acard-h">${S.help[I]}</h2>
        <p class="muted">${S.helpText[I]}</p>
        ${disabledBtn(S.helpCenter[I])}
      </div>
    </div>`;

  /* ---------- ANALYTICS (Overview + Reports tabs) ---------- */
  const st = stats, dev = st.source === 'local';
  const vDone = (st.videos && st.videos.watched) || 0;
  const qA = (st.quiz && st.quiz.answered) || 0;
  wrap.querySelector('[data-p=analytics]').innerHTML = `
    <div class="atabs"><button class="atab on" data-t="ov">${S.overview[I]}</button>
      <button class="atab" data-t="rp">${S.reports[I]}</button></div>
    ${dev ? `<div class="anote dev">${S.devMode[I]}</div>` : ''}
    <div class="afilters">
      <label>${S.startDate[I]} <input type="date" id="fFrom"></label>
      <label>${S.endDate[I]} <input type="date" id="fTo"></label>
      <div class="aseg">${[S.day[I], S.week[I], S.month[I], S.quarter[I]]
        .map((g, i) => `<button class="segb ${i === 0 ? 'on' : ''}" data-g="${i}">${g}</button>`).join('')}</div>
    </div>
    <div class="pane-ov">
      <div class="acard two">
        <div class="cleft">
          ${avatar(user, true)}
          <div class="aname">${esc(user.name)}</div>
          <div class="amail">${esc(user.email || '—')}</div>
          <div class="kv"><span>${L('آخرین بازدید','Last seen')}</span><b>${esc((st.sessions && st.sessions.lastSeen) || '—')}</b></div>
          <div class="kv"><span>${L('پیوستگی ورود','Login streak')}</span><b>${fmtInt((st.sessions && st.sessions.streak) || 0)}</b></div>
          <div class="kv"><span>${L('بهترین پیوستگی','Best streak')}</span><b>${fmtInt((st.sessions && st.sessions.best) || 0)}</b></div>
        </div>
        <div class="cright">
          <div class="chead">${S.sessions[I]}</div>
          <div class="csub muted">${S.sessionsNote[I]}</div>
          <div class="acts">${linkBtn('#', S.export[I], 'ghost')}</div>
          <div class="chart" data-chart="sessions"></div>
          <div class="cempty">${S.noActivity[I]}</div>
        </div>
      </div>

      <div class="acard two">
        <div class="cleft">
          <div class="chead">${S.videosWatched[I]}</div>
          <div class="chip">${S.allTime[I]}</div>
          <div class="bignum">${fmtInt(vDone)}</div>
          <div class="csub muted">${S.watchedNote[I]}</div>
        </div>
        <div class="cright">
          <div class="chead">${S.videosWatched[I]}</div>
          <div class="csub muted">${S.watchedNote[I]}</div>
          <div class="cempty">${vDone ? '' : S.noActivity[I]}</div>
          <div class="acts">${linkBtn(BASE + 'index.html', S.watchVideo[I], 'blue')}</div>
        </div>
      </div>

      <div class="acard two">
        <div class="cleft">
          <div class="chead">${S.questions[I]}</div>
          <div class="chip">${S.allTime[I]}</div>
          <div class="bignum">${fmtInt(qA)}</div>
          <div class="csub muted">${S.qNote[I]}</div>
        </div>
        <div class="cright">
          <div class="chead">${S.questions[I]}</div>
          <div class="csub muted">${S.qNote[I]}</div>
          <div class="chart" data-chart="quiz"></div>
          <div class="cempty">${qA ? '' : S.noActivity[I]}</div>
          <div class="acts">${linkBtn(BASE + 'index.html?v=oNEBmBtBvtw', S.takeQuiz[I], 'blue')}</div>
        </div>
      </div>
    </div>
    <div class="pane-rp" hidden>
      <div class="rp-controls">
        <span class="chip">${S.library[I]}</span>
        <button class="abtn ghost" id="rpTopics">${S.selectTopics[I]}</button>
        <span class="muted" id="rpSel"></span>
      </div>
      <div class="acard"><div class="cempty">${S.noReports[I]}</div></div>
    </div>`;

  /* ---------- CME ---------- */
  wrap.querySelector('[data-p=cme]').innerHTML = `
    <h1 class="atitle">${S.cmeTitle[I]}</h1>
    <div class="acard"><div class="cempty">${S.cmeEmpty[I]}</div></div>`;

  /* ---------------- charts (tiny inline SVG, no dependency) -------- */
  wrap.querySelectorAll('[data-chart]').forEach(node => {
    const days = (st.sessions && st.sessions.days) || [];
    const vals = days.map(d => Number(d.v) || 0);
    if (!vals.some(Boolean)) { node.hidden = true; return; }
    const max = Math.max.apply(null, vals) || 1;
    const W = 320, H = 90, bw = 18, gap = 6;
    const bars = vals.map((v, i) => {
      const h = Math.max(3, (v / max) * (H - 16));
      return `<rect x="${i * (bw + gap)}" y="${H - h}" width="${bw}" height="${h}" rx="2" fill="#0875E1" opacity="${0.45 + 0.55 * (v / max)}"/>`;
    }).join('');
    node.innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" role="img">
      <line x1="0" y1="${H - 1}" x2="${W}" y2="${H - 1}" stroke="#E5E7EB"/>
      ${bars}</svg>`;
  });

  /* ---------------- interactions ---------------- */
  const paneOf = (p) => wrap.querySelector('[data-p=' + p + ']');

  /* analytics tabs + filters */
  const ov = wrap.querySelector('.pane-ov'), rp = wrap.querySelector('.pane-rp');
  wrap.querySelectorAll('.atab').forEach(b => b.addEventListener('click', () => {
    wrap.querySelectorAll('.atab').forEach(x => x.classList.toggle('on', x === b));
    const isOv = b.dataset.t === 'ov';
    ov.hidden = !isOv; rp.hidden = isOv;
  }));
  wrap.querySelectorAll('.segb').forEach(b => b.addEventListener('click', () => {
    wrap.querySelectorAll('.segb').forEach(x => x.classList.toggle('on', x === b));
  }));

  /* reports topic modal */
  const m = $('#tpModal');
  const sel = new Set(); const lbl = new Map();
  $('#rpTopics').addEventListener('click', () => {
    $('#tpBody').innerHTML = groups.map(g => `<div class="tpg"><div class="tpgh">${esc(g.h)}</div>
      ${g.items.map(t => `<button class="tpc ${sel.has(t.key) ? 'on' : ''}" data-t="${esc(t.key)}" data-l="${esc(t.lbl)}">${esc(t.lbl)}</button>`).join('')}</div>`).join('');
    m.hidden = false;
  });
  $('#tpBody').addEventListener('click', (e) => {
    const b = e.target.closest('.tpc'); if (!b) return;
    const t = b.dataset.t;
    sel.has(t) ? sel.delete(t) : sel.add(t);
    b.classList.toggle('on', sel.has(t));
    lbl.set(t, b.dataset.l || t);
  });
  const closeM = () => { m.hidden = true; };
  $('#tpClose').addEventListener('click', closeM);
  $('#tpCancel').addEventListener('click', () => { sel.clear(); closeM(); });
  $('#tpApply').addEventListener('click', () => {
    $('#rpSel').textContent = sel.size ? Array.from(sel).map(k => lbl.get(k) || k).slice(0, 3).join('، ') + (sel.size > 3 ? '…' : '') : '';
    closeM();
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !m.hidden) closeM(); });

  /* settings toggles persist locally (device preference) */
  const K_PREF = 'np_acc_pref';
  let pref = {}; try { pref = JSON.parse(localStorage.getItem(K_PREF) || '{}'); } catch (e) {}
  const auto = $('#setAuto'), rem = $('#setRem'), qlen = $('#setQLen');
  if (auto) auto.checked = !!pref.auto;
  if (rem) rem.checked = !!pref.rem;
  if (qlen) qlen.value = String(pref.qlen || 3);
  const savePref = () => { pref.auto = auto.checked; pref.rem = rem.checked; pref.qlen = +qlen.value;
    try { localStorage.setItem(K_PREF, JSON.stringify(pref)); } catch (e) {} };
  if (auto) auto.addEventListener('change', savePref);
  if (rem) rem.addEventListener('change', savePref);
  if (qlen) qlen.addEventListener('change', savePref);
}

/* ---------------- boot ---------------- */
function go(page){
  document.querySelectorAll('.acc-page').forEach(p => p.hidden = p.dataset.p !== page);
  document.querySelectorAll('.anav a, .anav button').forEach(a => a.classList.toggle('on', a.dataset.p === page));
  /* keep the query string intact: ?plan=premium and friends must survive routing */
  try { history.replaceState(null, '', location.pathname + location.search + '#' + page); } catch (e) {}
}
/* the entry uses `await import()`, so DOMContentLoaded may already have fired */
async function bootAccount(){

  document.getElementById('accRoot').innerHTML = `
   <div class="acc-wrap">
    <aside class="acc-side">
      <div class="ahead"><h2>${S.account[I]}</h2><p class="muted">${S.manage[I]}</p></div>
      <div class="asuser" id="accUser"></div>
      <div class="anav">
        ${[['profile', '👤'], ['billing', '💳'], ['settings', '⚙️'], ['analytics', '📊'], ['cme', '🎓']]
          .map(([p, ic]) => `<button data-p="${p}"><span class="i">${ic}</span><span class="t">${S[p][I]}</span><span class="ar">›</span></button>`).join('')}
        <button data-p="signout"><span class="i">⏏</span><span class="t">${S.signout[I]}</span></button>
      </div>
      <div class="aside-foot">${linkBtn(BASE + 'index.html', S.backTo[I], 'ghost')}</div>
    </aside>
    <main class="acc-main" id="accMain"></main>
   </div>
    <div class="tpmodal" id="tpModal" hidden>
      <div class="tp">
        <div class="tp-h"><h3>${S.videoTopics[I]}</h3><button id="tpClose" aria-label="Close">✕</button></div>
        <div class="tp-div"></div>
        <div class="tp-body" id="tpBody"></div>
        <div class="tp-f">
          <button class="abtn ghost" id="tpCancel">${S.cancel[I]}</button>
          <button class="abtn blue" id="tpApply">${S.apply[I]}</button>
        </div>
      </div>
    </div>`;
  await render();
  document.querySelectorAll('.anav button').forEach(b => b.addEventListener('click', () => {
    if (b.dataset.p === 'signout') { try { sessionStorage.removeItem('np_user'); } catch (e) {} location.href = BASE + 'index.html'; return; }
    go(b.dataset.p);
  }));
  const start = (location.hash || '').replace('#', '') || 'profile';
  go(['profile','billing','settings','analytics','cme'].indexOf(start) > -1 ? start : 'profile');
  initShell();
}

if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',bootAccount,{once:true}); else bootAccount();
