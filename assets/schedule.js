/* ===== Study Schedule dashboard (self-contained, localStorage-only) =====
   IDs: du* ; has zero coupling to lib/player-core.js / app-*.js.
   localStorage:
     np_sched_data — {endDate:'2026-10-26', topics:[{id,fa,en,mins}], done:[{id killed,date:'YYYY-MM-DD',day}] }
     np_prefs_sched — {devAlloc, overPct, predLabel}   ← live(3) customizer */
const SCHED_KEY = 'np_sched_data';
const PREFS_KEY = 'np_prefs_sched';

let Data   = { endDate:'2026-10-26', topics:[], done:[] };
let Prefs  = { devAlloc:'bracket', overPct:0, predLabel:'…' };
let curDay = new Date();               // selected date in calendar
let view   = 'day';                    // day | week | month
let SEO = [];

const IMG = { hero:'assets/hero-char.png', clock:'assets/deadline-clock.png', star:'assets/star-char.png' };
try{ if(!location.pathname.endsWith('/com/schedule.html')) document.querySelectorAll('.dup-mascot,.du-dclock,.du-star').forEach(function(im){ if(im.getAttribute('src')&&im.getAttribute('src').indexOf('assets/')!==0) im.src=im.src.replace('../assets/','assets/'); }); }catch(e){}
try{ if(location.pathname.endsWith('/com/schedule.html')) document.querySelectorAll('.dup-mascot,.du-dclock,.du-star').forEach(function(im){ im.src='../'+im.getAttribute('src').replace('../','').replace('assets/','assets/'); }); }catch(e){}

const $  = id => document.getElementById(id);
let _schToastT=null;
function schToast(txt){ var e=$('schToast'); if(!e){ e=document.createElement('div'); e.id='schToast'; e.className='sch-toast'; document.body.appendChild(e); }
  e.textContent=txt; e.classList.add('show'); if(_schToastT) clearTimeout(_schToastT); _schToastT=setTimeout(function(){ e.classList.remove('show'); },2200); }
function toast(t){ schToast(t); }
const fa = s => document.documentElement.lang==='fa';
const L  = (faS,enS) => fa()?faS:enS;
const n  = x => fa()? Number(x).toLocaleString('fa-IR') : String(x);
const dayK = d => d.toISOString().slice(0,10);

/* ---------- data ---------- */
function loadAll(){
  try{ Data  = JSON.parse(localStorage.getItem(SCHED_KEY)) || null; }catch(e){}
  if(!Data || !Data.topics) Data = { endDate:'2026-10-26', topics:seedTopics(), done:[] };
  try{ Prefs  = JSON.parse(localStorage.getItem(PREFS_KEY)) || null; }catch(e){}
  if(!Prefs)  Prefs = { devAlloc:'bracket', overPct:0, predLabel:'…' };
}
function saveAll(){
  try{ localStorage.setItem(SCHED_KEY, JSON.stringify(Data)); }catch(e){}
  try{ localStorage.setItem(PREFS_KEY, JSON.stringify(Prefs)); }catch(e){}
}
function seedTopics(){
  return [
    {id:'t1', fa:'سونداژ و بلع (NG-tube، aspiration)', en:'Swan-Ganz & swallowing (NG-tube, aspiration)', mins:8,  d1:1, icon:'https://fonts.gstatic.com/s/i/notoemoji/latest/1f9ea/72.png'},
    {id:'t2', fa:'ضدمیکروبی‌ها: đơn (vancomycin, aminoglycoside)', en:'Antimicrobials: dosing (vancomycin, aminoglycoside)', mins:10, d1:0, icon:'https://fonts.gstatic.com/s/i/notoemoji/latest/1f489/72.png'},
    {id:'t3', fa:'سیستم قلبی-عروقی (semilunar)', en:'Cardiovascular system (semilunar)', mins:75, d1:0, icon:'https://fonts.gstatic.com/s/i/notoemoji/latest/1f493/72.png'}
  ];
}

