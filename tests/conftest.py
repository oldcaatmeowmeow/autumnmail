from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from autumnmail.server import create_app
from autumnmail.store import repo


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTUMNMAIL_DATA_DIR", str(tmp_path))
    repo.reset_secret_store()
    app = create_app("test-token", dev=True)
    with TestClient(app) as test_client:
        test_client.headers.update({"X-App-Token": "test-token"})
        yield test_client
    repo.reset_secret_store()
