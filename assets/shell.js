/* Nurse Plus — persistent app shell: hamburger + left drawer menu.
   Auto-imported by app-ir.js/app-com.js and the premium pages.
   Language is taken from <html lang>. RTL sites mirror to the start side
   automatically (logical properties in CSS). */
export function initShell(){
  if (window.__npShellRan) return; window.__npShellRan = true;

  const lang = document.documentElement.getAttribute('lang') === 'fa' ? 'fa' : 'en';
  const rtl  = lang === 'fa';
  const S = {
    menu:    lang==='fa' ? 'منو' : 'Menu',
    close:   lang==='fa' ? 'بستن' : 'Close',
    home:    lang==='fa' ? 'خانه' : 'Home',
    askAI:   lang==='fa' ? 'دستیار هوشمند (Ask AI)' : 'Ask AI',
    beta:    'BETA',
    myTools: lang==='fa' ? 'ابزارهای من' : 'My tools',
    vTopics: lang==='fa' ? 'موضوعات ویدیو' : 'Video Topics',
    lists:   lang==='fa' ? 'پلی‌لیست‌ها' : 'Playlists',
    qbank:   lang==='fa' ? 'بانک سؤال' : 'QBank',
    sched:   lang==='fa' ? 'برنامه مطالعه' : 'Study Schedule',
    settings:lang==='fa' ? 'تنظیمات' : 'Settings',
    help:    lang==='fa' ? 'مرکز راهنمایی' : 'Help center',
    privacy: lang==='fa' ? 'حریم خصوصی' : 'Privacy',
    plans:   lang==='fa' ? 'پلن‌ها' : 'Plans',
    vPlans:  lang==='fa' ? 'مشاهده پلن‌ها' : 'View plans',
    cta:     lang==='fa' ? 'خرید اشتراک' : 'Purchase plan',
    trial:   lang==='fa' ? 'Free Trial · آزمایشی' : 'Free Trial',
    premium: lang==='fa' ? 'Premium · فعال' : 'Premium',
  };

  const plan  = (()=>{ try{ return (window.__NP_USER&&window.__NP_USER.plan)||(new URLSearchParams(location.search).get('plan'))||'free'; }catch(e){ return 'free'; } })();
  let name; try{ name = (window.__NP_USER&&window.__NP_USER.name) || sessionStorage.getItem('np_user') || (lang==='fa'?'مهمان':'Guest'); }catch(e){ name = lang==='fa'?'مهمان':'Guest'; }
  const brand = 'Nurse <b>Plus</b>';
  const home = (location.pathname.endsWith('/premium.html')||location.pathname.endsWith('premium.html')) ? (document.querySelector('link[href*="globals.css"]')? ((document.querySelector('link[href*="globals.css"]').getAttribute('href').startsWith('../'))?'index.html':'index.html') : 'index.html') : 'index.html';

  const svg = (d, extra)=>'<svg viewBox="0 0 24 24" aria-hidden="true">'+(d||'')+(extra||'')+'</svg>';
  const ico = {
    home:  svg('<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10.5V20h13v-9.5"/>'),
    ask:   svg('<circle cx="12" cy="12" r="3.2"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M19.1 4.9l-1.8 1.8M6.7 17.3l-1.8 1.8"/>'),
    topics:svg('<rect x="4" y="3.5" width="15" height="17" rx="2.5"/><polygon points="10,9 14.5,12 10,15" fill="#086288" stroke="none"/>'),
    list:  svg('<path d="M5 6h11M5 12h11M5 18h11"/><circle cx="19.5" cy="6" r="1.4"/><circle cx="19.5" cy="12" r="1.4"/><circle cx="19.5" cy="18" r="1.4"/>'),
    qbank: svg('<path d="M6 3.5h9.5L19 7v13.5H6z"/><path d="M9 9h7M9 12.5h7M9 16h4"/>'),
    sched: svg('<rect x="4" y="5" width="16" height="15" rx="2.5"/><path d="M4 9.5h16M8 3.5v3M16 3.5v3"/>'),
    gear:  svg('<circle cx="12" cy="12" r="3.2"/><path d="M12 2.8v2.4M12 18.8v2.4M2.8 12h2.4M18.8 12h2.4M5.4 5.4l1.7 1.7M16.9 16.9l1.7 1.7M18.6 5.4l-1.7 1.7M7.1 16.9l-1.7 1.7"/>'),
    help:  svg('<circle cx="12" cy="12" r="9"/><path d="M9.6 9.2a2.5 2.5 0 1 1 3.7 2.7c-.7.5-1.3 1-1.3 2"/><circle cx="12" cy="17" r="0.4" fill="#086288"/>'),
    shield:svg('<path d="M12 3 5 6v5c0 5 3.4 8 7 10 3.6-2 7-5 7-10V6z"/>'),
    plansItem: svg('<path d="M12 3l2.6 5.3 5.9.9-4.2 4.1 1 5.8L12 16.4 6.7 19.1l1-5.8L3.5 9.2l5.9-.9z"/>'),
  };

  const drawer = document.createElement('aside');
  drawer.className = 'np-drawer';
  drawer.id = 'npDrawer';
  drawer.setAttribute('role','dialog');
  drawer.setAttribute('aria-modal','true');
  drawer.setAttribute('aria-label', S.menu);
  const initial = (name||'?').trim().charAt(0).toUpperCase();
  drawer.innerHTML = [
    '<div class="np-dhead">',
      '<div class="np-logo">', brand, '</div>',
      '<button class="np-x" id="npClose" aria-label="', S.close, '">', svg('<path d="M5 5l14 14M19 5L5 19"/>'), '</button>',
    '</div>',
    '<div class="np-user">',
      '<div class="np-av">', initial, '</div>',
      '<div><div class="np-uname"></div><span class="np-badge" id="npPlanBadge"></span></div>',
    '</div>',
    '<a class="np-cta" href="premium.html">', S.cta, '</a>',
    '<nav class="np-nav" aria-label="', S.menu, '">',
      '<ul class="np-items">',
        '<li><a class="np-item" href="', home, '">', ico.home, '<span>', S.home, '</span></a></li>',
        '<li><a class="np-item np-ask" href="#" data-np-noop>', ico.ask, '<span>', S.askAI, '</span><span class="np-beta">', S.beta, '</span></a></li>',
        '<li class="np-sec">', S.myTools, '</li>',
        '<li><a class="np-item" href="#" data-np-noop>', ico.topics, '<span>', S.vTopics, '</span></a></li>',
        '<li><a class="np-item" href="#" data-np-noop>', ico.list,  '<span>', S.lists,  '</span></a></li>',
        '<li><a class="np-item" href="#" data-np-noop>', ico.qbank, '<span>', S.qbank, '</span></a></li>',
        '<li><a class="np-item" href="#" data-np-noop>', ico.sched, '<span>', S.sched, '</span></a></li>',
        '<li><a class="np-item" href="#" data-np-noop>', ico.gear,  '<span>', S.settings, '</span></a></li>',
        '<li><a class="np-item" href="#" data-np-noop>', ico.help,  '<span>', S.help, '</span></a></li>',
        '<li><a class="np-item" href="#" data-np-noop>', ico.shield,'<span>', S.privacy, '</span></a></li>',
      '</ul>',
    '</nav>',
    '<div class="np-bottom">',
      '<div class="np-sec">', S.plans, '</div>',
      '<a class="np-item" href="premium.html">', ico.plansItem, '<span>', S.vPlans, '</span></a>',
      '<p class="np-footnote">© Nurse Plus</p>',
    '</div>',
  ].join('');

  drawer.querySelector('.np-uname').textContent = name;
  drawer.querySelector('#npPlanBadge').textContent = plan === 'premium' ? S.premium : S.trial;

  const ov = document.createElement('div'); ov.className='np-ov'; ov.id='npOv';
  const ham = document.createElement('button');
  ham.className='np-ham'; ham.id='npHam';
  ham.setAttribute('aria-label', S.menu);
  ham.setAttribute('aria-expanded','false');
  ham.innerHTML = '<span></span><span></span><span></span>';

  document.body.appendChild(ov);
  document.body.appendChild(drawer);
  document.body.appendChild(ham);

  let openT;
  const open = () => {
    drawer.classList.add('open'); ov.classList.add('show');
    ham.classList.add('open'); ham.setAttribute('aria-expanded','true');
    document.body.classList.add('np-lock');
  };
  const close = () => {
    drawer.classList.remove('open'); ov.classList.remove('show');
    ham.classList.remove('open'); ham.setAttribute('aria-expanded','false');
    document.body.classList.remove('np-lock');
  };
  ham.addEventListener('click', () => drawer.classList.contains('open') ? close() : open());
  ov.addEventListener('click', close);
  drawer.querySelector('#npClose').addEventListener('click', close);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
  drawer.querySelectorAll('.np-item').forEach(a => a.addEventListener('click', () => close()));
  drawer.querySelectorAll('[data-np-noop]').forEach(a => a.addEventListener('click', e => e.preventDefault()));
}

/* Auto-start on pages that don't call initShell explicitly (player pages set
   window.__npShellAuto=false in the head, then call initShell() after mount). */
if (typeof window !== 'undefined' && window.__npShellAuto !== false) {
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => initShell());
  else initShell();
}
