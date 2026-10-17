import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import common  # noqa: E402


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Keep every test away from the real data/, logs/ and network identity."""
    monkeypatch.setattr(common, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(common, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(common, "LOG_FILE", tmp_path / "logs" / "fetch_log.jsonl")
    monkeypatch.setattr(common, "USER_AGENT_FILE", tmp_path / "no_user_agent.txt")
    monkeypatch.setenv("SEC_USER_AGENT", "Test Runner test@example.com")
    return tmp_path
