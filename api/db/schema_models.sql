-- NursePlus — AI model metadata, manual overrides and usage tracking.
--
-- Portable across MySQL and SQLite: no AUTOINCREMENT, no TEXT DEFAULT, and
-- every statement is CREATE TABLE IF NOT EXISTS so it can be run on an
-- existing database.
--
-- llm_model_meta is separate from the legacy llm_models table on purpose:
-- that one has a single-column primary key, and model ids are NOT unique
-- across providers, so the identity here is (endpoint_id, model_id).

CREATE TABLE IF NOT EXISTS llm_model_meta (
  endpoint_id   VARCHAR(180) NOT NULL DEFAULT 'default',
  model_id      VARCHAR(190) NOT NULL,
  provider      VARCHAR(120) NOT NULL DEFAULT '',
  display_name  VARCHAR(190) NOT NULL DEFAULT '',
  cap_vision    VARCHAR(10) NOT NULL DEFAULT 'unknown',
  cap_reasoning VARCHAR(10) NOT NULL DEFAULT 'unknown',
  cap_tools     VARCHAR(10) NOT NULL DEFAULT 'unknown',
  cap_image_gen VARCHAR(10) NOT NULL DEFAULT 'unknown',
  cap_audio     VARCHAR(10) NOT NULL DEFAULT 'unknown',
  ctx_max       INTEGER NOT NULL DEFAULT 0,
  out_max       INTEGER NOT NULL DEFAULT 0,
  verify_status VARCHAR(16) NOT NULL DEFAULT 'unknown',
  meta_source   VARCHAR(32) NOT NULL DEFAULT 'none',
  meta_updated  VARCHAR(32) NOT NULL DEFAULT '',
  PRIMARY KEY (endpoint_id, model_id)
);

-- Manual overrides live in their own table so a metadata refresh can never
-- wipe what an administrator set by hand.
CREATE TABLE IF NOT EXISTS llm_model_overrides (
  endpoint_id   VARCHAR(180) NOT NULL DEFAULT 'default',
  model_id      VARCHAR(190) NOT NULL,
  cap_vision    VARCHAR(10) NOT NULL DEFAULT '',
  cap_reasoning VARCHAR(10) NOT NULL DEFAULT '',
  cap_tools     VARCHAR(10) NOT NULL DEFAULT '',
  cap_image_gen VARCHAR(10) NOT NULL DEFAULT '',
  cap_audio     VARCHAR(10) NOT NULL DEFAULT '',
  ctx_max       INTEGER NOT NULL DEFAULT -1,
  out_max       INTEGER NOT NULL DEFAULT -1,
  display_name  VARCHAR(190) NOT NULL DEFAULT '',
  set_by        VARCHAR(190) NOT NULL DEFAULT '',
  updated_at    VARCHAR(32) NOT NULL DEFAULT '',
  PRIMARY KEY (endpoint_id, model_id)
);

-- One row per model call. `task` separates the panel's own calls from the
-- pipeline stages so usage can be filtered per model and per task.
CREATE TABLE IF NOT EXISTS llm_usage (
  id                VARCHAR(64) NOT NULL,
  endpoint_id       VARCHAR(180) NOT NULL DEFAULT 'default',
  model_id          VARCHAR(190) NOT NULL DEFAULT '',
  task              VARCHAR(40) NOT NULL DEFAULT 'other',
  site              VARCHAR(8) NOT NULL DEFAULT 'ir',
  prompt_tokens     INTEGER NOT NULL DEFAULT 0,
  completion_tokens INTEGER NOT NULL DEFAULT 0,
  cached_tokens     INTEGER NOT NULL DEFAULT 0,
  reasoning_tokens  INTEGER NOT NULL DEFAULT 0,
  reasoning_known   INTEGER NOT NULL DEFAULT 0,
  est_prompt_tokens INTEGER NOT NULL DEFAULT 0,
  ctx_max           INTEGER NOT NULL DEFAULT 0,
  ctx_pct           REAL NOT NULL DEFAULT 0,
  cost              REAL NOT NULL DEFAULT 0,
  ok                INTEGER NOT NULL DEFAULT 1,
  latency_ms        INTEGER NOT NULL DEFAULT 0,
  error_kind        VARCHAR(32) NOT NULL DEFAULT '',
  created_at        VARCHAR(32) NOT NULL DEFAULT '',
  PRIMARY KEY (id)
);

-- Panel-level settings that are not secrets: thresholds, strategy, pricing.
CREATE TABLE IF NOT EXISTS llm_prefs (
  k             VARCHAR(64) NOT NULL,
  v             VARCHAR(4000) NOT NULL DEFAULT '',
  updated_at    VARCHAR(32) NOT NULL DEFAULT '',
  PRIMARY KEY (k)
);

-- The running summary of the panel conversation. /compress rewrites it.
CREATE TABLE IF NOT EXISTS chat_summary (
  scope      VARCHAR(32) NOT NULL DEFAULT 'panel',
  text       VARCHAR(8000) NOT NULL DEFAULT '',
  messages   INTEGER NOT NULL DEFAULT 0,
  task       VARCHAR(32) NOT NULL DEFAULT '',
  created_at VARCHAR(32) NOT NULL DEFAULT '',
  PRIMARY KEY (scope)
);
