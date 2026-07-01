from __future__ import annotations

from pathlib import Path
import json
import os


def test_index_loads(client) -> None:
    response = client.get('/')
    assert response.status_code == 200
    assert 'LitMap Slim' in response.text


def test_create_project_and_search(client) -> None:
    response = client.post('/projects', data={'title': 'Core map', 'description': 'testing'})
    assert response.status_code == 200
    assert 'Core map' in response.text

    response = client.post('/projects/core-map/search', data={'query': 'conductivity', 'limit': 5})
    assert response.status_code == 200
    assert 'Thermal and electrical conductivity' in response.text


def test_accept_scan_and_export(client) -> None:
    client.post('/projects', data={'title': 'Export map', 'description': ''})
    search = client.post('/projects/export-map/search', data={'query': 'conductivity', 'limit': 5})
    assert search.status_code == 200
    project_file = Path(os.environ['LITMAP_DATA_DIR']) / 'projects' / 'export-map.json'
    payload = json.loads(project_file.read_text())
    candidate = payload['candidates'][0]
    candidate_id = candidate['candidate_id']

    decision = client.post(f'/projects/export-map/candidates/{candidate_id}/decision', data={'decision': 'yes', 'notes': 'seed acceptance'})
    assert decision.status_code == 200

    pdf_dir = Path(os.environ['LITMAP_DATA_DIR']) / 'library' / 'pdfs'
    pdf_dir.mkdir(parents=True, exist_ok=True)
    slug = ''.join(ch if ch.isalnum() else '-' for ch in candidate['title'].lower())
    while '--' in slug:
        slug = slug.replace('--', '-')
    pdf_dir.joinpath(f'{slug.strip("-")}.pdf').write_text('pdf', encoding='utf-8')

    scan = client.post('/projects/export-map/library/scan', data={'candidate_id': candidate_id})
    assert scan.status_code == 200
    assert 'present' in scan.text

    export = client.post('/projects/export-map/export', data={'candidate_id': candidate_id})
    assert export.status_code == 200
    assert 'Export written to' in export.text
    assert (Path(os.environ['LITMAP_DATA_DIR']) / 'exports' / 'export-map' / 'manifest.json').exists()
