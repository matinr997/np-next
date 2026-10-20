<?php
// GET  /api/jobs.php -> {ok, jobs:[...]}
// POST /api/jobs.php {action:'create', urls:[...]}  -> {ok, created:[], skipped:[]}
// POST /api/jobs.php {action:'claim', worker}      -> {ok, job|null}
// POST /api/jobs.php {action:'update', id, stage, progress, status, error, ...}
// POST /api/jobs.php {action:'cancel', id}
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/security.php';
require_once __DIR__ . '/catalogue.php';

const NP_STAGES  = ['discover', 'transcript', 'translate', 'quiz', 'publish'];
const NP_STATUSES = ['queued', 'running', 'done', 'failed', 'skipped', 'canceled'];

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    np_require_admin();
    $rows = np_all('SELECT id, yt_id, url, kind, channel, stage, status, progress, title_fa, title_en,
                           error, log, created_by, created_at, updated_at
                    FROM pipeline_jobs ORDER BY created_at DESC LIMIT 300');
    np_json(['ok' => true, 'jobs' => $rows]);
}

$admin = np_require_admin();
$b = np_body();
$act = np_str($b, 'action');

if ($act === 'create') {
    $raw = $b['urls'] ?? [];
    if (is_string($raw)) $raw = preg_split('/[\r\n]+/', $raw);
    if (!is_array($raw)) $raw = [];
    $created = []; $skipped = []; $seen = [];

    foreach ($raw as $u) {
        $u = trim((string)$u);
        if ($u === '') continue;
        $yt = np_yt_id($u);
        if ($yt === null) {
            $skipped[] = ['url' => $u, 'yt_id' => null, 'reason' => 'invalid',
                          'message' => 'لینک یوتیوب معتبر نیست'];
            continue;
        }
        if (isset($seen[$yt])) {
            $skipped[] = ['url' => $u, 'yt_id' => $yt, 'reason' => 'duplicate',
                          'message' => 'این لینک تکراری است'];
            continue;
        }
        $seen[$yt] = true;

        $dup = np_duplicate($yt);
        if ($dup['duplicate']) {
            $skipped[] = ['url' => $u, 'yt_id' => $yt, 'reason' => $dup['reason'],
                          'message' => np_msg_duplicate((string)$dup['reason'])];
            continue;
        }
        $id = np_id('job');
        $now = np_now();
        np_q('INSERT INTO pipeline_jobs (id, yt_id, url, stage, status, progress, created_by, created_at, updated_at)
              VALUES (?,?,?,?,?,?,?,?,?)',
             [$id, $yt, $u, 'discover', 'queued', 0, $admin['email'], $now, $now]);
        $created[] = ['id' => $id, 'url' => $u, 'yt_id' => $yt];
    }
    np_json(['ok' => true, 'created' => $created, 'skipped' => $skipped]);
}

if ($act === 'claim') {
    $worker = np_str($b, 'worker', 'worker');

    // Reap abandoned jobs. If a worker dies mid-job (killed, laptop asleep,
    // host reboot) the row stays 'running' for ever and, because the claim is
    // FIFO, it blocks every job behind it. Anything untouched for 15 minutes
    // is considered abandoned and goes back into the queue.
    $cutoff = gmdate('Y-m-d H:i:s', time() - 900);
    np_q("UPDATE pipeline_jobs SET status = 'queued', stage = 'discover', progress = 0,
          log = ?, updated_at = ? WHERE status = 'running' AND updated_at < ?",
         ['requeued: the previous worker stopped responding', np_now(), $cutoff]);

    $rows = np_all("SELECT id, yt_id, url, kind, stage, status, progress, title_fa, title_en
                    FROM pipeline_jobs WHERE status = 'queued' ORDER BY created_at ASC LIMIT 10");
    foreach ($rows as $r) {
        $now = np_now();
        $st = np_q("UPDATE pipeline_jobs SET status = 'running', stage = 'discover', progress = 0,
                    log = ?, updated_at = ? WHERE id = ? AND status = 'queued'",
                   ['claimed by ' . $worker, $now, $r['id']]);
        if ($st->rowCount() > 0) {
            $r['status'] = 'running'; $r['stage'] = 'discover';
            np_json(['ok' => true, 'job' => $r]);
        }
    }
    np_json(['ok' => true, 'job' => null]);
}

if ($act === 'update') {
    $id = np_str($b, 'id');
    if ($id === '') np_json(['ok' => false, 'error' => 'missing_id'], 400);
    $sets = []; $args = [];
    if (array_key_exists('stage', $b)) {
        $s = np_str($b, 'stage');
        if (!in_array($s, NP_STAGES, true)) $s = 'discover';
        $sets[] = 'stage = ?'; $args[] = $s;
    }
    if (array_key_exists('status', $b)) {
        $s = np_str($b, 'status');
        if (!in_array($s, NP_STATUSES, true)) $s = 'queued';
        $sets[] = 'status = ?'; $args[] = $s;
    }
    if (array_key_exists('progress', $b)) { $sets[] = 'progress = ?'; $args[] = max(0, min(100, (int)$b['progress'])); }
    if (array_key_exists('error', $b))  { $sets[] = 'error = ?';  $args[] = np_str($b, 'error'); }
    if (array_key_exists('log', $b))    { $sets[] = 'log = ?';    $args[] = np_str($b, 'log'); }
    if (array_key_exists('yt_id', $b))  { $sets[] = 'yt_id = ?';  $args[] = np_str($b, 'yt_id'); }
    if (array_key_exists('title_fa', $b)) { $sets[] = 'title_fa = ?'; $args[] = np_str($b, 'title_fa'); }
    if (array_key_exists('title_en', $b)) { $sets[] = 'title_en = ?'; $args[] = np_str($b, 'title_en'); }
    if (!$sets) np_json(['ok' => false, 'error' => 'nothing_to_update'], 400);
    $sets[] = 'updated_at = ?'; $args[] = np_now();
    $args[] = $id;
    np_q('UPDATE pipeline_jobs SET ' . implode(', ', $sets) . ' WHERE id = ?', $args);
    np_json(['ok' => true]);
}

if ($act === 'cancel') {
    $id = np_str($b, 'id');
    if ($id === '') np_json(['ok' => false, 'error' => 'missing_id'], 400);
    np_q("UPDATE pipeline_jobs SET status = 'canceled', updated_at = ? WHERE id = ? AND status IN ('queued','running')",
         [np_now(), $id]);
    np_json(['ok' => true]);
}

np_json(['ok' => false, 'error' => 'unknown_action'], 400);
