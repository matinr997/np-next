#!/usr/bin/env python3
"""Generate every SEO-visible artefact from seo/site.json + data/videos.json.

    python3 scripts/gen_seo.py

Produces:
  * canonical / hreflang / Open Graph / JSON-LD injected into the 8 static pages
  * videos/<slug>/  and  com/videos/<slug>/   dedicated watch pages (VideoObject)
  * topics/<slug>/  and  com/topics/<slug>/   topic landing pages
  * robots.txt, sitemap.xml, sitemap-video.xml, 404.html
  * data/seo.json  slug map consumed by the player to build card links

Run it after ANY change to seo/site.json, videos.json, or a page title. It is
idempotent: regenerating produces byte-identical output, which is what makes
stable URLs possible.
"""
import html, json, os, re, shutil, sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seo_config import (ROOT, SITE_JSON, esc, fmt_mmss, iso8601, jdump, load_site,
                        slugify, to_seconds, topic_slug, truncate, url, video_slug)

DEP = ['ir', 'com']
NOW = datetime.now(timezone.utc).strftime('%Y-%m-%d')

# Publication state machine. Only videos whose content is genuinely present and
# whose metadata has been reviewed are allowed into the sitemap; everything else
# is served noindex so it can never become thin indexable content.
VALID_STATUS = ('draft', 'processing', 'needs_review', 'published', 'archived')

WATCH_CSS = """
/* Scoped to .wp and aligned with assets/globals.css: same 14px radius, same
   #E3EEF7 hairline, same rgba(15,45,70,.05) shadow, same #086288 accent, same
   Inter+Vazirmatn stack. A watch page must LOOK like the product it belongs to. */
.wp{--ink:#12212e;--mut:#5a6b7a;--line:#E3EEF7;--acc:#086288;--acc2:#4D8DBA;--wash:#F5F8FA;
 /* same max-width as the app's own .wrap so the two never look like different products */
 max-width:1260px;margin:0 auto;padding:22px 18px 60px}
/* main + related sidebar, mirroring the app's own .d-grid split (1fr 340px / 18px) */
.wp-body{display:grid;grid-template-columns:minmax(0,1fr);gap:18px}
.wp-main,.wp-side{min-width:0}   /* min-width:0 stops a grid child from overflowing */
.wp *{box-sizing:border-box}
.wp a{color:#086288;text-decoration:none}
.wp a:hover{text-decoration:underline}
.wp .wp-crumb{font-size:14px;color:#5a6b7a;padding:18px 0 6px}
.wp .wp-crumb a{color:#5a6b7a}
.wp h1{font-size:clamp(22px,4.2vw,31px);line-height:1.32;margin:10px 0 14px;font-weight:800;
 color:#086288;letter-spacing:-.01em}
.wp h2{font-size:18.5px;margin:38px 0 12px;font-weight:700;color:#12212e;
 border-inline-start:4px solid #086288;padding-inline-start:11px}
.wp p{margin:0 0 14px;line-height:1.85}
.wp .wp-meta{display:flex;flex-wrap:wrap;gap:8px 14px;font-size:14px;color:#5a6b7a;margin:0 0 22px}
.wp .wp-player{position:relative;aspect-ratio:16/9;background:#000;border-radius:14px;overflow:hidden;
 box-shadow:0 10px 30px rgba(8,32,48,.14);margin:0 0 10px}
.wp .wp-player iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.wp .wp-bar{display:flex;gap:12px;align-items:center;margin:0 0 8px;padding:12px 14px;
 background:#F5F8FA;border:1px solid #E3EEF7;border-radius:14px;font-size:14px;color:#5a6b7a}
.wp .wp-bar img{width:92px;border-radius:8px;flex:none}
.wp .wp-bar strong{color:#12212e}
.wp .wp-ch{list-style:none;margin:0;padding:0;border:1px solid #E3EEF7;border-radius:14px;overflow:hidden;
 box-shadow:0 1px 2px rgba(15,45,70,.05)}
.wp .wp-ch li{border-bottom:1px solid #E3EEF7}
.wp .wp-ch li:last-child{border-bottom:0}
.wp .wp-ch a{display:flex;gap:14px;padding:11px 15px;font-size:15px;color:#12212e}
.wp .wp-ch a:hover{background:#F5F8FA;text-decoration:none}
.wp .wp-ch time{flex:none;color:#086288;font-weight:700;font-size:13px;min-width:54px;padding-top:2px;
 font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.wp .wp-obj{display:grid;gap:9px;margin:0;padding:0;list-style:none}
.wp .wp-obj li{background:#F5F8FA;border:1px solid #E3EEF7;border-radius:10px;padding:11px 15px;font-size:15px}
.wp .wp-rel{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px;margin:0;padding:0;list-style:none}
.wp .wp-rel a{display:block;background:#fff;border:1px solid #E3EEF7;border-radius:14px;padding:12px;
 color:#12212e;height:100%;box-shadow:0 1px 2px rgba(15,45,70,.05)}
.wp .wp-rel a:hover{border-color:#4D8DBA;text-decoration:none;box-shadow:0 6px 18px rgba(15,45,70,.10)}
.wp .wp-rel img{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:10px;margin-bottom:9px;background:#eef2f5}
.wp .wp-rel b{display:block;font-size:14px;font-weight:650;line-height:1.45;color:#086288}
.wp .wp-rel i{display:block;font-style:normal;font-size:12.5px;color:#5a6b7a;margin-top:5px}
.wp .wp-box{background:#F5F8FA;border:1px solid #E3EEF7;border-radius:12px;padding:15px 17px;font-size:14.5px;color:#5a6b7a}
.wp .wp-box strong{color:#12212e}
.wp .wp-cta{display:flex;flex-wrap:wrap;gap:11px;margin:26px 0 0}
.wp .wp-btn{display:inline-block;padding:12px 21px;border-radius:12px;font-weight:700;font-size:15px}
.wp .wp-btn.p{background:#086288;color:#fff}
.wp .wp-btn.p:hover{background:#075072;text-decoration:none}
.wp .wp-btn.s{background:#fff;color:#086288;border:1.5px solid #4D8DBA}
.wp .wp-foot{margin-top:52px;padding-top:22px;border-top:1px solid #E3EEF7;font-size:13.5px;color:#5a6b7a}
.wp .wp-foot p{margin:0 0 9px}
.wp .wp-foot strong{color:#12212e}
@media(min-width:1000px){
 .wp-body{grid-template-columns:minmax(0,1fr) 340px;align-items:start}
 .wp-side .wp-rel{grid-template-columns:1fr;gap:12px}
 .wp-side .wp-rel a{display:flex;gap:12px;padding:10px;align-items:flex-start}
 .wp-side .wp-rel img{width:104px;flex:none;margin-bottom:0}
 .wp-side .wp-rel b{font-size:13.5px}
 .wp-side .wp-rel i{margin-top:3px}
}
@media(max-width:1000px){.wp-side .wp-rel{grid-template-columns:repeat(auto-fill,minmax(210px,1fr))}}
@media(max-width:640px){
 .wp{padding:14px 12px 52px}
 .wp .wp-rel{grid-template-columns:1fr}
 .wp h2{margin:30px 0 10px}
 .wp .wp-bar{padding:10px}
}
@media(max-width:360px){.wp .wp-bar img{display:none}}
"""


