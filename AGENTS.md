# AGENTS.md

## Project

Automates WeChat Read (微信读书) sessions via API calls. Python 3.10, no package manager, only `requests` + `urllib3` as dependencies.

## Files

- `main.py` — entrypoint. Runs the read loop, handles cookie refresh, calls push on completion.
- `config.py` — all configuration: headers, cookies, reading count, push tokens, book/chapter IDs, and a `data` template for the read request payload.
- `push.py` — push notification dispatch (pushplus, wxpusher, telegram, serverchan).
- `log_utils.py` — custom logging with in-place progress refresh.

## Running

```bash
python main.py
```

No tests, lint, typecheck, or formatter configured.

## Config

`config.py` values are overridden by env vars when present. In GitHub Actions, only env vars are used (secrets + vars). For local/Docker deployment, edit `config.py` directly.

Key env vars: `WXREAD_CURL_BASH`, `READ_NUM`, `PUSH_METHOD`, and the corresponding token vars for each push provider.

## Important constraints

- **Do not modify the `data` dict in `config.py`** (book `b`, chapter `c`, `appId`, etc.). It's tuned for "三体" and other books may not register reading time correctly.
- Each read iteration sleeps 30 seconds. `READ_NUM=40` = ~20 minutes.
- `config.py:convert()` parses a `curl_bash` command to extract headers and cookies. Supports both `-H 'Cookie: ...'` and `-b '...'` formats.
- Cookie refresh hits `/web/login/renewal` with 3 payload variants; fails hard if none return `wr_skey`.
- Push retries up to 5 times with 3–6 minute random backoff per attempt.
- Docker cron runs daily at 01:00 Beijing time (UTC 17:00).
