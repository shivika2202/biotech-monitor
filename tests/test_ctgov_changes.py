from datetime import date

import pytest

from track_ctgov_changes import _as_date, diff_snapshots, flag_for


@pytest.mark.parametrize("text, expected", [
    ("2028-07-27", date(2028, 7, 27)),
    ("2028-07", date(2028, 7, 1)),
    ("2028", date(2028, 1, 1)),
    (None, None),
    ("not a date", None),
])
def test_as_date_handles_partial_registry_dates(text, expected):
    assert _as_date(text) == expected


@pytest.mark.parametrize("field, old, new, expected", [
    ("overall_status", "RECRUITING", "TERMINATED", "trial stopped (terminated)"),
    ("overall_status", "RECRUITING", "ACTIVE_NOT_RECRUITING", "enrollment closed"),
    ("enrollment", 100, 80, "enrollment target cut 20%"),
    ("enrollment", 100, 95, None),  # under 10% is noise, not a flag
    ("primary_completion_date", "2028-07", "2028-10", "primary completion moved later by 92 days"),
    ("completion_date", "2029-01-15", "2028-12-31", "study completion moved earlier by 15 days"),
    ("primary_completion_type", "ESTIMATED", "ACTUAL",
     "primary completion date is now actual (primary data collection done)"),
    ("has_results", False, True, "results posted"),
    ("location_count", 30, 31, None),
])
def test_flag_for(field, old, new, expected):
    assert flag_for(field, old, new) == expected


def trial(**overrides):
    base = {"overall_status": "RECRUITING", "enrollment": 100, "last_update_posted": "2026-10-01",
            "matched_tickers": ["DYN"]}
    return {**base, **overrides}


def test_diff_reports_changes_new_and_dropped_trials():
    prev = {"NCT1": trial(), "NCT2": trial(), "NCT3": trial()}
    curr = {"NCT1": trial(overall_status="SUSPENDED"), "NCT2": trial(), "NCT4": trial()}

    diffs = {d["nct_id"]: d for d in diff_snapshots(prev, curr)}

    assert set(diffs) == {"NCT1", "NCT3", "NCT4"}  # NCT2 unchanged, so not reported
    assert diffs["NCT1"]["kind"] == "changed"
    assert diffs["NCT1"]["flags"] == ["trial stopped (suspended)"]
    assert diffs["NCT3"]["kind"] == "no_longer_returned"
    assert diffs["NCT4"]["kind"] == "new_to_tracking"


def test_diff_ignores_fields_that_move_on_every_edit():
    prev = {"NCT1": trial()}
    curr = {"NCT1": trial(last_update_posted="2026-10-15", matched_tickers=["DYN", "BIIB"])}
    assert diff_snapshots(prev, curr) == []
