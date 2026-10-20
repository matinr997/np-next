<?php
// Provider adapter — one place that knows how to talk to an OpenAI-compatible
// endpoint, and one place that decides what may be claimed about a model.
//
// Two rules drive the design:
//   1. Never advertise a capability we have no evidence for. Every capability
//      is three-state: 'yes', 'no' or 'unknown'.
//   2. Never present a locally computed number as if the provider had
//      returned it. Token estimates are labelled as estimates everywhere.
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';

const NP_CAP_FIELDS = ['vision', 'reasoning', 'tools', 'image_gen', 'audio'];

/** Three-state capability value. Anything we cannot read is 'unknown'. */
function np_cap_state($v): string {
    if ($v === null) return 'unknown';
    if (is_bool($v)) return $v ? 'yes' : 'no';
    if (is_int($v) || is_float($v)) return ((int)$v) > 0 ? 'yes' : 'no';
    if (is_string($v)) {
        $s = strtolower(trim($v));
        if ($s === '') return 'unknown';
        if (in_array($s, ['1', 'true', 'yes', 'y', 'on', 'supported', 'available', 'enabled'], true)) return 'yes';
        if (in_array($s, ['0', 'false', 'no', 'n', 'off', 'unsupported', 'unavailable', 'disabled'], true)) return 'no';
    }
    return 'unknown';
}

/** Combine two capability flags ('no' + 'yes' = 'yes'; both present and 'no' = 'no'). */
function np_cap_merge($a, $b): string {
    $sa = np_cap_state($a);
    $sb = np_cap_state($b);
    if ($sa === 'yes' || $sb === 'yes') return 'yes';
    if ($sa === 'no' && $sb === 'no') return 'no';
    if ($sa === 'unknown' && $sb === 'unknown') return 'unknown';
    // one of them is 'no' and the other is unknown -> still unknown
    return 'unknown';
}

/**
 * Normalise one entry of an OpenAI-compatible /models listing.
 * The router we use returns a `capabilities` object; other providers return
 * nothing but an id. A model with no metadata is still listed — its
 * capabilities are simply 'unknown'.
 */
function np_normalize_model(array $m): array {
    $id = trim((string)($m['id'] ?? ''));
    if ($id === '') return [];
    $c = is_array($m['capabilities'] ?? null) ? $m['capabilities'] : [];

    $vision    = np_cap_state($c['vision'] ?? null);
    $reasoning = np_cap_state($c['reasoning'] ?? null);
    $tools     = np_cap_state($c['tools'] ?? null);
    $imageGen  = np_cap_state($c['imageOutput'] ?? null);
    $audio     = np_cap_merge($c['audioInput'] ?? null, $c['audioOutput'] ?? null);
    if (!array_key_exists('audioInput', $c) && !array_key_exists('audioOutput', $c)
        && !array_key_exists('audio', $c)) {
        $audio = np_cap_state($c['audio'] ?? null);
    }

    $ctx = (int)($c['contextWindow'] ?? $m['context_length'] ?? $m['context_window'] ?? 0);
    $out = (int)($c['maxOutput'] ?? $m['max_completion_tokens'] ?? $m['max_output_tokens'] ?? 0);

    // A provider that says nothing about a model leaves it unknown. We never
    // guess from the name.
    $said = array_key_exists('vision', $c) || array_key_exists('reasoning', $c)
         || array_key_exists('tools', $c) || $ctx > 0;
    $source = $said ? 'provider' : 'none';
    $verify = $said ? 'confirmed' : 'unknown';

    return [
        'id'       => $id,
        'provider' => trim((string)($m['owned_by'] ?? $m['provider'] ?? '')),
        'name'     => trim((string)($m['name'] ?? $m['display_name'] ?? $id)),
        'caps'     => [
            'vision'    => $vision,
            'reasoning' => $reasoning,
            'tools'     => $tools,
            'image_gen' => $imageGen,
            'audio'     => $audio,
        ],
        'ctx_max'  => $ctx,
        'out_max'  => $out,
        'verify'   => $verify,
        'source'   => $source,
    ];
}

