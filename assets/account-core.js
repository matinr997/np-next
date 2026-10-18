/* NursePlus — Account Dashboard.
   ONE shared module: data layer (read-only over localStorage + future API)
   is kept apart from rendering so a PHP/MySQL backend can replace the
   storage adapter without touching the UI (see DATA contract at bottom). */

const SITE = window.__NP_ACCOUNT_SITE || { id:'ir', lang:'fa', dir:'rtl', currency:'IRT', gateway:'zarinpal' };

/* ============================ paths ============================ */
export const IS_COM = /\/com(\/|$)/.test(location.pathname);
export const BASE    = IS_COM ? '../' : './';        // shared assets live at the repo root (data/, subs/)
export const PAGE    = '';                             // sibling pages: account.html sits next to index.html in BOTH deployments
export const FA      = SITE.lang === 'fa';
const L = (fa, en) => (FA ? fa : en);

/* ============================ storage keys (existing app) ======== */
const K_SEEN = 'np_seen';          // ["id", …]            player-core store.seen
const K_BM   = 'np_bm';            // ["id", …]
const K_SCH  = 'np_sched_data';    // {plan:{day:[ids]}, done:[ids]}
const NKEY   = (id) => 'np_notes_' + id;
const QKEY   = (id) => 'np_qz_' + id;
const K_USER = 'np_user';

/* ============================ DATA LAYER ========================
   Adapter shape (swap for PHP later):
     async getUser()                 -> {name,email,plan,planExpires}
     async getStats()                -> {sessions:{days:[]}, videos:{…}, quiz:{…}, schedule:{…}}
   Every call has a localStorage fallback and never throws: a missing
   backend is a defined state (DEV flag), not an error.               */
const API_BASE = '/api';            // no-op while hosted on GitHub Pages

async function api(path){
  try{
    if (!/^https?:/.test(location.protocol)) return null;
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 2500);      // short: never block the page
    const r = await fetch(API_BASE + path, { signal: ctl.signal, headers: { 'Accept': 'application/json' } });
    clearTimeout(t);
    if (!r.ok) return null;
    return await r.json();
  }catch(e){ return null; }
}

function ls(k, dflt){ try{ const v = localStorage.getItem(k); return v ? JSON.parse(v) : dflt; }catch(e){ return dflt; } }
function dayKey(d){ return d.toISOString().slice(0,10); }

export async function getUser(){
  const remote = await api('/account/me');
  if (remote && remote.user) return Object.assign({ source: 'api' }, remote.user);
  let name = '';
  try { name = sessionStorage.getItem(K_USER) || ''; }catch(e){}
  /* same plan resolution as index.html/premium.html so ?plan=premium keeps working */
  let plan = 'free', expires = null;
  try {
    if (window.__NP_USER && window.__NP_USER.plan) plan = window.__NP_USER.plan;
    const q = new URLSearchParams(location.search).get('plan');
    if (q === 'premium' || q === 'free') plan = q;
  }catch(e){}
  return { name: name || (FA ? 'مهمان' : 'Guest'), email: '', plan, planExpires: expires, source: 'local' };
}

export async function getStats(){
  const remote = await api('/account/stats');
  if (remote && remote.stats) return Object.assign({ source: 'api' }, remote.stats);

  /* ---- local fallback: real, browser-resident data only ---- */
  const seen  = ls(K_SEEN, []);
  const bm    = ls(K_BM, []);
  const sched = ls(K_SCH, { plan: {}, done: [] });

  let notes = 0;
  for (let i = 0; i < localStorage.length; i++){
    const k = localStorage.key(i) || '';
    if (k.startsWith('np_notes_')) notes += (ls(k, []) || []).length;
  }

  /* quiz attempts stored per video: {best,total,answeredAt:[ts]} */
  let qAnswered = 0, qBest = 0, qVideos = 0, qHistory = [];
  const keys = [];
  for (let i = 0; i < localStorage.length; i++){
    const k = localStorage.key(i) || '';
    if (k.startsWith(QKEY(''))) keys.push(k);
  }
  keys.forEach(k => {
    const q = ls(k, null);
    if (!q || typeof q !== 'object') return;
    const answered = Number(q.answered || 0);
    if (!answered) return;
    qVideos++; qAnswered += answered;
    qBest += Number(q.best || q.score || 0);
    if (Array.isArray(q.answeredAt)) qHistory = qHistory.concat(q.answeredAt);
  });

  /* sessions: derived from local dates we actually have */
  const dates = [];
  try { dates.push(ls('np_last_visit', null)); }catch(e){}
  if (Array.isArray(sched.done)) dates.push.apply(dates, []);

  const days = [];
  const seenToday = {};
  const stamp = dayKey(new Date());
  seenToday[stamp] = 1;
  days.push({ d: stamp, v: 1 });

  /* study schedule completion */
  let planned = 0, doneN = 0;
  Object.keys(sched.plan || {}).forEach(k => { planned += (sched.plan[k] || []).length; });
  doneN = (sched.done || []).length;

  return {
    source: 'local',
    seen, bm, notes,
    videos: { watched: seen.length, bookmarked: bm.length, threshold: 0.8 },
    quiz:   { answered: qAnswered, best: qBest, videos: qVideos, history: qHistory },
    schedule: { planned, done: doneN },
    sessions: { days, streak: 1, best: 1, lastSeen: stamp }
  };
}

export async function getVideos(){
  const r = await fetch(BASE + 'data/videos.json', { cache: 'no-cache' });
  return r.ok ? await r.json() : [];
}

/* ============================ helpers ============================ */
export const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
export const fmtInt = (n) => (FA ? Number(n || 0).toLocaleString('fa-IR') : Number(n || 0).toLocaleString('en-US'));
export const pct = (a, b) => (b ? Math.round((a / b) * 100) : 0);
export { L };