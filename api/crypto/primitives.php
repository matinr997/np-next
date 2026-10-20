<?php
// NursePlus — crypto primitives (pure PHP, no Composer/extension dependency).
//
// Everything here is deterministic maths: hashing, base58/bech32 encoding and
// secp256k1 point arithmetic. No network, no secrets.
//
// Why pure PHP: the Netafraz shared plan cannot run Composer at deploy time
// and the PHP build there has a small extension set. GMP and hash() are
// enough for everything this gateway needs.
//
// A private key NEVER enters this file's callers. The public web app derives
// addresses from an extended PUBLIC key (xpub); spending needs the seed and
// lives in a separate offline signer. See api/crypto/wallet.php.
declare(strict_types=1);

if (!extension_loaded('gmp')) {
    // The gateway refuses to run rather than silently mis-deriving addresses.
    throw new RuntimeException('The PHP GMP extension is required for the crypto gateway.');
}

/* ======================================================================
 * 1. Hashing
 * ==================================================================== */

/** Keccak-256 (the pre-NIST padding used by Ethereum). NOT sha3-256. */
function np_keccak256(string $msg): string
{
    $rate = 136;                       // 1088 bits for Keccak-256
    $len  = strlen($msg);
    $pad  = $rate - ($len % $rate);

    if ($pad === 1) {
        $msg .= "\x81";                // 0x01 | 0x80 in one byte
    } else {
        $msg .= str_repeat("\x00", $pad - 2) . "\x01" . "\x80";
    }

    // state: 25 lanes of 64 bits, lane index = x + 5*y
    $A = array_fill(0, 25, gmp_init(0));
    $mod = gmp_pow(2, 64);                       // the lane modulus is 2^64

    // absorb
    $blocks = strlen($msg) / $rate;
    for ($b = 0; $b < $blocks; $b++) {
        $chunk = substr($msg, $b * $rate, $rate);
        for ($i = 0; $i < $rate / 8; $i++) {
            $lane = gmp_init(bin2hex(strrev(substr($chunk, $i * 8, 8))), 16);
            $A[$i] = gmp_xor($A[$i], $lane);
        }
        $A = np_keccak_f1600($A, $mod);
    }

    // squeeze: 32 bytes = 4 lanes, little-endian
    $out = '';
    for ($i = 0; $i < 4; $i++) {
        // a lane shorter than 16 hex chars must be zero-padded on the LEFT
        // before the byte reversal, or the byte order breaks.
        $lane = str_pad(gmp_strval($A[$i], 16), 16, '0', STR_PAD_LEFT);
        $out .= strrev($lane);
    }
    return hex2bin($out);
}

