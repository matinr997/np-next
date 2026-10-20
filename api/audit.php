<?php
// The content audit.
//
// Every video is checked against a set of rules that can be decided from the
// data alone — a missing Persian title, a missing quiz, a transcript that
// was never written. The findings are stored so an administrator can work
// through them, apply a correction and rerun the audit.
//
// What the audit does NOT do: claim that medical content is clinically
// correct. A rule-based audit can say a quiz is missing; it cannot say the
// nursing advice in a video is right. Anything that needs clinical judgement
// is flagged for a qualified human.
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/security.php';
require_once __DIR__ . '/catalogue.php';

/** The rules. Each one returns a list of findings for one video. */
function np_audit_rules(array $v): array {
    $id = (string)($v['id'] ?? '');
    $out = [];
    $add = function ($cat, $sev, $evidence, $action) use (&$out, $id) {
        $out[] = ['video_id' => $id, 'yt_id' => $id, 'category' => $cat, 'severity' => $sev,
                  'evidence' => $evidence, 'recommended' => $action];
    };

    if (trim((string)($v['title_fa'] ?? '')) === '') {
        $add('missing_title_fa', 'high', 'title_fa is empty',
             'Regenerate the Persian title (stage title_fa).');
    }
    if (trim((string)($v['title_en'] ?? '')) === '') {
        $add('missing_title_en', 'high', 'title_en is empty',
             'Regenerate the English title (stage title_en).');
    }
    if (trim((string)($v['summary_fa'] ?? '')) === '' || trim((string)($v['summary_en'] ?? '')) === '') {
        $add('missing_summary', 'medium', 'summary_fa or summary_en is empty',
             'Regenerate the SEO description (stage seo).');
    }
    if (!is_file(__DIR__ . '/../subs/' . $id . '.json')) {
        $add('missing_transcript', 'high', 'subs/' . $id . '.json is missing',
             'Acquire the transcript (stage transcript).');
    }
    if (!is_file(__DIR__ . '/../quizzes/' . $id . '.json')) {
        $add('missing_quiz', 'medium', 'quizzes/' . $id . '.json is missing',
             'Generate a quiz (stage quiz) and validate it (stage quiz_validate).');
    } else {
        $q = json_decode((string)file_get_contents(__DIR__ . '/../quizzes/' . $id . '.json'), true);
        $qs = is_array($q['questions'] ?? null) ? $q['questions'] : [];
        if (count($qs) < 3) {
            $add('quiz_too_short', 'medium', 'the quiz has ' . count($qs) . ' questions',
                 'Regenerate the quiz with at least three questions.');
        }
        foreach ($qs as $i => $qq) {
            $type = (string)($qq['type'] ?? '');
            $bad = false;
            if ($type === 'mc') {
                $bad = count(is_array($qq['of'] ?? null) ? $qq['of'] : []) !== 4
                    || !is_int($qq['c'] ?? null);
            } elseif ($type === 'cloze') {
                foreach ((array)($qq['blanks'] ?? []) as $b) {
                    if (!is_array($b) || count((array)($b['of'] ?? [])) !== 3) { $bad = true; break; }
                }
            } elseif ($type === 'dnd') {
                foreach ((array)($qq['items'] ?? []) as $it) {
                    if (!is_array($it) || empty($it['fa']) || empty($it['en'])) { $bad = true; break; }
                }
            } else { $bad = true; }
            if ($bad) {
                $add('invalid_quiz_structure', 'high',
                     'question ' . ($i + 1) . ' has an invalid structure (' . ($type ?: 'no type') . ')',
                     'Repair the quiz with scripts/fix_quiz_format.py.');
                break;
            }
        }
    }
    if ((int)($v['dur_seconds'] ?? 0) <= 0) {
        $add('missing_duration', 'low', 'dur_seconds is 0',
             'Read the duration again (stage identify).');
    }
    if (trim((string)($v['channel'] ?? '')) === '') {
        $add('missing_channel', 'low', 'channel is empty',
             'Read the channel again (stage identify).');
    }
    // publication consistency
    $status = strtolower((string)($v['status'] ?? ''));
    if ($status !== 'published' && $status !== 'draft') {
        $add('inconsistent_status', 'medium', 'status is "' . $status . '"',
             'Set the status to draft or published (stage publish).');
    }
    // a video that is published still needs a human to look at the medicine
    if ($status === 'published') {
        $add('needs_human_review', 'info',
             'the video is live on the site',
             'A human with a clinical background should read the transcript and the quiz. '
             . 'An automated audit does not validate medical advice.');
    }
    return $out;
}

