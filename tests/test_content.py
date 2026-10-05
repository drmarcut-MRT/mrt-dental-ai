from app import create_app
from app.services.content import save_proposals

def make_app(tmp_path):
    return create_app({"TESTING":True,"DATA_DIR":str(tmp_path / "data"),"MEDIA_DIR":str(tmp_path / "media")})

def test_create_brief(tmp_path):
    c=make_app(tmp_path).test_client()
    r=c.post("/api/content/briefs",json={"topic":"Implant dentar","platform":"Instagram","format":"Reel","tone":"Profesional","instructions":"Explică simplu"})
    assert r.status_code==201
    assert r.get_json()["topic"]=="Implant dentar"
    assert len(c.get("/api/content/briefs").get_json())==1

def test_reject_empty_topic(tmp_path):
    c=make_app(tmp_path).test_client()
    r=c.post("/api/content/briefs",json={"topic":"   "})
    assert r.status_code==400

def test_save_missing_proposal_does_not_create_one(tmp_path):
    c=make_app(tmp_path).test_client()
    brief=c.post("/api/content/briefs",json={"topic":"Igienizare"}).get_json()
    r=c.put(f'/api/content/proposals/{brief["id"]}',json={"content":"text"})
    assert r.status_code==404
    assert c.get("/api/content/proposals").get_json()=={}

def test_finalize_moves_content_to_library(tmp_path):
    app=make_app(tmp_path); c=app.test_client()
    brief=c.post("/api/content/briefs",json={"topic":"Implant dentar","platform":"Instagram","format":"Reel"}).get_json()
    with app.app_context():
        save_proposals({str(brief["id"]):{"content":"Text aprobat","status":"draft"}})
    r=c.post(f'/api/content/proposals/{brief["id"]}/finalize')
    assert r.status_code==200
    body=r.get_json()
    assert body["proposal"]["status"]=="final"
    lib=c.get("/api/content/library").get_json()
    assert len(lib)==1 and lib[0]["content"]=="Text aprobat"

def test_complete_content_flow_without_external_ai(tmp_path, monkeypatch):
    app=make_app(tmp_path); c=app.test_client()
    brief=c.post("/api/content/briefs",json={"topic":"Implant dentar","platform":"Instagram","format":"Reel","tone":"Profesional"}).get_json()
    monkeypatch.setattr("app.services.content.ai_text", lambda prompt: "Text AI sigur pentru test")
    generated=c.post(f'/api/content/proposals/{brief["id"]}/generate')
    assert generated.status_code==200
    assert generated.get_json()["status"]=="draft"
    saved=c.put(f'/api/content/proposals/{brief["id"]}',json={"content":"Text editat și aprobat"})
    assert saved.status_code==200
    finalized=c.post(f'/api/content/proposals/{brief["id"]}/finalize')
    assert finalized.status_code==200
    assert finalized.get_json()["library_item"]["content"]=="Text editat și aprobat"
    assert c.get("/api/content/library").get_json()[0]["status"]=="approved"


def test_delete_brief_removes_only_its_proposal_and_library_item(tmp_path, monkeypatch):
    app = make_app(tmp_path); client = app.test_client()
    monkeypatch.setattr('app.services.content.ai_text', lambda prompt: 'Text de test')
    first = client.post('/api/content/briefs', json={'topic': 'Primul'}).get_json()['id']
    second = client.post('/api/content/briefs', json={'topic': 'Al doilea'}).get_json()['id']
    for bid in (first, second):
        assert client.post(f'/api/content/proposals/{bid}/generate').status_code == 200
        assert client.post(f'/api/content/proposals/{bid}/finalize').status_code == 200
    assert client.delete(f'/api/content/briefs/{first}').status_code == 204
    assert [row['id'] for row in client.get('/api/content/briefs').get_json()] == [second]
    assert list(client.get('/api/content/proposals').get_json()) == [second]
    assert [row['brief_id'] for row in client.get('/api/content/library').get_json()] == [second]
    assert client.post(f'/api/content/proposals/{first}/generate').status_code == 404
    assert client.delete(f'/api/content/briefs/{first}').status_code == 404


def test_delete_missing_brief_does_not_change_data(tmp_path):
    client = make_app(tmp_path).test_client()
    brief = client.post('/api/content/briefs', json={'topic': 'Păstrat'}).get_json()
    assert client.delete('/api/content/briefs/unknown').status_code == 404
    assert client.get('/api/content/briefs').get_json() == [brief]


def test_edit_and_revision_need_new_approval_and_preserve_approved_snapshot(tmp_path, monkeypatch):
    client = make_app(tmp_path).test_client()
    monkeypatch.setattr('app.services.content.ai_text', lambda prompt: 'Prima versiune')
    bid = client.post('/api/content/briefs', json={'topic': 'Test'}).get_json()['id']
    client.post(f'/api/content/proposals/{bid}/generate')
    client.post(f'/api/content/proposals/{bid}/finalize')
    same = client.put(f'/api/content/proposals/{bid}', json={'content': 'Prima versiune'}).get_json()
    assert same['status'] == 'final'
    edited = client.put(f'/api/content/proposals/{bid}', json={'content': 'Modificat'}).get_json()
    assert edited['status'] == 'draft' and 'approved_at' not in edited
    assert client.get('/api/content/library').get_json()[0]['content'] == 'Prima versiune'
    client.post(f'/api/content/proposals/{bid}/finalize')
    monkeypatch.setattr('app.services.content.ai_text', lambda prompt: 'Revizuit')
    revised = client.post(f'/api/content/proposals/{bid}/revise', json={'instruction': 'Mai scurt'}).get_json()
    assert revised['status'] == 'draft' and 'approved_at' not in revised
    client.post(f'/api/content/proposals/{bid}/finalize')
    library = client.get('/api/content/library').get_json()
    assert len(library) == 1 and library[0]['content'] == 'Revizuit'


def test_invalid_content_payloads_are_rejected(tmp_path, monkeypatch):
    client = make_app(tmp_path).test_client()
    assert client.post('/api/content/briefs', json={'topic': 1}).status_code == 400
    assert client.post('/api/content/briefs', json={'topic': 'x', 'instructions': None}).status_code == 400
    monkeypatch.setattr('app.services.content.ai_text', lambda prompt: 'Test')
    bid = client.post('/api/content/briefs', json={'topic': 'Test'}).get_json()['id']
    client.post(f'/api/content/proposals/{bid}/generate')
    assert client.put(f'/api/content/proposals/{bid}', json={'content': None}).status_code == 400
    assert client.post(f'/api/content/proposals/{bid}/revise', json={'instruction': []}).status_code == 400