/** The Keccak-f[1600] permutation. $mod is 2^64 (the lane modulus). */
function np_keccak_f1600(array $A, $GmpMod): array
{
    static $RC = [
        '0000000000000001', '0000000000008082', '800000000000808a', '8000000080008000',
        '000000000000808b', '0000000080000001', '8000000080008081', '8000000000008009',
        '000000000000008a', '0000000000000088', '0000000080008009', '000000008000000a',
        '000000008000808b', '800000000000008b', '8000000000008089', '8000000000008003',
        '8000000000008002', '8000000000000080', '000000000000800a', '800000008000000a',
        '8000000080008081', '8000000000008080', '0000000080000001', '8000000080008008',
    ];
    static $R = [
        [0, 36, 3, 41, 18],
        [1, 44, 10, 45, 2],
        [62, 6, 43, 15, 61],
        [28, 55, 25, 21, 56],
        [27, 20, 39, 8, 14],
    ];

    $one = gmp_init(1);
    $notMask = gmp_sub(gmp_pow(2, 64), 1);     // the 64-bit all-ones mask

    for ($round = 0; $round < 24; $round++) {
        // ---- theta
        $C = [];
        for ($x = 0; $x < 5; $x++) {
            $C[$x] = gmp_xor(gmp_xor($A[$x], $A[$x + 5]),
                      gmp_xor($A[$x + 10], gmp_xor($A[$x + 15], $A[$x + 20])));
        }
        $D = [];
        for ($x = 0; $x < 5; $x++) {
            $D[$x] = gmp_xor($C[($x + 4) % 5], np_keccak_rotl($C[($x + 1) % 5], 1, $GmpMod));
        }
        for ($y = 0; $y < 5; $y++) {
            for ($x = 0; $x < 5; $x++) {
                $A[$x + 5 * $y] = gmp_xor($A[$x + 5 * $y], $D[$x]);
            }
        }

        // ---- rho + pi
        // $R is row-major as r[x][y] (the Keccak reference layout), and
        // A[x + 5*y] is the lane A[x][y].
        $B = array_fill(0, 25, null);
        for ($y = 0; $y < 5; $y++) {
            for ($x = 0; $x < 5; $x++) {
                $B[$y + 5 * ((2 * $x + 3 * $y) % 5)] = np_keccak_rotl($A[$x + 5 * $y], $R[$x][$y], $GmpMod);
            }
        }

        // ---- chi
        for ($y = 0; $y < 5; $y++) {
            for ($x = 0; $x < 5; $x++) {
                $b1 = $B[($x + 1) % 5 + 5 * $y];
                $b2 = $B[($x + 2) % 5 + 5 * $y];
                // ~b1 within 64 bits (GMP has no gmp_complement, and its
                // complement would be a negative number).
                $notB1 = gmp_sub($notMask, $b1);
                $A[$x + 5 * $y] = gmp_xor($B[$x + 5 * $y], gmp_and($notB1, $b2));
            }
        }

        // ---- iota
        $A[0] = gmp_xor($A[0], gmp_init($RC[$round], 16));
    }
    return $A;
}

/** 64-bit left rotation on a GMP integer. */
function np_keccak_rotl($x, int $n, $maskPlusOne)
{
    if ($n === 0) return $x;
    $left  = gmp_mod(gmp_mul($x, gmp_pow(2, $n)), $maskPlusOne);
    $right = gmp_div_r($x, gmp_pow(2, 64 - $n));
    return gmp_mod(gmp_add($left, $right), $maskPlusOne);
}

/** Raw binary digests (not hex) — the encoders below need the bytes. */
function np_sha256(string $s): string { return hash('sha256', $s, false); }
function np_ripemd160(string $s): string { return hash('ripemd160', $s, false); }
function np_hash160(string $s): string { return np_ripemd160(np_sha256($s)); }

/* ======================================================================
 * 2. Base58 / Base58Check
 * ==================================================================== */

function np_base58_encode(string $bin): string
{
    $alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
    $n = gmp_init(0);
    for ($i = 0, $m = strlen($bin); $i < $m; $i++) {
        $n = gmp_add(gmp_mul($n, 256), ord($bin[$i]));
    }
    $out = '';
    while (gmp_cmp($n, 0) > 0) {
        $q = gmp_div_q($n, 58);
        $r = gmp_intval(gmp_sub($n, gmp_mul($q, 58)));
        $out = $alphabet[$r] . $out;
        $n = $q;
    }
    for ($i = 0, $m = strlen($bin); $i < $m && $bin[$i] === "\x00"; $i++) {
        $out = '1' . $out;
    }
    return $out === '' ? '1' : $out;
}

function np_base58_decode(string $str): string
{
    $alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
    $n = gmp_init(0);
    for ($i = 0, $m = strlen($str); $i < $m; $i++) {
        $p = strpos($alphabet, $str[$i]);
        if ($p === false) throw new RuntimeException('Bad base58 character.');
        $n = gmp_add(gmp_mul($n, 58), $p);
    }
    $out = '';
    while (gmp_cmp($n, 0) > 0) {
        $q = gmp_div_q($n, 256);
        $r = gmp_intval(gmp_sub($n, gmp_mul($q, 256)));
        $out = chr($r) . $out;
        $n = $q;
    }
    for ($i = 0, $m = strlen($str); $i < $m && $str[$i] === '1'; $i++) {
        $out = "\x00" . $out;
    }
    return $out;
}

