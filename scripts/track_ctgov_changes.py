"""Track what changed in ClinicalTrials.gov records for watchlist companies.

The ClinicalTrials.gov API only returns each study's CURRENT record. To know what
changed, this script keeps its own history:

1. For every company in config/watchlist.csv, fetch ALL studies where it is the
   lead sponsor or a collaborator (not just recently updated ones), using the
   same name matching as filter_ctgov_watchlist.py.
2. Save a snapshot of the fields that matter for catalysts (status, enrollment,
   completion dates, primary outcomes, results posted, ...) to
   data/ctgov_snapshots/<stamp>_snapshot.json.
3. Compare with the previous snapshot and write the differences to
   data/ctgov_changes/<stamp>_changes.md (for reading) and .json (for scripts).

The first run has nothing to compare against, so it only records a baseline.
Changes show up from the second run on. A change is reported as "between
snapshot A and snapshot B"; the registry does not tell us the exact day.

Source: ClinicalTrials.gov API v2 (U.S. National Library of Medicine). Free, no key.
"""

import argparse
import csv
import json
import time
from datetime import date

from common import CONFIG_DIR, DATA_DIR, FetchError, fetch, log_event, run_main, run_stamp, save, utc_now
from filter_ctgov_watchlist import core_name, sponsor_hits

SCRIPT = "track_ctgov_changes.py"
API_URL = "https://clinicaltrials.gov/api/v2/studies"
PAGE_SIZE = 200
SECONDS_BETWEEN_REQUESTS = 0.5
SNAPSHOT_DIR = "ctgov_snapshots"
CHANGES_DIR = "ctgov_changes"

# Shown for context, never reported as a "change" (they move on every edit).
CONTEXT_FIELDS = {"last_update_posted", "last_update_submitted", "status_verified_date", "matched_tickers"}
STOPPED_STATUSES = {"TERMINATED", "SUSPENDED", "WITHDRAWN"}


# ---------- fetching ----------

