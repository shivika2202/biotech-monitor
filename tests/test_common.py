import hashlib
import json
from datetime import datetime, timezone

import pytest

import common
from common import FetchError


NOW = datetime(2026, 10, 17, 20, 13, tzinfo=timezone.utc)


def test_run_stamp_is_sortable_utc_minute():
    assert common.run_stamp(NOW) == "2026-10-17T2013Z"


def test_save_writes_file_sidecar_and_log(isolated):
    path = common.save("test.py", "demo", "2026-10-17T2013Z_x.json", b'{"a": 1}',
                       source_url="https://example.com/x", now=NOW, extra={"note": "hi"})

    assert path.read_bytes() == b'{"a": 1}'
    sidecar = json.loads(path.with_name(path.name + ".source.json").read_text())
    assert sidecar["source_url"] == "https://example.com/x"
    assert sidecar["sha256"] == hashlib.sha256(b'{"a": 1}').hexdigest()
    assert sidecar["fetched_at_utc"] == "2026-10-17T20:13:00+00:00"
    assert sidecar["note"] == "hi"

    log = [json.loads(line) for line in common.LOG_FILE.read_text().splitlines()]
    assert log[-1]["status"] == "OK" and log[-1]["output"] == "data/demo/2026-10-17T2013Z_x.json"


def test_save_refuses_to_overwrite():
    common.save("test.py", "demo", "f.txt", b"first", source_url="u", now=NOW)
    with pytest.raises(FetchError, match="refusing to overwrite"):
        common.save("test.py", "demo", "f.txt", b"second", source_url="u", now=NOW)


def test_user_agent_must_be_set(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT")
    with pytest.raises(FetchError, match="SEC requires"):
        common.user_agent()


def test_user_agent_can_come_from_file(isolated, monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT")
    common.USER_AGENT_FILE.write_text("Jane Doe jane@example.com\n")
    assert common.user_agent() == "Jane Doe jane@example.com"


def test_run_main_logs_failure_and_exits_nonzero():
    def broken():
        raise FetchError("source down")

    with pytest.raises(SystemExit) as exit_info:
        common.run_main("test.py", broken)
    assert exit_info.value.code == 1
    last = json.loads(common.LOG_FILE.read_text().splitlines()[-1])
    assert last["status"] == "FAILED" and last["error"] == "source down"