/** Base58Check: payload + 4 bytes of double-SHA256 checksum. */
function np_base58check_encode(string $payload): string
{
    $chk = substr(np_sha256(np_sha256($payload)), 0, 4);
    return np_base58_encode($payload . $chk);
}

function np_base58check_decode(string $str): string
{
    $raw = np_base58_decode($str);
    if (strlen($raw) < 5) throw new RuntimeException('Base58Check payload is too short.');
    $payload = substr($raw, 0, -4);
    $chk     = substr($raw, -4);
    if (!hash_equals(substr(np_sha256(np_sha256($payload)), 0, 4), $chk)) {
        throw new RuntimeException('Base58Check checksum mismatch.');
    }
    return $payload;
}

/* ======================================================================
 * 3. Bech32 (BIP-173) — Bitcoin native segwit addresses
 * ==================================================================== */

function np_bech32_encode(string $hrp, array $data): string
{
    $charset = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l';
    $values  = [];
    foreach ($data as $d) {
        $v = gmp_intval($d);
        $acc = 0; $bits = 0; $out = [];
        for ($i = 0; $i < 5; $i++) {           // 5-bit groups
            $acc = ($acc << 1) | (($v >> $i) & 1);
            $bits++;
            if ($bits === 5) { $out[] = $acc; $acc = 0; $bits = 0; }
        }
        if ($bits > 0) $out[] = ($acc << (5 - $bits)) & 31;
        $values = array_merge($values, $out);
    }
    $values = array_merge($values, [0]);
    $polymod = np_bech32_polymod(array_merge(np_bech32_hrp_expand($hrp), $values)) ^ 1;
    $checksum = [];
    for ($i = 0; $i < 6; $i++) $checksum[] = ($polymod >> (5 * (5 - $i))) & 31;
    $all = array_merge($values, $checksum);
    $out = $hrp . '1';
    foreach ($all as $d) $out .= $charset[$d];
    return $out;
}

function np_bech32_hrp_expand(string $hrp): array
{
    $out = [];
    $len = strlen($hrp);
    for ($i = 0; $i < $len; $i++) $out[] = ord($hrp[$i]) >> 5;
    $out[] = 0;
    for ($i = 0; $i < $len; $i++) $out[] = ord($hrp[$i]) & 31;
    return $out;
}

function np_bech32_polymod(array $values): int
{
    $gen = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3];
    $chk = 1;
    foreach ($values as $v) {
        $b = ($chk >> 25);
        $chk = (($chk & 0x1ffffff) << 5) ^ $v;
        for ($i = 0; $i < 5; $i++) {
            if (($b >> $i) & 1) $chk ^= $gen[$i];
        }
    }
    return $chk & 0xffffffff;
}

/** Convert an 8-bit value into 5-bit groups (the bech32 data payload). */
function np_convert_bits(array $data, int $fromBits, int $toBits, bool $pad = true): array
{
    $acc = 0; $bits = 0; $out = []; $maxv = (1 << $toBits) - 1;
    foreach ($data as $value) {
        $value = (int)$value;
        if ($value < 0 || ($value >> $fromBits) !== 0) {
            throw new RuntimeException('convert_bits: value out of range.');
        }
        $acc = ($acc << $fromBits) | $value;
        $bits += $fromBits;
        while ($bits >= $toBits) {
            $bits -= $toBits;
            $out[] = ($acc >> $bits) & $maxv;
        }
    }
    if ($pad) {
        if ($bits > 0) $out[] = ($acc << ($toBits - $bits)) & $maxv;
    } elseif ($bits >= $fromBits || ((($acc << ($toBits - $bits)) & $maxv) !== 0)) {
        throw new RuntimeException('convert_bits: invalid padding.');
    }
    return $out;
}

/* ======================================================================
 * 4. secp256k1
 * ==================================================================== */

function np_secp_p(): string { return gmp_init('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F', 16); }
function np_secp_n(): string { return gmp_init('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141', 16); }
function np_secp_gx(): string { return gmp_init('79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798', 16); }
function np_secp_gy(): string { return gmp_init('483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8', 16); }