# ---------------------------------------------------------------- data layer
def load_videos():
    with open(os.path.join(ROOT, 'data', 'videos.json'), encoding='utf-8') as f:
        return json.load(f)


def normalise(v):
    """Attach the derived fields every generator needs. Pure function of the
    source record + configured publication state, so output is reproducible."""
    o = dict(v)
    o['slug'] = video_slug(v)
    o['tsec'] = to_seconds(v.get('dur'))
    o['dur_txt'] = fmt_mmss(o['tsec']) if o['tsec'] else str(v.get('dur', ''))
    o['status'] = v.get('status') or 'published'
    assert o['status'] in VALID_STATUS, 'bad status %r for %s' % (o['status'], v['id'])
    o['indexable'] = bool(v.get('indexable', True)) and o['status'] == 'published'
    o['updated'] = v.get('updated') or v.get('publishedAt') or NOW
    # chapters -> ascii timestamps so they can be linked and put into Clip markup
    ch, ch_en = v.get('ch') or [], v.get('ch_en') or []
    o['chapters'] = []
    for i in range(max(len(ch), len(ch_en))):
        fa = ch[i] if i < len(ch) else ['', '']
        en = ch_en[i] if i < len(ch_en) else ['', '']
        t = to_seconds(fa[0] if fa and fa[0] else (en[0] if en else ''))
        o['chapters'].append({'sec': t, 'fa': (fa[1] if len(fa) > 1 else ''),
                              'en': (en[1] if len(en) > 1 else '')})
    o['chapters'] = [c for c in o['chapters'] if c['sec'] > 0]
    return o


def learning_points(o, dep):
    """Objectives derived from the video's own chapter titles. Nothing is
    invented: if a chapter is named, that topic is what the lesson covers."""
    keys = ['fa', 'en'] if dep == 'ir' else ['en', 'fa']
    pts = []
    for c in o['chapters']:
        label = (c[keys[0]] or c[keys[1]] or '').strip()
        if label and label not in pts:
            pts.append(label)
    if not pts:
        pts = [(o['sum'] if dep == 'ir' else o['sum_en'])[:150]]
    lead = 'در پایان این درس می‌توانید:' if dep == 'ir' else 'After this lesson you will be able to:'
    return lead, pts[:9]


def describe(o, dep, kind='video'):
    """Meta description. Built from real record fields only."""
    if kind == 'topic':
        n, mins = len(o['vids']), round(sum(x['tsec'] for x in o['vids']) / 60)
        if dep == 'ir':
            head = o['cat']
            return truncate('%s — %d درس پرستاری با متن کامل، سرفصل زمانی و آزمون NCLEX؛ حدود %d دقیقه آموزش. '
                            'منابع: %s.' % (head, n, mins, '، '.join(o['chans'])), 158)
        head = o['cat_en']
        return truncate('%s — %d nursing lessons with full transcripts, timestamped chapters and NCLEX '
                        'quizzes; about %d minutes. From %s.' % (head, n, mins, ', '.join(o['chans'])), 158)
    body = (o['sum'] if dep == 'ir' else o['sum_en']) or (o['fa'] if dep == 'ir' else o['en'])
    nch = len(o['chapters'])
    tail = (' با %d سرفصل زمانی، متن کامل و آزمون NCLEX.' % nch) if dep == 'ir' else \
           (' with %d timestamped chapters, a full transcript and an NCLEX quiz.' % nch)
    return truncate(body + tail, 158)


