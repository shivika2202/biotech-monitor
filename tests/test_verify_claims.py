"""The claim checks, run against canned SEC and web responses (no network)."""

from types import SimpleNamespace

import pytest

import verify_claims as vc

FOLDER = "https://www.sec.gov/Archives/edgar/data/1/{acc}/"


def form4_xml(owner, lots, original_date=None):
    rows = "".join(
        f"<nonDerivativeTransaction><transactionDate><value>{d}</value></transactionDate>"
        f"<transactionCoding><transactionCode>P</transactionCode></transactionCoding>"
        f"<transactionAmounts><transactionShares><value>{s}</value></transactionShares>"
        f"<transactionPricePerShare><value>{p}</value></transactionPricePerShare>"
        f"<transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>"
        f"</transactionAmounts></nonDerivativeTransaction>"
        for d, s, p in lots)
    original = f"<dateOfOriginalSubmission>{original_date}</dateOfOriginalSubmission>" if original_date else ""
    return (f"<ownershipDocument>{original}<reportingOwner><reportingOwnerId><rptOwnerName>{owner}"
            f"</rptOwnerName></reportingOwnerId></reportingOwner>"
            f"<nonDerivativeTable>{rows}</nonDerivativeTable></ownershipDocument>").encode()


@pytest.fixture
def sec(monkeypatch):
    """Serve a fixed list of Form 4 filings instead of calling EDGAR."""
    filings, docs = [], {}

    def add(form, filed, acc, xml):
        f = {"form": form, "filed": filed, "accession": acc, "doc": f"xslF345X06/f{acc}.xml",
             "folder": FOLDER.format(acc=acc)}
        filings.append(f)
        docs[f["folder"] + f"f{acc}.xml"] = xml  # the script strips the xslF345X06/ prefix

    monkeypatch.setattr(vc, "sec_filings", lambda cik, forms, after: filings)
    monkeypatch.setattr(vc, "get", lambda url, **kw: SimpleNamespace(content=docs[url]))
    monkeypatch.setattr(vc.time, "sleep", lambda s: None)
    return add


PARAMS = {"cik": 1, "owner_contains": "Chen", "from_date": "2026-08-12", "to_date": "2026-09-16"}


def test_form4_confirms_matching_totals(sec):
    sec("4", "2026-08-18", "a1", form4_xml("CHEN THOMAS C", [("2026-08-14", 1000, 4.0)]))
    r = vc.check_sec_form4_purchases({**PARAMS, "expect_shares": 1000, "expect_value": 4000})
    assert r["status"] == "CONFIRMED"


def test_form4_amendment_replaces_original_instead_of_double_counting(sec):
    lot = ("2026-08-14", 33787, 3.8477)
    sec("4/A", "2026-08-20", "a2", form4_xml("CHEN THOMAS C", [lot], original_date="2026-08-18"))
    sec("4", "2026-08-18", "a1", form4_xml("CHEN THOMAS C", [lot]))

    r = vc.check_sec_form4_purchases({**PARAMS, "expect_shares": 33787})

    assert r["status"] == "CONFIRMED", r["detail"]
    assert "33,787 shares" in r["detail"]
    assert any("replaced by a later 4/A" in e for e in r["evidence"])


def test_form4_reports_contradiction_with_both_numbers(sec):
    sec("4", "2026-09-15", "a3", form4_xml("CHEN THOMAS C", [("2026-09-11", 5556, 3.60), ("2026-08-14", 49016, 4.0)]))
    r = vc.check_sec_form4_purchases({**PARAMS, "expect_shares": 49016})
    assert r["status"] == "CONTRADICTED"
    assert "54,572 vs claimed 49,016" in r["detail"]


def test_form4_ignores_other_insiders(sec):
    sec("4", "2026-09-15", "a4", form4_xml("SOMEONE ELSE", [("2026-09-11", 100, 1.0)]))
    assert vc.check_sec_form4_purchases(PARAMS)["status"] == "NOT_FOUND"


@pytest.fixture
def page(monkeypatch):
    def serve(html):
        monkeypatch.setattr(vc, "get", lambda url, **kw: SimpleNamespace(text=html))
    return serve


WEB = {"url": "https://www.fda.gov/x", "terms": ["August 19, 2026", "accelerated approval", "Priority Review Voucher"]}


def test_web_check_any_term_is_enough_by_default(page):
    page("<p>Issued an accelerated approval today.</p>")
    assert vc.check_web_page_contains(WEB)["status"] == "CONFIRMED"


def test_web_check_require_all_downgrades_partial_match_to_partial(page):
    page("<p>For Immediate Release: August 19, 2026. Issued an accelerated approval.</p>")
    r = vc.check_web_page_contains({**WEB, "require_all": True})
    assert r["status"] == "PARTIAL"
    assert "Priority Review Voucher" in r["detail"]


def test_web_check_require_all_confirms_full_match(page):
    page("<p>August 19, 2026: accelerated approval. Received a Priority Review Voucher.</p>")
    assert vc.check_web_page_contains({**WEB, "require_all": True})["status"] == "CONFIRMED"


def test_web_check_nothing_found(page):
    page("<p>Unrelated page</p>")
    assert vc.check_web_page_contains(WEB)["status"] == "NOT_FOUND"