/** Parse a body that is either JSON or a single-object server-sent event. */
function np_parse_body(string $raw): array {
    $raw = trim($raw);
    if ($raw === '') return [];
    $j = json_decode($raw, true);
    if (is_array($j)) return $j;
    // text/event-stream with one JSON payload per "data:" line
    $last = [];
    foreach (preg_split('/\r?\n/', $raw) as $line) {
        $line = trim($line);
        if ($line === '' || $line[0] === ':') continue;
        if (strpos($line, 'data:') === 0) $line = trim(substr($line, 5));
        if ($line === '' || $line === '[DONE]') continue;
        $d = json_decode($line, true);
        if (is_array($d)) $last = $d;
    }
    return is_array($last) ? $last : [];
}

/** Pull the usage block out of a chat completion, whatever shape it has. */
function np_extract_usage(array $raw): array {
    $u = is_array($raw['usage'] ?? null) ? $raw['usage'] : [];
    $pd = is_array($u['prompt_tokens_details'] ?? null) ? $u['prompt_tokens_details'] : [];
    $cd = is_array($u['completion_tokens_details'] ?? null) ? $u['completion_tokens_details'] : [];
    $cost = $u['cost'] ?? 0;
    if (is_array($cost)) $cost = $cost['total'] ?? 0;
    return [
        'prompt_tokens'     => (int)($u['prompt_tokens'] ?? $u['input_tokens'] ?? 0),
        'completion_tokens' => (int)($u['completion_tokens'] ?? $u['output_tokens'] ?? 0),
        'cached_tokens'     => (int)($pd['cached_tokens'] ?? $u['cached_tokens'] ?? 0),
        'reasoning_tokens'  => (int)($cd['reasoning_tokens'] ?? $u['reasoning_tokens'] ?? 0),
        'cost'              => (float)$cost,
    ];
}

/**
 * Rough token count for a pre-flight estimate.
 * ~4 characters per token is the usual rule of thumb. This is ALWAYS an
 * estimate — the panel labels it as such and the real number comes from the
 * provider's usage block after the call.
 */
function np_estimate_tokens($text): int {
    $s = (string)$text;
    if ($s === '') return 0;
    return (int)ceil(strlen($s) / 4);
}

/** Estimate the input side of a request: messages plus any extra context. */
function np_estimate_request_tokens(array $messages, string $extra = ''): int {
    $json = json_encode($messages, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    return np_estimate_tokens((string)$json) + np_estimate_tokens($extra);
}

/**
 * POST a chat completion. Returns:
 *   ok       bool
 *   content  the assistant text
 *   usage    token counts reported by the provider
 *   error    message when ok is false
 *   latency  milliseconds
 */
function np_provider_chat(string $endpoint, string $key, array $payload, int $timeout = 180): array {
    $ep = rtrim(trim($endpoint), '/');
    if ($ep === '') return ['ok' => false, 'error' => 'endpoint is empty', 'content' => '', 'usage' => [], 'latency' => 0];
    $url = $ep . '/chat/completions';
    $body = json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    $headers = ['Content-Type: application/json', 'Accept: application/json'];
    if ($key !== '') $headers[] = 'Authorization: Bearer ' . $key;

    $t0 = microtime(true);
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true, CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $body, CURLOPT_HTTPHEADER => $headers,
            CURLOPT_TIMEOUT => $timeout, CURLOPT_CONNECTTIMEOUT => 10,
        ]);
        $raw = curl_exec($ch);
        $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $err  = curl_error($ch);
        $ms   = (int)round((microtime(true) - $t0) * 1000);
        if ($raw === false) return ['ok' => false, 'error' => $err !== '' ? $err : 'request failed',
                                   'content' => '', 'usage' => [], 'latency' => $ms, 'code' => 0];
        $j = np_parse_body((string)$raw);
        if ($code < 200 || $code >= 300) {
            $msg = (string)($j['error']['message'] ?? ('HTTP ' . $code));
            return ['ok' => false, 'error' => $msg, 'content' => '', 'usage' => np_extract_usage($j),
                    'latency' => $ms, 'code' => $code, 'raw' => $j];
        }
        return ['ok' => true, 'error' => '', 'content' => np_first_text($j),
                'usage' => np_extract_usage($j), 'latency' => $ms, 'code' => $code, 'raw' => $j];
    }
    $ctx = stream_context_create(['http' => [
        'method' => 'POST', 'timeout' => $timeout, 'ignore_errors' => true,
        'header' => implode("\r\n", $headers), 'content' => $body,
    ]]);
    $raw = @file_get_contents($url, false, $ctx);
    $ms  = (int)round((microtime(true) - $t0) * 1000);
    if ($raw === false) return ['ok' => false, 'error' => 'request failed', 'content' => '', 'usage' => [], 'latency' => $ms];
    $j = np_parse_body((string)$raw);
    return ['ok' => true, 'error' => '', 'content' => np_first_text($j),
            'usage' => np_extract_usage($j), 'latency' => $ms, 'code' => 200, 'raw' => $j];
}

