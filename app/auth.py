"""Protect staging UI and APIs with HTTP Basic authentication over HTTPS."""
import hmac
from urllib.parse import urlsplit
from flask import jsonify, request


def validate_credentials(username, password):
    if not username or any(c in username for c in ':\r\n'):
        raise RuntimeError('Configure a valid STAGING_AUTH_USERNAME.')
    if len(password) < 32:
        raise RuntimeError('Configure a random STAGING_AUTH_PASSWORD of at least 32 characters.')


def configure_auth(app):
    username = app.config.get('STAGING_AUTH_USERNAME', '')
    password = app.config.get('STAGING_AUTH_PASSWORD', '')
    environment = app.config.get('RAILWAY_ENVIRONMENT_NAME') or app.config.get('APP_ENVIRONMENT')
    required = environment == 'staging' or bool(username or password)
    if not required:
        return
    validate_credentials(username, password)

    @app.before_request
    def authenticate_staging():
        # Railway's health probe carries no credentials. It can only read health.
        if request.path == '/health' and request.method in ('GET', 'HEAD'):
            return None
        auth = request.authorization
        supplied_user = (auth.username or '') if auth and auth.type.lower() == 'basic' else ''
        supplied_password = (auth.password or '') if auth and auth.type.lower() == 'basic' else ''
        user_ok = hmac.compare_digest(supplied_user.encode('utf-8'), username.encode('utf-8'))
        password_ok = hmac.compare_digest(supplied_password.encode('utf-8'), password.encode('utf-8'))
        if not (user_ok and password_ok):
            response = jsonify(error='Autentificare necesară pentru staging.')
            response.status_code = 401
            response.headers['WWW-Authenticate'] = 'Basic realm="MRT staging", charset="UTF-8"'
            return response
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('Origin')
            cross_site = request.headers.get('Sec-Fetch-Site') == 'cross-site'
            if origin:
                try:
                    parsed = urlsplit(origin)
                    cross_site = cross_site or parsed.scheme not in ('http', 'https') or parsed.netloc.lower() != request.host.lower()
                except ValueError:
                    cross_site = True
            if cross_site:
                return jsonify(error='Cerere din altă origine refuzată.'), 403

    @app.after_request
    def protect_responses(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response
