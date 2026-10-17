#!/usr/bin/env node
// One-time extraction: pull VIDEOS (fa) from the base template, CHEN (en chapters)
// + CM (category map) from mk4.py, quiz from quiz_now.json, subs into per-video files.
// Run: node scripts/extract-data.mjs
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SCRATCH = '/Users/matin/.hermes/profiles/brain-hub/cache/scratch';
const DESIGN = '/Users/matin/Documents/02-Areas/Nurseplus+/Azmoon nursefile/Site code desighn';

// 1) VIDEOS (with fa chapters) from the base template
const html = readFileSync(join(DESIGN, 'video-preview-pro.html'), 'utf8');
const vm = html.match(/const VIDEOS = (\[[\s\S]*?\]);/);
if (!vm) throw new Error('VIDEOS block not found');
const VIDEOS = eval(vm[1]);

// 2) CHEN (English chapters) + CM (category map) from mk4.py
const mk = readFileSync(join(SCRATCH, 'mk4.py'), 'utf8');
const chenSrc = mk.match(/CHEN\s*=\s*(\{[\s\S]*?\n\})/);
const CHEN = chenSrc ? eval('(' + chenSrc[1] + ')') : {};
const cmSrc = mk.match(/CM\s*=\s*(\{[\s\S]*?\})/);
const CM = cmSrc ? eval('(' + cmSrc[1] + ')') : {};
console.log('videos:', VIDEOS.length, '| CHEN keys:', Object.keys(CHEN).length, '| CM:', JSON.stringify(CM));

// 3) merge: fa chapters stay in ch, en chapters in ch_en, add cat_en
const out = VIDEOS.map(v => ({
  id: v.id,
  dur: v.dur,
  tr: !!v.tr,
  cat: v.cat,
  cat_en: CM[v.cat] || 'General',
  src: v.src,
  views: v.views || 0,
  publishedAt: v.publishedAt || '',
  fa: v.fa,
  en: v.en,
  sum: v.sum || '',
  sum_en: v.sum_en || '',
  ch: (v.ch || []).filter(c => c[0] !== '—'),
  ch_en: (CHEN[v.id] || []).filter(c => c[0] !== '—'),
}));
mkdirSync(join(ROOT, 'data'), { recursive: true });
writeFileSync(join(ROOT, 'data', 'videos.json'), JSON.stringify(out, null, 1));
console.log('videos.json:', out.length, 'videos; chapters fa/en:',
  out.reduce((a, v) => a + v.ch.length, 0), '/', out.reduce((a, v) => a + v.ch_en.length, 0));

// 4) quiz (order must match VIDEOS order: 3 per video)
const quiz = JSON.parse(readFileSync(join(SCRATCH, 'quiz_now.json'), 'utf8'));
writeFileSync(join(ROOT, 'data', 'quiz.json'), JSON.stringify(quiz, null, 1));
console.log('quiz.json:', quiz.length, 'questions; all have ts:', quiz.every(q => typeof q.ts === 'number'));

// 5) subs → one file per video (lazy-load at runtime)
const subs = JSON.parse(readFileSync(join(SCRATCH, 'subs_bilingual.json'), 'utf8'));
mkdirSync(join(ROOT, 'public', 'subs'), { recursive: true });
let cues = 0;
for (const [id, list] of Object.entries(subs)) {
  writeFileSync(join(ROOT, 'public', 'subs', id + '.json'), JSON.stringify(list));
  cues += list.length;
}
console.log('subs:', Object.keys(subs).length, 'files,', cues, 'cues total');
const missing = out.filter(v => !subs[v.id]).map(v => v.id);
if (missing.length) console.log('WARN videos without subs:', missing);
const noTr = out.filter(v => !v.tr).map(v => v.id);
console.log('videos with tr:false:', noTr);
