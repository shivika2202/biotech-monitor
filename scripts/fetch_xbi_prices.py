"""Download State Street's published NAV history file for XBI.

Source: State Street Global Advisors (the fund's manager). Free, no account or key.

Important: this is NAV (net asset value per share, computed by the fund from its
holdings at market close), NOT the exchange trading price. The two are usually
close but are not the same number. The sidecar file records this.
"""

import io
from datetime import datetime

import openpyxl

from common import XLSX_CONTENT_TYPE, FetchError, fetch, run_main, run_stamp, save, utc_now

SCRIPT = "fetch_xbi_prices.py"
URL = "https://www.ssga.com/us/en/intermediary/library-content/products/fund-data/etfs/us/navhist-us-en-xbi.xlsx"
EXPECTED_HEADER = ("Date", "NAV", "Shares Outstanding", "Total Net Assets")


def check_file(content):
    """Return (newest_date, oldest_date, row_count). Raise FetchError if the layout is off."""
    try:
        ws = openpyxl.load_workbook(io.BytesIO(content), read_only=True).active
        rows = [r for r in ws.iter_rows(values_only=True)]
    except Exception as e:
        raise FetchError(f"Downloaded file is not a readable spreadsheet: {e}") from e

    if rows[1][:2] != ("Ticker Symbol:", "XBI"):
        raise FetchError(f"Row 2 should identify XBI, found {rows[1][:2]}")

    header_index = next((i for i, r in enumerate(rows) if r[:len(EXPECTED_HEADER)] == EXPECTED_HEADER), None)
    if header_index is None:
        raise FetchError(f"Column headers changed; expected {EXPECTED_HEADER}")

    dates = []
    for r in rows[header_index + 1:]:
        if not r[0]:
            break
        try:
            dates.append(datetime.strptime(r[0], "%d-%b-%Y").date())
        except (TypeError, ValueError) as e:
            raise FetchError(f"Unexpected date value {r[0]!r} in NAV history") from e
        if not isinstance(r[1], (int, float)):
            raise FetchError(f"NAV for {r[0]} is not a number: {r[1]!r}")
    if not dates:
        raise FetchError("File has the right headers but no NAV rows")
    return max(dates).isoformat(), min(dates).isoformat(), len(dates)


def main():
    now = utc_now()
    resp = fetch(URL, expect_content_type=XLSX_CONTENT_TYPE)
    newest, oldest, count = check_file(resp.content)
    save(SCRIPT, "xbi_prices", f"{run_stamp(now)}_navhist-us-en-xbi.xlsx", resp.content,
         source_url=resp.url, now=now,
         extra={"publisher": "State Street Global Advisors",
                "measure": "NAV per share (not exchange trading price)",
                "newest_date": newest, "oldest_date": oldest, "nav_rows": count})


if __name__ == "__main__":
    run_main(SCRIPT, main)
