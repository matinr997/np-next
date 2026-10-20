<?php
// NursePlus API — security layer.
//
// Four things every endpoint must not forget:
//   1. a write request carries a CSRF token that matches the session
//   2. a sensitive endpoint is rate limited
//   3. an administrative action is written to the activity log
//   4. a configurable endpoint URL is never allowed to point at a private
//      address unless the deployment explicitly says so
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';

/* ------------------------------------------------------------------ CSRF
 * The panel is same-origin and cookie-authenticated, so a write endpoint
 * must prove the request came from the panel. The worker does not use a
 * session and is exempt: it authenticates with the worker token instead. */
function np_csrf_token(): string {
    if (session_status() !== PHP_SESSION_ACTIVE) @session_start();
    if (empty($_SESSION['csrf'])) {
        $_SESSION['csrf'] = bin2hex(random_bytes(24));
    }
    return (string)$_SESSION['csrf'];
}

/** True when the request carries the session's CSRF token. */
function np_csrf_ok(): bool {
    if (np_worker_ok()) return true;                 // the worker is token-authenticated
    $sent = '';
    if (isset($_SERVER['HTTP_X_CSRF_TOKEN'])) $sent = (string)$_SERVER['HTTP_X_CSRF_TOKEN'];
    if ($sent === '') {
        $h = function_exists('getallheaders') ? getallheaders() : [];
        if (is_array($h)) foreach ($h as $k => $v) {
            if (strtolower((string)$k) === 'x-csrf-token') { $sent = (string)$v; break; }
        }
    }
    if ($sent === '') return false;
    if (session_status() !== PHP_SESSION_ACTIVE) @session_start();
    $want = (string)($_SESSION['csrf'] ?? '');
    return $want !== '' && hash_equals($want, $sent);
}

/** Abort the request when the CSRF token is missing or wrong. */
function np_require_csrf(): void {
    if (np_csrf_ok()) return;
    np_json(['ok' => false, 'error' => 'csrf_failed',
             'message' => 'The request did not come from the panel (CSRF token missing).'], 403);
}

/* ------------------------------------------------------------- rate limit
 * A small fixed-window counter kept in the database, so it works on shared
 * hosting where there is no memcached. */
function np_rate_limit(string $bucket, int $limit, int $windowSec): void {
    $cfg = np_cfg();
    $allow = (bool)($cfg['allow_rate_limit_bypass'] ?? false);
    if ($allow) return;
    $now = time();
    $key = $bucket;
    try {
        $row = np_one('SELECT v FROM llm_prefs WHERE k = ? LIMIT 1', ['rl:' . $key]);
        $state = $row ? json_decode((string)$row['v'], true) : null;
        if (!is_array($state) || (int)($state['start'] ?? 0) + $windowSec <= $now) {
            $state = ['start' => $now, 'count' => 0];
        }
        $state['count'] = (int)($state['count'] ?? 0) + 1;
        np_upsert('llm_prefs', ['k' => 'rl:' . $key, 'v' => json_encode($state),
                                'updated_at' => gmdate('Y-m-d H:i:s')], ['k']);
        if ($state['count'] > $limit) {
            np_json(['ok' => false, 'error' => 'rate_limited',
                     'message' => 'Too many requests. Please wait a moment and try again.',
                     'retry_after' => $windowSec - ($now - (int)$state['start'])], 429);
        }
    } catch (Throwable $e) {
        // never let the limiter itself break a request
    }
}

/* ---------------------------------------------------------- activity log */
function np_actor(): string {
    $a = np_admin();
    if (is_array($a) && !empty($a['email'])) return (string)$a['email'];
    return 'worker';
}

function np_activity(string $action, string $target = '', $detail = ''): void {
    try {
        np_q('INSERT INTO activity_log (id, actor, action, target, detail, ip, created_at)'
            . ' VALUES (?,?,?,?,?,?,?)',
            [np_id('act'), np_actor(), $action, $target,
             is_scalar($detail) ? (string)$detail : json_encode($detail, JSON_UNESCAPED_UNICODE),
             (string)($_SERVER['REMOTE_ADDR'] ?? ''), np_now()]);
    } catch (Throwable $e) {
        // logging must never break the operation
    }
}