/** The assistant text of a chat completion, whatever the router returned. */
function np_first_text(array $j): string {
    $choices = is_array($j['choices'] ?? null) ? $j['choices'] : [];
    if (!$choices) return '';
    $msg = $choices[0]['message'] ?? $choices[0]['delta'] ?? null;
    if (is_array($msg)) {
        if (isset($msg['content']) && is_string($msg['content'])) return $msg['content'];
        if (isset($msg['reasoning']) && is_string($msg['reasoning'])) return $msg['reasoning'];
    }
    if (isset($choices[0]['text']) && is_string($choices[0]['text'])) return $choices[0]['text'];
    return '';
}

/**
 * The prompt that compresses a conversation.
 * It asks for the important parts to survive: decisions, facts, file names,
 * identifiers, open questions and anything the user asked to be remembered.
 */
function np_compress_prompt(string $lang = 'fa'): string {
    if ($lang === 'en') {
        return "Summarise the conversation below into a compact handover note.\n"
             . "KEEP: decisions that were made, facts and figures that were established, file names, "
             . "identifiers, code that was written, questions that are still open, and anything the user "
             . "explicitly asked to remember.\n"
             . "DROP: pleasantries, repeated statements, and failed attempts that led nowhere.\n"
             . "Write plain prose or short bullets. No preamble, no closing line, no questions.\n"
             . "Reply with the summary only.";
    }
    return "گفتگوی زیر را به یک یادداشت فشرده و قابل انتقال تبدیل کن.\n"
         . "این‌ها را حتماً نگه دار: تصمیم‌هایی که گرفته شد، واقعیت‌ها و اعدادی که تثبیت شدند، "
         . "نام فایل‌ها، شناسه‌ها، کدی که نوشته شد، سؤال‌های باز، و هر چیزی که کاربر گفته به یاد بماند.\n"
         . "این‌ها را حذف کن: تعارف‌ها، تکرارها، و تلاش‌های ناموفقی که به جایی نرسیدند.\n"
         . "با نثر ساده یا بولت‌های کوتاه بنویس. بدون مقدمه، بدون جملهٔ پایانی، بدون سؤال.\n"
         . "فقط خلاصه را برگردان.";
}

/**
 * Plan what to do with a request that is close to the context limit.
 * Returns:
 *   est        estimated input tokens
 *   ctx_max    the model's limit (0 = unknown)
 *   pct        utilisation percentage
 *   remaining  tokens left
 *   action     'none' | 'trim' | 'summarize' | 'warn'
 *   messages   the messages to actually send
 *   note       a human-readable note for the panel
 */
