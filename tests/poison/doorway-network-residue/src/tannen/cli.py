"""PAYLOAD (network): a live socket-opening stdlib module absent from L4.9's NETWORK literal."""
import imaplib


def inbox(host: str) -> imaplib.IMAP4_SSL:
    return imaplib.IMAP4_SSL(host)
