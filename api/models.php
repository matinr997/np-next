<?php
// GET  /api/models.php?action=list
//        -> the model catalogue: capabilities, context size, verification
//           status, metadata source and the usage summary of each model
// GET  /api/models.php?action=detail&model=ID
//        -> one model in full, plus its recent usage rows
// GET  /api/models.php?action=usage&model=&task=&from=&to=&site=&limit=
//        -> usage rows, totals and breakdowns
// POST /api/models.php {action:'record', ...}   (worker token)
//        -> record one model call
// POST /api/models.php {action:'override', ...}  (admin)
//        -> set or clear a manual capability override
// POST /api/models.php {action:'refresh'}        (admin)
//        -> re-read the catalogue from the provider; overrides are kept
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/security.php';
require_once __DIR__ . '/provider.php';

const NP_CAP_COLS = [
    'vision' => 'cap_vision', 'reasoning' => 'cap_reasoning', 'tools' => 'cap_tools',
    'image_gen' => 'cap_image_gen', 'audio' => 'cap_audio',
];

/** Ensure the model metadata tables exist (idempotent, safe on every call). */
function np_models_schema(): void {
    static $done = false;
    if ($done) return;
    $done = true;
    $file = __DIR__ . '/db/schema_models.sql';
    if (is_file($file)) {
        try { np_run_schema($file); } catch (Throwable $e) { /* created by setup.php instead */ }
    }
    np_migrate([
        'llm_model_meta' => [
            'provider' => "VARCHAR(120) NOT NULL DEFAULT ''",
            'display_name' => "VARCHAR(190) NOT NULL DEFAULT ''",
            'cap_vision' => "VARCHAR(10) NOT NULL DEFAULT 'unknown'",
            'cap_reasoning' => "VARCHAR(10) NOT NULL DEFAULT 'unknown'",
            'cap_tools' => "VARCHAR(10) NOT NULL DEFAULT 'unknown'",
            'cap_image_gen' => "VARCHAR(10) NOT NULL DEFAULT 'unknown'",
            'cap_audio' => "VARCHAR(10) NOT NULL DEFAULT 'unknown'",
            'ctx_max' => 'INTEGER NOT NULL DEFAULT 0',
            'out_max' => 'INTEGER NOT NULL DEFAULT 0',
            'verify_status' => "VARCHAR(16) NOT NULL DEFAULT 'unknown'",
            'meta_source' => "VARCHAR(32) NOT NULL DEFAULT 'none'",
            'meta_updated' => "VARCHAR(32) NOT NULL DEFAULT ''",
        ],
        'llm_model_overrides' => [
            'cap_vision' => "VARCHAR(10) NOT NULL DEFAULT ''",
            'cap_reasoning' => "VARCHAR(10) NOT NULL DEFAULT ''",
            'cap_tools' => "VARCHAR(10) NOT NULL DEFAULT ''",
            'cap_image_gen' => "VARCHAR(10) NOT NULL DEFAULT ''",
            'cap_audio' => "VARCHAR(10) NOT NULL DEFAULT ''",
            'ctx_max' => 'INTEGER NOT NULL DEFAULT -1',
            'out_max' => 'INTEGER NOT NULL DEFAULT -1',
            'display_name' => "VARCHAR(190) NOT NULL DEFAULT ''",
            'set_by' => "VARCHAR(190) NOT NULL DEFAULT ''",
            'updated_at' => "VARCHAR(32) NOT NULL DEFAULT ''",
        ],
        'llm_usage' => [
            'task' => "VARCHAR(40) NOT NULL DEFAULT 'other'",
            'site' => "VARCHAR(8) NOT NULL DEFAULT 'ir'",
            'prompt_tokens' => 'INTEGER NOT NULL DEFAULT 0',
            'completion_tokens' => 'INTEGER NOT NULL DEFAULT 0',
            'cached_tokens' => 'INTEGER NOT NULL DEFAULT 0',
            'reasoning_tokens' => 'INTEGER NOT NULL DEFAULT 0',
            'est_prompt_tokens' => 'INTEGER NOT NULL DEFAULT 0',
            'ctx_max' => 'INTEGER NOT NULL DEFAULT 0',
            'ctx_pct' => 'REAL NOT NULL DEFAULT 0',
            'cost' => 'REAL NOT NULL DEFAULT 0',
            'ok' => 'INTEGER NOT NULL DEFAULT 1',
            'latency_ms' => 'INTEGER NOT NULL DEFAULT 0',
            'error_kind' => "VARCHAR(32) NOT NULL DEFAULT ''",
            'created_at' => "VARCHAR(32) NOT NULL DEFAULT ''",
        ],
    ]);
}