/* ---------- helpers ---------- */
const EN_PATH = ['today','min',''] ;
function fmtD(d){ // Sunday, October 18th
  const sx = d.getDate(), suf=(sx%10===1&&sx!==11)?'st':(sx%10===2&&sx!==12)?'nd':(sx%10===3&&sx!==13)?'rd':'th';
  const M=['January','February','March','April','May','June','July','August','September','October','November','December'];
  const WD=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  if(fa()) return ['یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه','جمعه','شنبه'][d.getDay()]+'، '+D2(d)+' '+['','ژانویه','فوریه','مارس','آوریل','مه','ژوئن','ژوئیه','اوت','سپتامبر','اکتبر','نوامبر','دسامبر'][d.getMonth()+1]+' '+fa2(d.getFullYear());
  return WD[d.getDay()]+', '+M[d.getMonth()]+' '+n(sx)+suf;
}
function fmtMonth(d){
  const M=['January','February','March','April','May','June','July','August','September','October','November','December'];
  return fa() ? ['','ژانویه','فوریه','مارس','آوریل','مه','ژوئن','ژوئیه','اوت','سپتامبر','اکتبر','نوامبر','دسامبر'][d.getMonth()+1]+' '+fa2(d.getFullYear())
              : M[d.getMonth()]+' '+d.getFullYear();
}
function endD(){ try{ return new Date(Data.endDate+'T00:00:00'); }catch(e){ return new Date(); } }
function D2(d){ try{ return Number(d.getDate()).toLocaleString('fa-IR'); }catch(e){ return d.getDate(); } }
function daysAway(){ return Math.max(0, Math.round((endD() - new Date(new Date().toDateString()))/86400000)); }
function dayTotal(d){
  const k=dayK(d);
  let m=0; Data.topics.forEach(t=>{
    m += (Data.done.some(x=>x.id===t.id && dayK(new Date(x.date))===k)) ? t.mins : t.mins*0;
  });
  return {
    assigned: Data.topics.reduce((a,t)=>a+t.mins,0),
    done:     Data.topics.filter(t=>Data.done.some(x=>x.id===t.id && dayK(new Date(x.date))===k)).reduce((a,t)=>a+t.mins,0)
  };
}
/* the schedule uses "total assigned minutes" as denominator */
function assignedTotal(){ return Data.topics.reduce((a,t)=>a+ (+t.mins||0), 0); }
function doneTotalAll(){
  return Data.topics.reduce((a,t)=>a + (Data.done.filter(x=>x.id===t.id).length ? t.mins : 0), 0);
}

/* ---------- renderers ---------- */
function paintCells(monthDate){
  const M=['January','February','March','April','May','June','July','August','September','October','November','December'];
  $('duMonth').textContent = fa()
    ? ['','ژانویه','فوریه','مارس','آوریل','مه','ژوئن','ژوئیه','اوت','سپتامبر','اکتبر','نوامبر','دسامبر'][monthDate.getMonth()+1]+' '+fa2(monthDate.getFullYear())
    : M[monthDate.getMonth()]+' '+monthDate.getFullYear();
  const first = new Date(monthDate.getFullYear(), monthDate.getMonth(), 1);
  const skip  = first.getDay();
  const last  = new Date(monthDate.getFullYear(), monthDate.getMonth()+1, 0).getDate();
  const todayK= dayK(new Date());
  let html='<i class="du-hour">Su</i><i class="du-hour">Mo</i><i class="du-hour">Tu</i><i class="du-hour">We</i><i class="du-hour">Th</i><i class="du-hour">Fr</i><i class="du-hour">Sa</i>';
  for(let i=0;i<skip;i++) html+='<i class="du-cell du-empty" style="grid-column:'+ (i+1) +'"></i>';
  for(let drec=1;drec<=last;drec++){
    const d=new Date(monthDate.getFullYear(),monthDate.getMonth(),drec), k=dayK(d);
    let cls='du-cell';
    if(k===todayK) cls+=' du-today';
    else if(Data.done.some(x=>dayK(new Date(x.date))===k && +x.mins>0)) cls+=' du-study';
    if(k===Data.endDate) cls+=' du-end';
    html+='<span class="'+cls+'"><button class="du-dayb" data-k="'+k+'" type="button">'+n(drec)+'</button></span>';
  }
  $('duCells').innerHTML=html;
  document.querySelectorAll('#duCells .du-dayb').forEach(b=>b.addEventListener('click',function(){ curDay=new Date(b.dataset.k+'T00:00:00'); paintView(); }));
}
function fa2(nn){ try{ return Number(nn).toLocaleString('fa-IR'); }catch(e){ return nn; } }

