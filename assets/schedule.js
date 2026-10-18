/* ===== Study Schedule v2 — real video plan (data/videos.json) =====
   - Day view   : clean to-do list — video NAME navigates to the video page (?v=ID), checkbox marks done
   - Week view  : 7 day cells with small topic+video tags
   - Month view : full month grid, tags inside each day cell
   - Pre-study checklist removed per spec
   localStorage: np_sched_data = { endDate, plan:{'YYYY-MM-DD':[videoId...]}, done:[videoId...] } */
const KEY='np_sched_data';
const $=id=>document.getElementById(id);
const FA=()=>document.documentElement.lang==='fa';
const L=(f,e)=>FA()?f:e;
const n=x=>{ try{ return FA()?Number(x).toLocaleString('fa-IR'):String(x); }catch(e){ return String(x); } };
const VBASE = location.pathname.indexOf('/com/')>=0 ? '../index.html' : 'index.html';
const DPATH = location.pathname.indexOf('/com/')>=0 ? '../data/videos.json' : 'data/videos.json';
const dayK=d=>d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');

let VIDEOS=[], Data={endDate:'2026-10-26', plan:{}, done:[]};
let curDay=new Date(), view='day', curMonth=new Date();
let _schToastT=null;
function schToast(txt){ var e=$('schToast'); if(!e){ e=document.createElement('div'); e.id='schToast'; e.className='sch-toast'; document.body.appendChild(e); }
  e.textContent=txt; e.classList.add('show'); if(_schToastT) clearTimeout(_schToastT); _schToastT=setTimeout(function(){ e.classList.remove('show'); },2200); }
function toast(t){ schToast(t); }

function durM(dur){ if(!dur) return 0; var p=String(dur).split(':').map(Number);
  if(p.length===3) return Math.round(p[0]*60+p[1]+p[2]/60);
  if(p.length===2) return Math.round(p[0]+p[1]/60); return 0; }
function vById(id){ for(var i=0;i<VIDEOS.length;i++) if(VIDEOS[i].id===id) return VIDEOS[i]; return null; }
function vName(v){ return FA()?v.fa:v.en; }
function vTopic(v){ return FA()?v.cat:v.cat_en; }
function realToday(){ return new Date(new Date().toDateString()); }

/* ---------- plan (generated once, then persisted) ---------- */
function genPlan(){
  var end; try{ end=new Date(Data.endDate+'T00:00:00'); }catch(e){ end=realToday(); }
  var start=realToday();
  var days=Math.max(1, Math.round((end-start)/86400000)+1);
  var byTopic={}; VIDEOS.forEach(function(v){ (byTopic[v.cat_en]||(byTopic[v.cat_en]=[])).push(v.id); });
  var ordered=[]; Object.keys(byTopic).sort().forEach(function(t){ ordered=ordered.concat(byTopic[t]); });
  var plan={};
  ordered.forEach(function(id,i){
    var k=dayK(new Date(start.getTime()+Math.min(days-1, Math.floor(i*days/ordered.length))*86400000));
    (plan[k]||(plan[k]=[])).push(id);
  });
  return plan;
}
function planFor(k){ return (Data.plan&&Data.plan[k])||[]; }
function dayMins(k){ return planFor(k).reduce(function(a,id){ var v=vById(id); return a+(v?durM(v.dur):0); },0); }

