# NursePlus — دیتابیس (Database)

## موتور

| محیط | موتور | چرا |
|---|---|---|
| توسعهٔ محل | SQLite | بدون نصب، فایل `.data/nurseplus.sqlite` |
| تولید (نتفراز) | MySQL / MariaDB | روی هاست اشتراکی موجود است |

لایهٔ PDO یکسان است؛ تفاوت فقط در `api/config.php` است.

## اسکیما

سه فایل، همه portable (بدون `AUTOINCREMENT`، بدون `TEXT DEFAULT`):

| فایل | محتوا |
|---|---|
| `api/db/schema.sqlite.sql` | اسکیمای پایه برای توسعه |
| `docs/schema.sqlite.sql` → `api/schema.mysql.sql` | نسخهٔ MySQL که همراه کد می‌رود |
| `api/db/schema_models.sql` | metadata مدل‌ها، override، usage، prefs، خلاصهٔ چت |
| `api/db/schema_ops.sql` | مراحل، مرکز خطا، گزارش فعالیت، audit، patchها |

## جدول‌ها

### محتوا
| جدول | نقش |
|---|---|
| `users` | کاربران؛ `role='admin'` برای پنل |
| `videos` | آینهٔ `data/videos.json` پس از import |
| `chat_messages` | پیام‌های گفتگوی پنل |
| `chat_summary` | خلاصهٔ running از `/compress` |

### پایپ‌لاین
| جدول | نقش |
|---|---|
| `pipeline_jobs` | صف کارها؛ `kind` در ('video','chat') |
| `job_stages` | **چک‌لیست**: یک ردیف برای هر مرحلهٔ هر کار |

### مدل و مصرف
| جدول | نقش |
|---|---|
| `llm_settings` | endpoint، کلید، مدل (کلید هرگز به مرورگر نمی‌رود) |
| `llm_models` | فهرست سادهٔ شناسه‌ها (سازگاری با نسخهٔ قبل) |
| `llm_model_meta` | قابلیت‌ها، context، منبع، وضعیت تأیید |
| `llm_model_overrides` | بازنویسی دستی — جدا از metadata خودکار |
| `llm_usage` | یک ردیف برای هر فراخوانی مدل |
| `llm_prefs` | تنظیمات غیرمحرمانه (آستانه‌ها، استراتژی، rate limit) |

### عملیاتی
| جدول | نقش |
|---|---|
| `error_log` | مرکز خطا |
| `activity_log` | هر اقدام ادمین |
| `content_issues` | یافته‌های بررسی محتوا |
| `bugfix_patches` | patchهای پیشنهادی و تست‌شده |

## کلیدها و indexها

- `llm_model_meta` و `llm_model_overrides`: کلید `(endpoint_id, model_id)` —
  چون شناسهٔ مدل بین providerها یکتا نیست.
- `llm_usage`: کلید `id` + index روی `model_id` و `created_at`
  (در `np_migrate` اضافه می‌شود).
- `job_stages`: کلید `id` + index روی `(job_id, stage)`.

## زمان

همه‌جا **UTC** ذخیره می‌شود (`gmdate('Y-m-d H:i:s')`) و در UI به وقت محلی
نمایش داده می‌شود.

## مهاجرت

```bash
# روی هاست، یک‌بار:
https://domain.ir/api/setup.php
```

`api/setup.php`:
1. اسکیمای پایه را اجرا می‌کند (`CREATE TABLE IF NOT EXISTS`)
2. `api/db/schema_models.sql` و `api/db/schema_ops.sql` را اجرا می‌کند
3. `np_migrate()` ستون‌های جدید را به جدول‌های موجود اضافه می‌کند
4. ادمین اول را از `api/config.php` می‌سازد

**مهلت اجرای migration در درخواست عمومی ممنوع است.** `setup.php` را بعد از
اجرا حذف کنید یا با یک توکن محافظت کنید.

## پشتیبان‌گیری

```bash
# قبل از هر migration
mysqldump -u USER -p DBNAME > backup-$(date +%F).sql
```

بازگردانی:

```bash
mysql -u USER -p DBNAME < backup-2026-10-20.sql
```

## بازگشت (rollback)

- migrationها **هرگز** `DROP` یا `TRUNCATE` نمی‌کنند — فقط `ADD COLUMN`
- اگر یک ستون اضافه مشکل‌ساز بود، نسخهٔ قبلی کد را برگردانید؛ ستون بی‌استفاده
  می‌ماند و کار می‌کند
- برای حذف کامل: restore از dump