function paintView(){
  const isM = (view==='month');
  $('duDate').textContent = isM ? fmtMonth(curDay) : fmtD(curDay);
  $('duBlocks').innerHTML = Data.topics.map(function(t){ return loop(t, {
    done: (isM||view==='week') ? Data.done.some(function(x){ return x.id===t.id; })
                               : Data.done.some(function(x){ return x.id===t.id && dayK(new Date(x.date))===dayK(curDay); })
  }); }).join('');
  drawStatistics();
  drawOverall();
}
function loop(t, ctx){
  const IsDone = ctx && ctx.done;
  return '<div class="du-block'+(IsDone?' is-done':'')+'" data-id="'+t.id+'" '+
         'onclick="TTR(this,event)" >'+
           '<span class="du-bico"><img src="'+t.icon+'" alt="" width="30" height="30"></span>'+
           '<span class="du-bname">'+(fa()?t.fa:t.en)+'</span>'+
           '<span class="du-times"><i class="du-mindot'+(IsDone?' dn':'')+'"><svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6L9 17l-5-5"/></svg></i><span class="du-mins">'+n(t.mins)+''+L(' دقیقه',' mins')+'</span></span>'+
           '<svg class="du-caret" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>'+
         '</div>';
}
function TTR(el, e){
  const id=el.dataset.id, k=dayK(curDay);
  var t=null; for(var i=0;i<Data.topics.length;i++){ if(Data.topics[i].id===id){ t=Data.topics[i]; break; } }
  const mins=t?t.mins:15;
  const has=Data.done.some(x=>x.id===id && dayK(new Date(x.date))===k);
  if(!has) Data.done.push({id:id, mins:mins, date:k});
  else Data.done=Data.done.filter(x=>!(x.id===id && dayK(new Date(x.date))===k));
  saveAll(); paintView(); paintCells(curDay);
}
function sumMonth(md){
  let s=0; Data.done.forEach(x=>{ const d=new Date(x.date); if(d.getMonth()===md.getMonth() && d.getFullYear()===md.getFullYear()) s+=(x.mins||0); });
  return s;
}
function drawStatistics(){
  const {done}=dayTotal(curDay);
  $('duStickMin').textContent=n(done)+L(' دقیقه',' mins');
  const overall=Math.round(100*doneTotalAll()/Math.max(1,assignedTotal()));
  $('duProgFill').style.width=overall+'%';
  $('duProgPct').textContent=n(overall)+'%';
  $('duTueInfo').textContent = view==='day'
    ? L('برای علامت‌زدن یک ماده به‌عنوان «خوانده‌شد» روی ردیفش کلیک کن.','Click a row to mark it studied on this date.')
    : L('نمای کلی — برای هر روز، تب Day را انتخاب کن.','Overview shown — switch to Day to edit one date.');
  Prefs.overPct=overall; saveAll();
}
function drawOverall(){
  const pct=Math.round(100*doneTotalAll()/Math.max(1,assignedTotal()));
  Prefs.overPct=pct;
  $('duOverallPct').textContent=n(pct)+'%';
  const ring=$('duRing'); const C=2*Math.PI*41;
  ring.style.strokeDasharray=C; ring.style.strokeDashoffset=C*(1-pct/100);
  const bad=pct<50;
  $('duStatusB').textContent = fa() ? 'Off track' : 'Off track';  /* EN per reference */
  $('duStatusB').className = 'du-statusb '+(bad?'du-statusb-red':'du-statusb-soft');
}

/* ---------- events + boot ---------- */
function devAllocToggle(){ /* opens popup flow described in prebtn */ }
function devAlloc3(){
  const pick=window.prompt(L('کدام پیش‌چک‌لیست؟ (۱، ۲ یا ۳)','Choose a pre-study checklist: 1, 2 or 3'), '1');
  if(!pick) return;
  Prefs.predLabel = L('پیش‌چک‌لیست '+pick+' انتخاب شد', 'Checklist '+pick+' selected');
  saveAll();
  var sp=document.getElementById('preLabel'); if(sp) sp.textContent=Prefs.predLabel;
  toast(L('پیش‌چک‌لیست ذخیره شد','Saved'));
}
document.querySelectorAll('#duToggles button').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('#duToggles button').forEach(x=>x.classList.remove('on'));
  b.classList.add('on'); view=b.dataset.v;
}));
if($('duPm')) $('duPm').onclick=()=>{ curDay=new Date(curDay.getFullYear(),curDay.getMonth()-1,1); paintCells(curDay); };
if($('duNx')) $('duNx').onclick=()=>{ curDay=new Date(curDay.getFullYear(),curDay.getMonth()+1,1); paintCells(curDay); };
if($('duPrev')) $('duPrev').onclick=()=>{ curDay.setDate(curDay.getDate()-1); paintView(); };
if($('duNext')) $('duNext').onclick=()=>{ curDay.setDate(curDay.getDate()+1); paintView(); };
if($('duToday')) $('duToday').onclick=()=>{ curDay=new Date(); paintView(); setActiveBadge(); };
if($('duAdd')) $('duAdd').onclick=()=>{ toast(L('در نسخهٔ پیش‌نمایش، افزودن مادهٔ دلخواه به‌زودی فعال می‌شود','Custom material is coming soon in this preview')); };
if($('duReset')) $('duReset').onclick=()=>{ try{ localStorage.removeItem(SCHED_KEY); localStorage.removeItem(PREFS_KEY); }catch(e){} location.reload(); };
function setActiveBadge(){ $('duActiveNum').textContent=n(1); }
function boot(){
  loadAll();
  try{ if(!Prefs.predLabel || Prefs.predLabel==='…') Prefs.predLabel = L('انتخاب پیش‌چک‌لیست (۱/۲/۳)','Choose a pre-study checklist (1/2/3)'); }catch(e){}
  $('preLabel').textContent=Prefs.predLabel||$('preLabel').textContent;
  $('duNextDate').textContent=fmtD(endD());
  $('duAway').textContent=L(n(daysAway())+' روز مانده', n(daysAway())+' days away');
  $('duOmsg').textContent=L('You\'re behind pace and should reach your goal 11% behind schedule.','You\'re behind pace and should reach your goal 11% behind schedule.');
  paintCells(curDay); paintView(); setActiveBadge();
  window.addEventListener('resize',function(){ requestAnimationFrame(drawOverall); });
}
document.readyState==='loading' ? document.addEventListener('DOMContentLoaded',boot) : boot();

window.devAllocToggle=devAllocToggle;
window.devAlloc3=devAlloc3;
window.TTR=TTR;
