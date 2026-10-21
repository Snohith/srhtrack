"""Article URL validation and stable identity.

RSS links are untrusted.  We never fetch an article URL server-side (that was
the old OG-image scraper); we only put links into Telegram messages.  Even so,
only public http(s) links are allowed so a malformed feed cannot turn an alert
into a file:, javascript:, localhost, or cloud-metadata URL.
"""
from __future__ import annotations

import hashlib
import ipaddress
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

MAX_URL_LENGTH = 2048

_TRACKING_PARAMS = {
    "fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid",
    "ref", "referrer", "source", "spm", "igshid", "yclid",
}
_UNSAFE_HOSTS = {
    "localhost", "metadata", "metadata.google.internal", "metadata.goog",
    "instance-data", "169.254.169.254",
}
_UNSAFE_SUFFIXES = (".localhost", ".local", ".internal", ".home.arpa")
_DASH_CHARS_RE = re.compile("[\u2010\u2011\u2012\u2013\u2014\u2015]")


def normalize_title(title):
    """Folds a headline into a stable comparison key.

    Google News and direct publisher feeds often carry the same story with
    cosmetic differences (case, spacing, dash style, curly quotes, a trailing
    outlet tag).  The stored title stays verbatim; only this key is folded.
    """
    text = str(title or "")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = _DASH_CHARS_RE.sub("-", text)
    text = " ".join(text.lower().split())
    for separator in (" - ", " | "):
        if separator not in text:
            continue
        head, _, tail = text.rpartition(separator)
        tail_words = tail.split()
        if (
            len(head) >= 15
            and 1 <= len(tail_words) <= 4
            and not any(char.isdigit() for char in tail)
        ):
            text = head.strip()
            break
    return text


def canonicalize_url(raw_url):
    """Return a safe, normalized http(s) URL, or "" when it must be rejected."""
    raw = str(raw_url or "").strip()
    if not raw or len(raw) > MAX_URL_LENGTH:
        return ""
    try:
        parts = urlsplit(raw)
        scheme = parts.scheme.lower()
        if scheme not in ("http", "https"):
            return ""
        if not parts.hostname or parts.username or parts.password:
            return ""
        host = parts.hostname.lower().rstrip(".")
        port = parts.port
    except (ValueError, TypeError, AttributeError):
        return ""

    if host in _UNSAFE_HOSTS or any(host.endswith(suffix) for suffix in _UNSAFE_SUFFIXES):
        return ""
    if not host or len(host) > 253:
        return ""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
        # Reject decimal/hex/octal IPv4 spellings that bypass ip_address().
        if re.fullmatch(
            r"(?:0x[0-9a-f]+|\d+)(?:\.(?:0x[0-9a-f]+|\d+)){0,3}", host, re.IGNORECASE
        ):
            return ""
        if any(not (char.isalnum() or char in "-._") for char in host):
            return ""
        if any(
            not label or len(label) > 63 or label.startswith("-") or label.endswith("-")
            for label in host.split(".")
        ):
            return ""
    if address is not None and (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    ):
        return ""

    netloc = f"[{host}]" if address is not None and address.version == 6 else host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{netloc}:{port}"

    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in _TRACKING_PARAMS
    ]
    path = parts.path or "/"
    return urlunsplit((scheme, netloc, path, urlencode(query, doseq=True), ""))


def is_safe_url(url):
    return bool(canonicalize_url(url))


def article_key(link, title):
    """Stable identity: canonical URL, with a title fallback for missing URLs."""
    safe_link = canonicalize_url(link)
    if safe_link:
        return "url:" + hashlib.sha256(safe_link.encode("utf-8")).hexdigest()
    title_key = normalize_title(title)
    if not title_key:
        return ""
    return "title:" + hashlib.sha256(title_key.encode("utf-8")).hexdigest()
