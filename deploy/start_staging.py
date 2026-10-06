"""Fail closed outside staging; use one synchronous worker for JSON storage."""
import os


def build_command(environ):
    environment = environ.get("RAILWAY_ENVIRONMENT_NAME") or environ.get("APP_ENVIRONMENT")
    if environment != "staging":
        raise RuntimeError("This launcher only starts the staging environment.")
    username = environ.get("STAGING_AUTH_USERNAME", "")
    if not username or any(c in username for c in ':\r\n'):
        raise RuntimeError("Configure a valid STAGING_AUTH_USERNAME.")
    if len(environ.get("STAGING_AUTH_PASSWORD", "")) < 32:
        raise RuntimeError("Configure a random STAGING_AUTH_PASSWORD of at least 32 characters.")
    secret = environ.get("SECRET_KEY", "")
    if len(secret) < 32 or secret in ("dev-only-change-me", "replace-with-a-long-random-value"):
        raise RuntimeError("Configure a dedicated staging SECRET_KEY of at least 32 characters.")
    if environ.get("DATA_DIR") != "/data/data" or environ.get("MEDIA_DIR") != "/data/media":
        raise RuntimeError("Staging requires DATA_DIR=/data/data and MEDIA_DIR=/data/media on its own volume.")
    try:
        port = int(environ.get("PORT", "8080"))
    except ValueError:
        raise RuntimeError("PORT must be a valid port number.") from None
    if not 1 <= port <= 65535:
        raise RuntimeError("PORT must be a valid port number.")
    return ["gunicorn", "--bind", f"0.0.0.0:{port}", "--workers", "1", "--threads", "1",
            "--timeout", "600", "--graceful-timeout", "600", "run:app"]


if __name__ == "__main__":
    command = build_command(os.environ)
    os.execvp(command[0], command)