def titles(o, dep, site):
    """The <title> a SERP can actually display (~60 chars before it truncates),
    plus the full name for the page's own <h1> and og:title. Truncating the tag
    while the heading stays complete is the correct split: nothing is hidden from
    the reader, nothing is cut off in the search result."""
    full = o['fa'] if dep == 'ir' else o['en']
    brand = site['brand'][dep]
    room = 62 - len(brand) - 3
    head = full if len(full) <= room else full[:room].rsplit(' ', 1)[0].rstrip(' ,,:;—-')
    return '%s | %s' % (head, brand), full


# ---------------------------------------------------------------- head blocks
def head_tags(site, dep, path, title, desc, image, typ='website', extra_ld=None, og_title=None, noindex=None):
    """The complete SEO head for a generated page. Absolute URLs only, so the
    output is identical whether the site is served from a repo subpath or a
    domain root."""
    u = url(site, dep, path)
    other = 'com' if dep == 'ir' else 'ir'
    out = []
    out.append('<title>%s</title>' % esc(title))
    out.append('<meta name="description" content="%s">' % esc(desc))
    ni = site.get('noindex') if noindex is None else noindex
    if ni:
        out.append('<meta name="robots" content="noindex, nofollow">')
    else:
        out.append('<meta name="robots" content="index, follow, max-image-preview:large, '
                   'max-video-preview:-1">')
    out.append('<link rel="canonical" href="%s">' % esc(u))
    out.append('<link rel="alternate" hreflang="%s" href="%s">' % (site['lang'][dep], esc(u)))
    out.append('<link rel="alternate" hreflang="%s" href="%s">'
               % (site['lang'][other], esc(url(site, other, swap_prefix(path, dep, other)))))
    out.append('<meta property="og:type" content="%s">' % typ)
    out.append('<meta property="og:url" content="%s">' % esc(u))
    out.append('<meta property="og:title" content="%s">' % esc(og_title or title))
    out.append('<meta property="og:description" content="%s">' % esc(desc))
    out.append('<meta property="og:image" content="%s">' % esc(image))
    out.append('<meta property="og:image:width" content="1280">')
    out.append('<meta property="og:image:height" content="720">')
    out.append('<meta property="og:image:alt" content="%s">' % esc(title))
    out.append('<meta property="og:site_name" content="%s">' % esc(site['brand'][dep]))
    out.append('<meta property="og:locale" content="%s">' % ('fa_IR' if dep == 'ir' else 'en_US'))
    if site['social'].get('twitter'):
        out.append('<meta name="twitter:card" content="summary_large_image">')
        out.append('<meta name="twitter:site" content="%s">' % esc(site['social']['twitter']))
    else:
        out.append('<meta name="twitter:card" content="summary_large_image">')
    blocks = list(extra_ld or [])
    out.append('<script type="application/ld+json">%s</script>' % jdump(blocks))
    return '\n'.join(out)


def swap_prefix(path, frm, to):
    """Map a path from one deployment's namespace into the other, keeping the
    language-specific slug identical so the hreflang pair is reciprocal."""
    for p in ('videos/', 'topics/'):
        if path.startswith(p):
            rest = path[len(p):]
            if rest.endswith('index.html'):
                rest = rest[:-len('index.html')]
            return p + rest
    return path.replace('.html', '')


def ld_site(site, dep):
    b = site['brand']
    return {'@context': 'https://schema.org', '@type': 'WebSite',
            'name': b[dep], 'url': url(site, dep, ''),
            'inLanguage': site['lang'][dep],
            'potentialAction': {'@type': 'SearchAction', 'target': url(site, dep, '') + '?q={search_term_string}',
                                'query-input': 'required name=search_term_string'}}


def ld_org(site, dep):
    return {'@context': 'https://schema.org', '@type': 'EducationalOrganization',
            'name': site['org']['name'], 'url': site['org']['urlPlaceholder'],
            'logo': site['canonicalOrigin'][dep].rstrip('/') + site['base'][dep].rstrip('/') + '/' + site['org']['logo'],
            'description': site['brandLine'][dep]}


def ld_breadcrumb(site, dep, items):
    """items: [(name, path), ...] with path relative to the deployment root."""
    return {'@context': 'https://schema.org', '@type': 'BreadcrumbList',
            'itemListElement': [
                {'@type': 'ListItem', 'position': i + 1, 'name': nm,
                 'item': url(site, dep, p)} for i, (nm, p) in enumerate(items)]}


def ld_video(site, dep, o):
    base = url(site, dep, '').rstrip('/')
    vid = {
        '@context': 'https://schema.org', '@type': 'VideoObject',
        'name': o['fa'] if dep == 'ir' else o['en'],
        'alternateName': o['en'] if dep == 'ir' else o['fa'],
        'description': describe(o, dep),
        'thumbnailUrl': ['https://i.ytimg.com/vi/%s/maxresdefault.jpg' % o['id'],
                         'https://i.ytimg.com/vi/%s/hqdefault.jpg' % o['id']],
        'uploadDate': str(o.get('publishedAt') or o['updated']),
        'duration': iso8601(o['tsec']),
        'embedUrl': 'https://www.youtube-nocookie.com/embed/%s' % o['id'],
        'contentUrl': 'https://www.youtube.com/watch?v=%s' % o['id'],
        'inLanguage': site['lang'][dep],
        'isFamilyFriendly': True,
        'genre': o['cat'] if dep == 'ir' else o['cat_en'],
        'educationalLevel': 'College',
        'timeRequired': iso8601(o['tsec']),
    }
    if o.get('views'):
        vid['interactionStatistic'] = {'@type': 'InteractionCounter',
                                       'interactionType': {'@type': 'WatchAction'},
                                       'userInteractionCount': int(o['views'])}
    if o['chapters']:
        vid['hasPart'] = [{
            '@type': 'Clip', 'name': c['fa'] if dep == 'ir' else c['en'],
            'startOffset': c['sec'],
            'url': '%s?v=%s&t=%d' % (base + ('/' if dep == 'ir' else ''), o['id'], c['sec'])}
            for c in o['chapters']]
    return vid


