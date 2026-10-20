<?php
// The assistant's tools.
//
// The LLM never touches SQL, the filesystem or the shell. It calls one of
// these functions with structured arguments, each one is validated, each one
// is permission-checked, and each one returns a structured result.
//
// Three tiers, and the tier decides whether the administrator has to
// confirm:
//   read      — analysis only, always allowed
//   mutate    — reversible, allowed but written to the activity log
//   sensitive — publication, deletion, anything that changes what visitors
//               see: the assistant must ask for confirmation first
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/security.php';
require_once __DIR__ . '/stage_lib.php';
require_once __DIR__ . '/catalogue.php';

function np_tool_defs(): array {
    return [
        ['name' => 'search_videos', 'tier' => 'read',
         'desc' => 'Find videos by title, channel, id or status. Returns a compact list.',
         'args' => ['query' => 'string', 'status' => 'string', 'limit' => 'int']],
        ['name' => 'get_video', 'tier' => 'read',
         'desc' => 'One video with its full metadata, transcript flag and quiz state.',
         'args' => ['yt_id' => 'string']],
        ['name' => 'list_videos_missing', 'tier' => 'read',
         'desc' => 'Videos that lack a quiz, a Persian title, an English title or a transcript.',
         'args' => ['what' => 'string', 'limit' => 'int']],
        ['name' => 'get_job', 'tier' => 'read',
         'desc' => 'The state of a job: its stage, its error and the full checklist.',
         'args' => ['job_id' => 'string']],
        ['name' => 'list_jobs', 'tier' => 'read',
         'desc' => 'Jobs by status, with their age. Use status=failed or status=stuck.',
         'args' => ['status' => 'string', 'limit' => 'int']],
        ['name' => 'queue_state', 'tier' => 'read',
         'desc' => 'How many jobs are queued, running, done or failed, and the oldest queued one.',
         'args' => []],
        ['name' => 'recent_errors', 'tier' => 'read',
         'desc' => 'The most recent errors with their stage and category.',
         'args' => ['category' => 'string', 'limit' => 'int']],
        ['name' => 'list_issues', 'tier' => 'read',
         'desc' => 'Open findings of the content audit.',
         'args' => ['category' => 'string', 'limit' => 'int']],
        ['name' => 'compare_titles', 'tier' => 'read',
         'desc' => 'Compare the Persian and the English title of a video.',
         'args' => ['yt_id' => 'string']],
        ['name' => 'audit_quality', 'tier' => 'read',
         'desc' => 'Check one video for missing pieces and suspicious terminology.',
         'args' => ['yt_id' => 'string']],
        ['name' => 'retry_stage', 'tier' => 'mutate',
         'desc' => 'Put a failed stage back in the queue. The other stages are not touched.',
         'args' => ['job_id' => 'string', 'stage' => 'string']],
        ['name' => 'cancel_job', 'tier' => 'mutate',
         'desc' => 'Cancel a job that is queued or running.',
         'args' => ['job_id' => 'string']],
        ['name' => 'publish_video', 'tier' => 'sensitive',
         'desc' => 'Publish a video. Needs the administrator to confirm.',
         'args' => ['yt_id' => 'string']],
        ['name' => 'unpublish_video', 'tier' => 'sensitive',
         'desc' => 'Take a video off the site. Needs the administrator to confirm.',
         'args' => ['yt_id' => 'string']],
    ];
}

function np_tool_tier(string $name): string {
    foreach (np_tool_defs() as $d) if ($d['name'] === $name) return (string)$d['tier'];
    return 'unknown';
}

/** Coerce an argument to the declared type. */
function np_tool_arg(array $args, string $key, string $type, $def = null) {
    $v = $args[$key] ?? null;
    if ($v === null || $v === '') return $def;
    switch ($type) {
        case 'int':  return (int)$v;
        case 'bool': return in_array(strtolower((string)$v), ['1', 'true', 'yes', 'on'], true);
        default:     return is_scalar($v) ? trim((string)$v) : $def;
    }
}

