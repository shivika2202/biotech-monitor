PY ?= .venv/bin/python

.PHONY: setup test weekly

setup:
	python3.12 -m venv .venv
	$(PY) -m pip install -r requirements-dev.txt

test:
	$(PY) -m pytest -q

# Runs the weekly pipeline in order. make stops at the first script that fails,
# so a broken source never feeds stale data into the later steps.
weekly:
	$(PY) scripts/fetch_xbi_prices.py
	$(PY) scripts/fetch_xbi_holdings.py
	$(PY) scripts/fetch_ctgov.py
	$(PY) scripts/track_ctgov_changes.py
	$(PY) scripts/filter_ctgov_watchlist.py
	$(PY) scripts/fetch_sec_8k.py
	$(PY) scripts/verify_claims.py
