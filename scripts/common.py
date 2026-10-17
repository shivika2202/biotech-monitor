"""Shared helpers for the fetch scripts.

Every fetch goes through `fetch()` and every saved file goes through `save()`,
so all scripts log the same way and fail the same way.

Rules this file enforces:
- Every attempt (success or failure) is appended to logs/fetch_log.jsonl.
- A failed or suspicious download raises FetchError and nothing is saved.
- Every saved data file gets a sidecar file "<name>.source.json" saying where
  it came from, when, and its SHA-256 fingerprint.
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = PROJECT_ROOT / "config"
LOG_FILE = PROJECT_ROOT / "logs" / "fetch_log.jsonl"

# SEC asks for a User-Agent naming a person and contact email. It is read from the
# environment (or a gitignored file) so no personal email lives in the code.
USER_AGENT_ENV = "SEC_USER_AGENT"
USER_AGENT_FILE = CONFIG_DIR / "user_agent.txt"
TIMEOUT_SECONDS = 60

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class FetchError(Exception):
    """A source was unavailable or returned something we can't trust."""


def utc_now():
    return datetime.now(timezone.utc)


def run_stamp(now):
    """Filename prefix like 2026-10-15T1430Z, so same-day runs never collide."""
    return now.strftime("%Y-%m-%dT%H%MZ")


def user_agent():
    """Return the User-Agent string, e.g. "Jane Doe jane@example.com". Raise FetchError if unset."""
    value = os.environ.get(USER_AGENT_ENV, "").strip()
    if not value and USER_AGENT_FILE.exists():
        value = USER_AGENT_FILE.read_text().strip()
    if "@" not in value:
        raise FetchError(f"No contact User-Agent set. SEC requires one: export {USER_AGENT_ENV}="
                         f"'Your Name you@example.com' or put that line in config/user_agent.txt")
    return value


def log_event(script, **fields):
    """Append one line to the fetch log and echo it to the terminal."""
    entry = {"logged_at_utc": utc_now().isoformat(timespec="seconds"), "script": script, **fields}
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    print(json.dumps(entry, indent=2))


def fetch(url, *, params=None, expect_content_type=None):
    """GET a URL. Raise FetchError on anything other than a clean 200.

    `expect_content_type` guards against sites that answer "200 OK" with an HTML
    error page instead of the file we asked for.
    """
    headers = {"User-Agent": user_agent(), "Accept-Encoding": "gzip, deflate"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as e:
        raise FetchError(f"Could not reach {url}: {type(e).__name__}: {e}") from e

    content_type = resp.headers.get("Content-Type", "")
    problem = None
    if resp.status_code != 200:
        problem = f"HTTP {resp.status_code}"
    elif expect_content_type and expect_content_type not in content_type:
        problem = f"expected content type {expect_content_type!r}, got {content_type!r}"
    elif not resp.content:
        problem = "empty response body"

    if problem:
        raise FetchError(f"{resp.url}: {problem}")
    return resp


def save(script, subdir, filename, content, *, source_url, now, extra=None):
    """Write raw bytes to data/<subdir>/<filename> plus a .source.json sidecar.

    Refuses to overwrite an existing file.
    """
    out_dir = DATA_DIR / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    if path.exists():
        raise FetchError(f"{path} already exists; refusing to overwrite")

    sha256 = hashlib.sha256(content).hexdigest()
    path.write_bytes(content)

    provenance = {
        "source_url": source_url,
        "fetched_at_utc": now.isoformat(timespec="seconds"),
        "fetched_by": f"scripts/{script}",
        "bytes": len(content),
        "sha256": sha256,
        **(extra or {}),
    }
    sidecar = path.with_name(path.name + ".source.json")
    sidecar.write_text(json.dumps(provenance, indent=2) + "\n")

    log_event(script, status="OK", url=source_url, output=str(path.relative_to(PROJECT_ROOT)),
              bytes=len(content), sha256=sha256, **(extra or {}))
    return path


def run_main(script, main):
    """Run a script's main(); on FetchError log it, print a loud message and exit 1."""
    try:
        main()
    except FetchError as e:
        log_event(script, status="FAILED", error=str(e))
        print(f"\nFETCH FAILED ({script}): {e}", file=sys.stderr)
        sys.exit(1)
