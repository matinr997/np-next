/* Nurse Plus site bootstrap — page-head inline <script> sets __NP_* globals BEFORE this module */
import { SKELETON_HTML } from '../lib/skeleton.js';
import { mount } from '../lib/player-core.js';
import { initShell } from '../assets/shell.js';
document.body.innerHTML = SKELETON_HTML.replace(/^[\s\S]*?<body[^>]*>|<\/body>\s*$/g,'').trim();
mount();
initShell();