/** Merge the provider metadata with the manual overrides. */
function np_model_rows(string $endpointId): array {
    $meta = np_all('SELECT * FROM llm_model_meta WHERE endpoint_id = ?', [$endpointId]);
    $ovr  = [];
    foreach (np_all('SELECT * FROM llm_model_overrides WHERE endpoint_id = ?', [$endpointId]) as $r) {
        $ovr[(string)$r['model_id']] = $r;
    }
    $use = [];
    foreach (np_all(
        'SELECT model_id, COUNT(*) AS requests, SUM(prompt_tokens) AS prompt_tokens,'
        . ' SUM(completion_tokens) AS completion_tokens, SUM(cached_tokens) AS cached_tokens,'
        . ' SUM(reasoning_tokens) AS reasoning_tokens, SUM(cost) AS cost,'
        . ' SUM(CASE WHEN ok = 0 THEN 1 ELSE 0 END) AS failures,'
        . ' AVG(latency_ms) AS avg_latency_ms, MAX(created_at) AS last_used'
        . ' FROM llm_usage WHERE endpoint_id = ? GROUP BY model_id', [$endpointId]) as $r) {
        $use[(string)$r['model_id']] = $r;
    }

    $out = [];
    foreach ($meta as $m) {
        $id  = (string)$m['model_id'];
        $o   = $ovr[$id] ?? null;
        $caps = [];
        $overridden = [];
        foreach (NP_CAP_COLS as $field => $col) {
            $v = (string)$m[$col];
            if ($o !== null && (string)$o[$col] !== '') {
                $v = (string)$o[$col];
                $overridden[] = $field;
            }
            $caps[$field] = $v === '' ? 'unknown' : $v;
        }
        $ctx = (int)$m['ctx_max'];
        $outMax = (int)$m['out_max'];
        if ($o !== null && (int)$o['ctx_max'] >= 0) { $ctx = (int)$o['ctx_max']; $overridden[] = 'ctx_max'; }
        if ($o !== null && (int)$o['out_max'] >= 0) { $outMax = (int)$o['out_max']; $overridden[] = 'out_max'; }
        $u = $use[$id] ?? null;
        $out[] = [
            'id'           => $id,
            'provider'     => (string)$m['provider'],
            'name'         => (string)($o !== null && (string)$o['display_name'] !== '' ? $o['display_name'] : $m['display_name']) ?: $id,
            'caps'         => $caps,
            'ctx_max'      => $ctx,
            'out_max'      => $outMax,
            'verify'       => (string)$m['verify_status'],
            'source'       => (string)$m['meta_source'],
            'refreshed_at' => (string)$m['meta_updated'],
            'overridden'   => array_values(array_unique($overridden)),
            'usage'        => $u === null ? [
                'requests' => 0, 'prompt_tokens' => 0, 'completion_tokens' => 0,
                'cached_tokens' => 0, 'reasoning_tokens' => 0, 'cost' => 0.0,
                'failures' => 0, 'avg_latency_ms' => 0, 'last_used' => '',
            ] : [
                'requests' => (int)$u['requests'],
                'prompt_tokens' => (int)$u['prompt_tokens'],
                'completion_tokens' => (int)$u['completion_tokens'],
                'cached_tokens' => (int)$u['cached_tokens'],
                'reasoning_tokens' => (int)$u['reasoning_tokens'],
                'cost' => (float)$u['cost'],
                'failures' => (int)$u['failures'],
                'avg_latency_ms' => (int)round((float)$u['avg_latency_ms']),
                'last_used' => (string)$u['last_used'],
            ],
        ];
    }
    return $out;
}

/** Read the catalogue from the provider and store it. Overrides are kept. */
function np_models_refresh(string $endpoint, string $key): array {
    $r = np_fetch_models($endpoint, $key);
    if (!$r['ok']) return ['ok' => false, 'error' => $r['error'] ?? 'failed'];
    $epId = np_endpoint_id($endpoint);
    $now = np_now();
    $n = 0;
    foreach ($r['json']['data'] as $raw) {
        if (!is_array($raw)) continue;
        $m = np_normalize_model($raw);
        if (!$m) continue;
        $caps = $m['caps'];
        np_upsert('llm_model_meta', [
            'endpoint_id'   => $epId,
            'model_id'      => $m['id'],
            'provider'      => $m['provider'],
            'display_name'  => $m['name'],
            'cap_vision'    => $caps['vision'],
            'cap_reasoning' => $caps['reasoning'],
            'cap_tools'     => $caps['tools'],
            'cap_image_gen' => $caps['image_gen'],
            'cap_audio'     => $caps['audio'],
            'ctx_max'       => $m['ctx_max'],
            'out_max'       => $m['out_max'],
            'verify_status' => $m['verify'],
            'meta_source'   => $m['source'],
            'meta_updated'  => $now,
        ], ['endpoint_id', 'model_id']);
        // keep the legacy list in step so nothing else breaks
        np_upsert('llm_models',
            ['model_id' => $m['id'], 'owned_by' => $m['provider'], 'updated_at' => $now], ['model_id']);
        $n++;
    }
    return ['ok' => true, 'count' => $n, 'endpoint_id' => $epId];
}

