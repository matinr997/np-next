#!/usr/bin/env python3
"""Build the Netafraz deployment package from the current repo state.

Run this EVERY time before uploading to public_html:
    python3 scripts/build_deploy.py

It re-copies every runtime file (so new videos/subs/quizzes are picked up
automatically), refreshes the README, and writes a fresh ZIP.
"""
import glob, json, os, shutil, subprocess, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEP  = os.path.join(ROOT, 'deploy', 'nurseplus-site')
PUB  = os.path.join(DEP, 'public_html')

# ---------- 1. fresh copy ----------
if os.path.isdir(os.path.join(ROOT, 'deploy')):
    shutil.rmtree(os.path.join(ROOT, 'deploy'))
os.makedirs(PUB, exist_ok=True)

PAGES = [('index.html',''), ('premium.html',''), ('schedule.html',''), ('account.html',''),
         ('com/index.html','com/'), ('com/premium.html','com/'),
         ('com/schedule.html','com/'), ('com/account.html','com/'),
         ('lib/player-core.js','lib/'), ('lib/skeleton.js','lib/'),
         ('data/videos.json','data/'), ('data/seo.json','data/'),
         ('robots.txt',''), ('sitemap.xml',''), ('sitemap-video.xml',''),
         ('404.html',''), ('seo/site.json','seo/')]

for rel, dest in PAGES:
    src = os.path.join(ROOT, rel)
    if not os.path.exists(src):
        print('  ! missing', rel); continue
    out = os.path.join(PUB, dest, os.path.basename(rel))   # dest may be '', 'lib/', 'com/', 'data/'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    shutil.copy(src, out)

os.makedirs(PUB + '/assets', exist_ok=True)
for f in glob.glob(os.path.join(ROOT, 'assets', '*')):
    b = os.path.basename(f)
    if b.endswith(('.css', '.js', '.png')):
        shutil.copy(f, PUB + '/assets/' + b)

for sub in ('subs', 'quizzes'):
    os.makedirs(PUB + '/' + sub, exist_ok=True)
    for f in glob.glob(os.path.join(ROOT, sub, '*.json')):
        shutil.copy(f, PUB + '/' + sub + '/')

# ---------- 1b. generated watch + topic pages (both languages) ----------
# These ARE the indexable content. If gen_seo.py has not run, the package would
# ship without them and the sitemap would point at nothing.
n_pages = 0
for base_rel in ('', 'com/'):
    for kind in ('videos', 'topics'):
        src = os.path.join(ROOT, base_rel, kind)
        if not os.path.isdir(src):
            continue
        n_pages += sum(1 for _ in glob.glob(os.path.join(src, '*', 'index.html')))
        shutil.copytree(src, os.path.join(PUB, base_rel, kind), dirs_exist_ok=True)
print('  watch/topic pages: %d' % n_pages)

# ---------- 1c. SEO gate ----------
import sys as _sys
_lint = subprocess.run([_sys.executable, os.path.join(ROOT, 'scripts', 'check_seo.py'), ROOT,
                        '--site-url', 'https://matinr997.github.io/np-next'],
                       capture_output=True, text=True)
_err = [l for l in _lint.stdout.splitlines() if l.strip().startswith('[')]
print('  SEO lint: %s' % ('PASS' if _lint.returncode == 0 else 'FAIL (%d errors)' % _err.__len__()))
if _lint.returncode != 0:
    for l in _err:
        print('    ' + l.strip())

# ---------- 2. the API + the admin panel ----------
# The panel is useless without the API next to it, so both travel together.
# config.php holds the database credentials: it is gitignored, blocked by
# api/.htaccess, and must never be copied into a package.
os.makedirs(PUB + '/api', exist_ok=True)
for src in sorted(glob.glob(os.path.join(ROOT, 'api', '*.php'))):
    name = os.path.basename(src)
    if name in ('config.php', 'config.local.php'):
        print('  ! refusing to package %s (secrets)' % name)
        continue
    shutil.copy(src, PUB + '/api/' + name)
