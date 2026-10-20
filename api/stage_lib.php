<?php
// The pipeline checklist.
//
// One row per stage per job. The checklist is the single source of truth for
// "where is this video" — it is written by the worker as it goes and read by
// the panel. Because it lives in the database it survives a reload, a worker
// crash and a deployment.
//
// A stage can be retried on its own: retrying it never touches the stages
// that already completed.
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/security.php';

/** The stages of the pipeline, in order. `required` marks the ones that must
 *  pass before a video may be published. */
function np_stage_defs(): array {
    return [
        ['key' => 'url_validate',    'fa' => 'اعتبارسنجی لینک',            'en' => 'URL validation',                       'required' => 1],
        ['key' => 'identify',         'fa' => 'شناسایی و دریافت اطلاعات',   'en' => 'Identification and metadata',           'required' => 1],
        ['key' => 'transcript',       'fa' => 'دریافت زیرنویس',             'en' => 'Subtitle or transcript acquisition',    'required' => 1],
        ['key' => 'stt',              'fa' => 'تبدیل گفتار به متن',         'en' => 'Speech to text',                       'required' => 0],
        ['key' => 'cleanup',          'fa' => 'پاک‌سازی متن',              'en' => 'Transcript cleanup',                   'required' => 1],
        ['key' => 'extract_en',       'fa' => 'استخراج محتوای انگلیسی',      'en' => 'English content extraction',          'required' => 1],
        ['key' => 'translate_fa',     'fa' => 'ترجمهٔ فارسی',               'en' => 'Persian translation',                  'required' => 1],
        ['key' => 'title_fa',         'fa' => 'عنوان فارسی',                'en' => 'Persian title',                        'required' => 1],
        ['key' => 'title_en',         'fa' => 'عنوان انگلیسی',              'en' => 'English title',                        'required' => 1],
        ['key' => 'seo',              'fa' => 'توضیحات و metadata سئو',     'en' => 'SEO description and metadata',         'required' => 1],
        ['key' => 'qc',               'fa' => 'کنترل کیفیت محتوا',          'en' => 'Educational quality check',            'required' => 1],
        ['key' => 'quiz',             'fa' => 'ساخت آزمون',                'en' => 'Quiz generation',                      'required' => 1],
        ['key' => 'quiz_validate',    'fa' => 'اعتبارسنجی ساختار آزمون',   'en' => 'Quiz structural validation',           'required' => 1],
        ['key' => 'terminology',      'fa' => 'اعتبارسنجی اصطلاحات پزشکی',  'en' => 'Medical terminology validation',       'required' => 0],
        ['key' => 'persist',          'fa' => 'ذخیره در دیتابیس',          'en' => 'Database persistence',                 'required' => 1],
        ['key' => 'consistency',      'fa' => 'کنترل سازگاری نهایی',        'en' => 'Final consistency check',              'required' => 1],
        ['key' => 'publish',          'fa' => 'انتشار',                    'en' => 'Publication or draft approval',        'required' => 1],
    ];
}

function np_stage_label(string $key, string $lang = 'fa'): string {
    foreach (np_stage_defs() as $d) {
        if ($d['key'] === $key) return $lang === 'en' ? (string)$d['en'] : (string)$d['fa'];
    }
    return $key;
}

/** Create the checklist for a job. Existing rows are left alone. */
function np_stages_seed(string $jobId, string $ytId = ''): int {
    $n = 0;
    $seq = 0;
    foreach (np_stage_defs() as $d) {
        $seq++;
        $id = np_id('st');
        $exists = np_one('SELECT id FROM job_stages WHERE job_id = ? AND stage = ? LIMIT 1',
                         [$jobId, $d['key']]);
        if ($exists) { $n++; continue; }
        np_q('INSERT INTO job_stages (id, job_id, yt_id, stage, seq, status, attempts,'
            . ' retryable, updated_at) VALUES (?,?,?,?,?,?,?,?,?)',
            [$id, $jobId, $ytId, $d['key'], $seq, 'pending', 0, 1, np_now()]);
        $n++;
    }
    return $n;
}

