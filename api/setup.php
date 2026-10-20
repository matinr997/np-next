<?php
// One-time setup: create the tables and the first admin.
// On Netafraz run once:  https://your-domain.ir/api/setup.php
// The admin credentials come from api/config.php ('admin' => email/password).
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';

$cfg = np_cfg();
$db  = $cfg['db'] ?? [];
$driver = strtolower((string)($db['driver'] ?? 'mysql'));

$schema = $driver === 'sqlite'
    ? __DIR__ . '/db/schema.sqlite.sql'
    : (__DIR__ . '/schema.mysql.sql');           // packaged next to the code
if ($driver !== 'sqlite' && !is_file($schema)) {
    $schema = __DIR__ . '/../docs/schema.sql';     // running from the repo
}

$out = ['ok' => true, 'driver' => $driver, 'schema' => basename((string)$schema)];
try {
    $out['statements'] = np_run_schema((string)$schema);
} catch (Throwable $e) {
    np_json(['ok' => false, 'error' => 'schema_failed', 'message' => $e->getMessage()], 500);
}
// A table that already existed does NOT get new columns from CREATE TABLE IF NOT EXISTS.
$out['migrated'] = np_migrate([
    'pipeline_jobs' => [
        'kind'       => "VARCHAR(16) NOT NULL DEFAULT 'video'",
        'title_fa'   => 'VARCHAR(255) NULL',
        'title_en'   => 'VARCHAR(255) NULL',
        'progress'   => 'TINYINT UNSIGNED NOT NULL DEFAULT 0',
        'log'        => 'TEXT NULL',
        'error'      => 'TEXT NULL',
        'channel'    => 'VARCHAR(120) NULL',
    ],
    'llm_settings' => [
        'endpoint' => "VARCHAR(255) NOT NULL DEFAULT ''",
        'api_key'  => "VARCHAR(255) NOT NULL DEFAULT ''",
        'model'    => "VARCHAR(190) NOT NULL DEFAULT ''",
    ],
    'llm_models' => [
        'owned_by' => "VARCHAR(120) NOT NULL DEFAULT ''",
    ],
]);

$admin = $cfg['admin'] ?? [];
$email = (string)($admin['email'] ?? '');
$pass  = (string)($admin['password'] ?? '');
if ($email !== '' && $pass !== '') {
    $exists = np_one('SELECT id FROM users WHERE email = ? LIMIT 1', [$email]);
    if (!$exists) {
        $id = np_id('u');
        np_q('INSERT INTO users (id, name, email, pass_hash, plan, role, created_at, updated_at)
              VALUES (?,?,?,?,?,?,?,?)',
             [$id, (string)($admin['name'] ?? 'Admin'), $email, password_hash($pass, PASSWORD_DEFAULT),
              'premium', 'admin', np_now(), np_now()]);
        $out['admin_created'] = $email;
    } else {
        $out['admin_exists'] = $email;
    }
} else {
    $out['admin_skipped'] = 'admin.email / admin.password not set in config.php';
}
np_json($out);
