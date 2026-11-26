"""Exercise the HTTP contract and upstream failures without using a live provider."""
import copy

import pytest
import requests
from fastapi.testclient import TestClient

from backend import main


PAYLOAD = {'events': [{'id': '456', 'date': '2026-10-20T00:00Z',
    'status': {'type': {'description': 'Finalizado', 'completed': True}},
    'competitions': [{'competitors': [
        {'homeAway': 'home', 'score': '2', 'team': {'displayName': 'Mandante'}},
        {'homeAway': 'away', 'score': '1', 'team': {'displayName': 'Visitante'}},
    ]}]}]}


@pytest.fixture(autouse=True)
def clear_cache():
    main._cache.clear()
    yield
    main._cache.clear()


def upstream(monkeypatch, payload=PAYLOAD, error=None):
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs))
        if error:
            raise error
        response = requests.Response()
        response.status_code = 200
        response.json = lambda: copy.deepcopy(payload)
        return response
    monkeypatch.setattr(main.requests, 'get', get)
    return calls


def test_http_health():
    response = TestClient(main.app).get('/api/health')
    assert response.status_code == 200
    assert response.json()['ok'] is True


def test_matches_cache_and_expiry(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(main.time, 'monotonic', lambda: now[0])
    calls = upstream(monkeypatch)
    client = TestClient(main.app)
    first = client.get('/api/matches?season=2026')
    assert first.status_code == 200
    assert first.json()['matches'][0]['home_score'] == 2
    assert first.json()['cached'] is False
    assert client.get('/api/matches?season=2026').json()['cached'] is True
    assert len(calls) == 1
    assert calls[0][1]['params'] == {'dates': '2026', 'limit': 500}
    assert calls[0][1]['timeout'] == 14
    now[0] += 1200
    assert client.get('/api/matches?season=2026').json()['cached'] is False
    assert len(calls) == 2
    assert client.get('/api/matches?season=2025').json()['season'] == 2025
    assert len(calls) == 3


@pytest.mark.parametrize('error', [requests.Timeout(), requests.HTTPError('503'), requests.ConnectionError()])
def test_upstream_failure_is_502(monkeypatch, error):
    upstream(monkeypatch, error=error)
    response = TestClient(main.app).get('/api/matches?season=2026')
    assert response.status_code == 502
    assert response.json()['detail'] == 'Fonte de partidas temporariamente indisponível.'
    assert main._cache == {}


@pytest.mark.parametrize('payload', [[], None, {}, {'events': None}, {'events': {}}])
def test_invalid_upstream_envelope_is_not_success(monkeypatch, payload):
    upstream(monkeypatch, payload=payload)
    response = TestClient(main.app).get('/api/matches?season=2026')
    assert response.status_code == 502
    assert main._cache == {}


def test_empty_season_is_valid(monkeypatch):
    upstream(monkeypatch, payload={'events': []})
    response = TestClient(main.app).get('/api/matches?season=2026')
    assert response.status_code == 200
    assert response.json()['matches'] == []


@pytest.mark.parametrize('season', ['2017', '2031', 'abc'])
def test_invalid_season_does_not_call_provider(monkeypatch, season):
    calls = upstream(monkeypatch)
    assert TestClient(main.app).get(f'/api/matches?season={season}').status_code == 422
    assert not calls


@pytest.mark.parametrize('score', [None, '', 'bad', 'nan', 'Infinity', '-1', '2.5', True])
def test_invalid_scores_remain_unknown(score):
    payload = copy.deepcopy(PAYLOAD)
    payload['events'][0]['competitions'][0]['competitors'][0]['score'] = score
    assert main._parse_scoreboard(payload)[0]['home_score'] is None


def test_malformed_events_are_skipped():
    payload = {'events': [None, {}, {'competitions': [None]},
        {'competitions': [{'competitors': ['bad', None]}]}, *PAYLOAD['events']]}
    assert len(main._parse_scoreboard(payload)) == 1