# ---------------------------------------------------------------- generators
PAGE_SHELL = """<!doctype html>
<html lang="%(lang)s" dir="%(dir)s"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
%(head)s
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Vazirmatn:wght@400;700;800&display=swap">
<!-- the product's own stylesheet first, so the page inherits its identity -->
<link rel="stylesheet" href="%(assets)s">
<style>%(css)s</style>
</head><body class="wp-page"><div class="wp">
%(body)s
</div></body></html>
"""


# Every generated page lives two levels under its deployment root
# ({base}videos/<slug>/index.html), so BOTH deployments need the same '../../'.
UP = '../../'


def asset_rel(dep, depth):
    """globals.css lives at the deployment root, so the prefix is just the
    nesting depth. On GitHub Pages .com sits one level deeper than .ir."""
    return '/'.join(['..'] * depth) + '/assets/globals.css' if depth else 'assets/globals.css'


def page(site, dep, path, title, desc, image, body, ld, typ='website', og_title=None, depth=2):
    return PAGE_SHELL % {
        'lang': site['lang'][dep], 'dir': site['dir'][dep],
        'head': head_tags(site, dep, path, title, desc, image, typ, ld, og_title),
        'assets': asset_rel(dep, depth),
        'css': WATCH_CSS, 'body': body}


def watch_page(site, dep, o, related):
    ir = dep == 'ir'
    title, h1 = titles(o, dep, site)
    desc = describe(o, dep)
    # og:image wants the largest still; the inline thumb stays small.
    img = 'https://i.ytimg.com/vi/%s/maxresdefault.jpg' % o['id']
    thumb = 'https://i.ytimg.com/vi/%s/hqdefault.jpg' % o['id']
    path = 'videos/%s/' % o['slug']
    other = 'com' if ir else 'ir'
    alt = swap_prefix(path, dep, other)
    lead, pts = learning_points(o, dep)
    summ = o['sum'] if ir else o['sum_en']

    e = html.escape
    b = []
    crumb_topics = UP + 'topics/' + topic_slug(o) + '/'
    b.append('<nav class="wp-crumb"><a href="{up}">{brand}</a> › '
             '<a href="{tp}">{cat}</a> › {h1}</nav>'.format(
                 up=UP, brand=e(site['brand'][dep]), tp=crumb_topics,
                 cat=e(o['cat'] if ir else o['cat_en']), h1=e(h1[:58])))
    b.append('<h1>%s</h1>' % e(h1))
    ch_txt = e(o.get('src') or '')   # src = the YouTube channel that published the lecture
    b.append('<div class="wp-meta">'
             '<span>📺 %s</span><span>⏱️ %s</span>'
             '<span>🗂️ %s</span><span>🕒 %s</span></div>'
             % (e(ch_txt), e(o['dur_txt']), e(o['cat'] if ir else o['cat_en']),
                e(str(o.get('publishedAt') or ''))))
    b.append('<div class="wp-body"><main class="wp-main">')
    # The player iframe IS the LCP element on a watch page — never lazy-load it.
    b.append('<div class="wp-player"><iframe src="https://www.youtube-nocookie.com/embed/%s" '
             'title="%s" allow="accelerometer; clipboard-write; encrypted-media; '
             'picture-in-picture; fullscreen" allowfullscreen referrerpolicy="strict-origin-when-cross-origin">'
             '</iframe></div>' % (o['id'], e(h1)))
    b.append('<div class="wp-bar"><img src="%s" width="92" height="52" alt="%s" loading="lazy">'
             '<span>%s<br><strong>%s</strong></span></div>'
             % (thumb, e('%s — %s' % (o['en'] if not ir else o['fa'], ch_txt)), e(ch_txt), e(ch_txt)))

    b.append('<h2>%s</h2><p>%s</p>' % (e('این درس دربارهٔ چیست؟' if ir else 'What this lesson covers'), e(summ)))

    b.append('<h2>%s</h2><ul class="wp-obj">' % e('اهداف آموزشی' if ir else 'Learning objectives'))
    for p in pts:
        b.append('<li>%s</li>' % e(p))
    b.append('</ul>')

    # Chapters link back into the interactive player at the right timestamp.
    player = UP + 'index.html'
    if o['chapters']:
        b.append('<h2>%s</h2>' % e('سرفصل‌های زمانی' if ir else 'Timestamped chapters'))
        b.append('<ul class="wp-ch">')
        for c in o['chapters']:
            lbl = (c['fa'] or c['en']) if ir else (c['en'] or c['fa'])
            b.append('<li><a href="%s?v=%s&amp;t=%d"><time>%s</time><span>%s</span></a></li>'
                     % (player, o['id'], c['sec'], fmt_mmss(c['sec']), e(lbl)))
        b.append('</ul>')

    b.append('<h2>%s</h2>' % e('آزمون NCLEX' if ir else 'NCLEX quiz'))
    has_q = os.path.exists(os.path.join(ROOT, 'quizzes', o['id'] + '.json'))
    if has_q:
        b.append('<p>%s</p><div class="wp-cta"><a class="wp-btn p" href="%s?v=%s">%s</a></div>'
                 % (e('برای این درس آزمون چندگزینه‌ای، جای‌خالی و مرتب‌سازی آماده شده است.'
                      if ir else 'A multiple-choice, cloze and ordering quiz is ready for this lesson.'),
                    player, o['id'], e('شروع آزمون' if ir else 'Start the quiz')))
    else:
        b.append('<p class="wp-box">%s</p>' % e('آزمون این درس هنوز در حال آماده‌سازی است.'
                  if ir else 'The quiz for this lesson is still being prepared.'))

    b.append('</main>')

    # The sidebar is always rendered: a topic with a single video has no
    # siblings, and omitting the column left a hole in the two-column layout.
    b.append('<aside class="wp-side"><h2>%s</h2>' % e('درس‌های مرتبط' if ir else 'Related lessons'))
    if related:
        b.append('<ul class="wp-rel">')
        for r in related:
            lbl = r['fa'] if ir else r['en']
            b.append('<li><a href="%svideos/%s/"><img src="https://i.ytimg.com/vi/%s/hqdefault.jpg" '
                     'width="320" height="180" loading="lazy" alt="%s">'
                     '<b>%s</b><i>%s · %s</i></a></li>'
                     % (UP, r['slug'], r['id'], e('%s — %s' % (lbl, r['cat'] if ir else r['cat_en'])),
                        e(lbl[:78]), e(r['cat'] if ir else r['cat_en']), e(r['dur_txt'])))
        b.append('</ul>')
    else:
        b.append('<ul class="wp-rel wp-rel-one">')
        b.append('<li><a href="%sindex.html"><b>%s</b><i>%s</i></a></li>' % (UP, e('همهٔ ویدیوها' if ir else 'All videos'), e('رفتن به فهرست' if ir else 'Back to the library')))
        b.append('<li><a href="%stopics/%s/"><b>%s</b><i>%s</i></a></li>'
                 % (UP, topic_slug(o), e(o['cat'] if ir else o['cat_en']), e('موضوع' if ir else 'Topic')))
        b.append('</ul>')

    b.append('</div>')
    b.append('<div class="wp-foot">')
    b.append('<p><strong>%s</strong> %s</p>'
             % (e('منبع:' if ir else 'Source:'), e(ch_txt)))
    b.append('<p>%s <a href="https://www.youtube.com/watch?v=%s" rel="nofollow noopener" '
             'target="_blank">YouTube</a>.</p>'
             % (e('این صفحه یک ابزار آموزشی است و جایگزین مشاورهٔ پزشکی یا پرستاری نیست.'
                  if ir else 'This page is an educational tool and does not replace medical '
                            'or nursing advice.'), o['id']))
    b.append('<p>%s</p>'
             % e('متن گفتاری و سرفصل‌های زمانی از ویدیوی اصلی استخراج و ترجمه شده‌اند؛ '
                 'quiz و خلاصه برای همین درس نوشته شده است.'
                 if ir else 'The transcript and chapter timestamps were extracted and translated '
                            'from the original video; the summary and quiz were written for this '
                            'lesson.'))
    b.append('</div>')
    return page(site, dep, path, title, desc, img, '\n'.join(b),
                [ld_site(site, dep), ld_org(site, dep),
                 ld_breadcrumb(site, dep, [(site['brand'][dep], ''),
                                           (o['cat'] if ir else o['cat_en'], 'topics/%s/' % topic_slug(o)),
                                           (h1, path)]),
                 ld_video(site, dep, o)], typ='video.other', og_title=h1,
                depth=2 if ir else 3)


