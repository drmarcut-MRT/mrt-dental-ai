from app import create_app


def test_operational_page_and_assets():
    client = create_app({"TESTING": True}).test_client()
    page = client.get("/")
    assert page.status_code == 200
    for marker in (b'brief-form', b'brief-list', b'media-form', b'content-library', b'/static/app.js'):
        assert marker in page.data
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/app.css").status_code == 200