/** Jacobian point: [X, Y, Z]; Z = 0 means the point at infinity. */
function np_secp_inf(): array { return [gmp_init(0), gmp_init(1), gmp_init(0)]; }

function np_secp_double(array $p): array
{
    [$X1, $Y1, $Z1] = $p;
    if (gmp_cmp($Y1, 0) === 0 || gmp_cmp($Z1, 0) === 0) return np_secp_inf();
    $pm = np_secp_p();

    $A = gmp_mod(gmp_mul($X1, $X1), $pm);
    $B = gmp_mod(gmp_mul($Y1, $Y1), $pm);
    $C = gmp_mod(gmp_mul($B, $B), $pm);
    $t = gmp_mod(gmp_add($X1, $B), $pm);
    $t = gmp_mod(gmp_mul($t, $t), $pm);
    $D = gmp_mod(gmp_sub(gmp_sub($t, $A), $C), $pm);
    $D = gmp_mod(gmp_mul($D, 2), $pm);
    $E = gmp_mod(gmp_mul($A, 3), $pm);
    $F = gmp_mod(gmp_mul($E, $E), $pm);
    $X3 = gmp_mod(gmp_sub($F, gmp_mul($D, 2)), $pm);
    $Y3 = gmp_mod(gmp_sub(gmp_mul($E, gmp_sub($D, $X3)), gmp_mul($C, 8)), $pm);
    $Z3 = gmp_mod(gmp_mul(gmp_mul($Y1, 2), $Z1), $pm);
    return [$X3, $Y3, $Z3];
}

function np_secp_add(array $p, array $q): array
{
    [$X1, $Y1, $Z1] = $p;
    [$X2, $Y2, $Z2] = $q;
    if (gmp_cmp($Z1, 0) === 0) return $q;
    if (gmp_cmp($Z2, 0) === 0) return $p;
    $pm = np_secp_p();

    $Z1Z1 = gmp_mod(gmp_mul($Z1, $Z1), $pm);
    $Z2Z2 = gmp_mod(gmp_mul($Z2, $Z2), $pm);
    $U1   = gmp_mod(gmp_mul($X1, $Z2Z2), $pm);
    $U2   = gmp_mod(gmp_mul($X2, $Z1Z1), $pm);
    $S1   = gmp_mod(gmp_mul($Y1, gmp_mul($Z2, $Z2Z2)), $pm);
    $S2   = gmp_mod(gmp_mul($Y2, gmp_mul($Z1, $Z1Z1)), $pm);

    if (gmp_cmp($U1, $U2) === 0) {
        if (gmp_cmp($S1, $S2) !== 0) return np_secp_inf();
        return np_secp_double($p);
    }

    $H = gmp_mod(gmp_sub($U2, $U1), $pm);
    $I = gmp_mod(gmp_mul(gmp_mod(gmp_mul($H, 2), $pm), gmp_mod(gmp_mul($H, 2), $pm)), $pm);
    $J = gmp_mod(gmp_mul($H, $I), $pm);
    $r = gmp_mod(gmp_mul(gmp_sub($S2, $S1), 2), $pm);
    $V = gmp_mod(gmp_mul($U1, $I), $pm);

    $X3 = gmp_mod(gmp_sub(gmp_sub(gmp_mul($r, $r), $J), gmp_mul($V, 2)), $pm);
    $Y3 = gmp_mod(gmp_sub(gmp_mul($r, gmp_sub($V, $X3)), gmp_mul($S1, $J)), $pm);
    $Z3 = gmp_mod(gmp_mul(gmp_sub(gmp_sub(gmp_mod(gmp_mul(gmp_add($Z1, $Z2), gmp_add($Z1, $Z2)), $pm), $Z1Z1), $Z2Z2), $H), $pm);
    return [$X3, $Y3, $Z3];
}

