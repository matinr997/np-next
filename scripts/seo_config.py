#!/usr/bin/env python3
"""Shared SEO helpers. Reads seo/site.json — the single source of truth for URLs.

Nothing here may hardcode a hostname; every URL is composed from the config.
Imported by gen_seo.py and check_seo_site.py.
"""
import json, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_JSON = os.path.join(ROOT, 'seo', 'site.json')

# Digits ۰-۹ (Persian/Arabic-Indic) -> ASCII, used by chapter timestamps.
_FA_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


def load_site():
    with open(SITE_JSON, encoding='utf-8') as f:
        return json.load(f)


def slugify(text, maxlen=70):
    """Deterministic ASCII slug. Same input always yields the same slug, so URLs
    stay stable across regenerations (Google: use stable URLs)."""
    t = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode()
    t = re.sub(r'[^\w\s-]', ' ', t).lower()
    t = re.sub(r'[\s_]+', '-', t).strip('-')
    if len(t) > maxlen:
        cut = t[:maxlen]
        if '-' in cut[maxlen // 2:]:
            cut = cut[:cut.rindex('-')]
        t = cut.strip('-')
    return t


def to_seconds(ts):
    """'4:42', '1:00:16', '۰:۳۲' -> seconds. Branches on part count; a helper that
    assumes mm:ss silently mis-ranks a 3-hour video below a 24-minute one."""
    s = str(ts or '').strip().translate(_FA_DIGITS)
    parts = [p for p in s.split(':') if p != '']
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return 0
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    return nums[0] if nums else 0


def iso8601(seconds):
    """ISO 8601 duration for JSON-LD. VideoObject REQUIRES this; mm:ss is invalid."""
    s = int(seconds or 0)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return 'PT%dH%dM%dS' % (h, m, sec) if h else 'PT%dM%dS' % (m, sec)


def fmt_mmss(seconds):
    s = int(seconds or 0)
    return '%d:%02d' % (s // 60, s % 60)


def url(site, dep, path=''):
    """Absolute URL for a page in a deployment. Never relative, never bare origin."""
    base = site['base'][dep].rstrip('/')
    p = ('/' + str(path).lstrip('/')) if path else ''
    return site['canonicalOrigin'][dep].rstrip('/') + base + p


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))


def jdump(obj):
    """JSON-LD block. json.dumps escapes < > & so a title containing markup can
    never break out of the script tag."""
    import json as _j
    return _j.dumps(obj, ensure_ascii=False, indent=2).replace('</', '<\\/')


def truncate(text, limit):
    """Cut on a word boundary so a meta description never ends mid-word."""
    t = ' '.join(str(text).split())
    if len(t) <= limit:
        return t
    cut = t[:limit].rsplit(' ', 1)[0]
    return cut.rstrip(' ,،.:;—-') + '…'


def video_slug(v):
    return slugify(v.get('en') or v.get('fa') or v['id'])


def topic_slug(v):
    return slugify(v.get('cat_en') or v.get('cat') or 'other')