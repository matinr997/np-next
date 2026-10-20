<?php
// NursePlus API — the catalogue, shared by /api/videos.php and /api/jobs.php.
// The site renders data/videos.json; the DB mirrors it. Both are consulted so a
// duplicate is caught even before the JSON has been imported into MySQL.
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';

/** "4:42" / "1:03:05" -> seconds. The catalogue stores mm:ss or h:mm:ss. */
function np_dur_sec(string $s): int {
    $s = trim($s);
    if ($s === '') return 0;
    if (ctype_digit($s)) return (int)$s;
    $p = explode(':', $s);
    if (count($p) === 2) return ((int)$p[0]) * 60 + (int)$p[1];
    if (count($p) === 3) return ((int)$p[0]) * 3600 + ((int)$p[1]) * 60 + (int)$p[2];
    return 0;
}

/**
 * Make sure the videos table can answer "which were added last?".
 *
 * The column did not exist, so the ten newest videos could only be guessed
 * from the publication date. created_at is the real insertion time; the
 * existing rows are backfilled from published_at, which is the closest true
 * value the old records have.
 */
function np_videos_schema(): void {
    static $done = false;
    if ($done) return;
    $done = true;
    np_migrate(['videos' => ['created_at' => "VARCHAR(32) NOT NULL DEFAULT ''"]]);
    try {
        // the rows that were there before the column existed
        np_q("UPDATE videos SET created_at = published_at
              WHERE (created_at IS NULL OR created_at = '') AND published_at IS NOT NULL AND published_at <> ''");
        // and the ones with no publication date at all
        np_q("UPDATE videos SET created_at = ? WHERE created_at IS NULL OR created_at = ''",
             [gmdate('Y-m-d H:i:s')]);
    } catch (Throwable $e) { /* the table may not exist yet */ }
    try {
        $idx = np_driver() === 'sqlite'
            ? 'CREATE INDEX IF NOT EXISTS idx_videos_created ON videos (created_at DESC, id DESC)'
            : 'CREATE INDEX idx_videos_created ON videos (created_at DESC, id DESC)';
        np_db()->exec($idx);
    } catch (Throwable $e) { /* the index may already exist */ }
}

/** The catalogue the site actually shows: DB rows merged with data/videos.json. */
function np_catalogue(): array {
    np_videos_schema();
    $out = [];
    foreach (np_static_videos() as $v) {
        $id = (string)($v['id'] ?? '');
        if ($id === '') continue;
        $out[$id] = [
            'id'            => $id,
            'title_fa'      => (string)($v['fa'] ?? $v['title_fa'] ?? ''),
            'title_en'      => (string)($v['en'] ?? $v['title_en'] ?? ''),
            'summary_fa'    => (string)($v['sum'] ?? $v['summary_fa'] ?? ''),
            'summary_en'    => (string)($v['sum_en'] ?? $v['summary_en'] ?? ''),
            'topic'         => (string)($v['cat'] ?? $v['topic'] ?? ''),
            'topic_en'      => (string)($v['cat_en'] ?? $v['topic_en'] ?? ''),
            'channel'       => (string)($v['src'] ?? $v['channel'] ?? ''),
            'dur_seconds'   => np_dur_sec((string)($v['dur_sec'] ?? $v['dur'] ?? '')),
            'views'         => (int)($v['views'] ?? 0),
            'has_transcript' => !empty($v['tr']) || is_file(__DIR__ . '/../subs/' . $id . '.json'),
            'has_quiz'      => is_file(__DIR__ . '/../quizzes/' . $id . '.json'),
            'published_at'  => (string)($v['publishedAt'] ?? $v['published_at'] ?? ''),
            'created_at'    => (string)($v['created_at'] ?? $v['createdAt'] ?? ''),
            'status'        => (string)($v['status'] ?? 'published'),
        ];
    }
    try {
        foreach (np_all('SELECT id, title_fa, title_en, channel, dur_seconds, status, active FROM videos') as $r) {
            $id = (string)$r['id'];
            if (isset($out[$id])) {
                if ((int)($r['active'] ?? 1) === 1) $out[$id]['status'] = (string)($r['status'] ?: $out[$id]['status']);
                continue;
            }
            $out[$id] = [
                'id' => $id, 'title_fa' => (string)$r['title_fa'], 'title_en' => (string)$r['title_en'],
                'summary_fa' => (string)($r['summary_fa'] ?? ''), 'summary_en' => (string)($r['summary_en'] ?? ''),
                'topic' => (string)($r['topic'] ?? ''), 'topic_en' => (string)($r['topic_en'] ?? ''),
                'channel' => (string)$r['channel'], 'dur_seconds' => (int)$r['dur_seconds'],
                'views' => (int)($r['views'] ?? 0),
                'has_transcript' => (int)($r['has_transcript'] ?? 0) === 1,
                'has_quiz' => is_file(__DIR__ . '/../quizzes/' . $id . '.json'),
                'published_at' => (string)($r['published_at'] ?? ''),
                'created_at'   => (string)($r['created_at'] ?? ''),
                'status' => (string)$r['status'],
            ];
        }
    } catch (Throwable $e) { /* table not created yet — the JSON list still works */ }
    return array_values($out);
}

/** Is this video id already on the site (or already queued)? */
function np_duplicate(string $yt_id): array {
    foreach (np_catalogue() as $v) {
        if ($v['id'] === $yt_id) return ['duplicate' => true, 'reason' => 'exists_in_site', 'video' => $v];
    }
    $job = np_one("SELECT id, status FROM pipeline_jobs WHERE yt_id = ? AND status IN ('queued','running') LIMIT 1", [$yt_id]);
    if ($job) return ['duplicate' => true, 'reason' => 'already_queued', 'video' => null];
    return ['duplicate' => false, 'reason' => null, 'video' => null];
}

/** Persian reason for a skipped link. */
function np_msg_duplicate(string $reason): string {
    return $reason === 'already_queued'
        ? 'این ویدیو همین حالا در صف است'
        : 'این لینک تکراری است';
}
