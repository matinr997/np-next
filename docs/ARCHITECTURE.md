# NursePlus — معماری پروژه و برنامهٔ توسعه (Architecture)

> سند مرجع برای هر session آینده — ساختار تصمیم‌ها، نه توضیح کد.

## ۱) گردش کار توسعه (Development Workflow)

```
GitHub (matinr997/np-next)  →  تست/فیکس لوکال  →  ZIP پکیج  →  آپلود به Netafraz (public_html)
```

- کد و فیکس باگ‌ها **همیشه روی GitHub** انجام می‌شود (`main` = نسخهٔ قابل نمایش).
- بعد از تست، پکیج `deploy/nurseplus-site.zip` ساخته می‌شود (دستورالعمل: `deploy/README-DEPLOY.md`).
- آپلود به Netafraz: File Manager → `public_html` → Upload ZIP → Extract → Move محتویات یک سطح بالا.
- سایت زندهٔ GitHub Pages (`matinr997.github.io/np-next`) فقط **پیش‌نمایش** است؛ محیط اصلی = Netafraz.

## ۲) دو نسخه، یک هاست، یک دیتابیس

| | نسخهٔ ایران (ir) | نسخهٔ بین‌الملل (com) |
|---|---|---|
| مسیر | ریشهٔ دامنه `/` | زیرپوشهٔ `/com/` |
| زبان/جهت | فارسی، RTL | انگلیسی، LTR |
| پرداخت | زرین‌پال (تومان/IRR) | Stripe (USD) |
| تبلیغات نسخهٔ free | دارد | دارد |
| منطق/کد | **مشترک** — `lib/player-core.js`, `lib/skeleton.js`, `assets/globals.css`, `assets/schedule.js` | همان فایل‌ها |
| متفاوت | `assets/config-ir.js` + متن‌ها/قیمت‌ها در صفحات | `assets/config-com.js` + همان |

- هر دو نسخه از **یک دیتابیس MySQL مشترک** استفاده می‌کنند؛ تفاوت نسخه‌ها فقط `user.source` و درگاه پرداخت است.
- فرانت‌اند فعلاً **کاملاً static** است (بدون هیچ وابستگی به سرور)؛ بک‌اند بعداً اضافه می‌شود و نباید قابلیت‌های static را خراب کند.

## ۳) دیتابیس (بعداً روی Netafraz — یک MySQL واحد)

جدول‌های اصلی (طرح کامل: `docs/schema.sql`):

| جدول | محتوا |
|---|---|
| `users` | حساب کاربر: name, email, pass_hash, subscription(plan, expires), **source(ir/com)** |
| `videos` | اطلاعات ویدیوها: youtube id, title fa/en, topic, duration, source channel, views |
| `video_progress` | کدام کاربر کدام ویدیو را چقدر دیده (watched_seconds, pct, completed, last_seen) |
| `quiz_questions` | سؤالات آزمون هر ویدیو (mc/cloze/dnd — هم‌ساختار quizzes/*.json فعلی) |
| `quiz_results` | نتیجهٔ آزمون کاربر (score, total, taken_at) |
| `schedules` | برنامهٔ مطالعهٔ شخصی هر کاربر (title, end_date) |
| `schedule_items` | آیتم‌های برنامه: ویدیو + موضوع + روز (done/done_at) |
| `payments` | تراکنش‌ها: gateway(zarinpal/stripe), amount, currency(IRT/USD), status, ref_id |

قواعد:
- charset همهٔ جداول `utf8mb4` (فارسی + ایموجی).
- تاریخ‌ها/روزهای برنامه: `DATE` سروری (نه از client)؛ نمایش فارسی/انگلیسی فقط در UI.
- رمز فقط hash (bcrypt/argon2) — هیچ‌وقت plain.
- `payments.gateway` و `users.source` تعیین‌کنندهٔ مسیر zarinpal/stripe.

## ۴) بک‌اند روی Netafraz (بعداً)

- PHP 8.1+ (Select PHP Version در DirectAdmin)، پوشهٔ `api/` در `public_html`.
- `api/config.php` (کپی از `config.example.php`) — مقادیر DB؛ توسط `.htaccess` مسدود است.
- ترتیب پیاده‌سازی پیشنهادی: auth (ثبت‌نام/ورود) → video_progress → quiz_results → schedules → payments (زرین‌پال callback → Stripe checkout).
- تا بک‌اند آماده نشده، localStorage (`np_sched_data`, `np_seen`, `np_bm`, …) منبع حقیقت فرانت است؛ بعداً sync دوطرفه.

## ۵) پوشه‌ها — چیست و چه کجاست

```
lib/            منطق مشترک (پلیر، آزمون، پنل transcript، schedule؟ نه — schedule مستقل)
assets/         استایل‌ها + bootstrap دو نسخه + فونت/آیکن
subs/ quizzes/  دادهٔ ثابت (JSON) — هر ویدیو یک فایل
data/           videos.json (منبع برنامهٔ مطالعه)
scripts/        ابزارهای dev (gen_quiz.py و ...) — آپلود نمی‌شود
deploy/         پکیج آمادهٔ آپلود (zip) — آپلود نمی‌شود خودش؛ zip خروجی اینجاست
api/            فقط در پکیج آپلود (در repo فقط نمونهٔ PHP)
```
