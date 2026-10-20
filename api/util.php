<?php
// NursePlus API — shared helpers.
declare(strict_types=1);

// A JSON endpoint must never emit a PHP notice/warning into the response body —
// it would corrupt the payload for the panel. Notices go to the error log only.
error_reporting(E_ALL & ~E_DEPRECATED & ~E_USER_DEPRECATED);
ini_set('display_errors', '0');
ini_set('log_errors', '1');

function np_json($data, int $code = 200): void {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    header('X-Content-Type-Options: nosniff');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function np_body(): array {
    $raw = file_get_contents('php://input');
    if (!is_string($raw) || $raw === '') return [];
    $j = json_decode($raw, true);
    if (is_array($j)) return $j;
    parse_str($raw, $f);
    return is_array($f) ? $f : [];
}

function np_cfg(): array {
    static $c = null;
    if (is_array($c)) return $c;
    $file = __DIR__ . '/config.php';
    if (!is_file($file)) {
        np_json(['ok' => false, 'error' => 'config_missing',
                 'message' => 'api/config.php has not been created yet'], 500);
    }
    $c = require $file;
    if (!is_array($c)) $c = [];
    return $c;
}

/** Extract a YouTube video id from any accepted URL shape (or a bare id). */
function np_yt_id(string $raw): ?string {
    $raw = trim($raw);
    if ($raw === '') return null;
    if (preg_match('/^[A-Za-z0-9_-]{11}$/', $raw)) return $raw;
    $p = @parse_url($raw);
    if (!is_array($p)) return null;
    $host = strtolower((string)($p['host'] ?? ''));
    $path = (string)($p['path'] ?? '');
    $id = null;
    if (strpos($host, 'youtu.be') !== false) {
        $id = trim(explode('/', $path)[1] ?? '', '/');
    } elseif (strpos($host, 'youtube.com') !== false || strpos($host, 'youtube-nocookie.com') !== false) {
        if (preg_match('#^/(?:shorts|embed|live)/#i', $path)) {
            $parts = explode('/', trim($path, '/'));
            $id = $parts[1] ?? null;
        } elseif (preg_match('#^/watch#i', $path)) {
            parse_str((string)($p['query'] ?? ''), $q);
            $id = $q['v'] ?? null;
        }
    }
    if (!is_string($id) || $id === '') return null;
    $id = preg_split('/[?&#\s]/', $id)[0] ?? '';
    return preg_match('/^[A-Za-z0-9_-]{11}$/', $id) ? $id : null;
}

/** Every YouTube id inside a blob of pasted text (links and/or bare ids). */
function np_yt_ids_in(string $blob): array {
    $found = [];
    $rx = '#(?:youtube\.com/watch\?(?:[^\s]*&)?v=|youtu\.be/|youtube(?:-nocookie)?\.com/(?:shorts|embed|live)/)([A-Za-z0-9_-]{11})#i';
    if (preg_match_all($rx, $blob, $m)) foreach ($m[1] as $id) $found[$id] = true;
    if (preg_match_all('#(?m)^\s*([A-Za-z0-9_-]{11})\s*$#', $blob, $m2)) foreach ($m2[1] as $id) $found[$id] = true;
    return array_values(array_unique(array_keys($found)));
}

/** Stable, sortable id. */
function np_id(string $prefix = 'job'): string {
    return $prefix . '_' . bin2hex(random_bytes(8));
}

function np_now(): string {
    return gmdate('Y-m-d H:i:s');
}

function np_str(array $a, string $k, string $def = ''): string {
    $v = $a[$k] ?? null;
    return is_scalar($v) ? trim((string)$v) : $def;
}

/** True when the request carries a valid worker token (for headless daemons). */
function np_worker_ok(): bool {
    $cfg = np_cfg();
    $want = (string)($cfg['worker_token'] ?? '');
    if ($want === '') return false;
    $got = $_SERVER['HTTP_X_WORKER_TOKEN'] ?? '';
    return is_string($got) && $got !== '' && hash_equals($want, $got);
}

/** Session cookie for the admin panel. */
function np_session_start(): void {
    if (session_status() === PHP_SESSION_ACTIVE) return;
    session_set_cookie_params([
        'lifetime' => 0, 'path' => '/', 'httponly' => true,
        'samesite' => 'Lax', 'secure' => !empty($_SERVER['HTTPS']),
    ]);
    session_name('npsid');
    session_start();
}

/** The logged-in admin, or null. */
function np_admin(): ?array {
    np_session_start();
    $email = $_SESSION['admin_email'] ?? null;
    if (!is_string($email) || $email === '') return null;
    return ['email' => $email, 'name' => (string)($_SESSION['admin_name'] ?? $email), 'role' => 'admin'];
}

/** Guard: admin session OR worker token. */
function np_require_admin(): array {
    $a = np_admin();
    if ($a !== null) return $a;
    if (np_worker_ok()) return ['email' => 'worker', 'name' => 'pipeline worker', 'role' => 'worker'];
    np_json(['ok' => false, 'error' => 'unauthorized', 'message' => 'وارد حساب ادمین نشده‌اید'], 401);
}

/** Read the static catalogue that the site actually renders. */
function np_static_videos(): array {
    $f = __DIR__ . '/../data/videos.json';
    if (!is_file($f)) return [];
    $j = json_decode((string)file_get_contents($f), true);
    if (!is_array($j)) return [];
    if (isset($j['videos']) && is_array($j['videos'])) return $j['videos'];
    return array_values(array_filter($j, 'is_array'));
}