np_models_schema();

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$action = (string)($_GET['action'] ?? '');
if ($method === 'POST') {
    $b = np_body();
    $action = np_str($b, 'action', $action);
}

/* ---------------- POST ---------------- */
if ($method === 'POST') {
    if ($action === 'record') {
        if (!np_worker_ok()) np_json(['ok' => false, 'error' => 'forbidden'], 403);
        $model = np_str($b, 'model_id');
        $u = is_array($b['usage'] ?? null) ? $b['usage'] : [];
        // time-ordered id: sorts correctly on MySQL and SQLite alike
        $id = 'u' . gmdate('YmdHis') . '_' . bin2hex(random_bytes(4));
        np_q('INSERT INTO llm_usage (id, endpoint_id, model_id, task, site, prompt_tokens,'
            . ' completion_tokens, cached_tokens, reasoning_tokens, est_prompt_tokens, ctx_max,'
            . ' ctx_pct, cost, ok, latency_ms, error_kind, created_at)'
            . ' VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            [$id, np_str($b, 'endpoint_id', 'default'), $model,
             np_str($b, 'task', 'other'), np_str($b, 'site', 'ir'),
             (int)($u['prompt_tokens'] ?? 0), (int)($u['completion_tokens'] ?? 0),
             (int)($u['cached_tokens'] ?? 0), (int)($u['reasoning_tokens'] ?? 0),
             (int)($b['est_prompt_tokens'] ?? 0), (int)($b['ctx_max'] ?? 0),
             (float)($b['ctx_pct'] ?? 0), (float)($u['cost'] ?? 0),
             (int)($b['ok'] ?? 1) ? 1 : 0, (int)($b['latency_ms'] ?? 0),
             np_str($b, 'error_kind', ''), np_now()]);
        np_json(['ok' => true, 'id' => $id]);
    }

    if ($action === 'override') {
        np_require_admin();
        $epId = np_str($b, 'endpoint_id', 'default');
        $model = np_str($b, 'model_id');
        if ($model === '') np_json(['ok' => false, 'error' => 'model_id is required'], 400);
        $cur = np_one('SELECT * FROM llm_model_overrides WHERE endpoint_id = ? AND model_id = ?',
                      [$epId, $model]);
        $row = $cur ?: ['endpoint_id' => $epId, 'model_id' => $model,
            'cap_vision' => '', 'cap_reasoning' => '', 'cap_tools' => '',
            'cap_image_gen' => '', 'cap_audio' => '', 'ctx_max' => -1, 'out_max' => -1,
            'display_name' => '', 'set_by' => '', 'updated_at' => ''];
        $fields = array_merge(array_keys(NP_CAP_COLS), ['ctx_max', 'out_max', 'display_name']);
        foreach ($fields as $f) {
            if (!array_key_exists($f, $b)) continue;
            $v = $b[$f];
            if ($f === 'ctx_max' || $f === 'out_max') {
                $row[$f] = ($v === null || $v === '' || (int)$v < 0) ? -1 : (int)$v;
            } else {
                $row[$f] = np_cap_state($v);
                if ($row[$f] === 'unknown') $row[$f] = '';
            }
        }
        $row['set_by'] = np_str($b, 'set_by', 'admin');
        $row['updated_at'] = np_now();
        np_upsert('llm_model_overrides', $row, ['endpoint_id', 'model_id']);
        np_json(['ok' => true, 'override' => $row]);
    }

    if ($action === 'clear_override') {
        np_require_admin();
        $epId = np_str($b, 'endpoint_id', 'default');
        np_q('DELETE FROM llm_model_overrides WHERE endpoint_id = ? AND model_id = ?',
              [$epId, np_str($b, 'model_id')]);
        np_json(['ok' => true]);
    }

    if ($action === 'prefs') {
        np_require_admin();
        foreach ($b as $k => $v) {
            if ($k === 'action') continue;
            np_upsert('llm_prefs', ['k' => (string)$k, 'v' => (string)$v, 'updated_at' => np_now()], ['k']);
        }
        np_json(['ok' => true, 'prefs' => np_prefs_get()]);
    }

    if ($action === 'refresh') {
        np_require_admin();
        $s = np_llm_get();
        $r = np_models_refresh($s['endpoint'], $s['api_key']);
        if (!$r['ok']) np_json(['ok' => false, 'error' => $r['error']], 502);
        np_json(['ok' => true, 'count' => $r['count'], 'endpoint_id' => $r['endpoint_id']]);
    }

    np_json(['ok' => false, 'error' => 'unknown_action'], 400);
}

