<?php
// NursePlus API health check — your backend endpoint lives here later.
header('Content-Type: application/json; charset=utf-8');
echo json_encode([
  'ok'      => true,
  'service' => 'nurseplus-api',
  'php'     => PHP_VERSION,
  'time'    => date('c'),
], JSON_UNESCAPED_UNICODE);