function np_context_plan(array $messages, int $ctxMax, array $cfg = []): array {
    $strategy = (string)($cfg['strategy'] ?? 'summarize');
    $warnPct  = (int)($cfg['warn_pct'] ?? 80);
    $keep     = (int)($cfg['keep_messages'] ?? 6);

    $est = np_estimate_request_tokens($messages, (string)($cfg['extra'] ?? ''));
    $out = [
        'est' => $est, 'ctx_max' => $ctxMax, 'pct' => 0.0, 'remaining' => null,
        'action' => 'none', 'messages' => $messages, 'note' => '', 'source' => 'estimated',
    ];
    if ($ctxMax <= 0) {
        $out['note'] = 'The context limit of this model is unknown, so no guard was applied.';
        return $out;
    }
    $out['pct'] = round(($est / $ctxMax) * 100, 1);
    $out['remaining'] = max(0, $ctxMax - $est);
    if ($out['pct'] < $warnPct) return $out;

    $sys = [];
    $rest = [];
    foreach ($messages as $m) {
        if (($m['role'] ?? '') === 'system') $sys[] = $m; else $rest[] = $m;
    }
    if ($strategy === 'trim') {
        $keepMsgs = array_slice($rest, -max(1, $keep));
        $out['messages'] = array_merge($sys, $keepMsgs);
        $out['action'] = 'trim';
        $out['note'] = 'The oldest messages were removed to stay inside the context window.';
        return $out;
    }
    if ($strategy === 'warn') {
        $out['action'] = 'warn';
        $out['note'] = 'The estimated context is over the warning threshold. The request was not sent.';
        return $out;
    }
    // summarize — the caller compresses the history and calls us again
    $out['action'] = 'summarize';
    $out['note'] = 'The estimated context is over the warning threshold, so the history will be compressed first.';
    $out['keep_messages'] = $keep;
    return $out;
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


/** Write one model call into llm_usage. */
function np_models_record(string $epId, string $model, string $task, string $site, array $usage,
                          int $est, int $ctxMax, float $pct, bool $ok, int $latency, string $err): void {
    try {
        np_q('INSERT INTO llm_usage (id, endpoint_id, model_id, task, site, prompt_tokens,'
            . ' completion_tokens, cached_tokens, reasoning_tokens, est_prompt_tokens, ctx_max,'
            . ' ctx_pct, cost, ok, latency_ms, error_kind, created_at)'
            . ' VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            ['u' . gmdate('YmdHis') . '_' . bin2hex(random_bytes(4)), $epId, $model, $task, $site,
             (int)($usage['prompt_tokens'] ?? 0), (int)($usage['completion_tokens'] ?? 0),
             (int)($usage['cached_tokens'] ?? 0), (int)($usage['reasoning_tokens'] ?? 0),
             $est, $ctxMax, $pct, (float)($usage['cost'] ?? 0), $ok ? 1 : 0, $latency,
             substr($err, 0, 32), np_now()]);
    } catch (Throwable $e) {
        // never let accounting break a request
    }
}


/** Panel preferences: thresholds, context strategy, pricing. */
function np_prefs_get(): array {
    $out = [];
    foreach (np_all('SELECT k, v FROM llm_prefs') as $r) $out[(string)$r['k']] = (string)$r['v'];
    return array_merge([
        'warn_pct' => '80', 'error_pct' => '95', 'strategy' => 'summarize',
        'keep_messages' => '6', 'price_in' => '0', 'price_out' => '0',
    ], $out);
}

/* ---------- stored settings (endpoint, key, model) ---------- */

