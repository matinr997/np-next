<?php
// GET  /api/llm.php -> {ok, settings:{endpoint, model, has_key, model_count}, models:[{id,owned_by}]}
// POST /api/llm.php {action:'save', endpoint, api_key, model}
// POST /api/llm.php {action:'refresh_models', endpoint, api_key}
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/security.php';
require_once __DIR__ . '/provider.php';

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
        // the chat may run on its own model, apart from the video pipeline
        $chatModel = array_key_exists('chat_model', $b) ? np_str($b, 'chat_model') : $cur['chat_model'];
        np_llm_save(['endpoint' => $ep, 'api_key' => $key, 'model' => $model,
                     'chat_model' => $chatModel]);
        np_json(['ok' => true, 'settings' => ['endpoint' => $ep, 'model' => $model,
            'chat_model' => $chatModel, 'has_key' => $key !== '',
            'model_count' => (int)np_val('SELECT COUNT(*) FROM llm_models')]]);
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


    // ---- a chat call with the context guard, and usage accounting -------
    if ($act === 'chat' || $act === 'compress') {
        np_require_admin();
        $s = np_llm_get();
        $model = np_str($b, 'model', $s['model']);
        $messages = is_array($b['messages'] ?? null) ? $b['messages'] : [];
        $task = np_str($b, 'task', $act === 'compress' ? 'compress' : 'panel');
        $site = np_str($b, 'site', 'ir');
        $prefs = np_prefs_get();
        $epId = np_endpoint_id($s['endpoint']);

        $meta = np_one('SELECT ctx_max FROM llm_model_meta WHERE endpoint_id = ? AND model_id = ?',
                       [$epId, $model]);
        $ctxMax = $meta ? (int)$meta['ctx_max'] : 0;

        $plan = np_context_plan($messages, $ctxMax, $prefs + ['strategy' => $prefs['strategy']]);
        $compressed = null;

        if ($act === 'compress') {
            // the explicit /compress command: always summarise the history
            $c = np_compress_history($s['endpoint'], $s['api_key'], $model, $messages,
                                     $prefs + ['lang' => np_str($b, 'lang', 'fa')]);
            if (!$c['ok']) {
                np_json(['ok' => false, 'error' => $c['error'] ?? 'compress_failed',
                         'message' => 'فشرده‌سازی گفتگو انجام نشد: ' . ($c['error'] ?? '')], 502);
            }
            np_models_record($epId, $model, 'compress', $site, $c['usage'] ?? [], 0, $ctxMax, 0, true, 0, '');
            np_json(['ok' => true, 'summary' => $c['summary'], 'messages' => $c['messages'],
                     'removed' => (int)($c['removed'] ?? 0), 'usage' => $c['usage'] ?? [],
                     'context' => ['est' => np_estimate_request_tokens($c['messages']),
                                   'ctx_max' => $ctxMax, 'source' => 'estimated']]);
        }

        if ($plan['action'] === 'warn') {
            np_json(['ok' => false, 'error' => 'context_limit', 'action' => 'warn',
                     'message' => $plan['note'], 'context' => $plan], 409);
        }
        if ($plan['action'] === 'summarize') {
            $c = np_compress_history($s['endpoint'], $s['api_key'], $model, $messages,
                                     $prefs + ['lang' => np_str($b, 'lang', 'fa')]);
            if ($c['ok']) {
                $messages = $c['messages'];
                $compressed = ['summary' => $c['summary'], 'removed' => (int)($c['removed'] ?? 0)];
                $plan = np_context_plan($messages, $ctxMax, $prefs);
                $plan['action'] = 'summarized';
                $plan['note'] = 'The history was compressed before the request was sent.';
            } else {
                // compression failed: fall back to trimming so the request still goes through
                $plan = np_context_plan($messages, $ctxMax,
                                        $prefs + ['strategy' => 'trim']);
            }
        }

        $payload = ['model' => $model, 'messages' => $messages];
        if (isset($b['max_tokens'])) $payload['max_tokens'] = (int)$b['max_tokens'];
        if (isset($b['temperature'])) $payload['temperature'] = (float)$b['temperature'];
        $r = np_provider_chat($s['endpoint'], $s['api_key'], $payload, 240);
        $usage = $r['usage'] ?? [];
        $est = $plan['est'] ?? np_estimate_request_tokens($messages);
        $pct = $ctxMax > 0 ? round((($usage['prompt_tokens'] ?? $est) / $ctxMax) * 100, 1) : 0.0;
        np_models_record($epId, $model, $task, $site, $usage, $est, $ctxMax, $pct,
                         (bool)$r['ok'], (int)($r['latency'] ?? 0), (string)($r['error'] ?? ''));

        if (!$r['ok']) {
            np_json(['ok' => false, 'error' => $r['error'] ?? 'failed',
                     'message' => 'درخواست به مدل نرسید: ' . ($r['error'] ?? ''),
                     'context' => $plan, 'usage' => $usage], 502);
        }
        $ctxOut = [
            'est' => $est, 'actual_prompt' => (int)($usage['prompt_tokens'] ?? 0),
            'completion' => (int)($usage['completion_tokens'] ?? 0),
            'total' => (int)($usage['prompt_tokens'] ?? 0) + (int)($usage['completion_tokens'] ?? 0),
            'ctx_max' => $ctxMax, 'pct' => $pct,
            'remaining' => $ctxMax > 0 ? max(0, $ctxMax - (int)($usage['prompt_tokens'] ?? 0)) : null,
            'source' => ((int)($usage['prompt_tokens'] ?? 0) > 0) ? 'actual' : 'estimated',
            'action' => $plan['action'], 'note' => $plan['note'],
        ];
        np_json(['ok' => true, 'content' => $r['content'], 'usage' => $usage,
                 'context' => $ctxOut, 'compressed' => $compressed]);
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
                   'chat_model' => $s['chat_model'],
                   'has_key' => $s['api_key'] !== '', 'model_count' => count($models)],
    'models' => $models];
// The worker token is a shared secret and the worker NEEDS the key to call the
// model. A browser session never gets it.
if ($isWorker) $out['api_key'] = $s['api_key'];
np_json($out);