for name in ('.htaccess', 'README.txt', 'account-endpoints.md'):
    src = os.path.join(ROOT, 'api', name)
    if os.path.exists(src):
        shutil.copy(src, PUB + '/api/' + name)
# the MySQL schema has to travel with the code: api/setup.php creates the
# tables on the host, and docs/ is not deployed.
shutil.copy(os.path.join(ROOT, 'docs', 'schema.sql'), PUB + '/api/schema.mysql.sql')
if os.path.isdir(os.path.join(ROOT, 'api', 'db')):
    shutil.copytree(os.path.join(ROOT, 'api', 'db'), PUB + '/api/db', dirs_exist_ok=True)

# the admin panel (its head is already injected with noindex by gen_seo.py)
if os.path.isdir(os.path.join(ROOT, 'admin')):
    shutil.copytree(os.path.join(ROOT, 'admin'), PUB + '/admin', dirs_exist_ok=True)
    print('  admin panel: %d file(s)' % len(glob.glob(os.path.join(ROOT, 'admin', '*'))))

# ---------- 3. server config ----------
open(PUB + '/.htaccess', 'w', encoding='utf-8').write('''# ============ NursePlus static hosting (Netafraz / DirectAdmin) ============
Options -Indexes
AddDefaultCharset UTF-8
<IfModule mod_mime.c>
  AddType application/json .json
</IfModule>
<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE text/html text/css text/javascript application/javascript application/json image/svg+xml
</IfModule>
<IfModule mod_expires.c>
  ExpiresActive On
  ExpiresByType text/html                 "access plus 10 minutes"
  ExpiresByType text/css                  "access plus 7 days"
  ExpiresByType application/javascript    "access plus 7 days"
  ExpiresByType application/json          "access plus 1 hour"
  ExpiresByType image/png                 "access plus 30 days"
</IfModule>
# === HTTPS: uncomment AFTER enabling SSL in DirectAdmin ===
# <IfModule mod_rewrite.c>
#   RewriteEngine On
#   RewriteCond %{HTTPS} !=on
#   RewriteRule ^(.*)$ https://%{HTTP_HOST}/$1 [R=301,L]
# </IfModule>
# A real 404 status is a crawling signal; serving 404.html with a 200 is a soft 404.
ErrorDocument 404 /404.html
<FilesMatch "config\\.php$|\\.bak$|\\.env$">
  <IfModule mod_authz_core.c>
    Require all denied
  </IfModule>
  <IfModule !mod_authz_core.c>
    Order allow,deny
    Deny from all
  </IfModule>
</FilesMatch>
''')

# ---------- 4. README ----------
readme_src = os.path.join(ROOT, 'deploy-README.md')
if os.path.exists(readme_src):
    shutil.copy(readme_src, DEP + '/README-DEPLOY.md')

# ---------- 5. zip ----------
zp = DEP + '.zip'
zf = zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED, compresslevel=9)
count = 0
for dp, ds, fs in os.walk(DEP):
    for f in sorted(fs):
        if f == '.DS_Store':
            continue
        full = os.path.join(dp, f)
        zf.write(full, 'nurseplus-site/' + os.path.relpath(full, DEP))
        count += 1
zf.close()

# ---------- 6. integrity report ----------
videos = json.load(open(os.path.join(ROOT, 'data/videos.json'), encoding='utf-8'))
subs = len(glob.glob(os.path.join(ROOT, 'subs', '*.json')))
quizzes = len(glob.glob(os.path.join(ROOT, 'quizzes', '*.json')))
print('DEPLOY PACKAGE REBUILT')
print('  videos.json : %d' % len(videos))
print('  subs/       : %d' % subs)
print('  quizzes/    : %d' % quizzes)
print('  files       : %d' % count)
print('  size        : %d KB' % (os.path.getsize(zp) // 1024))
print('  zip         : %s' % zp)