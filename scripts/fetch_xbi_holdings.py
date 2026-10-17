"""Download State Street's published daily holdings file for XBI.

Source: State Street Global Advisors (the fund's manager).
The file is saved exactly as downloaded. Before saving we open it and check
that the layout is what we expect, and record the "As of" date printed inside.
"""

import io
import re

import openpyxl

from common import XLSX_CONTENT_TYPE, FetchError, fetch, run_main, run_stamp, save, utc_now

SCRIPT = "fetch_xbi_holdings.py"
URL = "https://www.ssga.com/us/en/intermediary/library-content/products/fund-data/etfs/us/holdings-daily-us-en-xbi.xlsx"
EXPECTED_HEADER = ("Name", "Ticker", "Identifier", "SEDOL", "Weight", "Sector", "Shares Held", "Local Currency")


def check_file(content):
    """Return (as_of_text, holding_count). Raise FetchError if the layout is off."""
    try:
        ws = openpyxl.load_workbook(io.BytesIO(content), read_only=True).active
        rows = [r for r in ws.iter_rows(values_only=True)]
    except Exception as e:
        raise FetchError(f"Downloaded file is not a readable spreadsheet: {e}") from e

    if rows[1][:2] != ("Ticker Symbol:", "XBI"):
        raise FetchError(f"Row 2 should identify XBI, found {rows[1][:2]}")

    match = re.fullmatch(r"As of (\d{2}-\w{3}-\d{4})", str(rows[2][1]))
    if rows[2][0] != "Holdings:" or not match:
        raise FetchError(f"Could not find the 'As of' date in row 3, found {rows[2][:2]}")

    header_index = next((i for i, r in enumerate(rows) if r[:len(EXPECTED_HEADER)] == EXPECTED_HEADER), None)
    if header_index is None:
        raise FetchError(f"Column headers changed; expected {EXPECTED_HEADER}")

    # Holdings are the rows after the header with a name in column A, up to the first blank row.
    count = 0
    for r in rows[header_index + 1:]:
        if not r[0]:
            break
        count += 1
    if count == 0:
        raise FetchError("File has the right headers but no holdings rows")
    return match.group(1), count


def main():
    now = utc_now()
    resp = fetch(URL, expect_content_type=XLSX_CONTENT_TYPE)
    as_of, count = check_file(resp.content)
    save(SCRIPT, "xbi_holdings", f"{run_stamp(now)}_holdings-daily-us-en-xbi.xlsx", resp.content,
         source_url=resp.url, now=now,
         extra={"publisher": "State Street Global Advisors",
                "holdings_as_of": as_of, "holding_rows": count})


if __name__ == "__main__":
    run_main(SCRIPT, main)
