#!/usr/bin/env python3
"""
Static SEO checker grounded in Google Search Central.

Usage:  python3 check_seo.py <site-root> [--site-url https://example.com]

Checks only what is statically knowable. It cannot verify indexing, ranking, or
rendered-JS behaviour -- use the URL Inspection tool and Rich Results Test for
those. Exit code 1 if any ERROR-level finding survives.
"""
import argparse, json, os, re, sys, html
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

ERROR, WARN, OK, INFO = "ERROR", "WARN", "OK", "INFO"
FA_RE = re.compile(r"[\u0600-\u06FF]")
errors, warns, notes = [], [], []

def add(sev, rule, msg):
    (errors if sev == ERROR else warns if sev == WARN else notes).append((sev, rule, msg))

def head_of(s):
    i = s.lower().find("</head>")
    return s[:i] if i > 0 else s[:4000]

def tag(html_src, pat, flags=re.I):
    m = re.search(pat, html_src, flags)
    if not m:
        return None
    # A probe pattern may or may not have a capture group; returning group(1)
    # unconditionally crashes the moment a page actually HAS the thing checked for.
    return html.unescape((m.group(1) if m.groups() else m.group(0)).strip())

def attr(s, a):
    return tag(s, r'\b%s\s*=\s*["\']([^"\']*)["\']' % a)

def iso8601(d):
    if not d: return False
    m = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?$", d.strip())
    return bool(m) and any(m.groups())

def load_jsonld(head):
    out = []
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', head, re.S | re.I):
        raw = m.group(1).strip()
        try:
            out.append((raw, json.loads(raw), None))
        except Exception as e:
            out.append((raw, None, str(e)))
    return out

