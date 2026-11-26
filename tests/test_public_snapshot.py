import csv
import os
import subprocess
from pathlib import Path
from scripts.build_public_snapshot import build, provenance, val


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
    assert j['players'][0]['matches'] is None
    assert j['players'][0]['starts'] is None


def test_snapshot_source_date_is_not_build_date(tmp_path):
    file = tmp_path / 'snapshot.csv'
    file.write_text('data')
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    subprocess.run(['git', '-C', str(tmp_path), 'add', 'snapshot.csv'], check=True)
    subprocess.run(['git', '-C', str(tmp_path), '-c', 'user.name=Test', '-c',
                    'user.email=test@example.invalid', 'commit', '-qm', 'source'], check=True,
                   env={**os.environ, 'GIT_AUTHOR_DATE': '2026-10-20T12:00:00Z',
                        'GIT_COMMITTER_DATE': '2026-10-20T12:00:00Z'})
    meta = provenance(tmp_path, [file])
    assert meta['updated'] == '20/10/2026'
    assert meta['source_updated_at'].startswith('2026-10-20')
    assert len(meta['source_commit']) == 40
    shallow_root = tmp_path / 'shallow'
    subprocess.run(['git', 'clone', '-q', '--depth', '1', tmp_path.as_uri(), str(shallow_root)], check=True)
    assert provenance(shallow_root, [shallow_root / 'snapshot.csv'])['source_updated_at'] is None
    file.write_text('changed data')
    dirty = provenance(tmp_path, [file])
    assert dirty['source_commit'] is None
    assert dirty['source_updated_at'] is None
    assert dirty['source_files'] != meta['source_files']


def test_nonfinite_metrics_stay_missing():
    for value in ('nan', 'inf', '-inf', '', 'bad'):
        assert val({'x': value}, 'x') is None
    assert val({'x': '0'}, 'x') == 0