def fetch_sponsor_studies(company_core):
    """All studies where `company_core` appears as sponsor or collaborator."""
    params = {
        "query.spons": company_core,
        "fields": "protocolSection,hasResults",
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
        raise FetchError(f"{company_core!r}: API reported {total} studies but returned {len(studies)}")
    for s in studies:
        if "protocolSection" not in s:
            raise FetchError(f"{company_core!r}: a study came back without protocolSection; API layout changed?")
    return studies, request_urls


# ---------- snapshot ----------

def _date(struct):
    return (struct or {}).get("date")


def _type(struct):
    return ((struct or {}).get("type") or "").upper() or None


def snapshot_of(study):
    p = study["protocolSection"]
    ident = p.get("identificationModule", {})
    status = p.get("statusModule", {})
    design = p.get("designModule", {})
    sc = p.get("sponsorCollaboratorsModule", {})
    arms = p.get("armsInterventionsModule", {})
    outcomes = p.get("outcomesModule", {})
    locations = p.get("contactsLocationsModule", {}).get("locations", [])
    enrollment = design.get("enrollmentInfo", {})
    return {
        "brief_title": ident.get("briefTitle"),
        "acronym": ident.get("acronym"),
        "overall_status": status.get("overallStatus"),
        "why_stopped": status.get("whyStopped"),
        "start_date": _date(status.get("startDateStruct")),
        "primary_completion_date": _date(status.get("primaryCompletionDateStruct")),
        "primary_completion_type": _type(status.get("primaryCompletionDateStruct")),
        "completion_date": _date(status.get("completionDateStruct")),
        "completion_type": _type(status.get("completionDateStruct")),
        "enrollment": enrollment.get("count"),
        "enrollment_type": (enrollment.get("type") or "").upper() or None,
        "phases": sorted(design.get("phases", [])),
        "lead_sponsor": sc.get("leadSponsor", {}).get("name"),
        "collaborators": sorted(c.get("name", "") for c in sc.get("collaborators", [])),
        "conditions": sorted(p.get("conditionsModule", {}).get("conditions", [])),
        "interventions": sorted(i.get("name", "") for i in arms.get("interventions", [])),
        "arm_count": len(arms.get("armGroups", [])),
        "primary_outcomes": [{"measure": o.get("measure"), "time_frame": o.get("timeFrame")}
                             for o in outcomes.get("primaryOutcomes", [])],
        "secondary_outcome_count": len(outcomes.get("secondaryOutcomes", [])),
        "location_count": len(locations),
        "countries": sorted({loc.get("country") for loc in locations if loc.get("country")}),
        "has_results": bool(study.get("hasResults")),
        "results_first_posted": _date(status.get("resultsFirstPostDateStruct")),
        "first_posted": _date(status.get("studyFirstPostDateStruct")),
        "last_update_posted": _date(status.get("lastUpdatePostDateStruct")),
        "last_update_submitted": status.get("lastUpdateSubmitDate"),
        "status_verified_date": status.get("statusVerifiedDate"),
    }


# ---------- diff ----------

def _as_date(text):
    """'2028-07' -> 2028-07-01, '2028-07-27' -> itself. None if unparseable."""
    if not text:
        return None
    parts = text.split("-")
    try:
        return date(int(parts[0]), int(parts[1]) if len(parts) > 1 else 1, int(parts[2]) if len(parts) > 2 else 1)
    except (ValueError, IndexError):
        return None


def flag_for(field, old, new):
    """Return a short reason if this change matters for catalysts, else None."""
    if field == "overall_status":
        if new in STOPPED_STATUSES:
            return f"trial stopped ({new.lower()})"
        if new == "ACTIVE_NOT_RECRUITING" and old == "RECRUITING":
            return "enrollment closed"
        if new == "COMPLETED":
            return "trial completed"
        return "status changed"
    if field == "why_stopped" and new:
        return "reason for stopping added"
    if field == "enrollment" and isinstance(old, int) and isinstance(new, int) and old:
        pct = (new - old) / old * 100
        if pct <= -10:
            return f"enrollment target cut {abs(pct):.0f}%"
        if pct >= 10:
            return f"enrollment target raised {pct:.0f}%"
    if field == "enrollment_type" and old == "ESTIMATED" and new == "ACTUAL":
        return "enrollment marked as actual (usually means enrollment finished)"
    if field in ("primary_completion_date", "completion_date"):
        a, b = _as_date(old), _as_date(new)
        label = "primary completion" if field.startswith("primary") else "study completion"
        if a and b and a != b:
            days = (b - a).days
            return f"{label} moved {'later' if days > 0 else 'earlier'} by {abs(days)} days"
    if field == "primary_completion_type" and old == "ESTIMATED" and new == "ACTUAL":
        return "primary completion date is now actual (primary data collection done)"
    if field == "primary_outcomes":
        return "primary outcome changed"
    if field == "has_results" and new and not old:
        return "results posted"
    if field == "phases":
        return "phase changed"
    return None


def diff_snapshots(prev, curr):
    """Compare two snapshot 'trials' dicts. Returns a list of per-trial change records."""
    out = []
    for nct in sorted(set(prev) | set(curr)):
        if nct not in prev:
            out.append({"nct_id": nct, "kind": "new_to_tracking", "trial": curr[nct], "changes": [], "flags": []})
            continue
        if nct not in curr:
            out.append({"nct_id": nct, "kind": "no_longer_returned", "trial": prev[nct], "changes": [],
                        "flags": ["no longer returned for any watchlist sponsor"]})
            continue
        changes, flags = [], []
        for field in curr[nct]:
            if field in CONTEXT_FIELDS:
                continue
            old, new = prev[nct].get(field), curr[nct].get(field)
            if old != new:
                reason = flag_for(field, old, new)
                changes.append({"field": field, "old": old, "new": new, "flag": reason})
                if reason:
                    flags.append(reason)
        if changes:
            out.append({"nct_id": nct, "kind": "changed", "trial": curr[nct], "changes": changes, "flags": flags})
    return out


# ---------- report ----------

def _fmt(value):
    if value is None or value == [] or value == "":
        return "(blank)"
    if isinstance(value, list):
        if value and isinstance(value[0], dict):
            return "; ".join(f"{o.get('measure')} [{o.get('time_frame')}]" for o in value)
        return ", ".join(str(v) for v in value)
    return str(value)


def render_markdown(stamp, prev_stamp, diffs, tracked, company_counts):
    lines = [f"# ClinicalTrials.gov changes for watchlist sponsors, snapshot {stamp}", ""]
    if prev_stamp is None:
        lines += [
            "**Baseline run.** There is no earlier snapshot to compare with, so no changes can be shown yet.",
            "Changes will appear from the next run on.",
            "",
        ]
    else:
        lines += [
            f"Compared with snapshot {prev_stamp}. Each change happened at some point between the two snapshots;",
            "the registry does not say the exact day. Source: ClinicalTrials.gov API v2 (independent registry;",
            "the content is entered by the sponsor).",
            "",
        ]
    lines += [f"Trials tracked this run: {tracked}", "",
              "| Ticker | Studies matched |", "|---|---|"]
    lines += [f"| {t} | {n} |" for t, n in company_counts.items()]
    lines.append("")
    if prev_stamp is None:
        return "\n".join(lines) + "\n"

    flagged = [d for d in diffs if d["flags"]]
    other = [d for d in diffs if not d["flags"] and d["kind"] == "changed"]
    new = [d for d in diffs if d["kind"] == "new_to_tracking"]

    def block(d):
        t = d["trial"]
        tick = ", ".join(t.get("matched_tickers", [])) or "?"
        out = [f"### {d['nct_id']} ({tick}): {t.get('brief_title')}",
               f"- Link: https://clinicaltrials.gov/study/{d['nct_id']}",
               f"- Record history: https://clinicaltrials.gov/study/{d['nct_id']}?tab=history",
               f"- Last update posted: {t.get('last_update_posted')}"]
        if d["flags"]:
            out.append("- **Why it matters:** " + "; ".join(d["flags"]))
        for c in d["changes"]:
            out.append(f"- {c['field']}: {_fmt(c['old'])} -> {_fmt(c['new'])}")
        return out + [""]

    lines += [f"## Flagged changes ({len(flagged)})", ""]
    for d in flagged:
        lines += block(d)
    if not flagged:
        lines += ["None.", ""]
    lines += [f"## Other changes ({len(other)})", ""]
    for d in other:
        lines += block(d)
    if not other:
        lines += ["None.", ""]
    lines += [f"## Newly tracked trials ({len(new)})", ""]
    for d in new:
        t = d["trial"]
        is_new_reg = t.get("first_posted") and prev_stamp and t["first_posted"] >= stamp_to_date(prev_stamp)
        why = "new registration" if is_new_reg else "not in the previous snapshot (sponsor match or record changed)"
        lines.append(f"- {d['nct_id']} ({', '.join(t.get('matched_tickers', []))}): {t.get('brief_title')}. "
                     f"{why}; first posted {t.get('first_posted')}; status {t.get('overall_status')}")
    if not new:
        lines.append("None.")
    return "\n".join(lines) + "\n"


def stamp_to_date(stamp):
    return stamp[:10]


# ---------- main ----------

def previous_snapshot(current_stamp):
    files = sorted(p for p in (DATA_DIR / SNAPSHOT_DIR).glob("*_snapshot.json")
                   if not p.name.startswith(current_stamp))
    if not files:
        return None, None
    path = files[-1]
    return path.name.split("_")[0], json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    with (CONFIG_DIR / "watchlist.csv").open() as f:
        companies = [(r["ticker"], core_name(r["company"])) for r in csv.DictReader(f) if r.get("ticker")]
    if not companies:
        raise FetchError("config/watchlist.csv has no companies")

    now = utc_now()
    stamp = run_stamp(now)
    trials, company_counts, queries = {}, {}, {}
    for ticker, core in companies:
        studies, urls = fetch_sponsor_studies(core)
        kept = 0
        for study in studies:
            hits = sponsor_hits(study["protocolSection"], [(ticker, core)])
            if not hits:
                continue  # the API's text search is looser than our name match
            nct = study["protocolSection"]["identificationModule"]["nctId"]
            snap = trials.get(nct) or snapshot_of(study)
            snap.setdefault("matched_tickers", [])
            if ticker not in snap["matched_tickers"]:
                snap["matched_tickers"].append(ticker)
            trials[nct] = snap
            kept += 1
        company_counts[ticker] = kept
        queries[ticker] = {"query": core, "api_returned": len(studies), "matched": kept, "request_urls": urls}

    snapshot = {"taken_at_utc": now.isoformat(timespec="seconds"), "queries": queries, "trials": trials}
    save(SCRIPT, SNAPSHOT_DIR, f"{stamp}_snapshot.json", json.dumps(snapshot, indent=2).encode(),
         source_url=API_URL, now=now,
         extra={"publisher": "ClinicalTrials.gov (U.S. National Library of Medicine)",
                "trial_count": len(trials), "matched_per_ticker": company_counts})

    prev_stamp, prev = previous_snapshot(stamp)
    diffs = diff_snapshots(prev["trials"], trials) if prev else []
    md = render_markdown(stamp, prev_stamp, diffs, len(trials), company_counts)
    changes = {"snapshot": stamp, "previous_snapshot": prev_stamp, "baseline": prev is None, "diffs": diffs}
    extra = {"snapshot": stamp, "previous_snapshot": prev_stamp,
             "changed_trials": sum(1 for d in diffs if d["kind"] == "changed"),
             "flagged_trials": sum(1 for d in diffs if d["flags"])}
    save(SCRIPT, CHANGES_DIR, f"{stamp}_changes.json", json.dumps(changes, indent=2).encode(),
         source_url=f"data/{SNAPSHOT_DIR}/{stamp}_snapshot.json (derived)", now=now, extra=extra)
    save(SCRIPT, CHANGES_DIR, f"{stamp}_changes.md", md.encode(),
         source_url=f"data/{SNAPSHOT_DIR}/{stamp}_snapshot.json (derived)", now=now, extra=extra)
    if prev is None:
        log_event(SCRIPT, status="NOTE", message="Baseline snapshot saved; changes will show from the next run.")


if __name__ == "__main__":
    run_main(SCRIPT, main)
