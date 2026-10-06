import pytest
from deploy.start_staging import build_command
from tools.check_sensitive import PATTERNS


def config():
    return {'RAILWAY_ENVIRONMENT_NAME': 'staging', 'SECRET_KEY': 'x' * 48,
            'DATA_DIR': '/data/data', 'MEDIA_DIR': '/data/media', 'PORT': '9000',
            'STAGING_AUTH_USERNAME': 'test-user', 'STAGING_AUTH_PASSWORD': 'test-only-' + 'x' * 32}


def test_staging_uses_railway_port_and_single_worker():
    command = build_command(config())
    assert command[command.index('--bind') + 1] == '0.0.0.0:9000'
    assert command[command.index('--workers') + 1] == '1'
    assert command[command.index('--threads') + 1] == '1'
    assert command[-1] == 'run:app'


def test_production_cannot_be_overridden_by_local_staging_flag():
    data = config(); data.update(RAILWAY_ENVIRONMENT_NAME='production', APP_ENVIRONMENT='staging')
    with pytest.raises(RuntimeError, match='only starts'): build_command(data)


@pytest.mark.parametrize('field,value', [('SECRET_KEY', ''), ('SECRET_KEY', 'replace-with-a-long-random-value'),
                                      ('DATA_DIR', './data'), ('MEDIA_DIR', './media'), ('PORT', 'invalid'), ('PORT', '0'),
                                      ('STAGING_AUTH_USERNAME', ''), ('STAGING_AUTH_USERNAME', 'bad:user'),
                                      ('STAGING_AUTH_PASSWORD', ''), ('STAGING_AUTH_PASSWORD', 'short')])
def test_staging_rejects_unsafe_configuration(field, value):
    data = config(); data[field] = value
    with pytest.raises(RuntimeError): build_command(data)


def test_secret_patterns_identify_synthetic_tokens_without_real_credentials():
    assert PATTERNS['OpenAI token'].search(('sk-' + 'a' * 24).encode())
    # Assemble the fixture so it is not itself a leaked credential URL in Git.
    assert PATTERNS['credential URL'].search(('https://' + 'user:password' + '@example.com').encode())
    assert not PATTERNS['OpenAI token'].search(b'OPENAI_API_KEY=')
