# انتقال به هاست نتفراز — راهنمای گام‌به‌گام

این سند از وضعیت فعلی مخزن (commit `d84da50`) نوشته شده است. هدف: سایت روی
هاست اشتراکی نتفراز بالا بیاید، پنل ادمین کار کند، و ویدیوی جدید با چسباندن
یک لینک ساخته شود.

## چرا کار می‌کند با اینکه دیتابیس از بیرون بسته است

```
مرورگر  ──HTTPS──▶  PHP روی هاست  ──PDO──▶  MySQL روی هاست
                          ▲
                          │ فقط HTTP (هدر X-Worker-Token)
                    worker روی مک
                      └── مدل هوش مصنوعی (روتر ۹router روی مک)
```

**worker هرگز مستقیم به MySQL وصل نمی‌شود.** از راه API سایت کار می‌کند.
تنها چیزی که از بیرون لازم است، آدرس عمومی سایت است.

---

## گام ۱ — دیتابیس

DirectAdmin → **MySQL Management** → Create new Database:

| | |
|---|---|
| Database name | `nurseplus` |
| Database user | `nurseplus` |
| Password | یک رمز قوی (همین را در `config.php` می‌گذاری) |

`utf8mb4` را انتخاب کن (پیش‌فرض است).

## گام ۲ — فایل config

داخل پروژه:

```bash
cp api/config.example.php api/config.php
```

و داخل `api/config.php` این‌ها را پر کن:

```php
'db' => [
  'driver'  => 'mysql',
  'host'    => 'localhost',
  'name'    => 'USERNAME_nurseplus',
  'user'    => 'USERNAME_nurseplus',
  'pass'    => 'PASSWORD',
  'charset' => 'utf8mb4',
],
'admin' => [
  'email'    => 'you@example.com',
  'password' => 'یک رمز قوی برای پنل',
  'name'     => 'Admin',
],
'worker_token' => 'یک رشتهٔ تصادفی ۳۲ بایتی',
```

ساخت `worker_token`:

```bash
php -r "echo bin2hex(random_bytes(32)), PHP_EOL;"
```

> `api/config.php` داخل `.gitignore` است و `api/.htaccess` جلوی دانلودش را
> می‌گیرد. **هرگز commit نشود.**

## گام ۳ — ساخت پکیج

```bash
python3 scripts/build_deploy.py
```

خروجی: `deploy/nurseplus-site.zip` (۱۳۲ فایل). شامل: سایت، صفحه‌های
watch/topic، `api/` (کل PHP)، `admin/` (پنل)، `data/`، `subs/`، `quizzes/`،
`.htaccess`.

> `api/config.php` عمداً داخل پکیج **نیست** — builder آن را رد می‌کند.

## گام ۴ — آپلود

DirectAdmin → **File Manager** → `public_html`:

1. `deploy/nurseplus-site.zip` را Upload کن
2. روی فایل ZIP → **Extract** (محتویات یک سطح بالا می‌آید، نه داخل پوشه)
3. پوشهٔ `nurseplus-site/` را اگر ساخته شد حذف کن

حالا `https://domain.ir/index.html` باید بالا بیاید.

## گام ۵ — ساخت جدول‌ها و ادمین

یک‌بار در مرورگر:

```
https://domain.ir/api/setup.php
```

باید JSON بدهد که `admin_created` دارد. این کار جدول‌ها را از
`api/schema.mysql.sql` می‌سازد و ادمین اول را از `config.php` می‌سازد.

تأیید:

```
https://domain.ir/api/index.php   →  "db":"connected"
```

## گام ۶ — worker روی مک

```bash
./scripts/worker.sh --daemon
```

لاگ: `deploy/worker.log`. توقف: `pkill -f pipeline_worker.py`.

worker از `api/config.php` آدرس سایت و `worker_token` را می‌خواند؛ چیزی برای
تنظیم نیست.

> اگر `config.php` آدرس سایت ندارد، با `--site` بده:
> `./scripts/worker.sh` با `NP_SITE=https://domain.ir` در محیط.

## گام ۷ — پنل

```
https://domain.ir/admin/
```

با ایمیل/رمز ادمین وارد شو. صفحه `noindex,nofollow` است (در گوگل نمی‌آید)
و `robots.txt` آن را مسدود نکرده — چون مسدودکردن مانع خواندن noindex می‌شود.

---

## بعد از نصب: روزمره

| کار | چطور |
|---|---|
| افزودن ویدیو | در پنل لینک را paste کن → «افزودن به صف» |
| لینک تکراری | خودکار رد می‌شود: «این لینک تکراری است» |
| ساخت آزمون از فایل | در تب «دستیار» فایل را رها کن (PDF/DOCX/TXT → آزمون، SRT → زیرنویس) |
| هر کار دیگر | همان تب — سؤال‌ها سریع، کدنویسی با عامل کامل |
| تغییر مدل | در پنل: endpoint + کلید + مدل (از بین ۵۷۹ مدل) |
| انتشار | worker خودش commit و push می‌کند → GitHub Pages به‌روز می‌شود |

## نکته‌های مهم

- **دامنهٔ نهایی را در `seo/site.json` بگذار** (`canonicalOrigin.ir` و
  `canonicalOrigin.com`)، بعد `python3 scripts/gen_seo.py` و
  `python3 scripts/build_deploy.py`. هیچ canonical/hreflang دستی عوض نشود.
- **کار از مک انجام می‌شود، نه از هاست.** دلیلش این است که endpoint مدل
  (`http://localhost:20128/v1`) فقط روی مک در دسترس است. اگر خواستی cron
  خود هاست هم کار کند، endpoint باید عمومی باشد.
- **HTTPS را در DirectAdmin فعال کن** و بعد در `.htaccess` بخش
  `# === HTTPS` را از حالت کامنت خارج کن و دوباره پکیج بساز.
- **phpMyAdmin** در DirectAdmin برای کارهای دستی دیتابیس هست.
