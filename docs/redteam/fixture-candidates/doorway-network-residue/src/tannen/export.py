"""PAYLOAD (network): two more socket-opening stdlib modules L4.9 does not name, one of them
imported inside a function body — a scan of what the package CAN do, not only what it does
at import time."""
import poplib


def serve() -> None:
    import socketserver

    socketserver.TCPServer(("127.0.0.1", 0), socketserver.BaseRequestHandler)


def mail(host: str) -> poplib.POP3:
    return poplib.POP3(host)
