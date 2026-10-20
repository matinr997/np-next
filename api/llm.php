<?php
// GET  /api/llm.php -> {ok, settings:{endpoint, model, has_key, model_count}, models:[{id,owned_by}]}
// POST /api/llm.php {action:'save', endpoint, api_key, model}
// POST /api/llm.php {action:'refresh_models', endpoint, api_key}
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';

function np_llm_get(): array {
    $r = np_one('SELECT endpoint, api_key, model FROM llm_settings WHERE id = 1');
    if (!$r) return ['endpoint' => '', 'api_key' => '', 'model' => ''];
    return ['endpoint' => (string)$r['endpoint'], 'api_key' => (string)$r['api_key'], 'model' => (string)$r['model']];
}

function np_llm_save(array $s): void {
    $now = np_now();
    np_upsert('llm_settings',
        ['id' => 1, 'endpoint' => $s['endpoint'], 'api_key' => $s['api_key'],
         'model' => $s['model'], 'updated_at' => $now], ['id']);
}

function np_http_json(string $url, array $headers = [], int $timeout = 20): array {
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true, CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_TIMEOUT => $timeout, CURLOPT_CONNECTTIMEOUT => 8,
            CURLOPT_HTTPHEADER => $headers,
        ]);
        $body = curl_exec($ch);
        $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $err  = curl_error($ch);
        if ($body === false) return ['ok' => false, 'error' => $err !== '' ? $err : 'request failed', 'code' => 0];
        $j = json_decode((string)$body, true);
        if ($code < 200 || $code >= 300) return ['ok' => false, 'error' => 'HTTP ' . $code, 'code' => $code, 'body' => substr((string)$body, 0, 300)];
        return ['ok' => true, 'json' => is_array($j) ? $j : [], 'code' => $code];
    }
    $ctx = stream_context_create(['http' => ['method' => 'GET', 'timeout' => $timeout, 'ignore_errors' => true,
        'header' => implode("\r\n", $headers)]]);
    $body = @file_get_contents($url, false, $ctx);
    if ($body === false) return ['ok' => false, 'error' => 'request failed', 'code' => 0];
    $j = json_decode((string)$body, true);
    if (!is_array($j)) return ['ok' => false, 'error' => 'bad response', 'code' => 0];
    return ['ok' => true, 'json' => $j, 'code' => 200];
}

/** Try <ep>/models then <ep>/v1/models — users type the base URL in many ways. */
function np_fetch_models(string $endpoint, string $key): array {
    $ep = rtrim(trim($endpoint), '/');
    if ($ep === '') return ['ok' => false, 'error' => 'endpoint is empty'];
    $cands = [$ep . '/models'];
    if (!preg_match('#/v\d+$#', $ep)) $cands[] = $ep . '/v1/models';
    $hdr = ['Accept: application/json'];
    if ($key !== '') $hdr[] = 'Authorization: Bearer ' . $key;
    $last = ['ok' => false, 'error' => 'no endpoint answered'];
    foreach ($cands as $u) {
        $r = np_http_json($u, $hdr);
        if ($r['ok'] && isset($r['json']['data']) && is_array($r['json']['data'])) return $r;
        $last = $r;
    }
    return $last;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    np_require_admin();
    $b = np_body();
    $act = np_str($b, 'action');

    if ($act === 'save') {
        $cur = np_llm_get();
        $ep   = np_str($b, 'endpoint', $cur['endpoint']);
        $key  = array_key_exists('api_key', $b) ? np_str($b, 'api_key') : '';
        if ($key === '' || $key === '••••••••') $key = $cur['api_key'];   // keep the stored key
        $model = np_str($b, 'model', $cur['model']);
        np_llm_save(['endpoint' => $ep, 'api_key' => $key, 'model' => $model]);
        np_json(['ok' => true, 'settings' => ['endpoint' => $ep, 'model' => $model,
            'has_key' => $key !== '', 'model_count' => (int)np_val('SELECT COUNT(*) FROM llm_models')]]);
    }

    if ($act === 'refresh_models') {
        $cur = np_llm_get();
        $ep  = np_str($b, 'endpoint', $cur['endpoint']);
        $key = array_key_exists('api_key', $b) ? np_str($b, 'api_key') : '';
        if ($key === '' || $key === '••••••••') $key = $cur['api_key'];
        $r = np_fetch_models($ep, $key);
        if (!$r['ok']) {
            np_json(['ok' => false, 'error' => $r['error'] ?? 'failed',
                     'message' => 'اتصال به endpoint مدل‌ها برقرار نشد: ' . ($r['error'] ?? '')], 502);
        }
        $list = [];
        foreach ($r['json']['data'] as $m) {
            $id = (string)($m['id'] ?? '');
            if ($id === '') continue;
            $list[$id] = ['id' => $id, 'owned_by' => (string)($m['owned_by'] ?? '')];
        }
        $now = np_now();
        np_q('DELETE FROM llm_models');
        foreach ($list as $id => $m) {
            np_upsert('llm_models',
                ['model_id' => $id, 'owned_by' => $m['owned_by'], 'updated_at' => $now], ['model_id']);
        }
        np_json(['ok' => true, 'models' => array_values($list), 'count' => count($list)]);
    }

    np_json(['ok' => false, 'error' => 'unknown_action'], 400);
}

// GET
$a = np_admin();
if ($a === null && !np_worker_ok()) {
    // the panel needs to know whether it is logged in, but the settings are private
    np_json(['ok' => true, 'authed' => false, 'settings' => null, 'models' => []]);
}
$s = np_llm_get();
$models = np_all('SELECT model_id AS id, owned_by FROM llm_models ORDER BY model_id');
$isWorker = np_worker_ok();
$out = ['ok' => true, 'authed' => true,
    'settings' => ['endpoint' => $s['endpoint'], 'model' => $s['model'],
                   'has_key' => $s['api_key'] !== '', 'model_count' => count($models)],
    'models' => $models];
// The worker token is a shared secret and the worker NEEDS the key to call the
// model. A browser session never gets it.
if ($isWorker) $out['api_key'] = $s['api_key'];
np_json($out);