/** Scalar multiplication (double-and-add, left to right). */
function np_secp_mul(array $p, $k): array
{
    $k = gmp_mod($k, np_secp_n());
    if (gmp_cmp($k, 0) === 0) return np_secp_inf();
    $acc = np_secp_inf();
    $bits = gmp_strval($k, 16);
    $bits = str_pad($bits, strlen($bits) * 2, '0', STR_PAD_LEFT);
    for ($i = 0, $m = strlen($bits); $i < $m; $i++) {
        $acc = np_secp_double($acc);
        if ($bits[$i] === '1') $acc = np_secp_add($acc, $p);
    }
    return $acc;
}

/** Convert a Jacobian point back to affine [X, Y]. */
function np_secp_to_affine(array $p): array
{
    [$X, $Y, $Z] = $p;
    if (gmp_cmp($Z, 0) === 0) throw new RuntimeException('Point at infinity has no affine form.');
    $pm = np_secp_p();
    $zi  = gmp_invert($Z, $pm);
    $zi2 = gmp_mod(gmp_mul($zi, $zi), $pm);
    $zi3 = gmp_mod(gmp_mul($zi2, $zi), $pm);
    return [gmp_mod(gmp_mul($X, $zi2), $pm), gmp_mod(gmp_mul($Y, $zi3), $pm)];
}

/** 33-byte compressed public key from a private key (dev/signer tooling only). */
function np_secp_pubkey_from_private(string $priv32): string
{
    $k = gmp_init(bin2hex($priv32), 16);
    if (gmp_cmp($k, 0) === 0 || gmp_cmp($k, np_secp_n()) >= 0) {
        throw new RuntimeException('Private key out of range.');
    }
    $G = [np_secp_gx(), np_secp_gy(), gmp_init(1)];
    [$X, $Y] = np_secp_to_affine(np_secp_mul($G, $k));
    return np_secp_compress($X, $Y);
}

function np_secp_compress($X, $Y): string
{
    $prefix = (gmp_intval(gmp_mod($Y, 2)) === 0) ? "\x02" : "\x03";
    return $prefix . str_pad(gmp_strval($X, 16), 64, '0', STR_PAD_LEFT);
}

/** 65-byte uncompressed public key (EVM / TRON use it). */
function np_secp_uncompressed(string $pub33): string
{
    $prefix = $pub33[0];
    $x = gmp_init(bin2hex(substr($pub33, 1, 32)), 16);
    $pm = np_secp_p();
    $y2 = gmp_mod(gmp_sub(gmp_mod(gmp_mul($x, $x), $pm), 3), $pm);
    $y  = gmp_intval(gmp_powm($y2, gmp_div_q(gmp_add($pm, 1), 4), $pm));
    $y  = gmp_powm($y2, gmp_div_q(gmp_add($pm, 1), 4), $pm);
    if (gmp_cmp(gmp_mod(gmp_mul($y, $y), $pm), $y2) !== 0) {
        throw new RuntimeException('Public key is not on the curve.');
    }
    if ((gmp_intval(gmp_mod($y, 2)) === 0) !== ($prefix === "\x02")) {
        $y = gmp_sub($pm, $y);
    }
    return "\x04" . str_pad(gmp_strval($x, 16), 64, '0', STR_PAD_LEFT)
                . str_pad(gmp_strval($y, 16), 64, '0', STR_PAD_LEFT);
}

/* ======================================================================
 * 5. BIP32 — public (CKDpub) derivation from an xpub
 * ==================================================================== */

/** Parse a base58 xpub into its parts. */
function np_bip32_parse_xpub(string $xpub): array
{
    $raw = np_base58check_decode($xpub);
    if (strlen($raw) !== 78) throw new RuntimeException('An extended public key is 78 bytes.');
    return [
        'version'    => substr($raw, 0, 4),
        'depth'      => ord($raw[4]),
        'fingerprint'=> substr($raw, 5, 4),
        'child_num'  => substr($raw, 9, 4),
        'chain_code' => substr($raw, 13, 32),
        'key'        => substr($raw, 45, 33),
    ];
}

