from __future__ import annotations

from pathlib import Path
import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv('LITMAP_DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setenv('LITMAP_CONTEXT_SKIP_TESTS', '1')
    import app.config
    import app.main
    import app.store
    importlib.reload(app.config)
    importlib.reload(app.store)
    importlib.reload(app.main)
    return TestClient(app.main.app)
