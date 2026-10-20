-- ============================================================
-- NursePlus shared database — DRAFT (implement later on Netafraz)
-- ONE database for both versions (.ir + .com).
-- charset utf8mb4 everywhere (Persian + emoji). Engine InnoDB.
-- PHP backend (api/) reads these via config.php.
-- ============================================================

CREATE TABLE users (
  id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name         VARCHAR(120)  NOT NULL,
  email        VARCHAR(190)  NOT NULL UNIQUE,
  pass_hash    VARCHAR(255)  NOT NULL,                      -- bcrypt/argon2 only
  plan         ENUM('free','premium') NOT NULL DEFAULT 'free',
  plan_expires DATETIME      NULL,                          -- null = free
  source       ENUM('ir','com') NOT NULL,                  -- registration source (ir / com)
  role         ENUM('user','admin') NOT NULL DEFAULT 'user',-- اولین admin را دستی/آیتم setup می‌سازیم
  created_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- NEW (2026-10-18): topics جدول مستقل — «cat» متن آزاد حذف شد.
-- فرانت هنوز cat/cat_en از videos.json می‌خواند؛ DB هر دو را نگه می‌دارد
-- (cat برای نمایش سریع، topic_id برای گزارش ضعف و برنامهٔ مطالعه).
-- ============================================================
CREATE TABLE topics (
  id         SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  fa         VARCHAR(60)  NOT NULL UNIQUE,                  -- قلب و عروق
  en         VARCHAR(60)  NOT NULL UNIQUE,                  -- Cardiovascular
  icon       VARCHAR(16)  NULL,                             -- emoji
  sort_order TINYINT UNSIGNED NOT NULL DEFAULT 0,
  active     TINYINT(1)   NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE videos (
  id           CHAR(11) PRIMARY KEY,                        -- YouTube video id (e.g. oNEBmBtBvtw)
  title_fa     VARCHAR(255) NOT NULL,
  title_en     VARCHAR(255) NOT NULL,
  summary_fa   TEXT         NULL,                           -- NEW: sum از videos.json
  summary_en   TEXT         NULL,
  topic_id     SMALLINT UNSIGNED NULL,                      -- NEW: FK به topics
  topic        VARCHAR(60)  NOT NULL,                       -- (kept for fast display / import compat)
  topic_en     VARCHAR(60)  NOT NULL,
  dur_seconds  INT UNSIGNED NOT NULL DEFAULT 0,
  channel      VARCHAR(120) NOT NULL DEFAULT '',
  views        INT UNSIGNED NOT NULL DEFAULT 0,             -- نمای یوتیوب (اعتمادسازی)
  has_transcript TINYINT(1) NOT NULL DEFAULT 0,
  published_at DATE         NULL,
  -- ===== NEW (2026-10-18) =====
  chapters     JSON         NULL,                           -- [{t:sec, fa:'...', en:'...'}] — تایم‌لاین پلیر
  difficulty   ENUM('easy','medium','hard') NOT NULL DEFAULT 'medium',
  status       ENUM('draft','reviewed','published') NOT NULL DEFAULT 'draft',
                                                  -- pipeline می‌سازد → admin تایید → publish
  tags         JSON         NULL,                           -- ["ECG","valves",...]
  objectives_fa JSON       NULL,                            -- ["هدف یادگیری ...", ...]
  objectives_en JSON       NULL,
  active       TINYINT(1)   NOT NULL DEFAULT 1,
  KEY idx_topic (topic),
  KEY idx_status (status),
  CONSTRAINT v_topic FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL
  created_at     VARCHAR(32) NOT NULL DEFAULT '',
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE video_progress (
  id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id         BIGINT UNSIGNED NOT NULL,
  video_id        CHAR(11)        NOT NULL,
  watched_seconds INT UNSIGNED    NOT NULL DEFAULT 0,
  pct             TINYINT UNSIGNED NOT NULL DEFAULT 0,      -- 0..100
  completed       TINYINT(1)      NOT NULL DEFAULT 0,
  last_seen       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_user_video (user_id, video_id),
  CONSTRAINT fp_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fp_video FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE quiz_questions (
  id        BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  video_id  CHAR(11)     NOT NULL,
  ord       TINYINT UNSIGNED NOT NULL,                      -- ترتیب سؤال در آزمون
  type      ENUM('mc','cloze','dnd') NOT NULL,
  difficulty ENUM('easy','medium','hard') NOT NULL DEFAULT 'medium',  -- NEW: سطح سؤال برای گزارش ضعف
  q_fa      TEXT NOT NULL,
  q_en      TEXT NOT NULL,
  opts_fa   JSON NULL,                                      -- گزینه‌ها (mc)
  opts_en   JSON NULL,
  blanks    JSON NULL,                                      -- {0} markers (cloze)
  items     JSON NULL,                                      -- chips (dnd)
  keep      JSON NULL,                                      -- درست‌های dnd
  correct   TINYINT UNSIGNED NULL,                          -- mc
  ts        INT UNSIGNED NULL,                              -- ثانیه‌ی نمایش پاسخ در ویدیو
  why_fa    TEXT NULL,
  why_en    TEXT NULL,
  CONSTRAINT qq_video FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
  KEY idx_video (video_id, ord)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE quiz_results (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id    BIGINT UNSIGNED NOT NULL,
  video_id   CHAR(11)     NOT NULL,
  score      TINYINT UNSIGNED NOT NULL,
  total      TINYINT UNSIGNED NOT NULL,
  taken_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT qr_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT qr_video FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
  KEY idx_user_video (user_id, video_id, taken_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE schedules (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id    BIGINT UNSIGNED NOT NULL,
  title      VARCHAR(160) NOT NULL,
  end_date   DATE         NOT NULL,                        -- مثلاً 2026-10-26
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT s_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE schedule_items (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  schedule_id BIGINT UNSIGNED NOT NULL,
  video_id    CHAR(11)        NOT NULL,
  topic       VARCHAR(60)     NOT NULL DEFAULT '',
  study_day   DATE            NOT NULL,
  mins        SMALLINT UNSIGNED NOT NULL DEFAULT 0,        -- مدت ویدیو به دقیقه
  done        TINYINT(1)      NOT NULL DEFAULT 0,
  done_at     DATETIME        NULL,
  CONSTRAINT si_sched FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE,
  CONSTRAINT si_video FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
  KEY idx_day (schedule_id, study_day)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE payments (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id     BIGINT UNSIGNED NOT NULL,
  gateway     ENUM('zarinpal','stripe') NOT NULL,          -- ir / com
  plan_code   VARCHAR(20)   NOT NULL,                      -- m1 / y1 ...
  amount      INT UNSIGNED  NOT NULL,                      -- IRT (تومان) یا USD cents
  currency    ENUM('IRT','USD') NOT NULL,
  status      ENUM('pending','paid','failed','refunded') NOT NULL DEFAULT 'pending',
  authority   VARCHAR(64)   NULL,                          -- zarinpal authority
  ref_id      VARCHAR(64)   NULL,                          -- zarinpal ref / stripe txn
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  paid_at     DATETIME NULL,
  CONSTRAINT p_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  KEY idx_user (user_id, created_at),
  KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- قیمت هر پلن، جدا برای هر نسخه (.ir تومان/زرین‌پال — .com USD/Stripe)
-- کلاینت premium.html قیمت‌ها را ثابت دارد؛ اینجا منبع حقیقت برای فاکتور است.
-- ============================================================
CREATE TABLE plan_prices (
  id         TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  plan_code  VARCHAR(20)  NOT NULL,                          -- m1 / y1 / m3 ...
  source     ENUM('ir','com') NOT NULL,
  amount     INT UNSIGNED NOT NULL,                          -- IRT=تومان (مثلا 190000) / USD=cent (1499)
  currency   ENUM('IRT','USD') NOT NULL,
  gateway    ENUM('zarinpal','stripe') NOT NULL,
  active     TINYINT(1) NOT NULL DEFAULT 1,
  UNIQUE KEY uq_plan_source (plan_code, source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
INSERT INTO plan_prices (plan_code, source, amount, currency, gateway) VALUES
  ('m1','ir',190000,'IRT','zarinpal'),
  ('y1','ir',990000,'IRT','zarinpal'),
  ('m1','com',1499,'USD','stripe'),
  ('y1','com',9999,'USD','stripe');

-- ============================================================
-- صف پایپ‌لاین محتوا (admin panel)
-- admin در پنل لینک ویدیو را paste می‌کند → job ساخته می‌شود →
-- worker (Mac یا GitHub Actions) آن را مرحله‌به‌مرحله جلو می‌برد.
-- ============================================================
CREATE TABLE IF NOT EXISTS pipeline_jobs (
  id          VARCHAR(40)  PRIMARY KEY,                       -- job_<hex> (app-generated, portable)
  yt_id       CHAR(11)     NULL,                              -- YouTube id (11 chars)
  url         VARCHAR(500) NOT NULL DEFAULT '',               -- همان لینکی که admin paste کرده
  kind        VARCHAR(16)  NOT NULL DEFAULT 'video',         -- video | chat
  channel     VARCHAR(120) NULL,
  stage       ENUM('discover','transcript','translate','quiz','publish') NOT NULL DEFAULT 'discover',
  status      ENUM('queued','running','done','failed','skipped','canceled') NOT NULL DEFAULT 'queued',
  progress    TINYINT UNSIGNED NOT NULL DEFAULT 0,            -- 0..100
  title_fa    VARCHAR(255) NULL,
  title_en    VARCHAR(255) NULL,
  error       TEXT NULL,
  log         TEXT NULL,
  created_by  VARCHAR(190) NULL,                              -- admin email
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_status (status, stage),
  KEY idx_yt (yt_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- تنظیمات مدل هوش مصنوعی (endpoint + key + model) — تک‌ردیف
-- key هرگز به مرورگر برنمی‌گردد؛ فقط has_key:true گزارش می‌شود.
-- ============================================================
CREATE TABLE IF NOT EXISTS llm_settings (
  id         TINYINT UNSIGNED NOT NULL PRIMARY KEY DEFAULT 1,
  endpoint   VARCHAR(255) NOT NULL DEFAULT '',                -- مثلاً https://host/v1
  api_key    VARCHAR(255) NOT NULL DEFAULT '',
  model      VARCHAR(190) NOT NULL DEFAULT '',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- کش مدل‌های در دسترس endpoint (کاربر ممکن است ۵۰۰+ مدل داشته باشد)
CREATE TABLE IF NOT EXISTS llm_models (
  model_id   VARCHAR(190) NOT NULL PRIMARY KEY,
  owned_by   VARCHAR(120) NOT NULL DEFAULT '',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS chat_messages (
  id         VARCHAR(40)  NOT NULL PRIMARY KEY,
  job_id     VARCHAR(40)  NOT NULL,
  role       ENUM('user','agent','system') NOT NULL DEFAULT 'user',
  text       TEXT         NOT NULL,
  file_name  VARCHAR(255) NULL,
  file_path  VARCHAR(500) NULL,                              -- مسیر روی هاست (worker از راه HTTP می‌گیرد)
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_job (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