def topic_page(site, dep, t):
    ir = dep == 'ir'
    title = '%s | %s' % (t['cat'] if ir else t['cat_en'], site['brand'][dep])
    desc = describe(t, dep, 'topic')
    img = 'https://i.ytimg.com/vi/%s/hqdefault.jpg' % t['vids'][0]['id']
    path = 'topics/%s/' % t['slug']
    e = html.escape
    mins = round(sum(x['tsec'] for x in t['vids']) / 60)
    b = ['<nav class="wp-crumb"><a href="%s">%s</a> › %s</nav>'
         % (UP, e(site['brand'][dep]), e(t['cat'] if ir else t['cat_en']))]
    b.append('<h1>%s</h1>' % e(t['cat'] if ir else t['cat_en']))
    b.append('<div class="wp-meta"><span>🎞️ %s</span><span>⏱️ %s</span><span>📺 %s</span></div>'
             % (e(_n(len(t['vids']), ir)), e(_dur(mins, ir)), e('، '.join(t['chans']) if ir
                                                                else ', '.join(t['chans']))))
    intro = ('این بخش %d درس پرستاری دربارهٔ «%s» دارد؛ مجموعاً حدود %d دقیقه. هر درس متن گفتاری '
             'کامل، سرفصل زمانی، یادداشت زمان‌دار و آزمون NCLEX دارد و برای مرور و تثبیت مطالب '
             'طراحی شده است.'
             % (len(t['vids']), t['cat'], mins)) if ir else \
            ('This section has %d nursing lessons on %s, about %d minutes in total. Each lesson '
             'includes a full transcript, timestamped chapters, timed notes and an NCLEX quiz, and '
             'is designed for review and consolidation.'
             % (len(t['vids']), t['cat_en'], mins))
    b.append('<p>%s</p>' % e(intro))
    b.append('<div class="wp-body"><main class="wp-main">')
    b.append('<h2>%s</h2>' % e('فهرست درس‌ها' if ir else 'Lessons in this topic'))
    b.append('<ul class="wp-rel">')
    for v in sorted(t['vids'], key=lambda x: str(x.get('publishedAt') or ''), reverse=True):
        lbl = v['fa'] if ir else v['en']
        b.append('<li><a href="%svideos/%s/"><img src="https://i.ytimg.com/vi/%s/hqdefault.jpg" '
                 'width="320" height="180" loading="lazy" alt="%s"><b>%s</b><i>%s · %s</i></a></li>'
                 % (UP, v['slug'], v['id'], e('%s — %s' % (lbl, v['dur_txt'])), e(lbl[:78]),
                    e(v['dur_txt']), e(v['src'])))
    b.append('</ul>')
    b.append('</main><aside class="wp-side"><h2>%s</h2>' % e('موضوعات مرتبط' if ir else 'Related topics'))
    b.append('<p>')
    for other in t['siblings']:
        b.append('<a class="wp-btn s" style="margin:0 6px 8px 0" href="%stopics/%s/">%s</a>'
                 % (UP, other['slug'], e(other['cat'] if ir else other['cat_en'])))
    b.append('</p></aside></div>')
    b.append('<div class="wp-foot"><p><strong>%s</strong> %s</p></div>'
             % (e('همهٔ بخش‌ها:' if ir else 'All sections:'),
                e(' · '.join('%s' % (x['cat'] if ir else x['cat_en']) for x in t['siblings']))))
    return page(site, dep, path, title, desc, img, '\n'.join(b),
                [ld_site(site, dep), ld_org(site, dep),
                 ld_breadcrumb(site, dep, [(site['brand'][dep], ''),
                                           (t['cat'] if ir else t['cat_en'], path)]),
                 {'@context': 'https://schema.org', '@type': 'CollectionPage',
                  'name': title, 'description': desc, 'inLanguage': site['lang'][dep],
                  'url': url(site, dep, path)}], depth=2 if ir else 3)


