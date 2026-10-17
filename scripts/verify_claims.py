"""Check unverified claims from the filing notes against primary sources.

Reads config/claims.json. Each claim names a check method:

- sec_form4_purchases  SEC Form 4 insider filings (parsed from the XML on sec.gov):
                       finds open-market purchases (code P) by a named insider in a
                       date range and compares shares, average price and total value.
- sec_filing_text      Finds later SEC filings (e.g. the next 10-Q) that mention the
                       topic and quotes the sentences around the key numbers.
                       A human still reads the quotes; the status is NEEDS_READ.
- fda_drugsfda         openFDA Drugs@FDA API: is the brand approved, and when.
                       (Covers CDER drugs and biologics, NOT CBER gene therapies.)
- web_page_contains    Fetches one official web page and checks the names appear
                       ("require_all": every term must appear, else PARTIAL).
- ctgov_results        ClinicalTrials.gov: have results been posted for the trial.
- manual               No machine-readable source. Listed with where to look.

Each claim gets a status:
  CONFIRMED     the primary source matches the claim
  PARTIAL       the source matches the part it covers; the rest is unchecked
  CONTRADICTED  the source was found and disagrees
  NOT_FOUND     the source was checked and has nothing on it
  PENDING       the document that would settle it is not filed yet
  NEEDS_READ    relevant text was found; read the quotes to judge
  MANUAL        must be checked by hand
  ERROR         the source could not be reached (see the detail)

One claim failing to fetch does not stop the others. Output:
data/verification/<stamp>_verification.md and .json.
"""

import argparse
import html
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import date

import requests

from common import CONFIG_DIR, TIMEOUT_SECONDS, FetchError, log_event, run_main, run_stamp, save, user_agent, utc_now

SCRIPT = "verify_claims.py"
SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SEC_ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/"
OPENFDA_URL = "https://api.fda.gov/drug/drugsfda.json"
CTGOV_URL = "https://clinicaltrials.gov/api/v2/studies"
SEC_PAUSE = 0.2  # SEC asks for fewer than 10 requests per second


class NoMatch(Exception):
    """The source answered, but with 'nothing found' (e.g. openFDA 404)."""