# ---------------------------------------------------------------- pages
def check_one_page(root, p, titles, descs, h1s, site_url):
    """Analyse one page. Wrapped by the caller so a single malformed file reports
    as a finding instead of aborting the whole audit."""
    rel = os.path.relpath(p, root)
    s = open(p, encoding="utf-8", errors="ignore").read()
    head = head_of(s)
    row = {}

    t = tag(head, r"<title[^>]*>(.*?)</title>", re.I | re.S)
    d = tag(head, r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', re.I | re.S)
    c = attr(head, "rel")
    can = tag(head, r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)', re.I)
    og = tag(head, r'<meta[^>]*property=["\']og:title["\']', re.I)
    h1 = len(re.findall(r"<h1[\s>]", s, re.I))
    lang = attr(head[:400], "lang")
    dirn = attr(head[:400], "dir")

    if not t:
        add(ERROR, "title-missing", rel)
    else:
        titles.setdefault(t.lower(), []).append(rel)
        if len(t) > 65:
            add(WARN, "title-long", "%s (%d chars, aim <=65)" % (rel, len(t)))
        if len(t) < 15:
            add(WARN, "title-short", "%s (%d chars)" % (rel, len(t)))
    if not d:
        add(ERROR, "desc-missing", rel)
    else:
        descs.setdefault(d.lower(), []).append(rel)
        if not (70 <= len(d) <= 300):
            add(WARN, "desc-length", "%s (%d chars, aim 70-300)" % (rel, len(d)))
    if not can:
        add(ERROR, "canonical-missing", rel)
    elif site_url and urlparse(can).netloc != urlparse(site_url).netloc:
        add(ERROR, "canonical-foreign-host", "%s -> %s" % (rel, can))
    if not og:
        add(WARN, "og-missing", rel)
    if h1 != 1:
        # App-shell pages replace document.body from a module, so their h1 lives in
        # JS — possibly in a module the entry imports, not the entry itself.
        # Googlebot renders JS, so that is fine; say so instead of a false positive.
        in_js, where = 0, []
        cands = []
        for m in re.finditer(r'<script[^>]*src=["\']([^"\']+)["\']', s, re.I):
            cands.append(m.group(1))
        cands.append("lib/*.js")
        for c in cands:
            if c.endswith("*.js"):
                files = [os.path.join(root, "lib", f) for f in sorted(os.listdir(os.path.join(root, "lib")))
                         if f.endswith(".js")] if os.path.isdir(os.path.join(root, "lib")) else []
            else:
                files = [os.path.normpath(os.path.join(os.path.dirname(p), c.split("?")[0]))]
            for fp in files:
                if os.path.exists(fp) and fp.endswith(".js"):
                    n = len(re.findall(r"<h1[\s>]", open(fp, encoding="utf-8", errors="ignore").read()))
                    if n:
                        in_js += n
                        where.append(os.path.basename(fp))
        if h1 == 0 and in_js:
            add(INFO, "h1-in-js", "%s: h1 rendered from %s (%d) — app shell, fine for Googlebot"
                % (rel, ",".join(sorted(set(where))), in_js))
        else:
            add(WARN, "h1-count", "%s has %d <h1> and none in its JS bundle" % (rel, h1))
    h1s.setdefault(h1, []).append(rel)
    if not lang:
        add(ERROR, "html-lang-missing", rel)
    if not dirn:
        add(WARN, "html-dir-missing", rel + " (needed for RTL .ir)")
    if tag(head, r'<meta[^>]*name=["\']robots["\']', re.I):
        add(INFO, "robots-meta", rel + " declares a robots meta tag -- verify it is intentional")

    # hreflang reciprocity
    alts = re.findall(r'<link[^>]*hreflang=["\']([^"\']+)["\'][^>]*href=["\']([^"\']+)', head, re.I)
    if alts:
        codes = {c.lower() for c, _ in alts}
        if lang and lang.lower() not in codes:
            add(ERROR, "hreflang-no-selfref", "%s lang=%s not among %s" % (rel, lang, sorted(codes)))
        for c, u in alts:
            if not urlencode_is_abs(u):
                add(ERROR, "hreflang-not-absolute", "%s %s -> %s" % (rel, c, u))

    # JSON-LD
    for raw, obj, err in load_jsonld(head):
        if err:
            add(ERROR, "jsonld-invalid", "%s: %s" % (rel, err))
            continue
        for node in (obj if isinstance(obj, list) else [obj]):
            check_schema(node, rel)
    if not load_jsonld(head):
        add(WARN, "jsonld-missing", rel)

    # images
    for im in re.findall(r"<img\b[^>]*>", s, re.I):
                if "alt=" not in im:
                    add(WARN, "img-alt-missing", rel + ": " + im[:90])
                elif re.search(r'alt\s*=\s*["\']\s*["\']', im):
                    # Empty alt is CORRECT for a decorative image. It only hurts when
                    # the image IS the link, because Google reads alt as anchor text.
                    if re.search(r"<a\b[^>]*>\s*" + re.escape(im), s, re.I):
                        add(ERROR, "img-alt-empty-in-link",
                            rel + ": image link with alt=\"\" reads as an EMPTY anchor text to Google")
                    else:
                        add(INFO, "img-alt-empty-decorative", rel + ": alt=\"\" is correct for a decorative image")
                if "width=" not in im or "height=" not in im:
                    add(INFO, "img-dimensions", rel + ": " + im[:70])
    if re.search(r'<img[^>]*loading=["\']lazy["\'][^>]*>', s, re.I):
        add(INFO, "img-lazy", rel + ": confirm the LCP image is NOT lazy-loaded")

    # crawlable anchors
    anchors = len(re.findall(r"<a\b[^>]*href\s*=\s*[\"'][^\"']+[\"']", s, re.I))
    onclick_div = len(re.findall(r'<(?:div|li|span)[^>]*onclick=', s, re.I))
    if onclick_div and anchors < onclick_div:
        add(ERROR, "unreachable-content",
            "%s: %d click-handler element(s) vs %d <a href> -- content behind onclick is not a crawlable link"
            % (rel, onclick_div, anchors))
    for m in re.finditer(r'<(?:div|span)[^>]*href=', s, re.I):
        add(ERROR, "href-wrong-element", "%s: %s" % (rel, m.group(0)[:70]))
    if re.search(r'href\s*=\s*["\']javascript:', s, re.I):
        add(ERROR, "href-javascript", rel)
    for m in re.finditer(r'href=["\'](\.\./[^"\']+)', s):
        add(WARN, "parent-relative-href", "%s -> %s (use root-relative)" % (rel, m.group(1)))

    # Crawl every relative href against the filesystem. A link that looks right
    # and resolves one directory too high passes every regex audit and still 404s.
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\']', s, re.I):
        u = m.group(1)
        if u.startswith(("http", "//", "#", "mailto:", "javascript:")) or "{" in u:
            continue
        tgt = os.path.normpath(os.path.join(os.path.dirname(p), u.split("#")[0].split("?")[0]))
        if os.path.isdir(tgt) or not os.path.splitext(tgt)[1]:
            tgt = os.path.join(tgt, "index.html")
        if not os.path.exists(tgt):
            add(ERROR, "broken-internal-link", "%s -> %s resolves to %s (missing)"
                % (rel, u[:60], os.path.relpath(tgt, root)))
    print("  %-34s title=%-4s desc=%-4s canon=%-5s hreflang=%-3s og=%-4s ld=%-3s lang=%-4s a=%s"
          % (rel, "Y" if t else "N", "Y" if d else "N", "Y" if can else "N",
             len(alts) or "-", "Y" if og else "N", len(load_jsonld(head)) or "-",
             lang or "N", anchors))
    return


