from app import create_app
def test_health():
    app=create_app({"TESTING":True})
    c=app.test_client()
    r=c.get("/health")
    assert r.status_code==200
    assert r.get_json()["status"]=="ok"

def test_health_reports_v5_and_configuration_state(tmp_path):
    app=create_app({"TESTING":True,"DATA_DIR":str(tmp_path / "data"),"MEDIA_DIR":str(tmp_path / "media"),"OPENAI_API_KEY":"","FAL_KEY":""})
    body=app.test_client().get("/health").get_json()
    assert body["version"]=="mrt-dental-ai-v5"
    assert body["ai_configured"] is False
    assert body["media_configured"] is False
    assert "time" in body


def test_api_404_is_json(tmp_path):
    app=create_app({"TESTING":True,"DATA_DIR":str(tmp_path / "data"),"MEDIA_DIR":str(tmp_path / "media")})
    r=app.test_client().get("/api/does-not-exist")
    assert r.status_code==404
    assert "error" in r.get_json()
