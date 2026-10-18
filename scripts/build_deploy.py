#!/usr/bin/env python3
"""Build the Netafraz deployment package from the current repo state.

Run this EVERY time before uploading to public_html:
    python3 scripts/build_deploy.py

It re-copies every runtime file (so new videos/subs/quizzes are picked up
automatically), refreshes the README, and writes a fresh ZIP.
"""
import glob, json, os, shutil, sys, zipfile

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
         ('data/videos.json','data/')]

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

# ---------- 2. backend stub (kept in sync, never uploaded by accident) ----------
os.makedirs(PUB + '/api', exist_ok=True)
for name in ('index.php', 'config.example.php', '.htaccess', 'README.txt', 'account-endpoints.md'):
    src = os.path.join(ROOT, 'api', name)
    if os.path.exists(src):
        shutil.copy(src, PUB + '/api/' + name)

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
open(PUB + '/robots.txt', 'w', encoding='utf-8').write('User-agent: *\nAllow: /\n')

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