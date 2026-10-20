<?php
// GET /api/videos.php              -> {ok, videos:[...]}
// GET /api/videos.php?check=<id>   -> {ok, duplicate, video, reason}
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
np_json(['ok' => true, 'videos' => np_catalogue()]);