/** Public child derivation: K_par, c_par, index -> K_i, c_i. */
function np_bip32_ckdpub(array $kd, int $index): array
{
    if ($index >= 0x80000000) {
        throw new RuntimeException('A hardened child cannot be derived from a public key.');
    }
    $chain = $kd['chain_code'];
    $pub   = $kd['key'];

    for ($i = $index; $i < 0x80000000; $i++) {
        $data = $pub . pack('N', $i);
        $I    = hash_hmac('sha512', $data, $chain, true);
        $IL   = substr($I, 0, 32);
        $IR   = substr($I, 32, 32);
        if (gmp_cmp(gmp_init(bin2hex($IL), 16), np_secp_n()) >= 0) continue;

        $X = gmp_init(bin2hex(substr($pub, 1, 32)), 16);
        $yParity = (gmp_intval(gmp_mod(gmp_init(bin2hex(substr($pub, 1, 32)), 16), 2)) === 0) ? 0 : 1;
        // recover Y from the curve for the parent point
        $pm = np_secp_p();
        $y2 = gmp_mod(gmp_sub(gmp_mod(gmp_mul($X, $X), $pm), 3), $pm);
        $Y = gmp_powm($y2, gmp_div_q(gmp_add($pm, 1), 4), $pm);
        if (gmp_intval(gmp_mod($Y, 2)) !== $yParity) $Y = gmp_sub($pm, $Y);

        $parent = [$X, $Y, gmp_init(1)];
        $tweak  = np_secp_mul([np_secp_gx(), np_secp_gy(), gmp_init(1)],
                              gmp_init(bin2hex($IL), 16));
        $child  = np_secp_add($parent, $tweak);
        if (gmp_cmp($child[2], 0) === 0) continue;

        [$cx, $cy] = np_secp_to_affine($child);
        $newPub = np_secp_compress($cx, $cy);
        $fingerprint = substr(np_hash160($pub), 0, 4);
        return [
            'version'     => $kd['version'],
            'depth'       => $kd['depth'] + 1,
            'fingerprint' => $fingerprint,
            'child_num'   => pack('N', $i),
            'chain_code'  => $IR,
            'key'         => $newPub,
        ];
    }
    throw new RuntimeException('No valid child key found.');
}

/** Parse a derivation path such as m/44'/195'/0'/0 into the index list. */
function np_bip32_path(string $path): array
{
    $parts = explode('/', trim($path));
    $out = [];
    foreach ($parts as $p) {
        if ($p === '' || $p === 'm') continue;
        $hard = false;
        if (substr($p, -1) === "'" || strtolower(substr($p, -1)) === 'h') {
            $hard = true;
            $p = substr($p, 0, -1);
        }
        $n = (int)$p;
        if ((string)$n !== ltrim($p, '+')) {
            throw new RuntimeException('Bad derivation path segment: ' . $p);
        }
        $out[] = $hard ? ($n + 0x80000000) : $n;
    }
    return $out;
}

/** Derive a child public key by a full path (non-hardened segments only). */
function np_bip32_derive_path(array $kd, string $path): array
{
    foreach (np_bip32_path($path) as $idx) {
        $kd = np_bip32_ckdpub($kd, $idx);
    }
    return $kd;
}

/* ======================================================================
 * 6. Address encoders
 * ==================================================================== */

/** EVM: 0x + the last 20 bytes of keccak256 of the uncompressed key. */
function np_address_evm(string $pub33): string
{
    $uncompressed = np_secp_uncompressed($pub33);
    $hash = np_keccak256(substr($uncompressed, 1));   // drop the 0x04 tag
    return '0x' . bin2hex(substr($hash, 12));
}

/** TRON: base58check(0x41 || the last 20 bytes of keccak256). */
function np_address_tron(string $pub33): string
{
    $uncompressed = np_secp_uncompressed($pub33);
    $hash = np_keccak256(substr($uncompressed, 1));
    return np_base58check_encode("\x41" . substr($hash, 12));
}

/** Bitcoin native segwit v0: bech32(hrp, [witnessVersion, program]). */
function np_address_btc_bech32(string $pub33, string $hrp = 'bc'): string
{
    $program = np_hash160($pub33);
    $data = np_convert_bits(array_values(unpack('C*', $program)), 8, 5);
    array_unshift($data, 0);                          // witness version 0
    return np_bech32_encode($hrp, $data);
}
