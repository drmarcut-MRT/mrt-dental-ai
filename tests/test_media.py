import io
from unittest.mock import patch
import pytest
from app import create_app
from app.services import media


@pytest.fixture
def media_app(tmp_path):
    return create_app({"TESTING": True, "DATA_DIR": str(tmp_path / "data"),
                       "MEDIA_DIR": str(tmp_path / "media"), "FAL_KEY": "test"})


def seed(app, status="pending"):
    rec = {"id": "video1", "kind": "video", "status": status, "prompt": "Test", "saved": False,
           "status_url": "https://queue.fal.run/test/status", "response_url": "https://queue.fal.run/test/result",
           "cancel_url": "https://queue.fal.run/test/cancel"}
    with app.app_context(): media.upsert(rec)
    return rec


def test_video_completion_downloads_file_and_is_idempotent(media_app, monkeypatch):
    seed(media_app)
    client = media_app.test_client()
    queue = iter([{"status": "IN_PROGRESS"}, {"status": "COMPLETED"}, {"video": {"url": "https://cdn.example/test.mp4"}}])
    monkeypatch.setattr(media, "_queue_request", lambda *args: next(queue))
    assert client.post('/api/media/video1/refresh').get_json()['status'] == 'processing'
    with patch.object(media.urllib.request, "urlopen", return_value=io.BytesIO(b"video bytes")) as download:
        result = client.post('/api/media/video1/refresh')
        assert result.status_code == 200
        rec = result.get_json()
        assert rec['status'] == 'ready'
        assert client.get('/uploads/' + rec['filename']).data == b'video bytes'
        assert client.post('/api/media/video1/refresh').get_json()['filename'] == rec['filename']
        assert download.call_count == 1
    assert len(client.get('/api/library').get_json()) == 1


def test_failed_cancel_keeps_job_and_delete_does_not_remove_it(media_app, monkeypatch):
    seed(media_app)
    def fail(*args): raise RuntimeError('provider refused')
    monkeypatch.setattr(media, '_queue_request', fail)
    client = media_app.test_client()
    assert client.post('/api/media/video1/cancel').status_code == 502
    assert client.delete('/api/media/video1').status_code == 502
    assert client.get('/api/media').get_json()[0]['status'] == 'pending'


def test_cancel_is_idempotent_and_completed_job_cannot_be_cancelled(media_app, monkeypatch):
    seed(media_app)
    calls = []
    monkeypatch.setattr(media, '_queue_request', lambda *args: calls.append(args) or {})
    client = media_app.test_client()
    assert client.post('/api/media/video1/cancel').get_json()['status'] == 'cancelled'
    assert client.post('/api/media/video1/cancel').status_code == 200
    assert len(calls) == 1 and calls[0][1] == 'PUT'
    seed(media_app, 'ready')
    assert client.post('/api/media/video1/cancel').status_code == 409


@pytest.mark.parametrize('result,expected', [({'status': 'FAILED'}, 'failed'), ({'status': 'CANCELLED'}, 'cancelled')])
def test_terminal_provider_states(media_app, monkeypatch, result, expected):
    seed(media_app)
    monkeypatch.setattr(media, '_queue_request', lambda *args: result)
    assert media_app.test_client().post('/api/media/video1/refresh').get_json()['status'] == expected


def test_missing_video_result_stays_retryable(media_app, monkeypatch):
    seed(media_app)
    responses = iter([{'status': 'COMPLETED'}, {}])
    monkeypatch.setattr(media, '_queue_request', lambda *args: next(responses))
    client = media_app.test_client()
    assert client.post('/api/media/video1/refresh').status_code == 502
    assert client.get('/api/media').get_json()[0]['status'] == 'pending'


def test_queue_url_never_sends_key_to_another_host(media_app):
    with media_app.app_context(), patch.object(media.urllib.request, 'urlopen') as external:
        with pytest.raises(ValueError): media._queue_request('https://example.com/status')
        external.assert_not_called()