def _n(i, ir):
    return ('%d درس' % i) if ir else ('%d lessons' % i)


def _dur(mins, ir):
    return ('%d دقیقه' % mins) if ir else ('%d min' % mins)


# ---------------------------------------------------------------- static pages
def inject_static(site):
    """Rewrite the <head> SEO block of the 8 hand-written pages. The body stays
    JS-driven (app shell) — only the head is pre-rendered, because that is what
    search engines read first and what survives without script execution."""
    marks = '<!--seo:start-->', '<!--seo:end-->'
    for dep in DEP:
        pre = '' if dep == 'ir' else 'com/'
        for page_id in ('index', 'premium', 'schedule', 'account'):
            rel = pre + page_id + '.html'
            fp = os.path.join(ROOT, rel)
            if not os.path.exists(fp):
                continue
            src = open(fp, encoding='utf-8').read()
            meta = site['perPage']['home' if page_id == 'index' else page_id][dep]
            is_home = page_id == 'index'
            path = '' if is_home else page_id + '.html'
            img = 'https://i.ytimg.com/vi/oNEBmBtBvtw/maxresdefault.jpg'
            ld = [ld_site(site, dep), ld_org(site, dep)]
            if not is_home:
                ld.append(ld_breadcrumb(site, dep, [(site['brand'][dep], ''), (meta['h1'], path)]))
            desc = meta["desc"]
            block = head_tags(site, dep, path, meta['title'], desc, img, 'website', ld)
            # The block is removed and put back in the same place, so the
            # generator is idempotent: running it twice changes nothing.
            m = re.search(r'%s.*?%s' % (marks[0], marks[1]), src, flags=re.S)
            if m:
                # the block is replaced where it was
                new = src[:m.start()] + marks[0] + '\n' + block + '\n' + marks[1] + src[m.end():]
            else:
                # first run: the block goes after the hand-written title
                new = re.sub(r'(</title>)',
                             lambda mm: mm.group(1) + '\n' + marks[0] + '\n' + block + '\n' + marks[1],
                             src, count=1)
            # the block leaves a run of blank lines behind; collapse them so
            # the tree stays clean
            new = re.sub(r'(<!--seo:end-->)\n{2,}', r'\1\n', new)
            assert marks[0] in new and block in new, 'head injection failed for %s' % rel
            open(fp, 'w', encoding='utf-8').write(new)

    # The admin panel is a private page: it must never be indexed, but it also
    # must NOT be blocked in robots.txt — a crawl block would stop the crawler
    # from ever reading the noindex directive. So: crawlable, self-canonical,
    # noindex in the head.
    for dep, rel_admin in (('ir', 'admin/index.html'), ('com', 'com/admin/index.html')):
        ap = os.path.join(ROOT, rel_admin)
        if not os.path.exists(ap) or 'admin' not in site.get('perPage', {}):
            continue
        src = open(ap, encoding='utf-8').read()
        meta = site['perPage']['admin'][dep]
        path_admin = 'admin/'      # url() adds the /com/ prefix for the com dep
        block = head_tags(site, dep, path_admin, meta['title'], meta['desc'],
                          'https://i.ytimg.com/vi/oNEBmBtBvtw/maxresdefault.jpg',
                          'website', None, None, noindex=True)
        new = re.sub(r'%s.*?%s' % (marks[0], marks[1]), '', src, flags=re.S)
        # head_tags carries its own <title>; drop the page's original one so
        # the document does not end up with two titles.
        new = re.sub(r'<title>.*?</title>\s*', '', new, count=1, flags=re.S)
        if '</title>' in new:
            new = re.sub(r'(</title>)',
                         lambda m: m.group(1) + '\n' + marks[0] + '\n' + block + '\n' + marks[1],
                         new, count=1)
        else:
            new = re.sub(r'(<head[^>]*>)',
                         lambda m: m.group(1) + '\n' + marks[0] + '\n' + block + '\n' + marks[1],
                         new, count=1)
        assert marks[0] in new and block in new, 'head injection failed for %s' % rel_admin
        open(ap, 'w', encoding='utf-8').write(new)


