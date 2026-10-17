"""Find ClinicalTrials.gov studies updated recently, for each condition in config/ct_conditions.csv.

Source: ClinicalTrials.gov API v2 (U.S. National Library of Medicine). Free, no key.

"Updated recently" means the study's Last Update Posted date is within the last
N days. That catches status changes, new results, new sites, date changes, etc.
It does not tell you WHAT changed; that needs the record's history page.

One JSON file per condition holds the full study records exactly as the API
returned them. We follow every page of results and check the total matches the
count the API reports, so nothing is silently cut off.
"""

import argparse
import csv
import json
import re
import time
from datetime import timedelta

from common import CONFIG_DIR, FetchError, fetch, run_main, run_stamp, save, utc_now

SCRIPT = "fetch_ctgov.py"
API_URL = "https://clinicaltrials.gov/api/v2/studies"
PAGE_SIZE = 100
SECONDS_BETWEEN_REQUESTS = 0.5


def read_conditions():
    with (CONFIG_DIR / "ct_conditions.csv").open() as f:
        rows = [r for r in csv.DictReader(f) if r.get("condition", "").strip()]
    if not rows:
        raise FetchError("config/ct_conditions.csv has no conditions; nothing to fetch")
    return rows


def fetch_condition(condition, since):
    params = {
        "query.cond": condition,
        "filter.advanced": f"AREA[LastUpdatePostDate]RANGE[{since},MAX]",
        "pageSize": PAGE_SIZE,
        "countTotal": "true",
    }
    studies, total, request_urls = [], None, []
    while True:
        time.sleep(SECONDS_BETWEEN_REQUESTS)
        resp = fetch(API_URL, params=params, expect_content_type="application/json")
        request_urls.append(resp.url)
        body = resp.json()
        if "studies" not in body:
            raise FetchError(f"{resp.url}: response has no 'studies' field")
        if total is None:
            total = body.get("totalCount")
        studies.extend(body["studies"])
        token = body.get("nextPageToken")
        if not token:
            break
        params["pageToken"] = token

    if total is not None and total != len(studies):
        raise FetchError(f"{condition!r}: API reported {total} studies but returned {len(studies)}")
    return studies, request_urls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7, help="look back this many days (default 7)")
    args = parser.parse_args()

    now = utc_now()
    since = (now - timedelta(days=args.days)).date().isoformat()
    for row in read_conditions():
        condition, trend = row["condition"].strip(), row.get("trend", "").strip()
        studies, request_urls = fetch_condition(condition, since)
        slug = re.sub(r"[^a-z0-9]+", "-", condition.lower()).strip("-")
        content = json.dumps({"condition": condition, "trend": trend, "last_update_posted_on_or_after": since,
                              "studies": studies}, indent=2).encode()
        save(SCRIPT, "ctgov", f"{run_stamp(now)}_{slug}.json", content, source_url=request_urls[0], now=now,
             extra={"publisher": "ClinicalTrials.gov (U.S. National Library of Medicine)",
                    "condition": condition, "trend": trend, "last_update_posted_on_or_after": since,
                    "study_count": len(studies), "request_urls": request_urls})


if __name__ == "__main__":
    run_main(SCRIPT, main)
