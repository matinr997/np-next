# NursePlus — توسعهٔ محل (Local Development)

## پیش‌نیازها

| ابزار | نسخه | چرا |
|---|---|---|
| Python | 3.9+ | worker و اسکریپت‌ها |
| PHP | 8.0+ | API و پنل (۸٫۵ تست شده) |
| node | هر نسخهٔ جدید | فقط برای بررسی نحوی JS |
| SQLite | همراه PHP | دیتابیس توسعه |

```bash
python3 -m pip install --user yt-dlp youtube-transcript-api
```

## راه‌اندازی

```bash
cd nurseplus-web

# ۱) تنظیمات محلی
cp api/config.example.php api/config.php
#    درون آن: driver=sqlite، admin، worker_token

# ۲) دیتابیس و ادمین
php -S 127.0.0.1:8125 -t . &
curl http://127.0.0.1:8125/api/setup.php

# ۳) worker
./scripts/worker.sh --daemon
```

پنل: <http://127.0.0.1:8125/admin/index.html>

## پیکربندی

| متغیر | کجا | توضیح |
|---|---|---|
| endpoint | `api/config.php` → `llm` | پایهٔ URL بدون `/chat/completions` |
| کلید | `api/config.php` | هرگز commit نشود |
| مدل | پنل → تنظیمات مدل | یا در `api/config.php` |
| `allow_private_endpoint` | `api/config.php` | برای endpoint لوکال `true` |

> endpoint لوکال `http://localhost:20128/v1` فقط روی همان ماشین کار می‌کند.
> روی هاست، `localhost` یعنی خودِ هاست. برای تولید باید endpoint عمومی
> باشد یا worker روی ماشینی بماند که به آن دسترسی دارد.

## نکتهٔ امنیتی محل

برای اینکه endpoint لوکال مجاز باشد:

```php
'allow_private_endpoint' => true,
```

در تولید این را `false` بگذارید. دامنهٔ metadata ابری (169.254.169.254)
**همیشه** رد می‌شود.

## تست

```bash
python3 tests/test_api.py            # سناریوهای API
python3 tests/test_pipeline.py        # اعتبارسنجی آزمون و چک‌لیست
python3 scripts/check_seo.py . --site-url http://127.0.0.1:8125
```

تست‌ها به یک سرور محلی نیاز دارند:

```bash
php -S 127.0.0.1:8125 -t . &
```

## ساختار داده

```
data/videos.json     ← منبع محتوا (۲۰ ویدیو)
subs/<id>.json       ← transcript دوزبانه
quizzes/<id>.json    ← آزمون
lib/player-core.js   ← VIDEOS جاسازی‌شده (با sync_videos_to_core.py همگام می‌شود)
```

بعد از هر تغییر در `data/videos.json`:

```bash
python3 scripts/sync_videos_to_core.py
```

## کار از ابتدا

```bash
php -S 127.0.0.1:8125 -t .     # API + پنل
./scripts/worker.sh --daemon    # worker
```

سپس در پنل لینک یوتیوب را بچسبانید. مرحله‌به‌مرحله در «چک‌لیست پردازش»
دیده می‌شود.

## عیب‌یابی

| نشانه | علت | راه‌حل |
|---|---|---|
| `403 csrf_failed` | توکن منقضی شده | صفحه را تازه کنید |
| `endpoint_private_blocked` | endpoint لوکال در تولید | `allow_private_endpoint` را بررسی کنید |
| worker صف را خالی می‌بیند | `worker_token` ناهماهنگ | `api/config.php` هر دو طرف |
| `no such column` | migration اجرا نشده | `api/setup.php` را صدا بزنید |
| صف قفل شده | worker مرده | reaper بعد از ۱۵ دقیقه آزاد می‌کند |
