import pytest

from filter_ctgov_watchlist import core_name, sponsor_hits


@pytest.mark.parametrize("raw, expected", [
    ("uniQure N.V.", "uniqure"),
    ("Sarepta Therapeutics, Inc.", "sarepta therapeutics"),
    ("Scholar Rock Holding Corporation", "scholar rock"),
    ("BIOGEN INC.", "biogen"),
])
def test_core_name_strips_legal_suffixes(raw, expected):
    assert core_name(raw) == expected


def proto(lead, *collaborators):
    return {"sponsorCollaboratorsModule": {
        "leadSponsor": {"name": lead},
        "collaborators": [{"name": c} for c in collaborators],
    }}


WATCHLIST = [("QURE", "uniqure"), ("BIIB", "biogen"), ("DYN", "dyne therapeutics")]


def test_matches_subsidiary_as_lead_sponsor():
    assert sponsor_hits(proto("uniQure Biopharma B.V."), WATCHLIST) == [
        ("QURE", "lead sponsor", "uniQure Biopharma B.V.")]


def test_matches_collaborator_role():
    hits = sponsor_hits(proto("University of Rochester", "Biogen"), WATCHLIST)
    assert hits == [("BIIB", "collaborator", "Biogen")]


def test_requires_whole_word_match():
    # "biogen" must not match "Biogenix", and "uniqure" must not match "Uniquely Health".
    assert sponsor_hits(proto("Biogenix Labs", "Uniquely Health"), WATCHLIST) == []


def test_name_must_start_with_company_name():
    # A company name appearing mid-string is not the sponsor.
    assert sponsor_hits(proto("Friends of Dyne Therapeutics Patients"), WATCHLIST) == []
