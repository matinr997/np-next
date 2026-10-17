# Nurse Plus — Unified Web App (IR + COM)

One codebase → two deployments:

| Variant   | Path   | Lang     | Currency    | Gateway         |
|-----------|--------|----------|-------------|-----------------|
| Iran      | `/`    | fa / RTL | Toman (IRT) | ZarinPal (stub) |
| International | `/com/` | en / LTR | USD      | Stripe (stub)   |

Demo unlock: add `?plan=premium` to either URL (session only, no payment).

- `lib/player-core.js` — auto-ported vanilla app logic (lazily fetches `/subs/{id}.json`).
- `lib/skeleton.js` — extracted static HTML shell.
- `assets/` — css, per-deployment boot scripts, pricing configs.
- Pages: `index.html` + `premium.html` (IR), `com/index.html` + `com/premium.html` (COM).

NOT included yet (needs a real server): user accounts, payments, admin.