/* ------------------------------------------------------------- redaction
 * Secrets must never reach a log, an error message or the browser. */
function np_redact($text): string {
    $s = (string)$text;
    $s = preg_replace('/\b(sk-[A-Za-z0-9_\-]{6})[A-Za-z0-9_\-]+/', '$1…REDACTED', $s) ?? $s;
    $s = preg_replace('/(?i)(bearer\s+)[A-Za-z0-9._\-]{8,}/', '$1REDACTED', $s) ?? $s;
    $s = preg_replace('/(?i)("?(?:api_?key|password|passwd|token|secret)"?\s*[:=]\s*"?)([^"\s,&]{4,})/i',
                      '$1REDACTED', $s) ?? $s;
    $s = preg_replace('/\b([A-Za-z0-9_\-]{32,})\b/', 'REDACTED', $s) ?? $s;
    // absolute paths leak the server layout
    $s = preg_replace('#(/[A-Za-z0-9_\-./]{2,})/([A-Za-z0-9_\-./]+)#', '…/$2', $s) ?? $s;
    return $s;
}

/* ------------------------------------------------------------------ SSRF
 * The AI endpoint is configurable, which makes it an SSRF risk: a value
 * like http://169.254.169.254/ would reach the cloud metadata service.
 * Private and loopback addresses are refused unless the deployment
 * explicitly allows them (a local development endpoint needs this). */
function np_endpoint_allowed(string $endpoint): array {
    $ep = trim($endpoint);
    if ($ep === '') return ['ok' => false, 'error' => 'endpoint_missing'];
    if (!preg_match('#^https?://#i', $ep)) return ['ok' => false, 'error' => 'endpoint_not_a_url'];
    $p = @parse_url($ep);
    if (!is_array($p) || empty($p['host'])) return ['ok' => false, 'error' => 'endpoint_bad_host'];
    $host = (string)$p['host'];
    $port = (int)($p['port'] ?? ($p['scheme'] === 'https' ? 443 : 80));
    if ($port < 1 || $port > 65535) return ['ok' => false, 'error' => 'endpoint_bad_port'];

    $cfg = np_cfg();
    $allowPrivate = (bool)($cfg['allow_private_endpoint'] ?? false);
    $allowHosts = array_map('trim', explode(',', (string)($cfg['allow_private_hosts'] ?? '')));
    $isLocal = in_array(strtolower($host), array_map('strtolower', $allowHosts), true);
    if (!$isLocal) {
        $isLocal = (bool)preg_match('/^(localhost|127\.|0\.0\.0\.0|\[?::1\]?|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.)/i', $host);
    }
    if ($isLocal && !$allowPrivate) {
        return ['ok' => false, 'error' => 'endpoint_private_blocked',
                'message' => 'This endpoint points at a private or loopback address. '
                           . 'Set allow_private_endpoint in api/config.php for a local development setup.'];
    }
    // the cloud metadata service is never allowed, not even in development
    if (preg_match('/^169\.254\.169\.254$/', $host) || preg_match('/^metadata\.google\.internal$/i', $host)) {
        return ['ok' => false, 'error' => 'endpoint_metadata_blocked',
                'message' => 'This endpoint is a cloud metadata address and is always refused.'];
    }
    return ['ok' => true, 'host' => $host, 'port' => $port];
}

/** Validate an endpoint before it is stored or called. */
function np_require_safe_endpoint(string $endpoint): array {
    $r = np_endpoint_allowed($endpoint);
    if (!$r['ok']) {
        np_json(['ok' => false, 'error' => $r['error'],
                 'message' => $r['message'] ?? 'This endpoint is not allowed.'], 400);
    }
    return $r;
}
