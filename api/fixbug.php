<?php
// The Fix Bug workflow.
//
// The rules this file enforces:
//   - the model NEVER runs a shell command and NEVER writes a file itself
//   - a patch is a unified diff against a named file inside an allow-list
//   - high-risk areas are never patched automatically: authentication,
//     authorisation, database migrations, payment processing, the security
//     configuration and the deployment secrets
//   - the patch is prepared and tested in an isolated working copy, which
//     lives where the worker runs — the shared host never executes
//     model-generated code
//   - nothing is applied to the live tree without the administrator's
//     approval, and the patch, its tests and its source version are recorded
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/security.php';

/** Files a patch may touch. Everything else is refused. */
function np_fix_allowed_files(): array {
    return [
        'scripts/', 'api/', 'lib/', 'assets/', 'com/', 'data/', 'quizzes/', 'subs/',
    ];
}

/** Paths a patch may NEVER touch, whatever the allow-list says. */
function np_fix_forbidden_files(): array {
    return [
        'api/config.php', 'api/auth.php', 'api/security.php', 'api/db.php',
        'api/setup.php', 'api/.htaccess', '.git/', '.github/workflows/',
        'api/schema.mysql.sql', 'docs/schema.sql', 'deploy/', '.env', 'api/config.example.php',
    ];
}

/** Risk level of a file. */
function np_fix_risk(string $file): string {
    $f = strtolower($file);
    foreach (np_fix_forbidden_files() as $bad) {
        if (strpos($f, strtolower($bad)) === 0) return 'forbidden';
    }
    if (strpos($f, 'api/') === 0) return 'high';      // the API is the web surface
    if (strpos($f, 'lib/') === 0) return 'high';      // the player runs in the browser
    foreach (np_fix_allowed_files() as $ok) {
        if (strpos($f, $ok) === 0) return 'low';
    }
    return 'forbidden';
}

/** Pull the file names out of a unified diff. */
function np_fix_diff_files(string $diff): array {
    $files = [];
    foreach (preg_split('/\r?\n/', $diff) as $line) {
        if (preg_match('#^diff --git a/(\S+) b/(\S+)#', $line, $m)) { $files[] = $m[2]; continue; }
        if (preg_match('#^--- a/(\S+)#', $line, $m)) { $files[] = $m[1]; continue; }
        if (preg_match('#^\+\+\+ b/(\S+)#', $line, $m)) { $files[] = $m[1]; }
    }
    return array_values(array_unique($files));
}

/** The shape a patch must have. */
function np_fix_validate_patch(string $diff): array {
    $errs = [];
    if (trim($diff) === '') { $errs[] = 'the patch is empty'; return $errs; }
    if (strlen($diff) > 200000) $errs[] = 'the patch is too large';
    // only a unified diff is accepted
    if (!preg_match('/^diff --git /m', $diff) && !preg_match('/^--- a\//m', $diff)) {
        $errs[] = 'the patch is not a unified diff';
    }
    // a diff must not try to create a binary or run something
    if (preg_match('/^GIT binary patch/m', $diff)) $errs[] = 'binary patches are not allowed';
    if (preg_match('/^\+.*\bexec\s*\(/mi', $diff)) $errs[] = 'the patch adds a shell execution';
    if (preg_match('/^\+.*\b(shell_exec|system|passthru|popen|proc_open)\s*\(/mi', $diff)) {
        $errs[] = 'the patch adds a process execution';
    }
    if (preg_match('/^\+.*\beval\s*\(/mi', $diff)) $errs[] = 'the patch adds eval()';
    if (preg_match('/^\+.*rm\s+-rf/mi', $diff)) $errs[] = 'the patch deletes files recursively';
    // every file must be inside the allow-list and outside the forbidden list
    $files = np_fix_diff_files($diff);
    if (!$files) $errs[] = 'the patch does not name a file';
    $risk = 'low';
    foreach ($files as $f) {
        $r = np_fix_risk($f);
        if ($r === 'forbidden') { $errs[] = 'the patch touches a protected file: ' . $f; continue; }
        if ($r === 'high') $risk = 'high';
    }
    return $errs;
}

/** Record a proposed patch. */
function np_fix_store(string $errorId, string $jobId, string $title, string $rationale,
                     string $diff, array $checks, string $risk, string $sourceCommit): string {
    $id = np_id('fix');
    np_upsert('bugfix_patches', [
        'id' => $id, 'error_id' => $errorId, 'job_id' => $jobId,
        'title' => mb_substr($title, 0, 250), 'rationale' => $rationale,
        'files' => json_encode(np_fix_diff_files($diff), JSON_UNESCAPED_UNICODE),
        'diff' => $diff,
        'checks' => json_encode($checks, JSON_UNESCAPED_UNICODE),
        'status' => 'proposed', 'risk' => $risk, 'source_commit' => $sourceCommit,
        'applied' => 0, 'created_at' => np_now(), 'updated_at' => np_now(),
    ], ['id']);
    if ($errorId !== '') {
        np_q("UPDATE error_log SET fix_state = 'proposed', fix_id = ?, updated_at = ? WHERE id = ?",
             [$id, np_now(), $errorId]);
    }
    return $id;
}

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

