"""List ClinicalTrials.gov studies (from the newest fetch_ctgov.py run) whose lead
sponsor or a collaborator is a company in config/watchlist.csv.

Matching: legal suffixes (Inc, Corp, N.V., AG, Holdings, ...) are stripped from
both names, then the sponsor name must start with the watchlist company's name.
Example: "uniQure N.V." -> "uniqure" matches "uniQure Biopharma B.V.".

"What changed": the registry only shows the current state, not a diff. The
script reports what the dates prove (new registration or first results posted
inside the window), plus field-level changes from our own snapshots made by
track_ctgov_changes.py. Run that script before this one.
"""

import csv
import json
import re

from common import CONFIG_DIR, DATA_DIR, FetchError, run_main, run_stamp, save, utc_now

SCRIPT = "filter_ctgov_watchlist.py"
LEGAL_SUFFIXES = r"\b(inc|incorporated|corp|corporation|co|n\.?v|b\.?v|ag|plc|ltd|llc|holdings?)\b\.?"


def core_name(name):
    name = re.sub(LEGAL_SUFFIXES, " ", name.lower())
    return re.sub(r"[^a-z0-9]+", " ", name).strip()


def sponsor_hits(proto, companies):
    """(ticker, role, org) for each watchlist company that is the lead sponsor or a collaborator."""
    sc = proto.get("sponsorCollaboratorsModule", {})
    orgs = [("lead sponsor", sc.get("leadSponsor", {}).get("name", ""))]
    orgs += [("collaborator", c.get("name", "")) for c in sc.get("collaborators", [])]
    return [(t, role, org) for t, core in companies for role, org in orgs
            if re.match(re.escape(core) + r"\b", core_name(org))]


def newest_changes():
    """Newest output of track_ctgov_changes.py as a dict, or None if it has never run."""
    files = sorted((DATA_DIR / "ctgov_changes").glob("*_changes.json"))
    return json.loads(files[-1].read_text()) if files else None


def newest_run():
    files = sorted(p for p in (DATA_DIR / "ctgov").glob("*.json") if not p.name.endswith(".source.json"))
    if not files:
        raise FetchError("No ClinicalTrials.gov data in data/ctgov/; run fetch_ctgov.py first")
    stamp = files[-1].name.split("_")[0]
    return stamp, [p for p in files if p.name.startswith(stamp + "_")]


def what_changed(nct, status, since, changes):
    """Describe what changed, using what the dates prove plus our own snapshot diffs."""
    notes = []
    if status.get("studyFirstPostDateStruct", {}).get("date", "") >= since:
        notes.append("new registration (first posted %s)" % status["studyFirstPostDateStruct"]["date"])
    if status.get("resultsFirstPostDateStruct", {}).get("date", "") >= since:
        notes.append("results first posted %s" % status["resultsFirstPostDateStruct"]["date"])

    if changes is None:
        notes.append("field-level changes not tracked yet (run scripts/track_ctgov_changes.py)")
        return "; ".join(notes)

    snap = changes["snapshot"]
    snapshot_file = DATA_DIR / "ctgov_snapshots" / f"{snap}_snapshot.json"
    tracked = snapshot_file.exists() and nct in json.loads(snapshot_file.read_text())["trials"]
    last_update = status.get("lastUpdatePostDateStruct", {}).get("date", "")
    if not tracked:
        notes.append(f"not in snapshot {snap} (sponsor search did not return it)")
    elif last_update > snap[:10]:
        notes.append(f"updated {last_update}, after the newest snapshot {snap}; rerun track_ctgov_changes.py")
    elif changes["baseline"]:
        notes.append(f"baseline snapshot {snap} is the first one; field-level changes start next run")
    else:
        diff = next((d for d in changes["diffs"] if d["nct_id"] == nct), None)
        window = f"between snapshots {changes['previous_snapshot']} and {snap}"
        if diff is None:
            notes.append(f"no tracked field changed {window} (see the record's History of Changes for other edits)")
        elif diff["kind"] == "new_to_tracking":
            notes.append(f"first seen in snapshot {snap}, nothing earlier to compare")
        else:
            parts = [f"{c['field']} {c['old']} -> {c['new']}" for c in diff["changes"]]
            flag = f" [FLAG: {'; '.join(diff['flags'])}]" if diff["flags"] else ""
            notes.append(f"{window}: " + "; ".join(parts) + flag)
    return "; ".join(notes)


def main():
    with (CONFIG_DIR / "watchlist.csv").open() as f:
        companies = [(r["ticker"], core_name(r["company"])) for r in csv.DictReader(f)]
    stamp, files = newest_run()
    changes = newest_changes()

    matches = {}
    since = None
    for path in files:
        run = json.loads(path.read_text())
        since = run["last_update_posted_on_or_after"]
        for study in run["studies"]:
            proto = study["protocolSection"]
            nct = proto["identificationModule"]["nctId"]
            hits = sponsor_hits(proto, companies)
            if not hits:
                continue
            entry = matches.setdefault(nct, {"proto": proto, "hits": set(), "conditions": set()})
            entry["hits"].update(hits)
            entry["conditions"].add(run["condition"])

    lines = [
        f"# Watchlist sponsor matches in ClinicalTrials.gov run {stamp}",
        "",
        f"Studies with Last Update Posted on or after {since}, from the condition files in data/ctgov/{stamp}_*.json,",
        "where the lead sponsor or a collaborator matches a company in config/watchlist.csv.",
        "Source: ClinicalTrials.gov API v2 (independent registry; the content is entered by the sponsor).",
        "",
        f"Matches: {len(matches)}",
        "",
    ]
    for nct, e in sorted(matches.items()):
        p = e["proto"]
        status = p["statusModule"]
        lines += [
            f"## {nct}: {p['identificationModule'].get('briefTitle', '')}",
            f"- Link: https://clinicaltrials.gov/study/{nct}",
            "- Watchlist match: " + "; ".join(f"{t} ({role}: {org})" for t, role, org in sorted(e["hits"])),
            "- Found under condition search: " + ", ".join(sorted(e["conditions"])),
            f"- Overall status: {status.get('overallStatus', 'not given')}",
            f"- Last update posted: {status.get('lastUpdatePostDateStruct', {}).get('date', 'not given')}",
            f"- Primary completion: {status.get('primaryCompletionDateStruct', {}).get('date', 'not given')}"
            f" ({status.get('primaryCompletionDateStruct', {}).get('type', '').lower() or 'type not given'})",
            f"- What changed: {what_changed(nct, status, since, changes)}",
            "",
        ]

    now = utc_now()
    save(SCRIPT, "ctgov_watchlist", f"{run_stamp(now)}_matches.md", "\n".join(lines).encode(),
         source_url=f"data/ctgov/{stamp}_*.json (derived)", now=now,
         extra={"input_run": stamp, "input_files": [p.name for p in files], "match_count": len(matches),
                "changes_snapshot": changes["snapshot"] if changes else None})


if __name__ == "__main__":
    run_main(SCRIPT, main)
