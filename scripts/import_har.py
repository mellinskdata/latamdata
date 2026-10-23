"""Import an authorized user's HAR capture into compact LATAMDATA Série A data.

Usage: python scripts/import_har.py path/to/capture.har --output frontend/public/data/serie-a-2026.json
IMPORTANT: check the dataset's redistribution license before publishing it.
"""
import argparse
import base64
import json
from pathlib import Path
from urllib.parse import urlparse


def extract(har_path: Path) -> dict:
    har = json.loads(har_path.read_text(encoding='utf-8'))
    league_data = table_data = None
    for entry in har.get('log', {}).get('entries', []):
        url = urlparse(entry.get('request', {}).get('url', ''))
        if url.hostname != 'simonetti-stats.pages.dev':
            continue
        if url.path not in {'/wc_data.json', '/tabelas.json'}:
            continue
        content = entry.get('response', {}).get('content', {})
        raw = content.get('text', '')
        if not raw:
            continue
        if content.get('encoding') == 'base64':
            raw = base64.b64decode(raw).decode('utf-8')
        obj = json.loads(raw)
        if url.path == '/wc_data.json':
            league_data = obj
        else:
            table_data = obj
    if not league_data or not table_data:
        raise ValueError('O HAR precisa conter wc_data.json e tabelas.json com respostas completas.')
    table = table_data['tabelas']['brasil']
    players = []
    for p in league_data['players']:
        d = p.get('leagues', {}).get('brasil')
        if not d:
            continue
        players.append({
            'id': p.get('sbid') or f"{p.get('name')}|{d.get('club')}",
            'name': p.get('name'), 'club': d.get('club'), 'position': p.get('pos') or '-',
            'group': p.get('posg') or '-', 'age': p.get('age'), 'height': p.get('h'),
            'nation': p.get('nationality_pt') or p.get('nationality_en'),
            'minutes': d.get('min') or 0, 'matches': d.get('mp') or 0,
            'starts': d.get('st') or 0, 's': d.get('s') or {},
        })
    # Retain the most complete season record when the source repeats a player ID.
    by_id = {}
    for p in players:
        key = str(p['id'])
        old = by_id.get(key)
        if old is None or (p['minutes'], len(p['s'])) > (old['minutes'], len(old['s'])):
            by_id[key] = p
    players = list(by_id.values())
    clubs = []
    for t in league_data['teams']:
        if t.get('league') == 'brasil':
            clubs.append({'name': t['name'], 'matches': t.get('mp'),
                          'roster': t.get('roster'), 's': t.get('s') or {},
                          'table': table.get(t['name'], {})})
    return {
        'season': 2026, 'updated': league_data['updated'],
        'source': 'Captura fornecida pelo usuário, prototipagem; verificar direitos antes de publicar.',
        'metrics': league_data['metrics'], 'cats': league_data['cats'],
        'players': players, 'clubs': clubs,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('har', type=Path)
    parser.add_argument('--output', type=Path, default=Path('frontend/public/data/serie-a-2026.json'))
    args = parser.parse_args()
    data = extract(args.har)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f"Exportados {len(data['players'])} atletas, {len(data['clubs'])} clubes e {len(data['metrics'])} métricas para {args.output}")


if __name__ == '__main__':
    main()