/* ---------------- GET ---------------- */
$a = np_admin();
if ($a === null && !np_worker_ok()) {
    np_json(['ok' => true, 'authed' => false, 'models' => [], 'prefs' => np_prefs_get()]);
}
$s = np_llm_get();
$epId = np_endpoint_id($s['endpoint']);

if ($action === 'detail') {
    $model = (string)($_GET['model'] ?? '');
    $rows = np_model_rows($epId);
    $one = null;
    foreach ($rows as $r) if ($r['id'] === $model) { $one = $r; break; }
    if ($one === null) np_json(['ok' => false, 'error' => 'model_not_found'], 404);
    $hist = np_all('SELECT * FROM llm_usage WHERE endpoint_id = ? AND model_id = ?'
        . ' ORDER BY created_at DESC, id DESC LIMIT 50', [$epId, $model]);
    np_json(['ok' => true, 'model' => $one, 'history' => $hist, 'prefs' => np_prefs_get()]);
}

if ($action === 'usage') {
    $where = ['endpoint_id = ?'];
    $args = [$epId];
    if (!empty($_GET['model'])) { $where[] = 'model_id = ?'; $args[] = (string)$_GET['model']; }
    if (!empty($_GET['task']))  { $where[] = 'task = ?';     $args[] = (string)$_GET['task']; }
    if (!empty($_GET['site']))  { $where[] = 'site = ?';     $args[] = (string)$_GET['site']; }
    if (!empty($_GET['from']))  { $where[] = 'created_at >= ?'; $args[] = (string)$_GET['from']; }
    if (!empty($_GET['to']))    { $where[] = 'created_at <= ?'; $args[] = (string)$_GET['to']; }
    $w = implode(' AND ', $where);
    $limit = max(1, min(500, (int)($_GET['limit'] ?? 100)));
    $rows = np_all('SELECT * FROM llm_usage WHERE ' . $w . ' ORDER BY created_at DESC, id DESC LIMIT ' . $limit, $args);
    $tot = np_one('SELECT COUNT(*) AS requests, SUM(prompt_tokens) AS prompt_tokens,'
        . ' SUM(completion_tokens) AS completion_tokens, SUM(cached_tokens) AS cached_tokens,'
        . ' SUM(reasoning_tokens) AS reasoning_tokens, SUM(cost) AS cost,'
        . ' SUM(CASE WHEN ok = 0 THEN 1 ELSE 0 END) AS failures, AVG(latency_ms) AS avg_latency_ms'
        . ' FROM llm_usage WHERE ' . $w, $args);
    $byModel = np_all('SELECT model_id, COUNT(*) AS requests, SUM(prompt_tokens) AS prompt_tokens,'
        . ' SUM(completion_tokens) AS completion_tokens, SUM(cost) AS cost,'
        . ' SUM(CASE WHEN ok = 0 THEN 1 ELSE 0 END) AS failures, MAX(created_at) AS last_used'
        . ' FROM llm_usage WHERE ' . $w . ' GROUP BY model_id ORDER BY requests DESC', $args);
    $byTask = np_all('SELECT task, COUNT(*) AS requests, SUM(prompt_tokens) AS prompt_tokens,'
        . ' SUM(completion_tokens) AS completion_tokens, SUM(cost) AS cost'
        . ' FROM llm_usage WHERE ' . $w . ' GROUP BY task ORDER BY requests DESC', $args);
    $tot = $tot ?: [];
    foreach (['requests','prompt_tokens','completion_tokens','cached_tokens','reasoning_tokens','failures'] as $k) {
        $tot[$k] = (int)($tot[$k] ?? 0);
    }
    $tot['cost'] = (float)($tot['cost'] ?? 0);
    $tot['avg_latency_ms'] = (int)round((float)($tot['avg_latency_ms'] ?? 0));
    np_json(['ok' => true, 'rows' => $rows, 'totals' => $tot, 'by_model' => $byModel,
             'by_task' => $byTask, 'prefs' => np_prefs_get()]);
}

$rows = np_model_rows($epId);
np_json(['ok' => true, 'authed' => true, 'endpoint_id' => $epId, 'models' => $rows,
         'count' => count($rows), 'prefs' => np_prefs_get()]);