if ($method === 'GET') {
    if (np_admin() === null && !np_worker_ok()) np_json(['ok' => false, 'error' => 'forbidden'], 403);
    $act = (string)($_GET['action'] ?? 'list');
    if ($act === 'list') {
        $rows = np_all('SELECT * FROM bugfix_patches ORDER BY created_at DESC LIMIT 100');
        np_json(['ok' => true, 'patches' => $rows]);
    }
    if ($act === 'detail') {
        $id = (string)($_GET['id'] ?? '');
        $row = np_one('SELECT * FROM bugfix_patches WHERE id = ? LIMIT 1', [$id]);
        if (!$row) np_json(['ok' => false, 'error' => 'not_found'], 404);
        np_json(['ok' => true, 'patch' => $row,
                 'validation' => np_fix_validate_patch((string)$row['diff'])]);
    }
    np_json(['ok' => false, 'error' => 'unknown_action'], 400);
}

if ($method === 'POST') {
    $b = np_body();
    $act = np_str($b, 'action');

    /* ---- the worker prepares a patch: analyse, validate, test ---- */
    if ($act === 'propose') {
        if (!np_worker_ok()) np_json(['ok' => false, 'error' => 'forbidden'], 403);
        $diff = (string)($b['diff'] ?? '');
        $errs = np_fix_validate_patch($diff);
        if ($errs) {
            np_json(['ok' => false, 'error' => 'invalid_patch', 'problems' => $errs,
                     'message' => 'The proposed patch was refused: ' . implode('; ', $errs)], 400);
        }
        $files = np_fix_diff_files($diff);
        $risk = 'low';
        foreach ($files as $f) if (np_fix_risk($f) === 'high') $risk = 'high';
        $id = np_fix_store(np_str($b, 'error_id'), np_str($b, 'job_id'),
                            np_str($b, 'title', 'Proposed fix'), np_str($b, 'rationale'),
                            $diff, is_array($b['checks'] ?? null) ? $b['checks'] : [],
                            $risk, np_str($b, 'source_commit'));
        np_json(['ok' => true, 'id' => $id, 'files' => $files, 'risk' => $risk]);
    }

    /* ---- the worker reports the test results ---- */
    if ($act === 'test_result') {
        if (!np_worker_ok()) np_json(['ok' => false, 'error' => 'forbidden'], 403);
        $id = np_str($b, 'id');
        $checks = is_array($b['checks'] ?? null) ? $b['checks'] : [];
        $passed = (bool)($b['passed'] ?? false);
        $row = np_one('SELECT * FROM bugfix_patches WHERE id = ? LIMIT 1', [$id]);
        if (!$row) np_json(['ok' => false, 'error' => 'not_found'], 404);
        np_q('UPDATE bugfix_patches SET checks = ?, status = ?, updated_at = ? WHERE id = ?',
             [json_encode($checks, JSON_UNESCAPED_UNICODE),
              $passed ? 'tested' : 'test_failed', np_now(), $id]);
        if ($row['error_id'] !== '') {
            np_q('UPDATE error_log SET fix_state = ?, updated_at = ? WHERE id = ?',
                 [$passed ? 'tested' : 'test_failed', np_now(), (string)$row['error_id']]);
        }
        np_json(['ok' => true, 'passed' => $passed]);
    }

    /* ---- the administrator approves a tested patch ---- */
    if ($act === 'approve') {
        np_require_admin();
        np_require_csrf();
        $id = np_str($b, 'id');
        $row = np_one('SELECT * FROM bugfix_patches WHERE id = ? LIMIT 1', [$id]);
        if (!$row) np_json(['ok' => false, 'error' => 'not_found'], 404);
        if ((string)$row['status'] !== 'tested') {
            np_json(['ok' => false, 'error' => 'not_tested',
                     'message' => 'Only a patch whose checks passed can be approved.'], 400);
        }
        if ((string)$row['risk'] === 'high') {
            np_json(['ok' => false, 'error' => 'needs_manual_review',
                     'message' => 'This patch touches a sensitive area and must be applied by hand.'], 400);
        }
        np_q("UPDATE bugfix_patches SET status = 'approved', updated_at = ? WHERE id = ?",
             [np_now(), $id]);
        np_activity('bugfix_approve', $id, 'approved ' . (string)$row['title']);
        np_json(['ok' => true, 'id' => $id]);
    }

    if ($act === 'reject') {
        np_require_admin();
        np_require_csrf();
        $id = np_str($b, 'id');
        np_q("UPDATE bugfix_patches SET status = 'rejected', updated_at = ? WHERE id = ?",
             [np_now(), $id]);
        np_activity('bugfix_reject', $id, 'rejected');
        np_json(['ok' => true]);
    }

    /* ---- the worker reports that the patch was applied ---- */
    if ($act === 'applied') {
        if (!np_worker_ok()) np_json(['ok' => false, 'error' => 'forbidden'], 403);
        $id = np_str($b, 'id');
        np_q("UPDATE bugfix_patches SET status = 'applied', applied = 1, updated_at = ? WHERE id = ?",
             [np_now(), $id]);
        $row = np_one('SELECT * FROM bugfix_patches WHERE id = ? LIMIT 1', [$id]);
        if ($row && (string)$row['error_id'] !== '') {
            np_q("UPDATE error_log SET fix_state = 'applied', status = 'resolved', updated_at = ?"
                . ' WHERE id = ?', [np_now(), (string)$row['error_id']]);
        }
        np_json(['ok' => true]);
    }

    np_json(['ok' => false, 'error' => 'unknown_action'], 400);
}
