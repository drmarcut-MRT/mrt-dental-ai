import socket
import pytest


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch):
    """All tests must mock providers; no paid or accidental network calls."""
    def blocked(*args, **kwargs):
        raise AssertionError("External network is disabled during project tests")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
