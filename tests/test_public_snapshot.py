import csv
from pathlib import Path
from scripts.build_public_snapshot import build


def test_public_data_transform(tmp_path):
    folder=tmp_path/'data/snapshots'
    folder.mkdir(parents=True)
    with (folder/'bra_a_2026.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['player_id','player','club','position','position_label','age','nationality','minutes','rating','goals_total','xg_total'])
        w.writeheader()
        w.writerow({'player_id':'1','player':'Teste','club':'Clube A','position':'CF','position_label':'Atacante','age':'20','nationality':'Brasil','minutes':'900','rating':'7.1','goals_total':'5','xg_total':'6.2'})
    with (folder/'team_bra_a_2026.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['team','rating_team','possession_percentage_team'])
        w.writeheader();w.writerow({'team':'Clube A','rating_team':'7.1','possession_percentage_team':'51.2'})
    j=build(tmp_path)
    assert len(j['players'])==1
    assert len(j['clubs'])==1
    assert j['players'][0]['s']['1']==5
    assert j['players'][0]['s']['26']==6.2
    assert j['clubs'][0]['s']['202']==51.2