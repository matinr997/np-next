<?php
// NursePlus chat/assistant API.
//
//   POST /api/chat.php                     (multipart) file + message  -> uploads a file + queues a job
//   POST /api/chat.php  {action:'send', message}                       -> queues a chat job
//   GET  /api/chat.php?job_id=...                                     -> the conversation so far
//   GET  /api/chat.php?action=file&msg_id=...                         -> download an uploaded file
//   POST /api/chat.php  {action:'say', job_id, text}                   -> worker appends a message
//
// The heavy lifting happens in scripts/pipeline_worker.py, which lives where the
// LLM endpoint is reachable (the Mac). Uploaded files are streamed to it over
// HTTP, because the host filesystem is not shared.
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';

const NP_UPLOAD_DIR = __DIR__ . '/uploads';
const NP_MAX_UPLOAD = 32 * 1024 * 1024;   // 32 MB

function np_upload_dir(): string {
    if (!is_dir(NP_UPLOAD_DIR)) @mkdir(NP_UPLOAD_DIR, 0775, true);
    return NP_UPLOAD_DIR;
}

/** Append a row to chat_messages. */
function np_chat_add(string $job_id, string $role, string $text, ?string $file = null): string {
    $id = np_id('msg');
    np_q('INSERT INTO chat_messages (id, job_id, role, text, file_name, file_path, created_at, updated_at)
          VALUES (?,?,?,?,?,?,?,?)',
         [$id, $job_id, $role, $text, $file, null, np_now(), np_now()]);
    return $id;
}

function np_job_messages(string $job_id): array {
    return np_all('SELECT id, role, text, file_name, created_at FROM chat_messages
                   WHERE job_id = ? ORDER BY created_at ASC, rowid ASC', [$job_id]);
}

// ---------------------------------------------------------------- download
if (($_GET['action'] ?? '') === 'file') {
    np_require_admin();
    $mid = np_str($_GET, 'msg_id');
    if ($mid === '') np_json(['ok' => false, 'error' => 'missing_msg_id'], 400);
    $m = np_one('SELECT id, file_name, file_path FROM chat_messages WHERE id = ? LIMIT 1', [$mid]);
    if (!$m || !$m['file_path']) np_json(['ok' => false, 'error' => 'not_found'], 404);
    $path = (string)$m['file_path'];
    if (!is_file($path)) np_json(['ok' => false, 'error' => 'file_missing'], 404);
    $name = (string)($m['file_name'] ?: basename($path));
    header('Content-Type: application/octet-stream');
    header('Content-Disposition: attachment; filename="' . rawurlencode($name) . '"');
    header('Content-Length: ' . filesize($path));
    readfile($path);
    exit;
}

// ---------------------------------------------------------------- read
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    np_require_admin();
    $job = np_str($_GET, 'job_id');
    if ($job === '') np_json(['ok' => true, 'messages' => []]);
    np_json(['ok' => true, 'job_id' => $job, 'messages' => np_job_messages($job)]);
}

// ---------------------------------------------------------------- write
np_require_admin();
$b = np_body();
$act = np_str($b, 'action');

// worker appends progress / answer
if ($act === 'say') {
    $job = np_str($b, 'job_id');
    $txt = np_str($b, 'text');
    if ($job === '') np_json(['ok' => false, 'error' => 'missing_job_id'], 400);
    $id = np_chat_add($job, (string)($b['role'] ?? 'agent'), $txt);
    np_json(['ok' => true, 'id' => $id]);
}

// worker marks the job finished
if ($act === 'close') {
    $job = np_str($b, 'job_id');
    np_q("UPDATE pipeline_jobs SET status = 'done', progress = 100, updated_at = ? WHERE id = ?",
         [np_now(), $job]);
    np_json(['ok' => true]);
}

// ---- file upload (multipart) — the user's "upload anything" entry point
if ($act === '' && !empty($_FILES['file'])) {
    $f = $_FILES['file'];
    if (($f['error'] ?? 4) !== 0) {
        np_json(['ok' => false, 'error' => 'upload_failed', 'message' => 'آپلود فایل ناموفق بود'], 400);
    }
    if (($f['size'] ?? 0) > NP_MAX_UPLOAD) {
        np_json(['ok' => false, 'error' => 'too_large', 'message' => 'حجم فایل بیش از ۳۲ مگابایت است'], 413);
    }
    $orig = (string)($f['name'] ?? 'file');
    $safe = preg_replace('/[^\w.\- ]+/u', '_', $orig);
    $safe = trim((string)$safe) ?: 'file';
    $job = np_id('job');
    $dest = np_upload_dir() . '/' . $job . '_' . $safe;
    if (!@move_uploaded_file($f['tmp_name'], $dest)) {
        np_json(['ok' => false, 'error' => 'move_failed', 'message' => 'ذخیرهٔ فایل ناموفق بود'], 500);
    }
    $msg = np_str($_POST, 'message');
    $mid = np_chat_add($job, 'user', $msg !== '' ? $msg : ('فایل: ' . $orig), $safe);
    np_q('UPDATE chat_messages SET file_path = ? WHERE id = ?', [$dest, $mid]);

    $now = np_now();
    np_q('INSERT INTO pipeline_jobs (id, yt_id, url, kind, stage, status, progress, created_by, created_at, updated_at)
          VALUES (?,?,?,?,?,?,?,?,?,?)',
         [$job, null, '', 'chat', 'discover', 'queued', 0, 'admin', $now, $now]);
    np_json(['ok' => true, 'job_id' => $job, 'message_id' => $mid, 'file' => $safe]);
}

// ---- plain text message
if ($act === 'send') {
    $msg = np_str($b, 'message');
    if ($msg === '') np_json(['ok' => false, 'error' => 'empty', 'message' => 'پیام خالی است'], 400);
    $job = np_id('job');
    np_chat_add($job, 'user', $msg);
    $now = np_now();
    np_q('INSERT INTO pipeline_jobs (id, yt_id, url, kind, stage, status, progress, created_by, created_at, updated_at)
          VALUES (?,?,?,?,?,?,?,?,?,?)',
         [$job, null, '', 'chat', 'discover', 'queued', 0, 'admin', $now, $now]);
    np_json(['ok' => true, 'job_id' => $job]);
}

np_json(['ok' => false, 'error' => 'unknown_action'], 400);