/** Which videos have a quiz, a Persian title and so on. */
function np_content_issues(string $what, int $limit = 50): array {
    $out = [];
    foreach (np_catalogue() as $v) {
        $missing = [];
        if ($what === 'quiz' || $what === 'any') {
            $qf = __DIR__ . '/../quizzes/' . $v['id'] . '.json';
            if (!is_file($qf)) $missing[] = 'quiz';
        }
        if ($what === 'title_fa' || $what === 'any') {
            if ($v['title_fa'] === '') $missing[] = 'title_fa';
        }
        if ($what === 'title_en' || $what === 'any') {
            if ($v['title_en'] === '') $missing[] = 'title_en';
        }
        if ($what === 'transcript' || $what === 'any') {
            if (!$v['has_transcript']) $missing[] = 'transcript';
        }
        if (!$missing) continue;
        $out[] = ['id' => $v['id'], 'title_fa' => $v['title_fa'], 'title_en' => $v['title_en'],
                  'missing' => $missing];
        if (count($out) >= $limit) break;
    }
    return $out;
}

/** Run one tool. Returns ['ok'=>bool, 'data'=>mixed, 'error'=>string]. */
function np_tool_run(string $name, array $args): array {
    $tier = np_tool_tier($name);
    if ($tier === 'unknown') return ['ok' => false, 'error' => 'unknown_tool'];

    if ($tier === 'mutate' || $tier === 'sensitive') {
        // every write needs a valid session and a CSRF token
        if (np_admin() === null) return ['ok' => false, 'error' => 'not_authenticated'];
    }

    switch ($name) {
        case 'search_videos': {
            $q = strtolower((string)np_tool_arg($args, 'query', 'string', ''));
            $st = strtolower((string)np_tool_arg($args, 'status', 'string', ''));
            $lim = (int)np_tool_arg($args, 'limit', 'int', 25);
            $out = [];
            foreach (np_catalogue() as $v) {
                if ($st !== '' && strtolower($v['status']) !== $st) continue;
                if ($q !== '') {
                    $hay = strtolower($v['id'] . ' ' . $v['title_fa'] . ' ' . $v['title_en'] . ' ' . $v['channel']);
                    if (strpos($hay, $q) === false) continue;
                }
                $out[] = $v;
                if (count($out) >= $lim) break;
            }
            return ['ok' => true, 'data' => ['count' => count($out), 'videos' => $out]];
        }

        case 'get_video': {
            $id = (string)np_tool_arg($args, 'yt_id', 'string', '');
            foreach (np_catalogue() as $v) {
                if ($v['id'] === $id) {
                    $qf = __DIR__ . '/../quizzes/' . $id . '.json';
                    $sf = __DIR__ . '/../subs/' . $id . '.json';
                    $v['has_quiz'] = is_file($qf);
                    $v['has_subtitles'] = is_file($sf);
                    $v['has_transcript'] = $v['has_subtitles'];
                    $v['quiz_questions'] = 0;
                    if ($v['has_quiz']) {
                        $j = json_decode((string)file_get_contents($qf), true);
                        $v['quiz_questions'] = count(is_array($j['questions'] ?? null) ? $j['questions'] : []);
                    }
                    return ['ok' => true, 'data' => $v];
                }
            }
            return ['ok' => false, 'error' => 'video_not_found'];
        }

        case 'list_videos_missing': {
            $what = (string)np_tool_arg($args, 'what', 'string', 'any');
            $lim = (int)np_tool_arg($args, 'limit', 'int', 50);
            $rows = np_content_issues($what, $lim);
            return ['ok' => true, 'data' => ['count' => count($rows), 'videos' => $rows]];
        }

        case 'get_job': {
            $jid = (string)np_tool_arg($args, 'job_id', 'string', '');
            $job = np_one('SELECT * FROM pipeline_jobs WHERE id = ? LIMIT 1', [$jid]);
            if (!$job) return ['ok' => false, 'error' => 'job_not_found'];
            return ['ok' => true, 'data' => [
                'job' => $job, 'stages' => np_stages_list($jid),
                'progress' => np_stages_progress($jid),
                'retryable' => np_stages_retryable($jid)]];
        }

        case 'list_jobs': {
            $st = (string)np_tool_arg($args, 'status', 'string', '');
            $lim = (int)np_tool_arg($args, 'limit', 'int', 25);
            $w = '1 = 1'; $a = [];
            if ($st !== '') {
                if ($st === 'stuck') {
                    $w = "status = 'running' AND updated_at < ?";
                    $a[] = gmdate('Y-m-d H:i:s', time() - 900);
                } else { $w = 'status = ?'; $a[] = $st; }
            }
            $rows = np_all('SELECT * FROM pipeline_jobs WHERE ' . $w
                . ' ORDER BY created_at DESC LIMIT ' . max(1, min(100, $lim)), $a);
            return ['ok' => true, 'data' => ['count' => count($rows), 'jobs' => $rows]];
        }

        case 'queue_state': {
            $rows = np_all('SELECT status, COUNT(*) AS n FROM pipeline_jobs GROUP BY status');
            $byStatus = [];
            foreach ($rows as $r) $byStatus[(string)$r['status']] = (int)$r['n'];
            $oldest = np_one('SELECT id, yt_id, created_at FROM pipeline_jobs WHERE status = ?'
                . ' ORDER BY created_at ASC LIMIT 1', ['queued']);
            return ['ok' => true, 'data' => ['by_status' => $byStatus, 'oldest_queued' => $oldest]];
        }

        case 'recent_errors': {
            $cat = (string)np_tool_arg($args, 'category', 'string', '');
            $lim = (int)np_tool_arg($args, 'limit', 'int', 20);
            $w = '1 = 1'; $a = [];
            if ($cat !== '') { $w = 'category = ?'; $a[] = $cat; }
            $rows = np_all('SELECT id, job_id, yt_id, stage, category, severity, message,'
                . ' attempts, status, created_at FROM error_log WHERE ' . $w
                . ' ORDER BY created_at DESC LIMIT ' . max(1, min(100, $lim)), $a);
            return ['ok' => true, 'data' => ['count' => count($rows), 'errors' => $rows]];
        }

        case 'list_issues': {
            $cat = (string)np_tool_arg($args, 'category', 'string', '');
            $lim = (int)np_tool_arg($args, 'limit', 'int', 50);
            $w = "status = 'open'"; $a = [];
            if ($cat !== '') { $w .= ' AND category = ?'; $a[] = $cat; }
            $rows = np_all('SELECT * FROM content_issues WHERE ' . $w
                . ' ORDER BY created_at DESC LIMIT ' . max(1, min(200, $lim)), $a);
            return ['ok' => true, 'data' => ['count' => count($rows), 'issues' => $rows]];
        }

        case 'compare_titles': {
            $id = (string)np_tool_arg($args, 'yt_id', 'string', '');
            foreach (np_catalogue() as $v) {
                if ($v['id'] !== $id) continue;
                return ['ok' => true, 'data' => [
                    'id' => $id, 'title_fa' => $v['title_fa'], 'title_en' => $v['title_en'],
                    'same' => ($v['title_fa'] !== '' && $v['title_fa'] === $v['title_en'])]];
            }
            return ['ok' => false, 'error' => 'video_not_found'];
        }

        case 'audit_quality': {
            $id = (string)np_tool_arg($args, 'yt_id', 'string', '');
            $found = [];
            foreach (np_catalogue() as $v) {
                if ($v['id'] !== $id) continue;
                if ($v['title_fa'] === '') $found[] = ['issue' => 'missing_persian_title', 'severity' => 'high'];
                if ($v['title_en'] === '') $found[] = ['issue' => 'missing_english_title', 'severity' => 'high'];
                if (!$v['has_transcript']) $found[] = ['issue' => 'missing_transcript', 'severity' => 'high'];
                if (!is_file(__DIR__ . '/../quizzes/' . $id . '.json')) {
                    $found[] = ['issue' => 'missing_quiz', 'severity' => 'medium'];
                }
                if ($v['dur_seconds'] <= 0) $found[] = ['issue' => 'missing_duration', 'severity' => 'low'];
                if ($v['status'] === 'published') {
                    $found[] = ['issue' => 'published_content_needs_human_review',
                                'severity' => 'info',
                                'note' => 'An automated check does not make medical content clinically valid.'];
                }
                return ['ok' => true, 'data' => ['id' => $id, 'findings' => $found]];
            }
            return ['ok' => false, 'error' => 'video_not_found'];
        }

        case 'retry_stage': {
            $jid = (string)np_tool_arg($args, 'job_id', 'string', '');
            $st = (string)np_tool_arg($args, 'stage', 'string', '');
            $row = np_one('SELECT * FROM job_stages WHERE job_id = ? AND stage = ? LIMIT 1', [$jid, $st]);
            if (!$row) return ['ok' => false, 'error' => 'stage_not_found'];
            if ((string)$row['status'] !== 'failed') return ['ok' => false, 'error' => 'stage_not_failed'];
            if ((int)$row['retryable'] !== 1) return ['ok' => false, 'error' => 'stage_not_retryable'];
            np_q('UPDATE job_stages SET status = ?, error = NULL, error_kind = ?, finished_at = ?,'
                . ' updated_at = ? WHERE id = ?', ['pending', '', '', np_now(), (string)$row['id']]);
            np_q("UPDATE pipeline_jobs SET status = 'queued', stage = ?, error = NULL, updated_at = ?"
                . ' WHERE id = ?', [$st, np_now(), $jid]);
            np_activity('assistant_retry_stage', $jid . ':' . $st, 'retried by the assistant');
            return ['ok' => true, 'data' => ['job_id' => $jid, 'stage' => $st, 'status' => 'queued']];
        }

        case 'cancel_job': {
            $jid = (string)np_tool_arg($args, 'job_id', 'string', '');
            np_q("UPDATE pipeline_jobs SET status = 'cancelled', updated_at = ? WHERE id = ?"
                 . " AND status IN ('queued','running')", [np_now(), $jid]);
            np_q("UPDATE job_stages SET status = 'cancelled', finished_at = ?, updated_at = ?"
                 . " WHERE job_id = ? AND status IN ('pending','running')",
                 [np_now(), np_now(), $jid]);
            np_activity('assistant_cancel_job', $jid, 'cancelled by the assistant');
            return ['ok' => true, 'data' => ['job_id' => $jid, 'status' => 'cancelled']];
        }

        case 'publish_video':
        case 'unpublish_video': {
            // The tool prepares the action; the actual change needs the
            // administrator to confirm it in the panel.
            $id = (string)np_tool_arg($args, 'yt_id', 'string', '');
            $op = $name === 'publish_video' ? 'publish' : 'unpublish';
            $tok = np_id('cfm');
            np_q('INSERT INTO activity_log (id, actor, action, target, detail, ip, created_at)'
                . ' VALUES (?,?,?,?,?,?,?)',
                [$tok, np_actor(), 'assistant_confirm_' . $op, $id,
                 json_encode(['action' => $op, 'yt_id' => $id, 'needs_confirmation' => true],
                             JSON_UNESCAPED_UNICODE),
                 (string)($_SERVER['REMOTE_ADDR'] ?? ''), np_now()]);
            return ['ok' => true, 'data' => [
                'action' => $op, 'yt_id' => $id, 'requires_confirmation' => true,
                'confirmation_id' => $tok,
                'message' => 'This changes what visitors see. The administrator must confirm it in the panel.']];
        }
    }
    return ['ok' => false, 'error' => 'unknown_tool'];
}

/* ------------------------------------------------------------------ API */
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

if ($method === 'GET') {
    if (np_admin() === null && !np_worker_ok()) np_json(['ok' => false, 'error' => 'forbidden'], 403);
    np_json(['ok' => true, 'tools' => np_tool_defs()]);
}

if ($method === 'POST') {
    np_require_admin();
    np_require_csrf();
    $b = np_body();
    $name = np_str($b, 'tool');
    $args = is_array($b['args'] ?? null) ? $b['args'] : [];
    $r = np_tool_run($name, $args);
    if ($r['ok'] && np_tool_tier($name) === 'mutate') {
        np_activity('assistant_tool', $name, json_encode($args, JSON_UNESCAPED_UNICODE));
    }
    np_json(['ok' => (bool)$r['ok'], 'tool' => $name, 'tier' => np_tool_tier($name),
             'data' => $r['data'] ?? null, 'error' => $r['error'] ?? '']);
}