def test_missing_and_invalid_media(media_app):
    client = media_app.test_client()
    assert client.post('/api/media/generate', data={'kind': 'other', 'prompt': 'test'}).status_code == 400
    assert client.post('/api/media/missing/refresh').status_code == 404
    assert client.post('/api/media/missing/cancel').status_code == 404


def test_save_and_delete_ready_media(media_app, tmp_path):
    from pathlib import Path
    seed(media_app, 'ready')
    directory = Path(media_app.config['MEDIA_DIR']); directory.mkdir()
    (directory / 'test.mp4').write_bytes(b'video')
    with media_app.app_context():
        rec = media.find_record('video1'); rec['filename'] = 'test.mp4'; media.upsert(rec)
    client = media_app.test_client()
    assert client.post('/api/media/video1/save').get_json()['saved'] is True
    assert client.post('/api/media/video1/save').status_code == 200
    assert len(client.get('/api/library').get_json()) == 1
    assert client.delete('/api/media/video1').status_code == 204
    assert not (directory / 'test.mp4').exists()
    assert client.get('/api/library').get_json() == []
    assert client.get('/uploads/test.mp4').status_code == 404


def test_cannot_save_pending_or_missing_media(media_app):
    seed(media_app)
    client = media_app.test_client()
    assert client.post('/api/media/video1/save').status_code == 409
    assert client.post('/api/media/missing/save').status_code == 404


def test_delete_pending_video_requires_successful_provider_cancel(media_app, monkeypatch):
    seed(media_app)
    calls = []
    monkeypatch.setattr(media, '_queue_request', lambda *args: calls.append(args) or {})
    client = media_app.test_client()
    assert client.delete('/api/media/video1').status_code == 204
    assert calls[0][1] == 'PUT'
    assert client.get('/api/media').get_json() == []


def test_provider_explicitly_refusing_cancel_does_not_mark_cancelled(media_app, monkeypatch):
    seed(media_app)
    monkeypatch.setattr(media, '_queue_request', lambda *args: {'status': 'ALREADY_COMPLETED'})
    client = media_app.test_client()
    assert client.post('/api/media/video1/cancel').status_code == 409
    assert client.get('/api/media').get_json()[0]['status'] == 'pending'


def test_generate_image_and_video_routes_persist_mocked_results(media_app, monkeypatch):
    monkeypatch.setattr('app.routes.media.generate_image', lambda prompt: 'test.png')
    calls = []
    def submit(*args):
        calls.append(args)
        return {'request_id': 'r', 'status_url': 'https://queue.fal.run/status',
                'response_url': 'https://queue.fal.run/result', 'cancel_url': 'https://queue.fal.run/cancel'}
    monkeypatch.setattr('app.routes.media.submit_video', submit)
    client = media_app.test_client()
    image = client.post('/api/media/generate', data={'kind': 'image', 'prompt': 'imagine'})
    assert image.status_code == 201 and image.get_json()['status'] == 'ready'
    video = client.post('/api/media/generate', data={'kind': 'video', 'prompt': 'video', 'generate_audio': '1'})
    assert video.status_code == 201 and video.get_json()['status'] == 'pending'
    assert calls == [('video', '9:16', '5', '720p', True)]
    assert len(client.get('/api/media').get_json()) == 2


def test_submit_video_checks_response_and_supplies_missing_cancel_url(media_app):
    import json
    with media_app.app_context():
        with patch.object(media.urllib.request, 'urlopen', return_value=io.BytesIO(b'{}')):
            with pytest.raises(RuntimeError): media.submit_video('test', '9:16', '5', '720p', False)
        response = {'request_id': 'test/id', 'status_url': 'https://queue.fal.run/status', 'response_url': 'https://queue.fal.run/result'}
        with patch.object(media.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps(response).encode())):
            result = media.submit_video('test', '9:16', '5', '720p', False)
        assert result['cancel_url'].endswith('/requests/test%2Fid/cancel')
