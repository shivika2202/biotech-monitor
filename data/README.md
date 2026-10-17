# data/

The scripts write here. Raw downloads are not committed (they are large and can be
regenerated); see `examples/` for real outputs from the 2026-10-17 run.

| Folder | Written by | Contents |
|---|---|---|
| `xbi_prices/` | `fetch_xbi_prices.py` | State Street XBI NAV history (.xlsx, as downloaded) |
| `xbi_holdings/` | `fetch_xbi_holdings.py` | State Street XBI daily holdings (.xlsx, as downloaded) |
| `ctgov/` | `fetch_ctgov.py` | Recently updated trials per condition (full API records) |
| `ctgov_snapshots/` | `track_ctgov_changes.py` | Catalyst-relevant fields for every watchlist-sponsored trial |
| `ctgov_changes/` | `track_ctgov_changes.py` | Field-level diff against the previous snapshot |
| `ctgov_watchlist/` | `filter_ctgov_watchlist.py` | Recently updated trials sponsored by watchlist companies |
| `sec_8k/` | `fetch_sec_8k.py` | Recent 8-K filings for watchlist tickers |
| `verification/` | `verify_claims.py` | Status of each claim in `config/claims.json` |
| `filing_notes/` | written by hand | One note per 8-K, quotes checked word for word (tracked) |
| `catalysts.csv`, `failures.csv` | digest agent | Dated events, each with source URL, source type and verified flag (tracked) |

Every data file has a `<name>.source.json` sidecar with the source URL, fetch time
(UTC) and SHA-256. Every fetch attempt, including failures, is appended to
`logs/fetch_log.jsonl`. Files are stamped `YYYY-MM-DDTHHMMZ_` and never overwritten.
