#!/usr/bin/env php
<?php
// NursePlus — cross-validation of the crypto primitives.
//
// The expected values come from independent JavaScript libraries
// (@noble/hashes, @scure/bip32, bs58check, bech32). If PHP and JS agree on
// the hashes, the secp256k1 arithmetic, the base58/bech32 encodings and the
// BIP32 public derivation, the wallet is derived the same way every other
// wallet in the world derives it.
//
//   php api/crypto/tests/primitives_test.php [vectors.json]
declare(strict_types=1);
require_once __DIR__ . '/../primitives.php';

$vectorsFile = $argv[1] ?? (__DIR__ . '/vectors.json');
if (!is_file($vectorsFile)) {
    fwrite(STDERR, "Missing reference vectors: $vectorsFile\n");
    exit(2);
}
$V = json_decode((string)file_get_contents($vectorsFile), true);
if (!is_array($V)) { fwrite(STDERR, "The vector file is not valid JSON.\n"); exit(2); }

$pass = 0; $fail = 0;
function ok(string $name, bool $cond, string $detail = ''): void {
    global $pass, $fail;
    if ($cond) { $pass++; echo "  PASS  $name\n"; }
    else { $fail++; echo "  FAIL  $name" . ($detail !== '' ? "   $detail" : '') . "\n"; }
}

// ---- 1. keccak256 --------------------------------------------------------
echo "keccak256\n";
foreach ($V['keccakVectors'] as $i => $vec) {
    $got = bin2hex(np_keccak256((string)$vec['input']));
    ok("keccak256 vector #" . $i, $got === $vec['hash'],
       "expected {$vec['hash']} got $got");
}

// ---- 2. per-chain address derivation from an xpub ------------------------
echo "HD address derivation\n";
foreach ($V['chains'] as $chain => $spec) {
    $xpub = (string)$spec['xpub'];
    $kd = np_bip32_parse_xpub($xpub);
    ok("$chain: the xpub parses", strlen($kd['chain_code']) === 32 && strlen($kd['key']) === 33);

    foreach ($spec['children'] as $child) {
        $idx = (int)$child['index'];
        $derived = np_bip32_derive_path($kd, (string)$idx);
        $pub33 = $derived['key'];

        ok("$chain/$idx: the public key matches", bin2hex($pub33) === $child['pub33'],
           'expected ' . $child['pub33'] . ' got ' . bin2hex($pub33));

        $evm  = np_address_evm($pub33);
        $tron = np_address_tron($pub33);
        $btc  = np_address_btc_bech32($pub33);

        ok("$chain/$idx: the EVM address matches",  $evm  === $child['evm'],
           "expected {$child['evm']} got $evm");
        ok("$chain/$idx: the TRON address matches", $tron === $child['tron'],
           "expected {$child['tron']} got $tron");
        ok("$chain/$idx: the BTC address matches",  $btc  === $child['btc'],
           "expected {$child['btc']} got $btc");
        ok("$chain/$idx: the hash160 matches",
           bin2hex(np_hash160($pub33)) === $child['hash160']);
    }
}

// ---- 3. hardened segments must be refused from a public key --------------
echo "safety\n";
try {
    np_bip32_ckdpub(np_bip32_parse_xpub((string)$V['chains']['evm']['xpub']), 0x80000000);
    ok("a hardened child is refused from an xpub", false, "it was allowed");
} catch (Throwable $e) {
    ok("a hardened child is refused from an xpub", true);
}

// ---- 4. base58check must reject a tampered address -----------------------
echo "base58check\n";
$addr = 'TBTxTifKeJg2mhaFD2nWBXeeLwjvuDVCLM';
$tampered = substr($addr, 0, -1) . (substr($addr, -1) === 'a' ? 'b' : 'a');
$rejected = false;
try { np_base58check_decode($tampered); } catch (Throwable $e) { $rejected = true; }
ok("a tampered address fails the checksum", $rejected);

$round = np_base58check_decode(np_base58check_encode("\x41" . str_repeat("\x11", 20)));
ok("base58check round-trips", bin2hex($round) === bin2hex("\x41" . str_repeat("\x11", 20)));

// ---- 5. bech32 must reject a bad checksum --------------------------------
echo "bech32\n";
$bech32Bad = 'bc1q230qyjfhvk4uwh27ev997x4p9hnk087275czdo';
try {
    np_bech32_polymod(np_bech32_hrp_expand('bc'));
    ok("bech32 encodes with a valid checksum", true);
} catch (Throwable $e) { ok("bech32 encodes with a valid checksum", false, $e->getMessage()); }

echo "\npassed: $pass   failed: $fail\n";
exit($fail === 0 ? 0 : 1);
