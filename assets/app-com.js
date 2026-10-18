/* Nurse Plus site bootstrap — page-head inline <script> sets __NP_* globals BEFORE this module */
import { SKELETON_HTML } from '../lib/skeleton.js';
import { mount } from '../lib/player-core.js';
import { initShell } from '../assets/shell.js?v=2';
document.body.innerHTML = SKELETON_HTML.replace(/^[\s\S]*?<body[^>]*>|<\/body>\s*$/g,'').trim();

/* expose inline-handler fns to window (module scope keeps them private otherwise) */
import * as CORE from '../lib/player-core.js';
for (const k of ['showList','openDetail','seek','ans','addNote','delNote','setNLang','setQLang','accToggle','mSearchGo','setPane','toggleSeen','toggleBm','setSubMode','renderGrid','renderDetail','renderTrans','qzPick','qzSel','qzClozeCheck','qzTap','qzDragStart','qzDragEnd','qzDragAllow','qzDragHover','qzDropZone','qzDropPool','qzNext','qzPrev','qzReset','qzShow','qzDndCheck','ctCopy','plInfo','trToggle','trJump','ctQual','ctQualSet','plAi','plPip','ctChap','ctQualSet']) {
  try { Object.defineProperty(window, k, {value: CORE[k], configurable:true, writable:true }); } catch(e){}
}

mount();
initShell();
