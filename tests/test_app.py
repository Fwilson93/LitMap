from __future__ import annotations

def test_index_loads(client):
    response = client.get('/')
    assert response.status_code == 200


def test_create_project_and_search(client):
    client.post('/projects', data={'title': 'Test'})
    response = client.post('/projects/test/search', data={'query': 'iron', 'limit': 3})
    assert response.status_code == 200
