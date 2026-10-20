<?php
// NursePlus API — health check + endpoint list.
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';

$dbOk = false; $dbMsg = '';
try {
    np_val('SELECT 1');
    $dbOk = true;
} catch (Throwable $e) {
    $dbMsg = $e->getMessage();
}
header('Content-Type: application/json; charset=utf-8');
echo json_encode([
    'ok'      => true,
    'service' => 'nurseplus-api',
    'php'     => PHP_VERSION,
    'db'      => $dbOk ? 'connected' : 'unavailable',
    'db_msg'  => $dbOk ? '' : $dbMsg,
    'time'    => gmdate('c'),
    'routes'  => [
        'POST /api/auth.php'   => 'login | logout',
        'GET  /api/llm.php'    => 'llm settings + cached models',
        'POST /api/llm.php'    => 'save | refresh_models',
        'GET  /api/videos.php' => 'catalogue | ?check=<yt_id>',
        'GET  /api/jobs.php'   => 'queue',
        'POST /api/jobs.php'   => 'create | claim | update | cancel',
    ],
], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
