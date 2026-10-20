<?php
// The error centre.
//
// Structured errors from PHP, the worker, the database and the external APIs
// land in one table. The panel can then show what went wrong, how often, and
// what has been done about it.
//
// The stored message is always redacted: no API key, no bearer token and no
// absolute server path ever reaches this table.
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/security.php';

function np_error_add(string $category, string $message, array $ctx = []): string {
    $id = np_id('err');
    try {
        np_q('INSERT INTO error_log (id, job_id, yt_id, stage, category, severity, message,'
            . ' detail, attempts, status, fix_state, created_at, updated_at)'
            . ' VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            [$id,
             (string)($ctx['job_id'] ?? ''),
             (string)($ctx['yt_id'] ?? ''),
             (string)($ctx['stage'] ?? ''),
             $category,
             (string)($ctx['severity'] ?? 'error'),
             np_redact((string)$message),
             isset($ctx['detail']) ? np_redact(is_scalar($ctx['detail']) ? (string)$ctx['detail']
                 : json_encode($ctx['detail'], JSON_UNESCAPED_UNICODE)) : '',
             (int)($ctx['attempts'] ?? 1),
             'open', 'none', np_now(), np_now()]);
    } catch (Throwable $e) {
        // never let the error reporter break the operation that failed
    }
    return $id;
}

function np_error_list(array $f = []): array {
    $w = ['1 = 1']; $a = [];
    if (!empty($f['status']))   { $w[] = 'status = ?';   $a[] = (string)$f['status']; }
    if (!empty($f['category'])) { $w[] = 'category = ?'; $a[] = (string)$f['category']; }
    if (!empty($f['stage']))    { $w[] = 'stage = ?';    $a[] = (string)$f['stage']; }
    if (!empty($f['job_id']))   { $w[] = 'job_id = ?';   $a[] = (string)$f['job_id']; }
    if (!empty($f['from']))     { $w[] = 'created_at >= ?'; $a[] = (string)$f['from']; }
    if (!empty($f['to']))       { $w[] = 'created_at <= ?'; $a[] = (string)$f['to']; }
    $limit = max(1, min(300, (int)($f['limit'] ?? 100)));
    $sql = 'SELECT * FROM error_log WHERE ' . implode(' AND ', $w)
         . ' ORDER BY created_at DESC LIMIT ' . $limit;
    return np_all($sql, $a);
}

function np_error_summary(): array {
    $byCat = np_all('SELECT category, COUNT(*) AS n FROM error_log WHERE status = ?'
        . ' GROUP BY category ORDER BY n DESC', ['open']);
    $bySev = np_all('SELECT severity, COUNT(*) AS n FROM error_log GROUP BY severity');
    $tot = np_one('SELECT COUNT(*) AS total, SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) AS open,'
        . ' SUM(CASE WHEN fix_state = ? THEN 1 ELSE 0 END) AS fixing FROM error_log',
        ['open', 'fixing']);
    return ['by_category' => $byCat, 'by_severity' => $bySev,
            'total' => (int)($tot['total'] ?? 0), 'open' => (int)($tot['open'] ?? 0),
            'fixing' => (int)($tot['fixing'] ?? 0)];
}

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

if ($method === 'GET') {
    $admin = np_admin();
    $isWorker = np_worker_ok();
    if ($admin === null && !$isWorker) np_json(['ok' => false, 'error' => 'forbidden'], 403);
    $act = (string)($_GET['action'] ?? 'list');

    if ($act === 'list') {
        $rows = np_error_list([
            'status' => (string)($_GET['status'] ?? ''),
            'category' => (string)($_GET['category'] ?? ''),
            'stage' => (string)($_GET['stage'] ?? ''),
            'job_id' => (string)($_GET['job_id'] ?? ''),
            'from' => (string)($_GET['from'] ?? ''),
            'to' => (string)($_GET['to'] ?? ''),
            'limit' => (int)($_GET['limit'] ?? 100),
        ]);
        np_json(['ok' => true, 'errors' => $rows, 'summary' => np_error_summary()]);
    }

    if ($act === 'detail') {
        $id = (string)($_GET['id'] ?? '');
        $row = np_one('SELECT * FROM error_log WHERE id = ? LIMIT 1', [$id]);
        if (!$row) np_json(['ok' => false, 'error' => 'not_found'], 404);
        $patches = np_all('SELECT * FROM bugfix_patches WHERE error_id = ? ORDER BY created_at DESC',
                          [$id]);
        $job = null;
        if ((string)$row['job_id'] !== '') {
            $job = np_one('SELECT * FROM pipeline_jobs WHERE id = ? LIMIT 1', [(string)$row['job_id']]);
        }
        np_json(['ok' => true, 'error' => $row, 'patches' => $patches, 'job' => $job]);
    }

    np_json(['ok' => false, 'error' => 'unknown_action'], 400);
}

if ($method === 'POST') {
    $b = np_body();
    $act = np_str($b, 'action');

    // the worker reports an error
    if ($act === 'report') {
        if (!np_worker_ok()) np_json(['ok' => false, 'error' => 'forbidden'], 403);
        $id = np_error_add(np_str($b, 'category', 'other'), np_str($b, 'message'), [
            'job_id' => np_str($b, 'job_id'),
            'yt_id' => np_str($b, 'yt_id'),
            'stage' => np_str($b, 'stage'),
            'severity' => np_str($b, 'severity', 'error'),
            'detail' => $b['detail'] ?? '',
            'attempts' => (int)($b['attempts'] ?? 1),
        ]);
        np_json(['ok' => true, 'id' => $id]);
    }

    if ($act === 'resolve' || $act === 'ignore') {
        np_require_admin();
        np_require_csrf();
        $id = np_str($b, 'id');
        $st = $act === 'resolve' ? 'resolved' : 'ignored';
        np_q('UPDATE error_log SET status = ?, updated_at = ? WHERE id = ?', [$st, np_now(), $id]);
        np_activity('error_' . $act, $id, 'error ' . $st);
        np_json(['ok' => true]);
    }

    np_json(['ok' => false, 'error' => 'unknown_action'], 400);
}
