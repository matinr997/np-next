# NursePlus — امنیت (Security)

## اصل حاکم

هیچ فراخوانی مدل، هیچ فایل آپلودی، هیچ متن زیرنویس و هیچ دادهٔ یوتیوب
**دستور** محسوب نمی‌شود. مدل پیشنهاد می‌دهد؛ backend تصمیم می‌گیرد.

## احراز هویت

- نشست PHP با `HttpOnly`، `SameSite=Lax` و `Secure` روی HTTPS
- `session_regenerate_id(true)` بعد از ورود
- فقط `role='admin'` به پنل دسترسی دارد
- رمز با bcrypt ذخیره می‌شود (`PASSWORD_DEFAULT`)

## CSRF

هر نوشتنی (POST) باید هدر `X-CSRF-Token` را با توکن نشست بفرستد.

```php
np_require_csrf();   // در هر endpoint نوشتن
```

توکن با پاسخ ورود و با `GET /api/auth.php?action=csrf` می‌آید. اگر توکن
منقضی شود، پنل ۴۰۳ می‌گیرد و توکن تازه می‌گیرد.

**worker** از CSRF exempt است: با `X-Worker-Token` احراز می‌کند که یک
محرر مشترک است و فقط بین مک و هاست رد و بدل می‌شود.

## محدودیت نرخ

`np_rate_limit($bucket, $limit, $window)` روی جدول `llm_prefs` کار می‌کند
(بدون memcached، مناسب هاست اشتراکی). پاسخ ۴۲۹ با `retry_after`.

## محافظت از endpoint (SSRF)

endpoint یک URL قابل تنظیم است، پس ریسک SSRF دارد.

`np_endpoint_allowed()` در `api/security.php`:

| مقصد | نتیجه |
|---|---|
| `127.0.0.1`، `localhost`، `10.x`، `192.168.x`، `172.16-31.x`، `169.254.x` | رد، مگر `allow_private_endpoint=true` |
| `169.254.169.254` (metadata ابری) | **همیشه** رد |
| `metadata.google.internal` | **همیشه** رد |
| scheme غیر http/https | رد |
| پورت نامعتبر | رد |

در تولید `allow_private_endpoint` باید `false` باشد.

## سه سطح مجوز برای ابزارهای دستیار

| سطح | نمونه | رفتار |
|---|---|---|
| `read` | `search_videos`, `get_job` | همیشه مجاز |
| `mutate` | `retry_stage`, `cancel_job` | نیازمند نشست + CSRF + ثبت در گزارش فعالیت |
| `sensitive` | `publish_video`, `unpublish_video` | فقط **پیشنهاد**؛ اجرا نیازمند تأیید ادمین |

مدل به SQL، فایل‌سیستم یا shell دسترسی ندارد. ابزارها schema صریح دارند و
خروجشان ساختاریافته است.

## Fix Bug

محدودیت‌های سخت روی patch پیشنهادی:

| محدودیت | جزئیات |
|---|---|
| فقط unified diff | فرمت دیگر رد می‌شود |
| بدون shell | `exec`, `system`, `passthru`, `popen`, `proc_open` رد می‌شوند |
| بدون `eval` | رد می‌شود |
| بدون `rm -rf` | رد می‌شود |
| بدون patch باینری | رد می‌شود |
| allow-list فایل | فقط `scripts/`, `api/`, `lib/`, `assets/`, `com/`, `data/`, `quizzes/`, `subs/` |
| فهرست ممنوع | `api/config.php`, `api/auth.php`, `api/security.php`, `api/db.php`, `api/setup.php`, `.htaccess`, `.github/workflows/`, `deploy/`, `.env` |
| ریسک بالا | `api/` و `lib/` → تأیید دستی لازم دارد |
| تست | فقط patchی که چک‌هایش قبول شده قابل تأیید است |
| ایزوله | patch در یک کپی جداگانه ساخته و تست می‌شود؛ **هاست هرگز کد مدل‌ساخته را اجرا نمی‌کند** |

## پاک‌سازی داده حساس

`np_redact()` روی هر پیام خطا و هر جزئیات ذخیره‌شده اجرا می‌شود:

- `sk-…` → `sk-…REDACTED`
- `Bearer …` → `Bearer REDACTED`
- `api_key=`, `password=`, `token=`, `secret=` → مقدار REDACTED
- رشته‌های ۳۲+ کاراکتری → REDACTED
- مسیرهای مطلق → `…/filename`

## رازها

| راز | کجاست | چطور محافظت می‌شود |
|---|---|---|
| کلید API | `api/config.php` → `llm_settings` | در پنل فقط ماسک‌شده؛ به مرورگر نمی‌رود |
| `worker_token` | `api/config.php` | worker فقط |
| رمز ادمین | `api/config.php` → bcrypt در `users` | هرگز commit نمی‌شود |
| رمز دیتابیس | `api/config.php` | `api/.htaccess` جلوی دانلود را می‌گیرد |

`api/config.php` در `.gitignore` است و builder آن را داخل ZIP نمی‌گذارد.

## آپلود فایل

- ذخیره در `api/uploads/` (بیرون از مسیر اجرای PHP)
- سقف ۳۲ مگاباکت
- نام فایل پاک‌سازی می‌شود
- هرگز خودکار اجرا نمی‌شود
- فقط از worker (با `X-Worker-Token`) دانلود می‌شود

## XSS

همهٔ خروجی‌ها در JS با `esc()` escape می‌شوند و در PHP با `htmlspecialchars`.

## ثبت رویدادها

جدول `activity_log`: هر اقدام ادمین با actor، action، target، IP و زمان.
هر اقدام حساس (انتشار، تأیید patch، اجرای audit) ثبت می‌شود.

## قبل از تولید

- [ ] `allow_private_endpoint = false`
- [ ] رمز ادمین تولیدی و منحصربه‌فرد
- [ ] `worker_token` تصادفی ۳۲ بایتی
- [ ] HTTPS فعال
- [ ] `api/setup.php` بعد از اجرا حذف یا محافظت شود
- [ ] دسترسی پوشهٔ `api/uploads` غیرقابل‌نوشتن برای وب
- [ ] پشتیبان‌گیری خودکار از دیتابیس
- [ ] `api/config.php` روی هاست، خارج از دسترس عمومی
