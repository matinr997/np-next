<?php
// The stage checklist API. The functions live in stage_lib.php so another
// endpoint can use them without running this file's routing.
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/security.php';
require_once __DIR__ . '/stage_lib.php';

/* ------------------------------------------------------------------ API */
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

if ($method === 'GET') {
    $jobId = (string)($_GET['job_id'] ?? '');
    if ($jobId === '') np_json(['ok' => false, 'error' => 'missing_job_id'], 400);
    $admin = np_admin();
    if ($admin === null && !np_worker_ok()) np_json(['ok' => false, 'error' => 'forbidden'], 403);
    $lang = ((string)($_GET['lang'] ?? 'fa')) === 'en' ? 'en' : 'fa';
    np_json(['ok' => true, 'job_id' => $jobId, 'stages' => np_stages_list($jobId, $lang),
             'progress' => np_stages_progress($jobId),
             'retryable' => np_stages_retryable($jobId)]);
}

if ($method === 'POST') {
    $b = np_body();
    $act = np_str($b, 'action');

    // the worker writes the state
    if ($act === 'set' || $act === 'skip' || $act === 'seed') {
        if (!np_worker_ok()) np_json(['ok' => false, 'error' => 'forbidden'], 403);
        $jobId = np_str($b, 'job_id');
        if ($jobId === '') np_json(['ok' => false, 'error' => 'missing_job_id'], 400);
        if ($act === 'seed') {
            $n = np_stages_seed($jobId, np_str($b, 'yt_id'));
            np_json(['ok' => true, 'seeded' => $n, 'stages' => np_stages_list($jobId)]);
        }
        $stage = np_str($b, 'stage');
        if ($act === 'skip') {
            np_stage_skip($jobId, $stage, np_str($b, 'reason', 'not applicable'));
        } else {
            np_stage_set($jobId, $stage, np_str($b, 'status', 'running'), [
                'yt_id' => np_str($b, 'yt_id'),
                'input_ref' => np_str($b, 'input_ref'),
                'output_ref' => np_str($b, 'output_ref'),
                'error' => np_str($b, 'error'),
                'error_kind' => np_str($b, 'error_kind'),
                'model' => np_str($b, 'model'),
                'tokens' => (int)($b['tokens'] ?? 0),
                'cost' => (float)($b['cost'] ?? 0),
                'retryable' => array_key_exists('retryable', $b) ? (bool)$b['retryable'] : null,
                'skipped_reason' => np_str($b, 'skipped_reason'),
                'result' => $b['result'] ?? null,
            ]);
        }
        // keep the job's own progress in step with the checklist
        $p = np_stages_progress($jobId);
        np_q('UPDATE pipeline_jobs SET progress = ?, updated_at = ? WHERE id = ?',
             [$p['pct'], np_now(), $jobId]);
        np_json(['ok' => true, 'stages' => np_stages_list($jobId), 'progress' => $p]);
    }

    // the administrator retries one stage
    if ($act === 'retry') {
        np_require_admin();
        np_require_csrf();
        $jobId = np_str($b, 'job_id');
        $stage = np_str($b, 'stage');
        $row = np_one('SELECT * FROM job_stages WHERE job_id = ? AND stage = ? LIMIT 1',
                      [$jobId, $stage]);
        if (!$row) np_json(['ok' => false, 'error' => 'stage_not_found'], 404);
        if ((string)$row['status'] !== 'failed') {
            np_json(['ok' => false, 'error' => 'stage_not_failed',
                     'message' => 'Only a failed stage can be retried.'], 400);
        }
        if ((int)$row['retryable'] !== 1) {
            np_json(['ok' => false, 'error' => 'stage_not_retryable',
                     'message' => 'This stage is not eligible for a retry.'], 400);
        }
        // reset only this stage — the completed ones stay untouched
        np_q('UPDATE job_stages SET status = ?, error = NULL, error_kind = ?,'
            . ' finished_at = ?, skipped_reason = ?, updated_at = ? WHERE id = ?',
             ['pending', '', '', '', '', np_now(), (string)$row['id']]);
        np_q("UPDATE pipeline_jobs SET status = 'queued', stage = ?, error = NULL, updated_at = ?"
            . " WHERE id = ?", [$stage, np_now(), $jobId]);
        np_activity('stage_retry', $jobId . ':' . $stage, 'retried stage ' . $stage);
        np_json(['ok' => true, 'stages' => np_stages_list($jobId)]);
    }

    // the administrator cancels a job
    if ($act === 'cancel') {
        np_require_admin();
        np_require_csrf();
        $jobId = np_str($b, 'job_id');
        np_q("UPDATE pipeline_jobs SET status = 'cancelled', updated_at = ? WHERE id = ?",
             [np_now(), $jobId]);
        np_q("UPDATE job_stages SET status = 'cancelled', finished_at = ?, updated_at = ?"
            . " WHERE job_id = ? AND status IN ('pending','running')",
             [np_now(), np_now(), $jobId]);
        np_activity('job_cancel', $jobId, 'job cancelled');
        np_json(['ok' => true, 'stages' => np_stages_list($jobId)]);
    }

    np_json(['ok' => false, 'error' => 'unknown_action'], 400);
}