def check_pages(root, site_url):
    pages = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git", "node_modules", "deploy", ".hermes")]
        for f in fn:
            if f.endswith(".html"):
                pages.append(os.path.join(dp, f))
    if not pages:
        add(ERROR, "no-pages", "no HTML pages found")
        return pages
    titles, descs, h1s = {}, {}, {}
    print("== per-page ==")
    for p in sorted(pages):
        try:
            check_one_page(root, p, titles, descs, h1s, site_url)
        except Exception as e:
            add(ERROR, "page-parse-failed", "%s: %s: %s" % (os.path.relpath(p, root), type(e).__name__, e))
    for label, store in (("duplicate titles", titles), ("duplicate meta descriptions", descs)):
        for val, where in store.items():
            if len(where) > 1:
                add(ERROR, "duplicate-metadata", "%s: %r in %s" % (label, val[:60], where))
    return pages



def urlencode_is_abs(u):
    return bool(urlparse(u).scheme and urlparse(u).netloc)

def check_schema(node, rel):
    if not isinstance(node, dict):
        return
    if "@graph" in node and isinstance(node["@graph"], list):
        for n in node["@graph"]:
            check_schema(n, rel)
        return
    t = node.get("@type")
    types = t if isinstance(t, list) else [t]
    for ty in types:
        if not ty:
            add(ERROR, "jsonld-no-type", rel)
    for bad in ("Review", "AggregateRating", "Rating"):
        if bad in types:
            add(ERROR, "jsonld-unverifiable-claim",
                "%s: %s claims a score that cannot be verified -- fabrication risk" % (rel, bad))
    if "VideoObject" in types:
        for req in ("name", "description", "thumbnailUrl", "uploadDate", "duration"):
            if req not in node:
                add(ERROR, "videoobject-missing", "%s: %s" % (rel, req))
        d = node.get("duration")
        if d and not iso8601(str(d)):
            add(ERROR, "videoobject-duration",
                "%s: duration=%r must be ISO 8601 (PT15M12S), not mm:ss" % (rel, d))
        u = node.get("uploadDate")
        if u and not re.match(r"^\d{4}-\d{2}-\d{2}", str(u)):
            add(ERROR, "videoobject-uploaddate", "%s: %r must be ISO 8601 date" % (rel, u))
    if "datePublished" in node or "uploadDate" in node:
        for k in ("datePublished", "dateModified", "uploadDate"):
            v = node.get(k)
            if v and "now" in str(v).lower():
                add(ERROR, "fabricated-date", "%s: %s=%r" % (rel, k, v))

