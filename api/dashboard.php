<?php
// The dashboard.
//
// Every number here comes from a real query. There are no demo values: a
// metric that cannot be counted is reported as unknown rather than as zero.
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/security.php';
require_once __DIR__ . '/stage_lib.php';
require_once __DIR__ . '/provider.php';
require_once __DIR__ . '/catalogue.php';

/**
 * Why did the provider call fail? The panel shows this so the operator knows
 * whether to fix the key, the URL or wait for the provider.
 */
function np_llm_error_kind(int $status, string $error): string {
    $e = strtolower($error);
    if ($status === 401 || $status === 403 || strpos($e, 'unauthorized') !== false
        || strpos($e, 'invalid api key') !== false || strpos($e, 'api key') !== false) {
        return 'auth_error';
    }
    if ($status === 404 || $status === 400) return 'provider_error';
    if ($status >= 500) return 'provider_error';
    if ($status > 0) return 'provider_error';
    return 'network_error';
}

function np_dash_counters(): array {
    $published = 0; $draft = 0; $withQuiz = 0; $withSubs = 0;
    $catalogue = np_catalogue();
    $videos = count($catalogue);
    foreach ($catalogue as $v) {
        $st = strtolower((string)($v['status'] ?? ''));
        if ($st === 'published') $published++; else $draft++;
        if (is_file(__DIR__ . '/../quizzes/' . ($v['id'] ?? '') . '.json')) $withQuiz++;
        if (is_file(__DIR__ . '/../subs/' . ($v['id'] ?? '') . '.json')) $withSubs++;
    }
    return ['videos' => $videos, 'published' => $published, 'draft' => $draft,
            'with_quiz' => $withQuiz, 'with_transcript' => $withSubs];
}

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
if ($method !== 'GET') np_json(['ok' => false, 'error' => 'method_not_allowed'], 405);

/* The dashboard is the administrator's view. The worker may write the
   pipeline state, but it does not read the panel. */
$admin = np_admin();
if ($admin === null) np_json(['ok' => false, 'error' => 'forbidden'], 403);

$counters = np_dash_counters();

$jobs = np_all('SELECT status, COUNT(*) AS n FROM pipeline_jobs GROUP BY status');
$byStatus = [];
foreach ($jobs as $r) $byStatus[(string)$r['status']] = (int)$r['n'];

// the AI endpoint, as it is actually configured
$s = np_llm_get();
$llm = ['endpoint' => $s['endpoint'], 'model' => $s['model'],
        'has_key' => $s['api_key'] !== '', 'model_count' => 0, 'reachable' => null,
        'error' => '', 'error_kind' => 'unknown', 'checked_at' => ''];
try {
    $n = np_val('SELECT COUNT(*) FROM llm_model_meta WHERE endpoint_id = ?',
                [np_endpoint_id($s['endpoint'])]);
    $llm['model_count'] = (int)$n;
} catch (Throwable $e) { /* the table may not exist yet */ }

// The endpoint is only "reachable" if a request actually succeeds; a stored
// URL proves nothing. The kind of failure matters too: a bad key is not the
// same problem as a provider that is down.
if ($s['endpoint'] !== '' && $s['api_key'] !== '') {
    $r = np_fetch_models($s['endpoint'], $s['api_key']);
    $llm['reachable'] = (bool)$r['ok'];
    $llm['checked_at'] = gmdate('Y-m-d H:i:s') . ' UTC';
    if ($r['ok']) {
        $llm['error'] = '';
        $llm['error_kind'] = '';
    } else {
        $llm['error'] = (string)($r['error'] ?? '');
        $llm['error_kind'] = np_llm_error_kind((int)($r['code'] ?? 0), (string)($r['error'] ?? ''));
    }
} else {
    $llm['error_kind'] = $s['endpoint'] === '' ? 'no_endpoint' : 'no_key';
    $llm['checked_at'] = '';
}

$errSum = null;
try {
    $t = np_one('SELECT COUNT(*) AS total, SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) AS open'
        . ' FROM error_log', ['open']);
    $errSum = ['total' => (int)($t['total'] ?? 0), 'open' => (int)($t['open'] ?? 0)];
} catch (Throwable $e) { /* no table yet */ }

$review = 0;
try {
    $r = np_one("SELECT COUNT(*) AS n FROM job_stages WHERE status = 'waiting_for_review'");
    $review = (int)($r['n'] ?? 0);
} catch (Throwable $e) { /* no table yet */ }

// The dashboard shows the three newest records only. The Error Centre shows
// the whole history. The order is the real timestamp, newest first.
$recentErrors = [];
try {
    $recentErrors = np_all('SELECT id, job_id, yt_id, stage, category, severity, message, status,'
        . ' created_at FROM error_log ORDER BY created_at DESC, id DESC LIMIT 3');
} catch (Throwable $e) { /* no table yet */ }

$recentActions = [];
try {
    $recentActions = np_all('SELECT id, actor, action, target, detail, created_at'
        . ' FROM activity_log ORDER BY created_at DESC, id DESC LIMIT 3');
} catch (Throwable $e) { /* no table yet */ }

$stuck = [];
try {
    $stuck = np_all("SELECT id, yt_id, stage, status, updated_at FROM pipeline_jobs"
        . " WHERE status = 'running' AND updated_at < ?"
        . ' ORDER BY updated_at ASC LIMIT 10', [gmdate('Y-m-d H:i:s', time() - 900)]);
} catch (Throwable $e) { /* no table yet */ }

np_json([
    'ok' => true,
    'videos' => $counters,
    'jobs' => [
        'by_status' => $byStatus,
        'queued' => (int)($byStatus['queued'] ?? 0),
        'running' => (int)($byStatus['running'] ?? 0),
        'done' => (int)($byStatus['done'] ?? 0),
        'failed' => (int)($byStatus['failed'] ?? 0),
        'stuck' => $stuck,
    ],
    'review' => ['awaiting' => $review],
    'llm' => $llm,
    'errors' => $errSum ?? ['total' => 0, 'open' => 0],
    'recent_errors' => $recentErrors,
    'recent_actions' => $recentActions,
    'generated_at' => gmdate('Y-m-d H:i:s') . ' UTC',
]);