/* ---------- small renderers ---------- */
function tagHtml(id, cls){
  var v=vById(id); if(!v) return '';
  var done=Data.done.indexOf(id)>=0;
  return '<a class="'+cls+(done?' done':'')+'" href="'+VBASE+'?v='+v.id+'" title="'+vName(v).replace(/"/g,'&quot;')+'">'+
    '<b>'+vTopic(v)+'</b><span>'+vName(v)+'</span><i>'+n(durM(v.dur))+'m</i></a>';
}
function fmtD(d){
  var sx=d.getDate(), suf=(sx%10===1&&sx!==11)?'st':(sx%10===2&&sx!==12)?'nd':(sx%10===3&&sx!==13)?'rd':'th';
  var M=['January','February','March','April','May','June','July','August','September','October','November','December'];
  var WD=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  if(FA()) return ['یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه','جمعه','شنبه'][d.getDay()]+'، '+n(sx)+' '+
    ['','ژانویه','فوریه','مارس','آوریل','مه','ژوئن','ژوئیه','اوت','سپتامبر','اکتبر','نوامبر','دسامبر'][d.getMonth()+1];
  return WD[d.getDay()]+', '+M[d.getMonth()]+' '+n(sx)+suf;
}
function fmtMonth(d){
  var M=['January','February','March','April','May','June','July','August','September','October','November','December'];
  return FA() ? ['','ژانویه','فوریه','مارس','آوریل','مه','ژوئن','ژوئیه','اوت','سپتامبر','اکتبر','نوامبر','دسامبر'][d.getMonth()+1]+' '+n(d.getFullYear())
              : M[d.getMonth()]+' '+d.getFullYear();
}

/* ---------- sidebar mini calendar ---------- */
function paintCells(md){
  $('duMonth').textContent=fmtMonth(md);
  var skip=new Date(md.getFullYear(),md.getMonth(),1).getDay();
  var last=new Date(md.getFullYear(),md.getMonth()+1,0).getDate();
  var tK=dayK(realToday());
  var html='<i class="du-hour">Su</i><i class="du-hour">Mo</i><i class="du-hour">Tu</i><i class="du-hour">We</i><i class="du-hour">Th</i><i class="du-hour">Fr</i><i class="du-hour">Sa</i>';
  for(var i=0;i<skip;i++) html+='<i class="du-cell du-empty" style="grid-column:'+(i+1)+'"></i>';
  for(var drec=1;drec<=last;drec++){
    var d=new Date(md.getFullYear(),md.getMonth(),drec), k=dayK(d), cls='du-cell';
    if(k===tK) cls+=' du-today';
    else if(planFor(k).length) cls+=' du-study';
    if(k===Data.endDate) cls+=' du-end';
    html+='<span class="'+cls+'"><button class="du-dayb" data-k="'+k+'" type="button">'+n(drec)+'</button></span>';
  }
  $('duCells').innerHTML=html;
  var bs=$('duCells').querySelectorAll('.du-dayb');
  for(var j=0;j<bs.length;j++){ (function(b){ b.addEventListener('click',function(){ curDay=new Date(b.dataset.k+'T00:00:00'); paintView(); }); })(bs[j]); }
}

/* ---------- main views ---------- */
function renderDay(){
  var k=dayK(curDay), ids=planFor(k);
  if(!ids.length) return '<div class="du-empty-note">'+L('برای این روز ماده‌ای برنامه‌ریزی نشده — از نمای Week یا Month استفاده کن.','Nothing scheduled for this day — check the Week or Month view.')+'</div>';
  return ids.map(function(id){
    var v=vById(id); if(!v) return '';
    var done=Data.done.indexOf(id)>=0;
    return '<div class="du-item'+(done?' is-done':'')+'">'+
      '<button class="du-chk" data-v="'+id+'" aria-label="'+L('علامت زدن','mark done')+'"'+(done?' data-on="1"':'')+'><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg></button>'+
      '<a class="du-vname" href="'+VBASE+'?v='+v.id+'">'+vName(v)+'</a>'+
      '<span class="du-topic">'+vTopic(v)+'</span>'+
      '<span class="du-mins">'+n(durM(v.dur))+L(' دقیقه','m')+'</span>'+
    '</div>';
  }).join('');
}
function renderWeek(){
  var ws=new Date(new Date(curDay.getTime()-curDay.getDay()*86400000).toDateString());
  var tK=dayK(realToday());
  var html='<div class="du-week">';
  for(var i=0;i<7;i++){
    var d=new Date(ws.getTime()+i*86400000), k=dayK(d);
    var tags=planFor(k).map(function(id){ return tagHtml(id,'du-wtag'); }).join('');
    html+='<div class="du-wday'+(k===tK?' is-today':'')+(d<realToday()?' is-past':'')+'">'+
      '<div class="du-whd"><span>'+['Su','Mo','Tu','We','Th','Fr','Sa'][i]+'</span><b>'+n(d.getDate())+'</b></div>'+
      '<div class="du-wtags">'+(tags||'<i class="du-rest">—</i>')+'</div>'+
    '</div>';
  }
  return html+'</div>';
}
function renderMonth(){
  var md=curMonth, skip=new Date(md.getFullYear(),md.getMonth(),1).getDay();
  var last=new Date(md.getFullYear(),md.getMonth()+1,0).getDate();
  var tK=dayK(realToday());
  var html='<div class="du-mgrid">'+
    '<div class="du-mhd">Su</div><div class="du-mhd">Mo</div><div class="du-mhd">Tu</div><div class="du-mhd">We</div><div class="du-mhd">Th</div><div class="du-mhd">Fr</div><div class="du-mhd">Sa</div>';
  for(var i=0;i<skip;i++) html+='<div class="du-mcell du-mempty"></div>';
  for(var drec=1;drec<=last;drec++){
    var d=new Date(md.getFullYear(),md.getMonth(),drec), k=dayK(d);
    var tags=planFor(k).map(function(id){ return tagHtml(id,'du-wtag'); }).join('');
    html+='<div class="du-mcell'+(k===tK?' is-today':'')+(k===Data.endDate?' is-end':'')+(d<realToday()?' is-past':'')+'">'+
      '<div class="du-mnum">'+n(drec)+'</div><div class="du-mtags">'+tags+'</div></div>';
  }
  return html+'</div>';
}
function paintView(){
  if(view==='month'){
    $('duDate').textContent=fmtMonth(curMonth);
    $('duBlocks').innerHTML=renderMonth();
    $('duTueInfo').textContent=L('کل ماه — هر برچسب: موضوع + ویدیو؛ برای باز شدن ویدیو رویش بزن.','Whole month — each tag: topic + video; tap to open the video.');
  } else if(view==='week'){
    $('duDate').textContent=fmtD(curDay);
    $('duBlocks').innerHTML=renderWeek();
    $('duTueInfo').textContent=L('نمای هفته — برنامهٔ هر روز. با ‹ › هفته عوض کن.','Week view — each day plan. Use ‹ › to move weeks.');
  } else {
    $('duDate').textContent=fmtD(curDay);
    $('duBlocks').innerHTML=renderDay();
    $('duTueInfo').textContent=L('روی نام ویدیو بزن تا صفحهٔ پخش باز شود؛ روی ✓ بزن تا «خوانده‌شده» شود.','Tap a video name to open its page; tap ✓ to mark it done.');
  }
  drawSticky(); drawOverall();
}
function drawSticky(){
  var k=dayK(realToday()), ids=planFor(k);
  var mins=dayMins(k);
  var done=ids.filter(function(id){ return Data.done.indexOf(id)>=0; }).length;
  $('duStickMin').textContent=n(mins)+L(' دقیقه',' mins');
  var pct=ids.length? Math.round(100*done/ids.length):0;
  $('duProgFill').style.width=pct+'%';
  $('duProgPct').textContent=n(pct)+'%';
}
function drawOverall(){
  var pct=Math.round(100*Data.done.length/Math.max(1,VIDEOS.length));
  $('duOverallPct').textContent=n(pct)+'%';
  var ring=$('duRing'), C=2*Math.PI*41;
  ring.style.strokeDasharray=C; ring.style.strokeDashoffset=C*(1-pct/100);
  $('duStatusB').textContent='Off track';
  $('duStatusB').className='du-statusb '+(pct<50?'du-statusb-red':'du-statusb-soft');
}

/* ---------- boot + events ---------- */
function save(){ try{ localStorage.setItem(KEY, JSON.stringify(Data)); }catch(e){} }
function endCard(){
  var end; try{ end=new Date(Data.endDate+'T00:00:00'); }catch(e){ end=realToday(); }
  $('duNextDate').textContent=L('تاریخ پایان: ','Next end date is ')+fmtD(end);
  var away=Math.max(0, Math.round((end-realToday())/86400000));
  $('duAway').textContent=L(away+' روز مانده', away+' days away');
}
function badge(){ $('duActiveNum').textContent=n(1); }
function setToggle(v){ var tbs=document.querySelectorAll('#duToggles button');
  for(var j=0;j<tbs.length;j++) tbs[j].classList.toggle('on', tbs[j].dataset.v===v); }
function wire(){
  var tbs=document.querySelectorAll('#duToggles button');
  for(var i=0;i<tbs.length;i++){ (function(b){
    b.addEventListener('click',function(){ setToggle(b.dataset.v); view=b.dataset.v; paintView(); });
  })(tbs[i]); }
  $('duPm').onclick=function(){ curMonth=new Date(curMonth.getFullYear(),curMonth.getMonth()-1,1); paintCells(curMonth); if(view!=='month'){ setToggle('month'); view='month'; } paintView(); };
  $('duNx').onclick=function(){ curMonth=new Date(curMonth.getFullYear(),curMonth.getMonth()+1,1); paintCells(curMonth); if(view!=='month'){ setToggle('month'); view='month'; } paintView(); };
  $('duPrev').onclick=function(){ if(view==='month'){ curMonth=new Date(curMonth.getFullYear(),curMonth.getMonth()-1,1); paintCells(curMonth); } else { curDay=new Date(curDay.getTime()-(view==='week'?7:1)*86400000); } paintView(); };
  $('duNext').onclick=function(){ if(view==='month'){ curMonth=new Date(curMonth.getFullYear(),curMonth.getMonth()+1,1); paintCells(curMonth); } else { curDay=new Date(curDay.getTime()+(view==='week'?7:1)*86400000); } paintView(); };
  $('duToday').onclick=function(){ curDay=realToday(); curMonth=new Date(); paintCells(curMonth); paintView(); };
  $('duAdd').onclick=function(){ schToast(L('در نسخهٔ پیش‌نمایش، افزودن مادهٔ دلخواه به‌زودی فعال می‌شود','Custom material is coming soon in this preview')); };
  $('dupReset').onclick=function(){ try{ localStorage.removeItem(KEY); }catch(e){} location.reload(); };
  document.addEventListener('click',function(e){
    var chk=e.target.closest?e.target.closest('.du-chk'):null;
    if(chk){ var id=chk.dataset.v, i=Data.done.indexOf(id);
      if(i<0) Data.done.push(id); else Data.done.splice(i,1);
      save(); paintView(); paintCells(curMonth);
      schToast(Data.done.indexOf(id)>=0?L('انجام شد ✓','Done ✓'):L('برگشت به لیست','Back to list')); }
  });
}
function boot(){
  try{ Data=JSON.parse(localStorage.getItem(KEY))||null; }catch(e){ Data=null; }
  fetch(DPATH).then(function(r){ return r.json(); }).then(function(list){
    VIDEOS=list;
    if(!Data || !Data.plan || !Data.endDate){
      var _end=(Data&&Data.endDate)||'2026-10-26';
      Data={endDate:_end, plan:{}, done:[]};
      Data.plan=genPlan(); save();   /* Data must have endDate BEFORE genPlan runs */
    }
    endCard(); paintCells(curMonth); paintView(); badge(); wire();
  }).catch(function(){
    $('duBlocks').innerHTML='<div class="du-empty-note">'+L('خطا در بارگذاری فهرست ویدیوها.','Failed to load the video list.')+'</div>';
  });
}
document.readyState==='loading' ? document.addEventListener('DOMContentLoaded',boot) : boot();
