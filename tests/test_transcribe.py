import io
from app import create_app


def test_transcribe_romanian_passes_complete_audio_to_service(monkeypatch):
    captured = []
    def transcribe(filename, data, mime):
        captured.append((filename, data, mime))
        return 'Text în română'
    monkeypatch.setattr('app.routes.transcribe.transcribe_audio', transcribe)
    client = create_app({'TESTING': True}).test_client()
    payload = b'a' * 500
    result = client.post('/api/transcribe', data={'audio': (io.BytesIO(payload), 'dictare.webm', 'audio/webm')})
    assert result.status_code == 200
    assert result.get_json() == {'text': 'Text în română', 'language': 'ro'}
    assert captured == [('dictare.webm', payload, 'audio/webm')]


def test_transcription_rejects_missing_small_and_wrong_format(monkeypatch):
    def forbidden(*args): raise AssertionError('Provider should not be called')
    monkeypatch.setattr('app.routes.transcribe.transcribe_audio', forbidden)
    client = create_app({'TESTING': True}).test_client()
    assert client.post('/api/transcribe').status_code == 400
    assert client.post('/api/transcribe', data={'audio': (io.BytesIO(b'a'), 'a.webm', 'audio/webm')}).status_code == 400
    assert client.post('/api/transcribe', data={'audio': (io.BytesIO(b'a'*500), 'a.txt', 'text/plain')}).status_code == 415


def test_transcribe_limits_request_size():
    client = create_app({'TESTING': True, 'MAX_CONTENT_LENGTH': 512}).test_client()
    result = client.post('/api/transcribe', data={'audio': (io.BytesIO(b'a'*1000), 'a.webm', 'audio/webm')})
    assert result.status_code == 413 and 'error' in result.get_json()


def test_transcribe_provider_error_is_sanitized(monkeypatch):
    def fail(*args): raise RuntimeError('secret provider detail')
    monkeypatch.setattr('app.routes.transcribe.transcribe_audio', fail)
    client = create_app({'TESTING': True}).test_client()
    result = client.post('/api/transcribe', data={'audio': (io.BytesIO(b'a'*500), 'a.webm', 'audio/webm')})
    assert result.status_code == 502
    assert b'secret provider detail' not in result.data