def get(url, params=None, *, not_found_ok=False):
    """GET with the project's User-Agent. Every call is logged. Raise FetchError on failure."""
    headers = {"User-Agent": user_agent(), "Accept-Encoding": "gzip, deflate"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as e:
        log_event(SCRIPT, status="FAILED", url=url, error=f"{type(e).__name__}: {e}")
        raise FetchError(f"Could not reach {url}: {type(e).__name__}") from e
    if resp.status_code == 404 and not_found_ok:
        log_event(SCRIPT, status="OK", url=resp.url, note="404 = no match")
        raise NoMatch(resp.url)
    if resp.status_code != 200 or not resp.content:
        log_event(SCRIPT, status="FAILED", url=resp.url, error=f"HTTP {resp.status_code}")
        raise FetchError(f"{resp.url}: HTTP {resp.status_code}")
    log_event(SCRIPT, status="OK", url=resp.url, bytes=len(resp.content))
    return resp


def result(status, detail, evidence=None):
    return {"status": status, "detail": detail, "evidence": evidence or []}


# ---------- SEC helpers ----------

_submissions_cache = {}


def sec_filings(cik, forms, filed_after):
    """Filings of the given forms filed on/after a date, newest first, from the company's EDGAR list."""
    if cik not in _submissions_cache:
        time.sleep(SEC_PAUSE)
        _submissions_cache[cik] = get(SEC_SUBMISSIONS.format(cik=cik)).json()
    recent = _submissions_cache[cik].get("filings", {}).get("recent", {})
    keys = ("form", "filingDate", "accessionNumber", "primaryDocument")
    if any(k not in recent for k in keys):
        raise FetchError(f"SEC submissions for CIK {cik} missing fields {keys}")
    out = []
    for form, filed, acc, doc in zip(*(recent[k] for k in keys)):
        if form in forms and filed >= filed_after:
            out.append({"form": form, "filed": filed, "accession": acc, "doc": doc,
                        "folder": SEC_ARCHIVE.format(cik=cik, acc=acc.replace("-", ""))})
    return out


def html_to_text(raw):
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def snippets(text, term, width=220, limit=3):
    out = []
    for m in re.finditer(re.escape(term), text, flags=re.IGNORECASE):
        start, end = max(0, m.start() - width), min(len(text), m.end() + width)
        out.append("..." + text[start:end] + "...")
        if len(out) >= limit:
            break
    return out


# ---------- checks ----------

def _xml_value(node, path):
    el = node.find(path)
    return el.text.strip() if el is not None and el.text else None


def check_sec_form4_purchases(p):
    """Sum open-market purchases (transaction code P) by one insider over a date range."""
    filings = sec_filings(p["cik"], {"4", "4/A"}, p["from_date"])
    parsed = []
    for f in filings:
        raw_doc = re.sub(r"^xslF345X\d+/", "", f["doc"])  # the XML behind the rendered page
        time.sleep(SEC_PAUSE)
        root = ET.fromstring(get(f["folder"] + raw_doc).content)
        owners = [_xml_value(o, "reportingOwnerId/rptOwnerName") or "" for o in root.findall("reportingOwner")]
        if any(p["owner_contains"].lower() in o.lower() for o in owners):
            parsed.append((f, root, owners))

    # A 4/A restates the whole original Form 4, so it replaces that filing instead of adding to it.
    # The 4/A names the original only by its filing date, so match on same owners + that date.
    superseded = set()
    for f, root, owners in parsed:
        orig_date = _xml_value(root, "dateOfOriginalSubmission")
        if f["form"] != "4/A" or not orig_date:
            continue
        originals = [g for g, _, o in parsed if g["form"] == "4" and g["filed"] == orig_date and o == owners]
        if len(originals) > 1:
            return result("NEEDS_READ", f"Form 4/A filed {f['filed']} amends a Form 4 filed {orig_date}, but "
                          f"{len(originals)} Form 4s for this owner were filed that day; cannot tell which one "
                          "it replaces.", [g["folder"] + g["doc"] for g in originals + [f]])
        superseded.update(g["accession"] for g in originals)

    lots, seen_filings, evidence = [], [], []
    for f, root, owners in parsed:
        if f["accession"] in superseded:
            evidence.append(f"Form {f['form']} filed {f['filed']} (replaced by a later 4/A, not counted): "
                            f"{f['folder'] + f['doc']}")
            continue
        seen_filings.append(f)
        # Lateness is judged from the original report date, not the amendment's.
        reported = _xml_value(root, "dateOfOriginalSubmission") or f["filed"]
        for t in root.findall("nonDerivativeTable/nonDerivativeTransaction"):
            tdate = _xml_value(t, "transactionDate/value") or ""
            code = _xml_value(t, "transactionCoding/transactionCode")
            ad = _xml_value(t, "transactionAmounts/transactionAcquiredDisposedCode/value")
            if code == "P" and ad == "A" and p["from_date"] <= tdate[:10] <= p["to_date"]:
                shares = float(_xml_value(t, "transactionAmounts/transactionShares/value") or 0)
                price = float(_xml_value(t, "transactionAmounts/transactionPricePerShare/value") or 0)
                lots.append({"date": tdate[:10], "shares": shares, "price": price, "owner": owners,
                             "filing": f["folder"] + f["doc"], "filed": f["filed"], "reported": reported})
        evidence.append(f"Form {f['form']} filed {f['filed']}: {f['folder'] + f['doc']}")

    if not seen_filings:
        return result("NOT_FOUND", f"No Form 4 for an owner matching '{p['owner_contains']}' filed since "
                      f"{p['from_date']} in the issuer's EDGAR list (CIK {p['cik']}). Form 4s are due within "
                      "2 business days, so a missing one is itself worth noting.",
                      [SEC_SUBMISSIONS.format(cik=p["cik"])])
    if not lots:
        return result("CONTRADICTED", f"Form 4s found for '{p['owner_contains']}' but no open-market purchases "
                      f"(code P) dated {p['from_date']} to {p['to_date']}.", evidence)

    shares = sum(l["shares"] for l in lots)
    value = sum(l["shares"] * l["price"] for l in lots)
    avg = value / shares if shares else 0
    lot_text = "; ".join(f"{l['date']}: {l['shares']:,.0f} sh @ ${l['price']:.4f} (filed {l['filed']}"
                         + (f", amending {l['reported']}" if l["reported"] != l["filed"] else "") + ")"
                         for l in sorted(lots, key=lambda l: l["date"]))
    late = [l for l in lots if (date.fromisoformat(l["reported"]) - date.fromisoformat(l["date"])).days > 4]
    summary = (f"Form 4 purchases {p['from_date']} to {p['to_date']}: {shares:,.0f} shares, "
               f"${value:,.0f} total, average ${avg:.4f}. Lots: {lot_text}.")
    if late:
        summary += f" Note: {len(late)} lot(s) reported more than 4 days after the trade."

    problems = []
    if "expect_shares" in p and round(shares) != p["expect_shares"]:
        problems.append(f"shares {shares:,.0f} vs claimed {p['expect_shares']:,}")
    if "expect_avg_price" in p and abs(avg - p["expect_avg_price"]) > p.get("price_tolerance", 0.01):
        problems.append(f"average price ${avg:.4f} vs claimed ${p['expect_avg_price']:.2f}")
    if "expect_value" in p and abs(value - p["expect_value"]) > p["expect_value"] * p.get("value_tolerance_pct", 1) / 100:
        problems.append(f"total ${value:,.0f} vs claimed ${p['expect_value']:,}")
    if problems:
        return result("CONTRADICTED", summary + " Differences: " + "; ".join(problems) + ".", evidence)
    return result("CONFIRMED", summary, evidence)


def check_sec_filing_text(p):
    filings = sec_filings(p["cik"], set(p["forms"]), p["filed_after"])
    if not filings:
        return result("PENDING", f"No {'/'.join(p['forms'])} filed since {p['filed_after']} yet. "
                      "Rerun after the next one is filed.", [SEC_SUBMISSIONS.format(cik=p["cik"])])
    quotes, evidence = [], []
    for f in filings:
        docs = [f["doc"]]
        if p.get("include_exhibits"):
            time.sleep(SEC_PAUSE)
            index = get(f["folder"] + "index.json").json()
            docs += [i["name"] for i in index.get("directory", {}).get("item", [])
                     if re.search(r"ex-?99", i["name"], re.I) and i["name"].endswith((".htm", ".html"))]
        for doc in docs:
            time.sleep(SEC_PAUSE)
            text = html_to_text(get(f["folder"] + doc).text)
            if not all(term.lower() in text.lower() for term in p.get("must_contain", [])):
                continue
            url = f["folder"] + doc
            evidence.append(f"{f['form']} filed {f['filed']}: {url}")
            for term in p.get("look_for", []):
                for s in snippets(text, term, limit=2):
                    quotes.append(f"[{f['form']} {f['filed']}, '{term}'] {s}")
    if not evidence:
        return result("NOT_FOUND", f"{len(filings)} filing(s) since {p['filed_after']} checked; none mention "
                      f"{p.get('must_contain')}.", [f["folder"] + f["doc"] for f in filings])
    return result("NEEDS_READ", f"Found in {len(evidence)} document(s). Read the quotes to judge the claim.",
                  evidence + quotes[:12])


def check_fda_drugsfda(p):
    params = {"search": f'products.brand_name:"{p["brand_name"]}"', "limit": 5}
    try:
        data = get(OPENFDA_URL, params=params, not_found_ok=True).json()
    except NoMatch:
        return result("NOT_FOUND", f"'{p['brand_name']}' is not in Drugs@FDA (openFDA). openFDA can lag Drugs@FDA "
                      "by about a week; CBER biologics (gene and cell therapies) are never in it.",
                      [f"{OPENFDA_URL}?search={params['search']}"])
    lines, evidence, approvals = [], [], []
    for app in data.get("results", []):
        appl = app.get("application_number", "")
        num = re.sub(r"\D", "", appl)
        page = f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo={num}"
        evidence.append(f"{appl} ({app.get('sponsor_name')}): {page}")
        for s in app.get("submissions", []):
            if s.get("submission_type") == "ORIG" and s.get("submission_status") == "AP":
                d = s.get("submission_status_date", "")
                d = f"{d[:4]}-{d[4:6]}-{d[6:]}" if len(d) == 8 else d
                approvals.append(d)
                lines.append(f"{appl} original approval {d}")
    if not approvals:
        return result("NOT_FOUND", f"'{p['brand_name']}' is in openFDA but with no original approval listed.", evidence)
    first = min(approvals)
    detail = "; ".join(lines) + "."
    if p.get("approved_on_or_before") and first > p["approved_on_or_before"]:
        return result("CONTRADICTED", detail + f" Claim implies approval by {p['approved_on_or_before']}.", evidence)
    detail += " (Indication wording not checked; see the label on the application page.)"
    if p.get("covers"):
        return result("PARTIAL", detail + f" This confirms {p['covers']}.", evidence)
    return result("CONFIRMED", detail, evidence)


def check_web_page_contains(p):
    text = html_to_text(get(p["url"]).text)
    found = [t for t in p["terms"] if t.lower() in text.lower()]
    evidence = [f"{p.get('publisher', 'page')}: {p['url']}"]
    for t in found[:1]:
        evidence += snippets(text, t, width=150, limit=1)
    if not found:
        return result("NOT_FOUND", f"None of {p['terms']} appear on the page. The page may not be updated yet.",
                      evidence)
    missing = [t for t in p["terms"] if t not in found]
    if p.get("require_all") and missing:
        # Each term stands for one part of the claim, so a partial match is not a confirmation.
        return result("PARTIAL", f"Found {found} on the page but not {missing}. Only the found parts are confirmed.",
                      evidence + [s for t in found[1:] for s in snippets(text, t, width=150, limit=1)])
    status = "PARTIAL" if p.get("covers") else "CONFIRMED"
    detail = f"Found {found} on the page." + (f" This confirms {p['covers']}." if p.get("covers") else "")
    return result(status, detail, evidence)


def check_ctgov_results(p):
    params = {"query.spons": p["sponsor"], "query.intr": p["intervention"],
              "fields": "protocolSection,hasResults", "pageSize": 100}
    resp = get(CTGOV_URL, params=params)
    studies = resp.json().get("studies", [])
    if not studies:
        return result("NOT_FOUND", f"No ClinicalTrials.gov study for sponsor '{p['sponsor']}' and "
                      f"intervention '{p['intervention']}'.", [resp.url])
    lines, evidence, any_results = [], [], False
    for s in studies:
        proto = s["protocolSection"]
        nct = proto["identificationModule"]["nctId"]
        st = proto.get("statusModule", {})
        posted = st.get("resultsFirstPostDateStruct", {}).get("date")
        any_results |= bool(s.get("hasResults"))
        lines.append(f"{nct} ({st.get('overallStatus')}): results {'posted ' + posted if s.get('hasResults') else 'not posted'}")
        evidence.append(f"https://clinicaltrials.gov/study/{nct}")
    detail = "; ".join(lines) + "."
    if any_results:
        return result("NEEDS_READ", detail + " Open the results tab to compare with the company's numbers.", evidence)
    return result("NOT_FOUND", detail + " No registry results yet, so the protocol-method results are still "
                  "unpublished.", evidence)


def check_manual(p):
    return result("MANUAL", f"Where to check: {p['where']}. Why not automated: {p['why_manual']}")


CHECKS = {
    "sec_form4_purchases": check_sec_form4_purchases,
    "sec_filing_text": check_sec_filing_text,
    "fda_drugsfda": check_fda_drugsfda,
    "web_page_contains": check_web_page_contains,
    "ctgov_results": check_ctgov_results,
    "manual": check_manual,
}

ORDER = ["CONTRADICTED", "CONFIRMED", "PARTIAL", "NEEDS_READ", "NOT_FOUND", "PENDING", "MANUAL", "ERROR"]


def render(stamp, rows):
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in ORDER}
    lines = [f"# Claim verification run {stamp}", "",
             "Each claim from data/filing_notes/ was checked against the primary source named below.",
             "Only CONFIRMED means the claim matches a primary source. PARTIAL means the part noted matches.",
             "Everything else stays \"unverified\" in the digest.", "",
             "| Status | Count |", "|---|---|"]
    lines += [f"| {s} | {n} |" for s, n in counts.items() if n]
    lines.append("")
    for status in ORDER:
        group = [r for r in rows if r["status"] == status]
        if not group:
            continue
        lines += [f"## {status}", ""]
        for r in group:
            lines += [f"### {r['id']} ({r['ticker']})",
                      f"- Claim: {r['claim']}",
                      f"- From: {r['from_note']}",
                      f"- Check: {r['check']}",
                      f"- Result: {r['detail']}"]
            lines += [f"  - {e}" for e in r["evidence"]]
            lines.append("")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", help="only these claim ids")
    args = parser.parse_args()

    user_agent()  # fail loudly up front, not once per claim
    claims = json.loads((CONFIG_DIR / "claims.json").read_text())["claims"]
    if args.only:
        claims = [c for c in claims if c["id"] in args.only]
    if not claims:
        raise FetchError("No claims to check in config/claims.json")

    now = utc_now()
    rows = []
    for c in claims:
        check = CHECKS.get(c["check"])
        if check is None:
            r = result("ERROR", f"Unknown check type '{c['check']}'")
        else:
            try:
                r = check(c["params"])
            except (FetchError, ValueError, KeyError, ET.ParseError) as e:
                r = result("ERROR", f"{type(e).__name__}: {e}")
        rows.append({**{k: c[k] for k in ("id", "ticker", "claim", "from_note", "check")}, **r,
                     "checked_at_utc": now.isoformat(timespec="seconds")})
        print(f"{c['id']}: {r['status']}")

    stamp = run_stamp(now)
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in ORDER if any(r["status"] == s for r in rows)}
    save(SCRIPT, "verification", f"{stamp}_verification.json", json.dumps(rows, indent=2).encode(),
         source_url="config/claims.json (each claim lists its own sources)", now=now, extra={"status_counts": counts})
    save(SCRIPT, "verification", f"{stamp}_verification.md", render(stamp, rows).encode(),
         source_url="config/claims.json (each claim lists its own sources)", now=now, extra={"status_counts": counts})


if __name__ == "__main__":
    run_main(SCRIPT, main)
