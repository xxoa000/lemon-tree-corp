from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    assert client.get('/health').json() == {'status': 'ok'}

def test_org_has_eleven_members():
    assert len(client.get('/api/v1/employees').json()) == 11

def test_three_teams_and_all_members():
    teams = client.get('/api/v1/teams').json()
    assert len(teams) == 3
    assert sum(len(team['member_ids']) for team in teams) == 10  # CEO is outside the three teams

def test_manager_is_external_and_has_rank():
    manager = client.get('/api/v1/control-center/manager').json()
    assert manager['rank'] == '부장'
    assert manager['external_to_org'] is True
    assert manager['invocation_semantics'] == 'OWNER_DESIGN_REQUEST'