def clean_prev(path):
    if os.path.isdir(path):
        shutil.rmtree(path)


# ---------------------------------------------------------------- site files
def write_robots(site):
    lines = ['# %s — generated by scripts/gen_seo.py, edit seo/site.json instead' % site['org']['name'],
             'User-agent: *',
             'Allow: /',
             '',
             '# Faceted search permutations: they are the same content as the listing page.',
             'Disallow: /*?sort=',
             'Disallow: /*&sort=',
             'Disallow: /*?cat=',
             'Disallow: /*?q=',
             'Disallow: /*?t=',
             '']
    # One sitemap per host, not per deployment: a single sitemap may legitimately
# list URLs from both language versions of the same site.
    if site.get('noindex'):
        lines += ['# noindex is set in the HTML head on purpose: a robots.txt block would stop',
                  '# the crawl, so Google could never read the noindex directive.',
                  'User-agent: *', 'Disallow: /', '']
    else:
        lines.append('Sitemap: %s' % url(site, 'ir', 'sitemap.xml'))
        lines.append('Sitemap: %s' % url(site, 'ir', 'sitemap-video.xml'))
        lines.append('')
    open(os.path.join(ROOT, 'robots.txt'), 'w', encoding='utf-8').write('\n'.join(lines))


def write_sitemaps(site, entries, vids):
    NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="%s">' % NS]
    for dep, path, pri, freq in entries:
        out += ['  <url>', '    <loc>%s</loc>' % html.escape(url(site, dep, path)),
                '    <lastmod>%s</lastmod>' % NOW,
                '    <priority>%s</priority>' % pri,
                '    <changefreq>%s</changefreq>' % freq, '  </url>']
    out.append('</urlset>')
    open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8').write('\n'.join(out))

    VNS = 'http://www.google.com/schemas/sitemap-video/1.1'
    v = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<urlset xmlns="%s" xmlns:video="%s">' % (NS, VNS)]
    for dep in DEP:
        for o in vids:
            if not o['indexable']:
                continue
            loc = url(site, dep, 'videos/%s/' % o['slug'])
            v += ['  <url>', '    <loc>%s</loc>' % html.escape(loc),
                  '    <video:video>',
                  '      <video:thumbnail_loc>https://i.ytimg.com/vi/%s/maxresdefault.jpg</video:thumbnail_loc>' % o['id'],
                  '      <video:title>%s</video:title>' % html.escape(o['fa'] if dep == 'ir' else o['en']),
                  '      <video:description>%s</video:description>' % html.escape(describe(o, dep)),
                  '      <video:player_loc allow_embed="https://www.youtube-nocookie.com/embed/%s">'
                  'https://www.youtube.com/watch?v=%s</video:player_loc>' % (o['id'], o['id']),
                  # duration in a video sitemap is PLAIN SECONDS, not ISO 8601
                  '      <video:duration>%d</video:duration>' % o['tsec'],
                  '      <video:publication_date>%s</video:publication_date>' % o['updated'],
                  '      <video:family_friendly>yes</video:family_friendly>',
                  '      <video:live>no</video:live>',
                  '      <video:uploader info="https://www.youtube.com/@%s">%s</video:uploader>'
                  % (_chan_handle(o['src']), html.escape(o['src'])),
                  '      <video:tag>%s</video:tag>' % html.escape(
                      o['cat'] if dep == 'ir' else o['cat_en']),
                  '    </video:video>', '  </url>']
    v.append('</urlset>')
    open(os.path.join(ROOT, 'sitemap-video.xml'), 'w', encoding='utf-8').write('\n'.join(v))


def _chan_handle(src):
    s = re.sub(r'\s+', '', str(src))
    return s or 'youtube'


