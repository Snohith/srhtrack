"""Telegram delivery for the SRHXtra collector.

Only the Bot API sendMessage call is used.  There is no polling bot, no
command handler, no image fetching, and no heartbeat.  A queued article is
claimed atomically from SQLite, sent once, and then marked sent.  Failures
stay in the ledger for a bounded, backed-off retry.
"""
from __future__ import annotations

import html
import os
import time
from dataclasses import dataclass

import requests

from helpers.config import env_bool
from helpers.links import canonicalize_url
from helpers.log_books import problems_diary
from saved_stories.story_storage import (
    claim_due_deliveries,
    mark_delivery_dead,
    mark_delivery_failed,
    mark_delivery_sent,
)

TELEGRAM_TIMEOUT_SECS = 10
MAX_MESSAGE_CHARS = 4096
MAX_ALERTS_PER_RUN = 20
TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


@dataclass
class SendResult:
    ok: bool
    retryable: bool = True
    retry_after: float = 0.0
    error: str = ""


def telegram_settings():
    token = str(os.environ.get("TELEGRAM_BOT_TOKEN", "")).strip()
    chat_id = str(os.environ.get("TELEGRAM_CHAT_ID", "")).strip()
    return {
        "enabled": env_bool("TELEGRAM_ENABLED", True),
        "token": token,
        "chat_id": chat_id,
    }


def are_phone_alerts_ready():
    settings = telegram_settings()
    return bool(settings["enabled"] and settings["token"] and settings["chat_id"])


def _as_list(value):
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        try:
            import json
            loaded = json.loads(value)
            if isinstance(loaded, list):
                return [str(item) for item in loaded if str(item).strip()]
        except (TypeError, ValueError):
            pass
        return [value.strip()]
    return []


def _clip(text, limit):
    text = str(text or "")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _team_symbol(franchises):
    joined = " ".join(franchises).lower()
    if "women" in joined:
        return "🟣"
    if "leeds" in joined:
        return "🔵"
    if "eastern cape" in joined:
        return "🟢"
    return "🟠"


def format_article_alert(article):
    """One escaped Telegram card for one unique article."""
    people = _as_list(article.get("people"))
    franchises = _as_list(article.get("franchises"))
    topics = _as_list(article.get("topics"))
    title = html.escape(_clip(article.get("title", "Sunrisers update"), 300))
    summary = html.escape(_clip(article.get("summary", ""), 350))
    source = html.escape(str(article.get("source", "")))
    published = html.escape(str(article.get("published_at", "")))
    link = canonicalize_url(article.get("link", ""))

    lines = [f"{_team_symbol(franchises)} <b>SRHXtra</b>", "", f"<b>{title}</b>"]
    if summary:
        lines += ["", f"<blockquote expandable>{summary}</blockquote>"]
    if people:
        lines += ["", f"👤 {html.escape(', '.join(people))}"]
    if franchises:
        lines.append(f"🏏 {html.escape(', '.join(franchises))}")
    if topics:
        lines.append(f"🏷️ {html.escape(', '.join(topics))}")
    meta = " · ".join(part for part in (source, published) if part)
    if meta:
        lines += ["", f"📰 {meta}"]
    if link:
        lines += ["", f'<a href="{html.escape(link, quote=True)}">Read full story →</a>']
    return "\n".join(lines)[:MAX_MESSAGE_CHARS]


def send_telegram_message(text, preview_url=None):
    """POST one message. Never raises and never logs the token."""
    settings = telegram_settings()
    if not (settings["enabled"] and settings["token"] and settings["chat_id"]):
        return SendResult(False, retryable=False, error="Telegram is not configured")

    body = {
        "chat_id": settings["chat_id"],
        "text": str(text or "")[:MAX_MESSAGE_CHARS],
        "parse_mode": "HTML",
    }
    safe_preview = canonicalize_url(preview_url) if preview_url else ""
    if safe_preview:
        body["link_preview_options"] = {
            "url": safe_preview,
            "prefer_large_media": True,
            "show_above_text": False,
        }
    try:
        response = requests.post(
            TELEGRAM_API.format(token=settings["token"], method="sendMessage"),
            json=body,
            timeout=TELEGRAM_TIMEOUT_SECS,
        )
    except Exception as exc:
        problems_diary.warning(f"Telegram send failed: {type(exc).__name__}.")
        return SendResult(False, retryable=True, error=type(exc).__name__)

    try:
        payload = response.json()
    except Exception:
        payload = {}
    description = str(payload.get("description") or "")[:300]
    if response.status_code == 200 and payload.get("ok"):
        return SendResult(True)
    if response.status_code == 429:
        parameters = payload.get("parameters") or {}
        try:
            retry_after = float(parameters.get("retry_after") or 30)
        except (TypeError, ValueError):
            retry_after = 30.0
        problems_diary.warning(f"Telegram rate limit; retry after {retry_after:.0f}s.")
        return SendResult(False, retryable=True, retry_after=retry_after, error="rate limited")
    retryable = response.status_code >= 500 or response.status_code == 408
    problems_diary.warning(
        f"Telegram send failed: HTTP {response.status_code} {description}".rstrip()
    )
    return SendResult(False, retryable=retryable, error=description or f"HTTP {response.status_code}")


def send_pending_alerts(limit=MAX_ALERTS_PER_RUN):
    """Send due articles one by one; stop on a transient outage."""
    settings = telegram_settings()
    stats = {"claimed": 0, "sent": 0, "retried": 0, "failed": 0, "reason": "ok"}
    if not settings["enabled"]:
        stats["reason"] = "disabled"
        return stats
    if not (settings["token"] and settings["chat_id"]):
        stats["reason"] = "unconfigured"
        problems_diary.warning(
            "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID are missing; "
            "alerts stay pending in the database."
        )
        return stats

    for _ in range(max(1, int(limit))):
        claimed = claim_due_deliveries(1)
        if not claimed:
            break
        stats["claimed"] += 1
        article = claimed[0]
        link = canonicalize_url(article.get("link", ""))
        if not link:
            mark_delivery_dead(article["id"], "unsafe article link")
            stats["failed"] += 1
            continue
        result = send_telegram_message(format_article_alert(article), link)
        if result.ok:
            mark_delivery_sent(article["id"])
            stats["sent"] += 1
            time.sleep(0.2)
            continue

        if result.retryable:
            outcome = mark_delivery_failed(
                article["id"], result.error, retry_after=result.retry_after
            )
            stats["retried" if outcome == "retry" else "failed"] += 1
            # Telegram is rate-limiting or unreachable; do not hammer it.
            break
        mark_delivery_dead(article["id"], result.error)
        stats["failed"] += 1
        # A 400/401/403 is usually configuration-wide; stop this run.
        break
    return stats


def send_test_message():
    """Explicit manual setup check. Does not touch the delivery ledger."""
    result = send_telegram_message("✅ SRHXtra test alert — Telegram wiring works.")
    return result
