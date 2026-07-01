from __future__ import annotations

from pathlib import Path

from app.models import Candidate, Decision
from app.store import ProjectStore


def test_project_store_round_trip(tmp_path: Path) -> None:
    store = ProjectStore(tmp_path / 'projects', tmp_path / 'library', tmp_path / 'exports')
    project = store.create_project('Core Conductivity')
    project.upsert_candidates([
        Candidate(candidate_id='abc123', title='Thermal conductivity paper', authors=['A. Author'], journal='Nature', year=2012)
    ], query='conductivity')
    project.set_decision('abc123', Decision.YES)
    store.save(project)

    loaded = store.get(project.project_id)
    assert loaded.title == 'Core Conductivity'
    assert loaded.candidates[0].decision == Decision.YES