# ---------------------------------------------------------------- site files
def check_site_files(root, site_url):
    print("== site files ==")
    rp = os.path.join(root, "robots.txt")
    if os.path.exists(rp):
        rs = open(rp, encoding="utf-8", errors="ignore").read()
        if site_url and "Sitemap:" not in rs:
            add(WARN, "robots-no-sitemap", "robots.txt has no Sitemap: line")
        for line in rs.splitlines():
            if re.match(r"\s*Disallow:\s*/?\s*$", line):
                add(WARN, "robots-disallow-all", "robots.txt disallows everything -> nothing can be indexed")
        if re.search(r"User-agent:\s*\*", rs, re.I) is None:
            add(WARN, "robots-no-ua", "no User-agent group")
        print("  robots.txt            present")
    else:
        add(ERROR, "robots-missing", "no robots.txt")
        print("  robots.txt            MISSING")

    sp = os.path.join(root, "sitemap.xml")
    if os.path.exists(sp):
        try:
            tree = ET.parse(sp)
        except Exception as e:
            add(ERROR, "sitemap-malformed", str(e))
            print("  sitemap.xml           MALFORMED")
            return
        locs = [e.text.strip() for e in tree.getroot().iter()
                if e.tag.rsplit('}', 1)[-1] == 'loc' and e.text]
        bad = [l for l in locs if not urlparse(l).scheme]
        if bad:
            add(ERROR, "sitemap-relative-url", "%d entries are not absolute: %s" % (len(bad), bad[:3]))
        if locs and not bad and site_url:
            # every listed URL should share the canonical host
            off = sorted({urlparse(l).netloc for l in locs if urlparse(l).netloc != urlparse(site_url).netloc})
            if off:
                add(ERROR, "sitemap-wrong-host", "entries on another host than the canonical origin: %s" % off[:3])
        for e in tree.getroot().iter():
            if e.tag.rsplit('}', 1)[-1] == 'duration' and e.text:
                if not re.match(r"^\d+$", e.text.strip()):
                    add(ERROR, "video-sitemap-duration",
                        "<video:duration>=%r must be plain seconds in a sitemap (ISO 8601 is JSON-LD only)" % e.text)
                elif int(e.text) > 86400:
                    add(WARN, "video-sitemap-duration-long", "%s seconds" % e.text)
        if not locs:
            add(WARN, "sitemap-empty", "sitemap has no <loc> — <loc> is a CHILD of <url>, so a direct-child scan finds nothing")
        print("  sitemap.xml           %d URLs" % len(locs))
    else:
        add(ERROR, "sitemap-missing", "no sitemap.xml")
        print("  sitemap.xml           MISSING")

    for extra in ("404.html",):
        if not os.path.exists(os.path.join(root, extra)):
            add(WARN, "no-404", "no %s (a soft 404 is not an error signal to Google)" % extra)

def check_config(root, site_url):
    print("== config ==")
    # The configured canonical origin MUST appear in canonical/hreflang/OG/sitemap.
    # That is correct output, not a hardcoded host — allowlist it from the config.
    allowed_origins = set()
    cfg = os.path.join(root, 'seo', 'site.json')
    if os.path.exists(cfg):
        try:
            allowed_origins = {json.load(open(cfg, encoding='utf-8'))['canonicalOrigin'][k].split('//')[-1].split('/')[0]
                               for k in ('ir', 'com')}
        except Exception:
            pass
    hits = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git", "node_modules", ".hermes")]
        for f in fn:
            if not f.endswith((".js", ".html", ".css", ".json", ".xml", ".txt")):
                continue
            fp = os.path.join(dp, f)
            rel = os.path.relpath(fp, root)
            if rel.startswith("deploy" + os.sep) or "sitemap" in f:
                continue
            s = open(fp, encoding="utf-8", errors="ignore").read()
            for m in re.finditer(r"https?://[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", s):
                h = m.group(0)
                if h.startswith(("http://localhost", "http://127.0.0.1", "https://schema.org",
                                 "https://ogp.me", "https://www.w3.org", "https://i.ytimg.com",
                                 "https://www.youtube", "https://youtu.be", "https://nurseplus",
                                 "https://fonts.", "https://search.google")):
                    continue
                if h.split("//")[-1].split("/")[0] in allowed_origins:
                    continue
                hits.append((rel, h))
    if hits:
        add(WARN, "hardcoded-host", "%d hardcoded absolute host(s) outside the SEO config: %s"
            % (len(hits), sorted({h for _, h in hits})[:5]))
    print("  hardcoded hosts       %d  (canonical origins allowed: %s)"
          % (len(hits), sorted(allowed_origins) or "n/a — no seo/site.json"))

