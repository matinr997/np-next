# Account API contract (PHP) — consumed by assets/account-core.js

The dashboard works today from browser data. When the backend is ready,
implement these two endpoints; the UI switches to them automatically
(falls back to local data if they are missing or slow — 2.5s timeout).

## GET /api/account/me
```json
{ "user": { "name": "Sara", "email": "sara@example.com",
            "plan": "premium", "planExpires": "2027-02-01" } }
```

## GET /api/account/stats?from=YYYY-MM-DD&to=YYYY-MM-DD
```json
{ "stats": {
    "videos":  { "watched": 12, "bookmarked": 3, "threshold": 0.8 },
    "quiz":    { "answered": 40, "best": 32, "videos": 8, "history": [1735689600000] },
    "schedule":{ "planned": 16, "done": 5 },
    "sessions":{ "days": [{ "d": "2026-10-19", "v": 1 }], "streak": 3, "best": 9,
                 "lastSeen": "2026-10-19" }
} }
```
Tables used: users, video_progress, quiz_results, schedules, schedule_items.
Never send pass_hash to the browser. Payment state must come from the
`payments` table via the server, not from the client.
