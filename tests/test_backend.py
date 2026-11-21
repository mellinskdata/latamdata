from backend.main import _parse_scoreboard, health


def test_api_health():
    assert health()['ok'] is True


def test_scoreboard_parser():
    payload={'events':[{'id':'456','date':'2026-10-20T00:00Z',
        'status':{'type':{'description':'Finalizado','completed':True}},
        'competitions':[{'competitors':[
            {'homeAway':'home','score':'2','team':{'displayName':'Mandante'}},
            {'homeAway':'away','score':'1','team':{'displayName':'Visitante'}}]}]}]}
    result=_parse_scoreboard(payload)
    assert result[0]['home']=='Mandante'
    assert result[0]['away_score']==1
    assert result[0]['completed'] is True


def test_missing_score_is_none():
    payload={'events':[{'id':'new','competitions':[{'competitors':[
        {'homeAway':'home','team':{'name':'A'}},{'homeAway':'away','team':{'name':'B'}}]}]}]}
    result=_parse_scoreboard(payload)
    assert result[0]['home_score'] is None
    assert result[0]['away_score'] is None