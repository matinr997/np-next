# NursePlus — برنامهٔ پیاده‌سازی (Implementation Plan)

وضعیت هر بخش: ✅ انجام‌شده · 🟡 نیمه‌کاره · ⬜ باقی‌مانده

## ۱) زیرساخت

| مورد | وضعیت | کجاست |
|---|---|---|
| ساختار پروژه، سیستم طراحی مشترک IR/COM | ✅ | `assets/globals.css`, `assets/config-ir.js`, `assets/config-com.js` |
| صفحات مستقل SEO (watch/topic) | ✅ | `scripts/gen_seo.py`, `videos/*/index.html` |
| دیتابیس SQLite برای توسعه + MySQL برای تولید | ✅ | `api/db.php`, `docs/schema.sql` |
| مدل‌ها و مهاجرت تدریجی | ✅ | `np_migrate()` در `api/db.php` |
| ساختار JSON به‌عنوان منبع محتوا | ✅ | `data/videos.json` |
| بستهٔ نتفراز | ✅ | `scripts/build_deploy.py` → `deploy/nurseplus-site.zip` |

## ۲) پنل ادمین

| ماژول | وضعیت | کجاست |
|---|---|---|
| ورود، نشست، CSRF | ✅ | `api/auth.php`, `api/security.php` |
| افزودن ویدیو، چندتایی، تشخیص تکراری | ✅ | `api/jobs.php`, `api/videos.php` |
| صف پایپ‌لاین (ماندگار، قفل، reaper) | ✅ | `api/jobs.php`, `scripts/pipeline_worker.py` |
| **چک‌لیست ۱۷ مرحله‌ای ماندگار** | ✅ | `api/stages.php`, `api/stage_lib.php` |
| **مرکز خطا** | ✅ | `api/errors.php` |
| **Fix Bug** | ✅ | `api/fixbug.php` |
| **بررسی محتوا (audit)** | ✅ | `api/audit.php` |
| **داشبورد** | ✅ | `api/dashboard.php` |
| **ابزارهای دستیار (۱۴ ابزار، ۳ سطح مجوز)** | ✅ | `api/tools.php` |
| **مدیریت مدل + آیکن قابلیت + context** | ✅ | `api/models.php`, `admin/models.js` |
| **آمار مصرف بر اساس مدل و کار** | ✅ | `api/models.php?action=usage`, `admin/ops.js` |
| **دستور `/compress`** | ✅ | `api/chat.php`, `admin/admin.js` |
| گزارش فعالیت | ✅ | جدول `activity_log` |
| انتشار گروهی با تأیید | 🟡 | ابزار `publish_video` آماده است، UI تأیید مانده |
| آپلود فایل → آزمون/زیرنویس | ✅ | `api/chat.php` + `handle_uploaded_file` |

## ۳) پایپ‌لاین

پنج مرحلهٔ اجرایی: discover → transcript → translate → quiz → publish.
هر مرحلهٔ اجرایی به یک یا چند مرحله از چک‌لیست نگاشت می‌شود.

| قابلیت | وضعیت |
|---|---|
| دریافت metadata | ✅ `yt-dlp` |
| دریافت زیرنویس | ✅ `youtube-transcript-api` |
| ترجمهٔ فارسی با assert واقعی | ✅ |
| تولید آزمون چندمدلی | ✅ |
| اعتبارسنجی ساختار آزمون | ✅ `scripts/fix_quiz_format.py --check` |
| انتشار + commit/push | ✅ |
| گزارش خطا به مرکز خطا | ✅ |
| ثبت توکن و هزینه هر فراخوانی | ✅ |

## ۴) امنیت

| مورد | وضعیت |
|---|---|
| CSRF روی همهٔ نوشتن‌ها | ✅ |
| محدودیت نرخ | ✅ |
| گزارش فعالیت ادمین | ✅ |
| پاک‌سازی کلیدها و مسیرها از لاگ | ✅ |
| محافظ SSRF برای endpoint | ✅ |
| محافظت از آپلود | ✅ |
| تأیید دو مرحله‌ای برای عملیات حساس | 🟡 ابزارها آماده، UI تأیید مانده |
| هش پسورد | ✅ bcrypt |

## ۵) تست

| فایل | پوشش |
|---|---|
| `tests/test_api.py` | سناریوهای ۱ تا ۲۰ بند ۱۳ |
| `tests/test_pipeline.py` | اعتبارسنجی آزمون، چک‌لیست، guardها |

## ۶) کارهای باقی‌مانده

1. UI تأیید برای انتشار/حذف (بند F)
2. اجرای خودکار audit زمان‌بندی‌شده (cron)
3. تخمین هزینه واقعی — نیازمند قیمت‌نامه provider
4. import یک‌بارهٔ JSON → MySQL روی هاست
5. دامنهٔ نهایی در `seo/site.json`
