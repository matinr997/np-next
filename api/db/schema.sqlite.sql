-- NursePlus API — development schema (SQLite). Production MySQL lives in docs/schema.sql.
CREATE TABLE IF NOT EXISTS users (
  id          TEXT PRIMARY KEY,
  name        TEXT NOT NULL DEFAULT '',
  email       TEXT NOT NULL UNIQUE,
  pass_hash   TEXT NOT NULL,
  plan        TEXT NOT NULL DEFAULT 'free',
  plan_expires TEXT,
  role        TEXT NOT NULL DEFAULT 'user',
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS videos (
  id             TEXT PRIMARY KEY,
  title_fa       TEXT NOT NULL DEFAULT '',
  title_en       TEXT NOT NULL DEFAULT '',
  summary_fa     TEXT,
  summary_en     TEXT,
  topic          TEXT NOT NULL DEFAULT '',
  topic_en       TEXT NOT NULL DEFAULT '',
  dur_seconds    INTEGER NOT NULL DEFAULT 0,
  channel        TEXT NOT NULL DEFAULT '',
  views          INTEGER NOT NULL DEFAULT 0,
  has_transcript INTEGER NOT NULL DEFAULT 0,
  published_at   TEXT,
  chapters       TEXT,
  difficulty     TEXT NOT NULL DEFAULT 'medium',
  status         TEXT NOT NULL DEFAULT 'draft',
  tags           TEXT,
  objectives_fa  TEXT,
  objectives_en  TEXT,
  active         INTEGER NOT NULL DEFAULT 1,
  created_at     TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS llm_settings (
  id         INTEGER PRIMARY KEY,
  endpoint   TEXT NOT NULL DEFAULT '',
  api_key    TEXT NOT NULL DEFAULT '',
  model      TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS llm_models (
  model_id   TEXT PRIMARY KEY,
  owned_by   TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS pipeline_jobs (
  id         TEXT PRIMARY KEY,
  yt_id      TEXT,
  url        TEXT NOT NULL DEFAULT '',
  kind       TEXT NOT NULL DEFAULT 'video',
  channel    TEXT,
  stage      TEXT NOT NULL DEFAULT 'discover',
  status     TEXT NOT NULL DEFAULT 'queued',
  progress   INTEGER NOT NULL DEFAULT 0,
  title_fa   TEXT,
  title_en   TEXT,
  error      TEXT,
  log        TEXT,
  created_by TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON pipeline_jobs (status, stage);
CREATE INDEX IF NOT EXISTS idx_jobs_yt ON pipeline_jobs (yt_id);

CREATE TABLE IF NOT EXISTS chat_messages (
  id         TEXT PRIMARY KEY,
  job_id     TEXT NOT NULL,
  role       TEXT NOT NULL DEFAULT 'user',
  text       TEXT NOT NULL DEFAULT '',
  file_name  TEXT,
  file_path  TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_chat_job ON chat_messages (job_id);
