<?php
// GET  /api/auth.php -> {ok, user}
// POST /api/auth.php {action:'login', email, password} | {action:'logout'}
declare(strict_types=1);
require_once __DIR__ . '/util.php';
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/security.php';

$act = $_SERVER['REQUEST_METHOD'] === 'POST' ? np_str(np_body(), 'action') : '';

if ($act === 'login') {
    $b = np_body();
    $email = np_str($b, 'email');
    $pass  = np_str($b, 'password');
    if ($email === '' || $pass === '') {
        np_json(['ok' => false, 'error' => 'missing', 'message' => 'ایمیل و رمز را وارد کنید'], 400);
    }
    $u = np_one('SELECT id, name, email, pass_hash, role FROM users WHERE email = ? LIMIT 1', [$email]);
    if (!$u || !password_verify($pass, (string)$u['pass_hash'])) {
        np_json(['ok' => false, 'error' => 'bad_credentials', 'message' => 'ایمیل یا رمز اشتباه است'], 401);
    }
    if ((string)$u['role'] !== 'admin') {
        np_json(['ok' => false, 'error' => 'not_admin', 'message' => 'این حساب دسترسی ادمین ندارد'], 403);
    }
    np_session_start();
    session_regenerate_id(true);
    $_SESSION['admin_email'] = (string)$u['email'];
    $_SESSION['admin_name']  = (string)($u['name'] !== '' ? $u['name'] : $u['email']);
    np_json(['ok' => true, 'user' => ['email' => $u['email'], 'name' => $_SESSION['admin_name'], 'role' => 'admin'],
             'csrf' => np_csrf_token()]);
}

if ($act === 'logout') {
    np_session_start();
    $_SESSION = [];
    if (ini_get('session.use_cookies')) {
        $p = session_get_cookie_params();
        setcookie(session_name(), '', time() - 42000, $p['path'], $p['domain'], (bool)$p['secure'], (bool)$p['httponly']);
    }
    session_destroy();
    np_json(['ok' => true]);
}

$a = np_admin();
if (($_GET['action'] ?? '') === 'csrf') {
    // the panel needs a token before it may write anything
    np_json(['ok' => true, 'user' => $a, 'csrf' => np_csrf_token()]);
}
np_json(['ok' => true, 'user' => $a, 'csrf' => np_csrf_token()]);
