"""PAYLOAD (network): a dotted import whose package is not in L4.9's NETWORK literal."""
import xmlrpc.client


def remote(url: str) -> xmlrpc.client.ServerProxy:
    return xmlrpc.client.ServerProxy(url)