def write_404(site):
    b = ['<nav class="wp-crumb"><a href="./">%s</a></nav>' % html.escape(site['brand']['ir']),
         '<h1>صفحه پیدا نشد (۴۰۴)</h1>',
         '<p class="wp-box">این نشانی وجود ندارد یا جابه‌جا شده است. از جست‌وجوی بالای صفحهٔ اصلی '
         'استفاده کنید یا یکی از درس‌های زیر را ببینید.</p>']
    with open(os.path.join(ROOT, 'data', 'videos.json'), encoding='utf-8') as f:
        vs = [normalise(x) for x in json.load(f)][:6]
    b.append('<h2>پیشنهاد</h2><ul class="wp-rel">')
    for v in vs:
        b.append('<li><a href="./videos/%s/"><img src="https://i.ytimg.com/vi/%s/hqdefault.jpg" '
                 'width="320" height="180" loading="lazy" alt="%s"><b>%s</b><i>%s · %s</i></a></li>'
                 % (v['slug'], v['id'], html.escape(v['fa']), html.escape(v['fa'][:78]),
                    html.escape(v['dur_txt']), html.escape(v['cat'])))
    b.append('</ul><div class="wp-cta"><a class="wp-btn p" href="./">بازگشت به صفحهٔ اصلی</a></div>')
    head = head_tags(site, 'ir', '404.html', 'صفحه پیدا نشد | %s' % site['brand']['ir'],
                     'نشانی درخواستی در %s وجود ندارد یا جابه‌جا شده است. از فهرست درس‌های '
                     'پیشنهادی پایین همین صفحه یا جست‌وجوی کتابخانه استفاده کنید. تمام '
                     'درس‌ها با متن گفتاری، سرفصل زمانی و آزمون NCLEX در دسترس‌اند.'
                     % site['brand']['ir'],
                     'https://i.ytimg.com/vi/oNEBmBtBvtw/maxresdefault.jpg',
                     'website', [ld_site(site, 'ir')])
    open(os.path.join(ROOT, '404.html'), 'w', encoding='utf-8').write(
        page(site, 'ir', '404.html',
             'صفحه پیدا نشد | %s' % site['brand']['ir'],
             'نشانی درخواستی وجود ندارد یا جابه‌جا شده است. از فهرست درس‌های پیشنهادی '
             'پایین همین صفحه یا جست‌وجوی کتابخانه استفاده کنید — تمام درس‌ها با متن '
             'گفتاری، سرفصل زمانی و آزمون NCLEX در دسترس‌اند.', '', '\n'.join(b),
             [ld_site(site, 'ir')], depth=0))


# ---------------------------------------------------------------- main
def main():
    site = load_site()
    vids = [normalise(v) for v in load_videos()]
    seen = {}
    for o in vids:
        if o['slug'] in seen:
            raise SystemExit('slug collision: %s (%s / %s)' % (o['slug'], seen[o['slug']], o['id']))
        seen[o['slug']] = o['id']
    print('videos: %d  (%d indexable)' % (len(vids), sum(1 for o in vids if o['indexable'])))

    # topics
    bycat = {}
    for o in vids:
        bycat.setdefault(o['cat_en'], []).append(o)
    topics = []
    for cat_en, group in bycat.items():
        t = {'cat_en': cat_en, 'cat': group[0]['cat'], 'vids': group,
             'slug': topic_slug(group[0]),
             'chans': sorted({x['src'] for x in group})}
        topics.append(t)
    for t in topics:
        t['siblings'] = [x for x in topics if x['slug'] != t['slug']]
    topics.sort(key=lambda x: x['cat_en'])

    entries = []
    for dep in DEP:
        pre = '' if dep == 'ir' else 'com/'
        if 'account.html' in site.get('notIndexed', []):
            pass          # per-user dashboard: no indexable value, kept out of the sitemap
        else:
            entries.append((dep, pre + 'account.html', '0.2', 'monthly'))
        entries.append((dep, '', '1.0', 'daily'))
        entries.append((dep, 'premium.html', '0.5', 'monthly'))
        entries.append((dep, 'schedule.html', '0.4', 'weekly'))
        for t in topics:
            entries.append((dep, 'topics/%s/' % t['slug'], '0.7', 'weekly'))
        for o in vids:
            if o['indexable']:
                entries.append((dep, 'videos/%s/' % o['slug'], '0.8', 'monthly'))

    # clean + write
    for dep in DEP:
        clean_prev(os.path.join(ROOT, '' if dep == 'ir' else 'com', 'videos'))
        clean_prev(os.path.join(ROOT, '' if dep == 'ir' else 'com', 'topics'))
    made = 0
    for dep in DEP:
        base = ROOT if dep == 'ir' else os.path.join(ROOT, 'com')
        for o in vids:
            if not o['indexable']:
                continue
            related = [x for x in bycat[o['cat_en']] if x['id'] != o['id']][:4]
            d = os.path.join(base, 'videos', o['slug'])
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(
                watch_page(site, dep, o, related))
            made += 1
        for t in topics:
            d = os.path.join(base, 'topics', t['slug'])
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(
                topic_page(site, dep, t))
            made += 1
    print('pages written: %d' % made)

    inject_static(site)
    write_robots(site)
    write_sitemaps(site, entries, vids)
    write_404(site)

    # slug map for the player: one file, read by both deployments
    smap = {o['id']: o['slug'] for o in vids}
    with open(os.path.join(ROOT, 'data', 'seo.json'), 'w', encoding='utf-8') as f:
        json.dump({'slugs': smap}, f, ensure_ascii=False, indent=0)
    print('urls in sitemap: %d' % len(entries))
    print('robots.txt, sitemap.xml, sitemap-video.xml, 404.html written')
    print('data/seo.json written (%d slugs)' % len(smap))


if __name__ == '__main__':
    main()