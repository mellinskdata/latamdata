"""LATAMDATA optional match API. Standalone with ESPN fallback adapter.
Run: uvicorn backend.main:app --port 8000 --reload
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="LATAMDATA API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
_cache: dict[int, tuple[float, list[dict]]] = {}


def _parse_scoreboard(payload: dict) -> list[dict]:
    """Normalize ESPN public scoreboard without manufacturing missing results."""
    matches = []
    for event in payload.get('events', []) or []:
        comp = (event.get('competitions') or [None])[0]
        if not comp:
            continue
        comps = comp.get('competitors') or []
        home = next((c for c in comps if c.get('homeAway') == 'home'), {})
        away = next((c for c in comps if c.get('homeAway') == 'away'), {})
        if not home or not away:
            continue
        def score(c):
            try:
                return int(float(c['score'])) if c.get('score') not in ('', None) else None
            except (ValueError, TypeError):
                return None
        status = (event.get('status') or {}).get('type') or {}
        matches.append({
            'event_id': str(event.get('id', '')),
            'date': event.get('date'),
            'home': (home.get('team') or {}).get('displayName') or (home.get('team') or {}).get('name'),
            'away': (away.get('team') or {}).get('displayName') or (away.get('team') or {}).get('name'),
            'home_score': score(home),
            'away_score': score(away),
            'status': status.get('description') or status.get('detail') or 'Agendado',
            'completed': bool(status.get('completed', False)),
        })
    return matches


@app.get('/api/health')
def health():
    return {'ok': True, 'product': 'LATAMDATA', 'version': '0.2.0'}


@app.get('/api/matches')
def matches(season: int = Query(2026, ge=2018, le=2030)):
    cache = _cache.get(season)
    if cache and time.time() - cache[0] < 1200:
        return {'season': season, 'matches': cache[1], 'cached': True}
    try:
        response = requests.get(
            'https://site.api.espn.com/apis/site/v2/sports/soccer/bra.1/scoreboard',
            params={'dates': str(season), 'limit': 500},
            timeout=14,
            headers={'User-Agent': 'LATAMDATA/0.2; football analytics', 'Accept':'application/json'},
        )
        response.raise_for_status()
        result = _parse_scoreboard(response.json())
        _cache[season] = (time.time(), result)
        return {'season': season, 'matches': result, 'cached': False}
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail='Fonte de partidas temporariamente indisponível.') from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail='Resposta inválida da fonte de partidas.') from exc