function np_llm_get(): array {
    $r = np_one('SELECT endpoint, api_key, model, chat_model FROM llm_settings WHERE id = 1');
    if (!$r) return ['endpoint' => '', 'api_key' => '', 'model' => '', 'chat_model' => ''];
    return ['endpoint' => (string)$r['endpoint'], 'api_key' => (string)$r['api_key'],
            'model' => (string)$r['model'],
            // the chat may run on a different model than the video pipeline
            'chat_model' => (string)($r['chat_model'] ?? '')];
}

function np_llm_save(array $s): void {
    np_upsert('llm_settings',
        ['id' => 1, 'endpoint' => $s['endpoint'], 'api_key' => $s['api_key'],
         'model' => $s['model'],
         'chat_model' => (string)($s['chat_model'] ?? ''),
         'updated_at' => np_now()], ['id']);
}

/** A short, stable id for an endpoint so the same model on two endpoints
 *  does not collide. Model ids are NOT unique across providers. */
function np_endpoint_id(string $endpoint): string {
    $ep = rtrim(trim($endpoint), '/');
    if ($ep === '') return 'default';
    $host = parse_url($ep, PHP_URL_HOST) ?: $ep;
    $path = rtrim((string)(parse_url($ep, PHP_URL_PATH) ?: ''), '/');
    $base = $host . ($path === '' ? '' : $path);
    return substr(strtolower(preg_replace('/[^A-Za-z0-9._:\/-]+/', '-', $base)), 0, 180);
}

/** Try <ep>/models then <ep>/v1/models — people type the base URL many ways. */
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

/**
 * Compress a conversation into a handover note, keeping the system
 * instructions and the most recent messages intact.
 *
 * Returns ['ok'=>bool, 'summary'=>string, 'messages'=>array, 'usage'=>array].
 */
function np_compress_history(string $endpoint, string $key, string $model, array $messages, array $cfg = []): array {
    $lang = (string)($cfg['lang'] ?? 'fa');
    $keep = max(1, (int)($cfg['keep_messages'] ?? 6));

    $sys = [];
    $rest = [];
    foreach ($messages as $m) {
        if (($m['role'] ?? '') === 'system') $sys[] = $m; else $rest[] = $m;
    }
    if (count($rest) <= $keep) {
        return ['ok' => false, 'error' => 'not_enough_history', 'summary' => '', 'messages' => $messages, 'usage' => []];
    }
    $history = array_slice($rest, 0, count($rest) - $keep);
    $tail = array_slice($rest, -$keep);

    $transcript = '';
    foreach ($history as $m) {
        $role = (string)($m['role'] ?? 'user');
        $content = is_string($m['content'] ?? null) ? $m['content'] : json_encode($m['content'] ?? '');
        $transcript .= '[' . $role . '] ' . $content . "\n";
    }
    $req = [
        'model' => $model,
        'messages' => array_merge($sys, [[
            'role' => 'user',
            'content' => np_compress_prompt($lang) . "\n\n---\n" . $transcript . "\n---",
        ]]),
        'max_tokens' => (int)($cfg['max_tokens'] ?? 1200),
        'temperature' => 0.2,
    ];
    $r = np_provider_chat($endpoint, $key, $req, (int)($cfg['timeout'] ?? 180));
    if (!$r['ok']) return ['ok' => false, 'error' => $r['error'] ?? 'failed', 'summary' => '',
                          'messages' => $messages, 'usage' => $r['usage'] ?? []];
    $summary = trim((string)$r['content']);
    if ($summary === '') return ['ok' => false, 'error' => 'empty summary', 'summary' => '',
                                'messages' => $messages, 'usage' => $r['usage'] ?? []];
    $label = $lang === 'en' ? '[Compressed earlier conversation]' : '[خلاصهٔ گفتگوی پیشین]';
    $new = array_merge($sys, [[
        'role' => 'user',
        'content' => $label . "\n" . $summary,
    ]], $tail);
    return ['ok' => true, 'summary' => $summary, 'messages' => $new,
            'usage' => $r['usage'] ?? [], 'latency' => $r['latency'] ?? 0,
            'removed' => count($history)];
}