def check_dynamic(root):
    """Content injected by JS is invisible to a static HTML scan.
    Googlebot does render JS and re-parses hrefs, but ONLY from <a href> markup --
    a click handler on a div is not a link. Scan the sources for that."""
    print("\n== client-rendered navigation ==")
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git", "node_modules", ".hermes", "deploy")]
        for f in fn:
            if not f.endswith((".js", ".html")):
                continue
            fp = os.path.join(dp, f)
            rel = os.path.relpath(fp, root)
            s = open(fp, encoding="utf-8", errors="ignore").read()
            handlers = len(re.findall(r"<(?:div|li|span|section|article)[^>]*onclick=", s))
            js_anchors = len(re.findall(r"<a\b[^>]*href\s*=\\?[\"'`]([^\\\"'`]+)", s))
            nav_js = len(re.findall(r"(?:location\.href|location\.assign|window\.open)\s*=\s*[^;]{0,80}\.(?:html|php)", s))
            if handlers or nav_js:
                if handlers and not js_anchors:
                    add(ERROR, "unreachable-content",
                        "%s: %d click-handler element(s), 0 <a href> -- this content has no crawlable URL"
                        % (rel, handlers))
                elif handlers:
                    add(WARN, "unreachable-content",
                        "%s: %d click handler(s) vs %d anchor(s) -- each click target needs a real href"
                        % (rel, handlers, js_anchors))
            if nav_js and not js_anchors:
                add(WARN, "js-only-navigation", "%s: %d JS redirect(s) with no <a href> equivalent" % (rel, nav_js))
            print("  %-30s handlers=%-3d anchors=%-3d jsNav=%d" % (rel, handlers, js_anchors, nav_js))

            # JSON-LD assembled in JS is still structured data -- validate its shape.
            # Keys in a JS object literal may be unquoted, so match both forms.
            for m in re.finditer(r"['\"]?duration['\"]?\s*:\s*([^,}\n]{1,60})", s):
                v = m.group(1).strip()
                if re.search(r"\bdur\b|\.dur\b", v) and "PT" not in v:
                    add(ERROR, "videoobject-duration",
                        "%s: duration bound to %s -- must be ISO 8601 (PT15M12S), not the raw mm:ss field"
                        % (rel, v))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--site-url", default="")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    if not os.path.isdir(root):
        print("not a directory: %s" % root); return 2
    print("SEO static check: %s\n%s\n" % (root, "=" * 60))
    check_site_files(root, a.site_url)
    check_config(root, a.site_url)
    check_dynamic(root)
    print()
    check_pages(root, a.site_url)

    print("\n" + "=" * 60)
    for sev, bucket in ((ERROR, errors), (WARN, warns), (INFO, notes)):
        if bucket:
            print("\n%s (%d)" % (sev, len(bucket)))
            for _, rule, msg in sorted(bucket):
                print("  [%s] %s" % (rule, msg))
    print("\n%d error(s), %d warning(s), %d info" % (len(errors), len(warns), len(notes)))
    print("Static check only: indexing, ranking and rendered-JS behaviour are NOT verified here.")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())