/**
 * Record a stage transition.
 * status: pending | running | completed | failed | skipped | waiting_for_review | cancelled
 */
function np_stage_set(string $jobId, string $stage, string $status, array $opts = []): void {
    $row = np_one('SELECT * FROM job_stages WHERE job_id = ? AND stage = ? LIMIT 1',
                  [$jobId, $stage]);
    if (!$row) {
        np_stages_seed($jobId, (string)($opts['yt_id'] ?? ''));
        $row = np_one('SELECT * FROM job_stages WHERE job_id = ? AND stage = ? LIMIT 1',
                      [$jobId, $stage]);
        if (!$row) return;
    }
    $now = np_now();
    $attempts = (int)$row['attempts'];
    $started  = (string)$row['started_at'];
    $finished = (string)$row['finished_at'];

    if ($status === 'running') {
        $attempts++;
        if ($started === '') $started = $now;
        $finished = '';
    } elseif (in_array($status, ['completed', 'failed', 'skipped', 'cancelled'], true)) {
        $finished = $now;
        if ($started === '') $started = $now;
    }

    np_q('UPDATE job_stages SET status = ?, started_at = ?, finished_at = ?, attempts = ?,'
        . ' input_ref = ?, output_ref = ?, error = ?, error_kind = ?, model = ?, tokens = ?,'
        . ' cost = ?, retryable = ?, skipped_reason = ?, result = ?, updated_at = ?'
        . ' WHERE id = ?',
        [$status, $started, $finished, $attempts,
         (string)($opts['input_ref'] ?? $row['input_ref']),
         (string)($opts['output_ref'] ?? $row['output_ref']),
         isset($opts['error']) ? np_redact((string)$opts['error']) : $row['error'],
         (string)($opts['error_kind'] ?? $row['error_kind']),
         (string)($opts['model'] ?? $row['model']),
         (int)($opts['tokens'] ?? $row['tokens']),
         (float)($opts['cost'] ?? $row['cost']),
         isset($opts['retryable']) ? (int)(bool)$opts['retryable'] : (int)$row['retryable'],
         (string)($opts['skipped_reason'] ?? $row['skipped_reason']),
         isset($opts['result']) ? (is_scalar($opts['result']) ? (string)$opts['result']
             : json_encode($opts['result'], JSON_UNESCAPED_UNICODE)) : $row['result'],
         $now, (string)$row['id']]);
}

/** Mark a stage as skipped with an explicit reason — never silently. */
function np_stage_skip(string $jobId, string $stage, string $reason): void {
    np_stage_set($jobId, $stage, 'skipped', [
        'skipped_reason' => $reason,
        'error' => '',
        'retryable' => 0,
    ]);
}

/**
 * The whole checklist of a job, in order.
 * A job that has not run yet still shows the plan: every stage of the
 * pipeline with the status 'pending'. A missing row is never hidden.
 */
function np_stages_list(string $jobId, string $lang = 'fa'): array {
    $rows = np_all('SELECT * FROM job_stages WHERE job_id = ? ORDER BY seq ASC, stage ASC',
                    [$jobId]);
    $byStage = [];
    foreach ($rows as $r) $byStage[(string)$r['stage']] = $r;
    $out = [];
    // first the stages of the plan, in their defined order
    $seq = 0;
    foreach (np_stage_defs() as $d) {
        $key = (string)$d['key'];
        $seq++;
        if (!isset($byStage[$key])) {
            $out[] = [
                'stage' => $key, 'label' => $lang === 'en' ? (string)$d['en'] : (string)$d['fa'],
                'seq' => $seq, 'status' => 'pending',
                'started_at' => '', 'finished_at' => '', 'attempts' => 0,
                'input_ref' => '', 'output_ref' => '', 'error' => '', 'error_kind' => '',
                'model' => '', 'tokens' => 0, 'cost' => 0, 'retryable' => true,
                'skipped_reason' => '', 'result' => '', 'updated_at' => '',
            ];
        }
    }
    foreach ($rows as $r) {
        $out[] = [
            'stage'        => (string)$r['stage'],
            'label'        => np_stage_label((string)$r['stage'], $lang),
            'seq'          => (int)$r['seq'],
            'status'       => (string)$r['status'],
            'started_at'   => (string)$r['started_at'],
            'finished_at'  => (string)$r['finished_at'],
            'attempts'     => (int)$r['attempts'],
            'input_ref'    => (string)$r['input_ref'],
            'output_ref'   => (string)$r['output_ref'],
            'error'        => (string)($r['error'] ?? ''),
            'error_kind'   => (string)$r['error_kind'],
            'model'        => (string)$r['model'],
            'tokens'       => (int)$r['tokens'],
            'cost'         => (float)$r['cost'],
            'retryable'    => (int)$r['retryable'] === 1,
            'skipped_reason' => (string)$r['skipped_reason'],
            'result'       => (string)($r['result'] ?? ''),
            'updated_at'   => (string)$r['updated_at'],
        ];
    }
    return $out;
}

