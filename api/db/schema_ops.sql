-- NursePlus — operational tables: stage checklist, error centre, activity log,
-- content audit findings and bug-fix patches.
--
-- Portable across MySQL and SQLite (no AUTOINCREMENT, no TEXT DEFAULT) and
-- safe to run on an existing database.

-- ---------------------------------------------------------------- stages
-- One row per pipeline stage per job. This IS the checklist: it survives a
-- page reload, a worker restart and a deployment because it lives in the
-- database and not in the browser.
CREATE TABLE IF NOT EXISTS job_stages (
  id            VARCHAR(64) NOT NULL,
  job_id        VARCHAR(64) NOT NULL,
  yt_id         VARCHAR(64) NOT NULL DEFAULT '',
  stage         VARCHAR(40) NOT NULL DEFAULT '',
  seq           INTEGER NOT NULL DEFAULT 0,
  status        VARCHAR(20) NOT NULL DEFAULT 'pending',
  started_at    VARCHAR(32) NOT NULL DEFAULT '',
  finished_at   VARCHAR(32) NOT NULL DEFAULT '',
  attempts      INTEGER NOT NULL DEFAULT 0,
  input_ref     VARCHAR(400) NOT NULL DEFAULT '',
  output_ref    VARCHAR(400) NOT NULL DEFAULT '',
  error         TEXT NULL,
  error_kind    VARCHAR(40) NOT NULL DEFAULT '',
  model         VARCHAR(190) NOT NULL DEFAULT '',
  tokens        INTEGER NOT NULL DEFAULT 0,
  cost          REAL NOT NULL DEFAULT 0,
  retryable     INTEGER NOT NULL DEFAULT 1,
  skipped_reason VARCHAR(400) NOT NULL DEFAULT '',
  result        TEXT NULL,
  updated_at    VARCHAR(32) NOT NULL DEFAULT '',
  PRIMARY KEY (id)
);

-- ---------------------------------------------------------------- errors
-- The error centre. Every structured error from PHP, the worker, the
-- database or an external API lands here with a safe, redacted message.
CREATE TABLE IF NOT EXISTS error_log (
  id            VARCHAR(64) NOT NULL,
  job_id        VARCHAR(64) NOT NULL DEFAULT '',
  yt_id         VARCHAR(64) NOT NULL DEFAULT '',
  stage         VARCHAR(40) NOT NULL DEFAULT '',
  category      VARCHAR(40) NOT NULL DEFAULT 'other',
  severity      VARCHAR(16) NOT NULL DEFAULT 'error',
  message       TEXT NULL,
  detail        TEXT NULL,
  attempts      INTEGER NOT NULL DEFAULT 1,
  status        VARCHAR(20) NOT NULL DEFAULT 'open',
  fix_state     VARCHAR(24) NOT NULL DEFAULT 'none',
  fix_id        VARCHAR(64) NOT NULL DEFAULT '',
  created_at    VARCHAR(32) NOT NULL DEFAULT '',
  updated_at    VARCHAR(32) NOT NULL DEFAULT '',
  PRIMARY KEY (id)
);

-- ------------------------------------------------------- activity (audit)
-- Every administrative action is recorded here. Secrets never enter it.
CREATE TABLE IF NOT EXISTS activity_log (
  id            VARCHAR(64) NOT NULL,
  actor         VARCHAR(190) NOT NULL DEFAULT '',
  action        VARCHAR(60) NOT NULL DEFAULT '',
  target        VARCHAR(190) NOT NULL DEFAULT '',
  detail        TEXT NULL,
  ip            VARCHAR(64) NOT NULL DEFAULT '',
  created_at    VARCHAR(32) NOT NULL DEFAULT '',
  PRIMARY KEY (id)
);

-- -------------------------------------------------------- content audit
-- Findings of the content audit. Each one keeps its evidence and can be
-- marked resolved after a correction.
CREATE TABLE IF NOT EXISTS content_issues (
  id            VARCHAR(64) NOT NULL,
  video_id      VARCHAR(64) NOT NULL DEFAULT '',
  yt_id         VARCHAR(64) NOT NULL DEFAULT '',
  category      VARCHAR(40) NOT NULL DEFAULT '',
  severity      VARCHAR(16) NOT NULL DEFAULT 'warning',
  evidence      TEXT NULL,
  recommended   TEXT NULL,
  status        VARCHAR(20) NOT NULL DEFAULT 'open',
  run_id        VARCHAR(64) NOT NULL DEFAULT '',
  created_at    VARCHAR(32) NOT NULL DEFAULT '',
  updated_at    VARCHAR(32) NOT NULL DEFAULT '',
  PRIMARY KEY (id)
);

-- ------------------------------------------------------------ bug fixes
-- A proposed patch, its test results and its approval state. The patch is
-- prepared and tested in an isolated working copy; the host never executes
-- model-generated code.
CREATE TABLE IF NOT EXISTS bugfix_patches (
  id            VARCHAR(64) NOT NULL,
  error_id      VARCHAR(64) NOT NULL DEFAULT '',
  job_id        VARCHAR(64) NOT NULL DEFAULT '',
  title         VARCHAR(255) NOT NULL DEFAULT '',
  rationale     TEXT NULL,
  files         TEXT NULL,
  diff          TEXT NULL,
  checks        TEXT NULL,
  status        VARCHAR(24) NOT NULL DEFAULT 'proposed',
  risk          VARCHAR(16) NOT NULL DEFAULT 'low',
  source_commit VARCHAR(64) NOT NULL DEFAULT '',
  applied       INTEGER NOT NULL DEFAULT 0,
  created_at    VARCHAR(32) NOT NULL DEFAULT '',
  updated_at    VARCHAR(32) NOT NULL DEFAULT '',
  PRIMARY KEY (id)
);
