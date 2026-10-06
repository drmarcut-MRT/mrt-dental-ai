import base64
import pytest
from app import create_app


def settings(tmp_path):
    return {'TESTING': True, 'APP_ENVIRONMENT': 'staging', 'RAILWAY_ENVIRONMENT_NAME': '',
            'STAGING_AUTH_USERNAME': 'test-user', 'STAGING_AUTH_PASSWORD': 'test-only-' + 'x' * 32,
            'DATA_DIR': str(tmp_path / 'data'), 'MEDIA_DIR': str(tmp_path / 'media')}


def headers(config, password=None):
    value = config['STAGING_AUTH_USERNAME'] + ':' + (password or config['STAGING_AUTH_PASSWORD'])
    return {'Authorization': 'Basic ' + base64.b64encode(value.encode()).decode()}


@pytest.mark.parametrize('method,path', [('GET', '/'), ('GET', '/static/app.js'),
    ('GET', '/api/content/briefs'), ('POST', '/api/content/briefs'),
    ('GET', '/api/content/library'), ('GET', '/api/media'), ('GET', '/media/example.mp4'),
    ('POST', '/api/media/generate'), ('POST', '/api/transcribe'), ('DELETE', '/api/content/briefs/example')])
def test_staging_blocks_ui_api_files_and_writes(tmp_path, method, path):
    client = create_app(settings(tmp_path)).test_client()
    response = client.open(path, method=method)
    assert response.status_code == 401
    assert 'Basic realm=' in response.headers['WWW-Authenticate']
    assert response.headers['Cache-Control'] == 'no-store'
    assert not (tmp_path / 'data' / 'briefs.json').exists()


@pytest.mark.parametrize('authorization', ['', 'Basic invalid', 'Bearer example'])
def test_malformed_auth_does_not_bypass_protection(tmp_path, authorization):
    client = create_app(settings(tmp_path)).test_client()
    assert client.get('/', headers={'Authorization': authorization}).status_code == 401


def test_wrong_password_and_valid_credentials(tmp_path):
    config = settings(tmp_path); client = create_app(config).test_client()
    assert client.get('/', headers=headers(config, 'wrong')).status_code == 401
    response = client.get('/', headers=headers(config))
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    brief = client.post('/api/content/briefs', json={'topic': 'Demonstration'}, headers=headers(config))
    assert brief.status_code == 201
    assert client.get('/api/content/briefs', headers=headers(config)).json[0]['id'] == brief.json['id']


def test_health_probe_remains_read_only_and_public(tmp_path):
    client = create_app(settings(tmp_path)).test_client()
    assert client.get('/health').status_code == 200
    assert client.head('/health').status_code == 200
    assert client.post('/health').status_code == 401


@pytest.mark.parametrize('field,value', [('STAGING_AUTH_USERNAME', ''), ('STAGING_AUTH_PASSWORD', ''),
                                        ('STAGING_AUTH_PASSWORD', 'short')])
def test_staging_cannot_start_without_valid_credentials(tmp_path, field, value):
    config = settings(tmp_path); config[field] = value
    with pytest.raises(RuntimeError): create_app(config)


@pytest.mark.parametrize('origin', ['https://other.example', 'null', 'https://[invalid'])
def test_cross_origin_writes_are_blocked(tmp_path, origin):
    config = settings(tmp_path); client = create_app(config).test_client()
    response = client.post('/api/content/briefs', json={'topic': 'Blocked'},
                           headers={**headers(config), 'Origin': origin})
    assert response.status_code == 403
    assert client.get('/api/content/briefs', headers=headers(config)).json == []


def test_same_origin_write_allowed(tmp_path):
    config = settings(tmp_path); client = create_app(config).test_client()
    assert client.post('/api/content/briefs', json={'topic': 'Allowed'},
        headers={**headers(config), 'Origin': 'http://localhost'}).status_code == 201
