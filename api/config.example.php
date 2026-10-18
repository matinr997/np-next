<?php
// Copy this file to config.php and fill values from DirectAdmin > MySQL Management.
// config.php is blocked by .htaccess and never committed.
return [
  'db' => [
    'host'    => 'localhost',
    'name'    => 'USERNAME_nurseplus',
    'user'    => 'USERNAME_nurseplus',
    'pass'    => 'CHANGE_ME',
    'charset' => 'utf8mb4',
  ],
  'site' => [
    'ir'  => '/',
    'com' => '/com/',
  ],
  'debug' => true,
];
