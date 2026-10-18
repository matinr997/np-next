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
  created_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE videos (
  id           CHAR(11) PRIMARY KEY,                        -- YouTube video id (e.g. oNEBmBtBvtw)
  title_fa     VARCHAR(255) NOT NULL,
  title_en     VARCHAR(255) NOT NULL,
  topic        VARCHAR(60)  NOT NULL,                       -- قلب و عروق / Cardiovascular ...
  topic_en     VARCHAR(60)  NOT NULL,
  dur_seconds  INT UNSIGNED NOT NULL DEFAULT 0,
  channel      VARCHAR(120) NOT NULL DEFAULT '',
  views        INT UNSIGNED NOT NULL DEFAULT 0,
  has_transcript TINYINT(1) NOT NULL DEFAULT 0,
  published_at DATE         NULL,
  active       TINYINT(1)   NOT NULL DEFAULT 1,
  KEY idx_topic (topic)
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
