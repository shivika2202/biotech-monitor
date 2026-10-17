"""Layout checks on the State Street files, using small spreadsheets built in memory."""

import io

import openpyxl
import pytest

import fetch_xbi_holdings
import fetch_xbi_prices
from common import FetchError


def xlsx(rows):
    wb = openpyxl.Workbook()
    for r in rows:
        wb.active.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


HOLDINGS_TOP = [("Fund Name:", "SPDR S&P Biotech ETF"), ("Ticker Symbol:", "XBI"), ("Holdings:", "As of 15-Oct-2026"), ()]
HOLDINGS_HEADER = fetch_xbi_holdings.EXPECTED_HEADER


def test_holdings_counts_rows_until_first_blank():
    rows = HOLDINGS_TOP + [HOLDINGS_HEADER,
                           ("MODERNA INC", "MRNA", "x", "x", 2.64, "x", 1, "USD"),
                           ("BIOGEN INC", "BIIB", "x", "x", 1.69, "x", 1, "USD"),
                           (None,),
                           ("Footnote text that is not a holding",)]
    assert fetch_xbi_holdings.check_file(xlsx(rows)) == ("15-Oct-2026", 2)


def test_holdings_rejects_changed_columns():
    rows = HOLDINGS_TOP + [("Name", "Ticker", "Weight"), ("MODERNA INC", "MRNA", 2.64)]
    with pytest.raises(FetchError, match="Column headers changed"):
        fetch_xbi_holdings.check_file(xlsx(rows))


def test_holdings_rejects_a_different_fund():
    rows = [("Fund Name:", "Other"), ("Ticker Symbol:", "SPY")] + HOLDINGS_TOP[2:]
    with pytest.raises(FetchError, match="should identify XBI"):
        fetch_xbi_holdings.check_file(xlsx(rows))


def test_nav_history_reports_date_range():
    rows = [("Fund Name:", "x"), ("Ticker Symbol:", "XBI"), (), fetch_xbi_prices.EXPECTED_HEADER,
            ("15-Oct-2026", 149.81, 1, 1), ("08-Oct-2026", 149.32, 1, 1)]
    assert fetch_xbi_prices.check_file(xlsx(rows)) == ("2026-10-15", "2026-10-08", 2)


def test_nav_history_rejects_non_numeric_nav():
    rows = [("Fund Name:", "x"), ("Ticker Symbol:", "XBI"), (), fetch_xbi_prices.EXPECTED_HEADER,
            ("15-Oct-2026", "n/a", 1, 1)]
    with pytest.raises(FetchError, match="not a number"):
        fetch_xbi_prices.check_file(xlsx(rows))
