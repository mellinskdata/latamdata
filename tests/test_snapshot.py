import json
from pathlib import Path

SNAPSHOT=Path(__file__).resolve().parents[1]/'frontend/public/data/serie-a-2026.json'

def test_snapshot_integrity():
    d=json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    assert d['season']==2026
    assert len(d['players'])>0
    assert len(d['clubs'])>0
    assert len(d['metrics'])>=10
    assert len(set(m['id'] for m in d['metrics']))==len(d['metrics'])
    assert len(set(c['name'] for c in d['clubs']))==len(d['clubs'])
    assert len({str(p['id']) for p in d['players']}) == len(d['players'])
    assert all(isinstance(c.get('table'),dict) for c in d['clubs'])
    assert all(p['minutes']>=0 for p in d['players'])

def test_metric_types():
    d=json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    assert all(m['type'] in {'count','pct','ratio','percent'} for m in d['metrics'])
    assert len(set(str(m['id']) for m in d['metrics']))==len(d['metrics'])