<?php
// Copy this file to config.php and fill values from DirectAdmin > MySQL Management.
// config.php is blocked by .htaccess and never committed.
//
// driver: 'mysql' in production. Use 'sqlite' only for local development
//         (driver=sqlite + path=...); it needs no server at all.
return [
  'db' => [
    'driver'  => 'mysql',                  // mysql | sqlite
    'host'    => 'localhost',
    'name'    => 'USERNAME_nurseplus',
    'user'    => 'USERNAME_nurseplus',
    'pass'    => 'CHANGE_ME',
    'charset' => 'utf8mb4',
    // 'path' => __DIR__ . '/../.data/nurseplus.sqlite',   // sqlite only
  ],

  // The first admin account. api/setup.php creates it once, then this
  // section can be emptied — the password is stored hashed, never in clear.
  'admin' => [
    'email'    => 'you@example.com',
    'password' => 'CHANGE_ME_STRONG',
    'name'     => 'Admin',
  ],

  // Shared secret for headless workers (scripts/pipeline_worker.py).
  // The worker sends it as the X-Worker-Token header.
  // Generate:  php -r "echo bin2hex(random_bytes(32)), PHP_EOL;"
  'worker_token' => 'CHANGE_ME',

  'site' => [
    'ir'  => '/',
    'com' => '/com/',
  ],
  'debug' => false,
];
