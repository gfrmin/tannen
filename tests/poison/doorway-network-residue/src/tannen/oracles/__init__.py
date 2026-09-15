"""CONTROL (must pass): the doorway itself may open a connection (BRIEF §5.3)."""
import http.client


def connect(host: str) -> http.client.HTTPSConnection:
    return http.client.HTTPSConnection(host)
