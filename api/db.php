<?php
// NursePlus API — PDO layer. MySQL on Netafraz, SQLite for local development.
declare(strict_types=1);
require_once __DIR__ . '/util.php';

function np_db(): PDO {
    static $pdo = null;
    if ($pdo instanceof PDO) return $pdo;
    $cfg = np_cfg();
    $db = $cfg['db'] ?? [];
    $driver = strtolower((string)($db['driver'] ?? 'mysql'));
    $opt = [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES   => false,
    ];
    if ($driver === 'sqlite') {
        $path = (string)($db['path'] ?? (__DIR__ . '/../.data/nurseplus.sqlite'));
        @mkdir(dirname($path), 0775, true);
        $pdo = new PDO('sqlite:' . $path, null, null, $opt);
        $pdo->exec('PRAGMA foreign_keys = ON');
        $pdo->exec('PRAGMA journal_mode = WAL');
    } else {
        $dsn = sprintf('mysql:host=%s;dbname=%s;charset=%s',
            (string)($db['host'] ?? 'localhost'), (string)($db['name'] ?? ''),
            (string)($db['charset'] ?? 'utf8mb4'));
        $pdo = new PDO($dsn, (string)($db['user'] ?? ''), (string)($db['pass'] ?? ''), $opt);
    }
    return $pdo;
}

function np_q(string $sql, array $args = []): PDOStatement {
    $st = np_db()->prepare($sql);
    $st->execute($args);
    return $st;
}
function np_all(string $sql, array $args = []): array { return np_q($sql, $args)->fetchAll(); }
function np_one(string $sql, array $args = []): ?array {
    $r = np_q($sql, $args)->fetch();
    return $r === false ? null : $r;
}
function np_val(string $sql, array $args = []) {
    $r = np_q($sql, $args)->fetch(PDO::FETCH_NUM);
    return $r === false ? null : $r[0];
}

/** Run a schema file, statement by statement. */
function np_run_schema(string $file): int {
    if (!is_file($file)) return 0;
    $sql = (string)file_get_contents($file);
    // Drop '--' comment lines FIRST: otherwise a chunk that merely starts with a
    // comment swallows the CREATE TABLE that follows it in the same chunk.
    $lines = [];
    foreach (explode("\n", $sql) as $ln) {
        $t = ltrim($ln);
        if ($t === '' || str_starts_with($t, '--')) continue;
        $lines[] = $ln;
    }
    $n = 0;
    foreach (array_filter(array_map('trim', explode(';', implode("\n", $lines)))) as $stmt) {
        if ($stmt === '') continue;
        np_db()->exec($stmt);
        $n++;
    }
    return $n;
}

/** Portable upsert (works on MySQL and SQLite — no dialect-specific syntax). */
function np_upsert(string $table, array $data, array $keys): void {
    $where = []; $args = [];
    foreach ($keys as $k) { $where[] = $k . ' = ?'; $args[] = $data[$k]; }
    $w = implode(' AND ', $where);
    $exists = (int)np_val('SELECT COUNT(*) FROM ' . $table . ' WHERE ' . $w, $args) > 0;
    if ($exists) {
        $set = []; $u = [];
        foreach ($data as $c => $v) {
            if (in_array($c, $keys, true)) continue;
            $set[] = $c . ' = ?'; $u[] = $v;
        }
        np_q('UPDATE ' . $table . ' SET ' . implode(', ', $set) . ' WHERE ' . $w, array_merge($u, $args));
    } else {
        $cols = array_keys($data);
        np_q('INSERT INTO ' . $table . ' (' . implode(', ', $cols) . ') VALUES ('
             . implode(', ', array_fill(0, count($cols), '?')) . ')', array_values($data));
    }
}

/**
 * Add columns that a newer schema version introduced.
 * CREATE TABLE IF NOT EXISTS never adds a column to an existing table, so an
 * upgraded deployment would otherwise fail with "no such column" forever.
 */
function np_migrate(array $wanted): array {
    $done = [];
    foreach ($wanted as $table => $cols) {
        $have = [];
        try {
            if (np_driver() === 'sqlite') {
                foreach (np_all('PRAGMA table_info(' . $table . ')') as $r) {
                    $have[] = (string)($r['name'] ?? '');
                }
            } else {
                foreach (np_all('SHOW COLUMNS FROM ' . $table) as $r) {
                    $have[] = (string)($r['Field'] ?? '');
                }
            }
        } catch (Throwable $e) {
            continue;                                   // table does not exist yet
        }
        foreach ($cols as $col => $def) {
            if (in_array($col, $have, true)) continue;
            try {
                np_db()->exec('ALTER TABLE ' . $table . ' ADD COLUMN ' . $col . ' ' . $def);
                $done[] = $table . '.' . $col;
            } catch (Throwable $e) {
                // already there, or a dialect that dislikes the default
            }
        }
    }
    return $done;
}

function np_driver(): string {
    $cfg = np_cfg();
    return strtolower((string)($cfg['db']['driver'] ?? 'mysql'));
}
