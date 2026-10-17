"""List recent 8-K and 8-K/A filings from SEC EDGAR for tickers in config/watchlist.csv.

Sources (both official SEC):
- https://www.sec.gov/files/company_tickers.json  maps ticker -> CIK (SEC company ID)
- https://data.sec.gov/submissions/CIK##########.json  each company's filing list

SEC rules: identify yourself in the User-Agent and stay under 10 requests/second.

Output is one JSON file listing the matching filings, each with a direct link to
the filing on sec.gov and the URL of the SEC record it came from. This is a
filtered extract, not the raw SEC response; the sidecar says so.
"""

import argparse
import csv
import json
import time
from datetime import timedelta

from common import CONFIG_DIR, FetchError, fetch, run_main, run_stamp, save, utc_now

SCRIPT = "fetch_sec_8k.py"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
FORMS = {"8-K", "8-K/A"}
SECONDS_BETWEEN_REQUESTS = 0.2  # 5 per second, half the SEC limit


def read_watchlist():
    with (CONFIG_DIR / "watchlist.csv").open() as f:
        tickers = [row["ticker"].strip().upper() for row in csv.DictReader(f) if row.get("ticker", "").strip()]
    if not tickers:
        raise FetchError("config/watchlist.csv has no tickers; nothing to fetch")
    return tickers


def load_cik_map():
    data = fetch(TICKERS_URL, expect_content_type="application/json").json()
    try:
        return {row["ticker"].upper(): (int(row["cik_str"]), row["title"]) for row in data.values()}
    except (KeyError, AttributeError, TypeError) as e:
        raise FetchError(f"company_tickers.json layout changed: {e}") from e


def recent_8ks(cik, since):
    url = SUBMISSIONS_URL.format(cik=cik)
    recent = fetch(url, expect_content_type="application/json").json().get("filings", {}).get("recent")
    needed = ("form", "filingDate", "accessionNumber", "primaryDocument", "items")
    if not recent or any(k not in recent for k in needed):
        raise FetchError(f"{url}: filing list missing expected fields {needed}")

    filings = []
    for form, filed, accession, doc, items in zip(*(recent[k] for k in needed)):
        if form in FORMS and filed >= since:
            filings.append({
                "form": form,
                "filing_date": filed,
                "accession_number": accession,
                "items": items.split(",") if items else [],
                "filing_url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{doc}",
                "source_record": url,
            })
    return filings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30, help="look back this many days (default 30)")
    parser.add_argument("--tickers", nargs="+", help="only these tickers (must already be in the watchlist)")
    args = parser.parse_args()

    now = utc_now()
    since = (now - timedelta(days=args.days)).date().isoformat()
    tickers = read_watchlist()
    if args.tickers:
        requested = [t.upper() for t in args.tickers]
        not_listed = [t for t in requested if t not in tickers]
        if not_listed:
            raise FetchError(f"Not in config/watchlist.csv: {not_listed}")
        tickers = requested
    cik_map = load_cik_map()

    unknown = [t for t in tickers if t not in cik_map]
    if unknown:
        raise FetchError(f"Tickers not found in SEC ticker list: {unknown}")

    companies = []
    for ticker in tickers:
        time.sleep(SECONDS_BETWEEN_REQUESTS)
        cik, name = cik_map[ticker]
        companies.append({"ticker": ticker, "cik": cik, "sec_name": name, "filings": recent_8ks(cik, since)})

    content = json.dumps({"filed_on_or_after": since, "forms": sorted(FORMS), "companies": companies},
                         indent=2).encode()
    save(SCRIPT, "sec_8k", f"{run_stamp(now)}_8k.json", content, source_url=TICKERS_URL, now=now,
         extra={"publisher": "U.S. Securities and Exchange Commission (EDGAR)",
                "note": "Filtered extract; each filing lists its own source_record URL",
                "filed_on_or_after": since, "tickers": tickers,
                "filing_count": sum(len(c["filings"]) for c in companies)})


if __name__ == "__main__":
    run_main(SCRIPT, main)
