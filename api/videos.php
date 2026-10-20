<?php
// GET /api/videos.php                -> {ok, videos:[...]}          the whole catalogue
// GET /api/videos.php?recent=10      -> {ok, videos:[...]}          the newest ten
// GET /api/videos.php?check=<id>     -> {ok, duplicate, video, reason}
//
// "Newest" means the record creation time, not the publication date and not
// the YouTube upload date. The videos table carries created_at for that; the
// query is done in the database, so ten rows are ten rows and not the whole
// catalogue.
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/security.php';
require_once __DIR__ . '/catalogue.php';

if (($_GET['check'] ?? '') !== '') {
    $id = np_yt_id((string)$_GET['check']);
    if ($id === null) np_json(['ok' => false, 'error' => 'invalid_id'], 400);
    $d = np_duplicate($id);
    np_json(['ok' => true, 'duplicate' => $d['duplicate'], 'reason' => $d['reason'], 'video' => $d['video']]);
}

np_videos_schema();

$recent = isset($_GET['recent']) ? (int)$_GET['recent'] : 0;
if ($recent > 0) {
    $limit = max(1, min(100, $recent));
    // the database does the sorting; the id breaks a tie between two rows
    // that were added in the same second
    try {
        $rows = np_all('SELECT id, title_fa, title_en, channel, status, created_at, published_at,'
            . ' dur_seconds, views, has_transcript, active'
            . ' FROM videos WHERE active = 1 ORDER BY created_at DESC, id DESC LIMIT ' . $limit);
    } catch (Throwable $e) {
        $rows = [];
    }
    // The videos table is a mirror of the catalogue, not the catalogue
    // itself. When it holds nothing, the catalogue is the truth.
    if (!$rows) {
        $cat = np_catalogue();
        usort($cat, function ($a, $b) {
            $c = strcmp((string)$b['created_at'], (string)$a['created_at']);
            return $c !== 0 ? $c : strcmp((string)$b['id'], (string)$a['id']);
        });
        $rows = [];
        foreach (array_slice($cat, 0, $limit) as $r) {
            $rows[] = ['id' => $r['id'], 'title_fa' => $r['title_fa'], 'title_en' => $r['title_en'],
                       'channel' => $r['channel'], 'status' => $r['status'],
                       'created_at' => $r['created_at'], 'published_at' => $r['published_at'],
                       'dur_seconds' => $r['dur_seconds'], 'views' => $r['views'],
                       'has_transcript' => $r['has_transcript'] ? 1 : 0];
        }
    }
    try {
        $out = [];
        foreach ($rows as $r) {
            $out[] = [
                'id'            => (string)$r['id'],
                'title_fa'      => (string)$r['title_fa'],
                'title_en'      => (string)$r['title_en'],
                'channel'       => (string)$r['channel'],
                'status'        => (string)$r['status'],
                'created_at'    => (string)$r['created_at'],
                'published_at'  => (string)($r['published_at'] ?? ''),
                'dur_seconds'   => (int)$r['dur_seconds'],
                'views'         => (int)$r['views'],
                'has_transcript' => (int)$r['has_transcript'] === 1,
                'has_quiz'      => is_file(__DIR__ . '/../quizzes/' . $r['id'] . '.json'),
            ];
        }
        np_json(['ok' => true, 'videos' => $out, 'count' => count($out)]);
    } catch (Throwable $e) {
        np_json(['ok' => false, 'error' => 'query_failed', 'detail' => $e->getMessage()], 500);
    }
}

np_json(['ok' => true, 'videos' => np_catalogue()]);