/** How far along is this job? */
function np_stages_progress(string $jobId): array {
    $rows = np_all('SELECT status FROM job_stages WHERE job_id = ?', [$jobId]);
    if (!$rows) return ['done' => 0, 'total' => 0, 'pct' => 0, 'failed' => 0];
    $done = 0; $failed = 0; $total = count($rows);
    foreach ($rows as $r) {
        $s = (string)$r['status'];
        if (in_array($s, ['completed', 'skipped'], true)) $done++;
        if ($s === 'failed') $failed++;
    }
    return ['done' => $done, 'total' => $total, 'failed' => $failed,
            'pct' => $total > 0 ? (int)round($done * 100 / $total) : 0];
}

/** The stages of a job that may be retried right now. */
function np_stages_retryable(string $jobId): array {
    $out = [];
    foreach (np_stages_list($jobId) as $s) {
        if ($s['status'] === 'failed' && $s['retryable']) $out[] = $s['stage'];
    }
    return $out;
}


/**
 * The stages of many jobs, in one query.
 * The queue shows the checklist of every card, so this is the hot path.
 */
function np_stages_for_jobs(array $jobIds): array {
    $out = [];
    if (!$jobIds) return $out;
    $ph = implode(',', array_fill(0, count($jobIds), '?'));
    $rows = np_all('SELECT job_id, stage, seq, status, error, skipped_reason, attempts'
        . ' FROM job_stages WHERE job_id IN (' . $ph . ') ORDER BY seq ASC', $jobIds);
    foreach ($rows as $r) {
        $jid = (string)$r['job_id'];
        if (!isset($out[$jid])) $out[$jid] = [];
        $out[$jid][] = [
            'stage'  => (string)$r['stage'],
            'seq'    => (int)$r['seq'],
            'status' => (string)$r['status'],
            'error'  => (string)($r['error'] ?? ''),
            'skipped_reason' => (string)($r['skipped_reason'] ?? ''),
            'attempts' => (int)$r['attempts'],
        ];
    }
    return $out;
}

/** The checklist of a job as a compact list for the queue card. */
function np_stage_strip(string $jobId): array {
    $rows = np_all('SELECT stage, seq, status, error, skipped_reason, attempts'
        . ' FROM job_stages WHERE job_id = ? ORDER BY seq ASC', [$jobId]);
    $defs = np_stage_defs();
    $byKey = [];
    foreach ($rows as $r) $byKey[(string)$r['stage']] = $r;
    $out = [];
    $seq = 0;
    foreach ($defs as $d) {
        $seq++;
        $key = (string)$d['key'];
        $r = $byKey[$key] ?? null;
        $status = $r ? (string)$r['status'] : 'pending';
        $out[] = [
            'stage'  => $key,
            'label'  => (string)$d['en'],
            'label_fa' => (string)$d['fa'],
            'seq'    => $seq,
            'status' => $status,
            'error'  => $r ? (string)($r['error'] ?? '') : '',
            'attempts' => $r ? (int)$r['attempts'] : 0,
        ];
    }
    return $out;
}