/** Run the audit over the whole catalogue. */
function np_audit_run(): array {
    $runId = np_id('run');
    $now = np_now();
    $all = [];
    foreach (np_catalogue() as $v) {
        $all = array_merge($all, np_audit_rules($v));
    }
    // a fresh run replaces the open findings of the same categories
    try {
        np_q("UPDATE content_issues SET status = 'superseded', updated_at = ? WHERE status = 'open'",
             [$now]);
    } catch (Throwable $e) { /* no table yet */ }
    foreach ($all as $f) {
        try {
            np_q('INSERT INTO content_issues (id, video_id, yt_id, category, severity, evidence,'
                . ' recommended, status, run_id, created_at, updated_at)'
                . ' VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                [np_id('iss'), $f['video_id'], $f['yt_id'], $f['category'], $f['severity'],
                 $f['evidence'], $f['recommended'], 'open', $runId, $now, $now]);
        } catch (Throwable $e) { /* keep going: one bad row must not stop the run */ }
    }
    return ['run_id' => $runId, 'findings' => count($all)];
}

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

if ($method === 'GET') {
    if (np_admin() === null && !np_worker_ok()) np_json(['ok' => false, 'error' => 'forbidden'], 403);
    $act = (string)($_GET['action'] ?? 'list');
    if ($act === 'list') {
        $w = "status = 'open'"; $a = [];
        if (!empty($_GET['category'])) { $w .= ' AND category = ?'; $a[] = (string)$_GET['category']; }
        if (!empty($_GET['severity'])) { $w .= ' AND severity = ?';  $a[] = (string)$_GET['severity']; }
        $lim = max(1, min(500, (int)($_GET['limit'] ?? 200)));
        $rows = np_all('SELECT * FROM content_issues WHERE ' . $w
            . ' ORDER BY created_at DESC LIMIT ' . $lim, $a);
        $sum = np_all('SELECT category, severity, COUNT(*) AS n FROM content_issues'
            . " WHERE status = 'open' GROUP BY category, severity");
        np_json(['ok' => true, 'issues' => $rows, 'summary' => $sum]);
    }
    np_json(['ok' => false, 'error' => 'unknown_action'], 400);
}

if ($method === 'POST') {
    np_require_admin();
    np_require_csrf();
    $b = np_body();
    $act = np_str($b, 'action');
    if ($act === 'run') {
        $r = np_audit_run();
        np_activity('audit_run', $r['run_id'], 'content audit: ' . $r['findings'] . ' findings');
        np_json(['ok' => true, 'run_id' => $r['run_id'], 'findings' => $r['findings']]);
    }
    if ($act === 'resolve') {
        $id = np_str($b, 'id');
        np_q("UPDATE content_issues SET status = 'resolved', updated_at = ? WHERE id = ?",
             [np_now(), $id]);
        np_activity('audit_resolve', $id, 'issue resolved');
        np_json(['ok' => true]);
    }
    if ($act === 'ignore') {
        $id = np_str($b, 'id');
        np_q("UPDATE content_issues SET status = 'ignored', updated_at = ? WHERE id = ?",
             [np_now(), $id]);
        np_activity('audit_ignore', $id, 'issue ignored');
        np_json(['ok' => true]);
    }
    np_json(['ok' => false, 'error' => 'unknown_action'], 400);
}
