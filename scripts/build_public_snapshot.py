"""Build a publishable LATAMDATA snapshot from this repository's existing CSV data.

This avoids committing third-party HAR capture data to the public GitHub branch.
It purposefully exports only metrics supported by the repository snapshots.
"""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

METRIC_FIELDS = [
    (0, 'rating', 'Índice geral', 'geral', 'ratio'),
    (1, 'goals_total', 'Gols', 'gols', 'count'),
    (2, 'assists_total', 'Assistências', 'gols', 'count'),
    (11, 'shots90', 'Finalizações / 90', 'chute', 'ratio'),
    (12, 'shots_on_target90', 'Finalizações no alvo / 90', 'chute', 'ratio'),
    (26, 'xg_total', 'Gols esperados (xG)', 'xg', 'count'),
    (27, 'xa_total', 'Assistências esperadas (xA)', 'xg', 'count'),
    (38, 'passes90', 'Passes / 90', 'passe', 'ratio'),
    (41, 'key_pass90', 'Passes decisivos / 90', 'criacao', 'ratio'),
    (72, 'accurate_pass_team', 'Passes certos', 'passe', 'count'),
    (91, 'dribbles90', 'Dribles / 90', 'drible', 'ratio'),
    (106, 'tackles90', 'Desarmes / 90', 'defesa', 'ratio'),
    (109, 'interceptions90', 'Interceptações / 90', 'defesa', 'ratio'),
    (114, 'recoveries90', 'Recuperações / 90', 'defesa', 'ratio'),
    (125, 'saves90', 'Defesas / 90', 'goleiro', 'ratio'),
]
TEAM_FIELDS = {
    0: 'rating_team', 26: 'expected_goals_team',
    200: 'goals_team_match', 201: 'goals_conceded_team_match',
    202: 'possession_percentage_team', 203: 'clean_sheet_team',
    204: 'expected_goals_conceded_team', 205: 'big_chance_team',
    206: 'accurate_pass_team', 207: 'ontarget_scoring_att_team',
    208: 'total_tackle_team', 209: 'interception_team',
    210: 'effective_clearance_team',
}
TEAM_METRICS = [
    (200,'Gols por partida','gols','ratio'),
    (201,'Gols sofridos por partida','defesa','ratio'),
    (202,'Posse de bola (%)','passe','pct'),
    (203,'Jogos sem sofrer gols','defesa','count'),
    (204,'xG sofrido','xg','count'),
    (205,'Grandes chances','criacao','count'),
    (206,'Passes certos por partida','passe','ratio'),
    (207,'Finalizações no alvo por partida','chute','ratio'),
    (208,'Desarmes por partida','defesa','ratio'),
    (209,'Interceptações por partida','defesa','ratio'),
    (210,'Cortes por partida','defesa','ratio'),
]

CAT_NAMES = {'geral':'Visão Geral','gols':'Gols & Finalização','chute':'Chutes','xg':'Modelos (xG)','passe':'Passes','criacao':'Criação','drible':'Dribles','defesa':'Defesa','goleiro':'Goleiros'}


def val(row,key):
    try:
        n=float(row.get(key, ''))
        return n if n==n else None
    except (ValueError,TypeError):
        return None


def build(snapshot_root:Path):
    player_file=snapshot_root/'data/snapshots/bra_a_2026.csv'
    club_file=snapshot_root/'data/snapshots/team_bra_a_2026.csv'
    if not player_file.is_file() or not club_file.is_file():
        raise FileNotFoundError('Snapshots bra_a_2026.csv e team_bra_a_2026.csv não encontrados no repositório original.')
    with player_file.open(encoding='utf-8-sig',newline='') as f:
        raw=list(csv.DictReader(f))
    players=[]
    for p in raw:
        data={str(k):val(p,field) for k,field,*_ in METRIC_FIELDS if val(p,field) is not None and field!='accurate_pass_team'}
        players.append({'id':p.get('player_id') or f"{p['player']}|{p['club']}", 'name':p['player'],
            'club':p['club'], 'position':p.get('position_label') or p.get('position') or '-',
            'group':p.get('position') or '-', 'age':val(p,'age'), 'nation':p.get('nationality') or '-',
            'minutes':val(p,'minutes') or 0, 'matches':0, 'starts':0, 's':data})
    with club_file.open(encoding='utf-8-sig',newline='') as f:
        rawclubs=list(csv.DictReader(f))
    clubs=[]
    for t in rawclubs:
        stats={str(k):val(t,field) for k,field in TEAM_FIELDS.items() if val(t,field) is not None}
        clubs.append({'name':t['team'],'matches':None,'roster':sum(p['club']==t['team'] for p in players),
            's':stats,'table':{}})
    metrics=[{'id':i,'en':field,'pt':name,'cat':cat,'type':typ,'neg':False} for i,field,name,cat,typ in METRIC_FIELDS]
    metrics += [{'id':i,'en':name,'pt':name,'cat':cat,'type':typ,'neg':i==201} for i,name,cat,typ in TEAM_METRICS]
    return {'season':2026,'updated':datetime.now(timezone.utc).strftime('%d/%m/%Y'),
      'source':'Snapshots LATAMDATA do repositório · FotMob (integração não oficial)',
      'metrics':metrics,'cats':{c:{'pt':n} for c,n in CAT_NAMES.items()},
      'players':players,'clubs':clubs}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'frontend/public/data/serie-a-2026.json')
    ap.add_argument('--if-missing',action='store_true')
    args=ap.parse_args()
    if args.if_missing and args.output.exists():
        print('Usando snapshot já existente:',args.output)
        return
    data=build(args.source_root)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print('LATAMDATA snapshot:',len(data['players']),'players,',len(data['clubs']),'clubs',args.output)

if __name__=='__main__':
    main()