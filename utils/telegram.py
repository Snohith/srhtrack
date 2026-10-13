"""
Telegram alerting for @SRHXtra fresh-article ingestion.

Sends a Bot API message whenever newly matched articles are stored.
Best-effort by design: alerting must never break or slow the ingest cycle —
every public function returns a status instead of raising, and sends are
skipped silently when the bot is not configured.

Sends run synchronously inside the ingest cycle (ordering + guaranteed
delivery before the cycle is marked complete). Each POST typically takes
<1s; the per-call timeout below bounds the pathological case to
max_alerts × timeout seconds.

Configuration (environment or `.env`; see `.env.example`):
  TELEGRAM_ENABLED=yes|no            master switch (default: yes)
  TELEGRAM_BOT_TOKEN=...             token from @BotFather (secret — never logged)
  TELEGRAM_CHAT_ID=...               target chat / channel id from @userinfobot
  TELEGRAM_MODE=per_article|digest   default: per_article
  TELEGRAM_MAX_ALERTS_PER_CYCLE=10   cap for per-article mode (1-50); overflow
                                     is collapsed into one digest message.

Security notes:
  - RSS titles/summaries/links are untrusted: all interpolated values are
    HTML-escaped, and article URLs are restricted to http/https only.
  - The bot token is a secret: it is never written to logs. Request
    exceptions may embed the request URL (which contains the token), so only
    the exception *type* is logged, never its message. Bot API error
    descriptions are generic strings (e.g. "Bad Request: chat not found")
    and are safe to log.
"""
import html
import os
from urllib.parse import urlparse

import requests

from utils.logger import error_logger

TELEGRAM_API_TIMEOUT_SECS = 6
TELEGRAM_MAX_MESSAGE_CHARS = 4096
DEFAULT_MAX_ALERTS_PER_CYCLE = 10


def _load_dotenv(path=".env"):
    """Minimal .env loader (no extra dependency): KEY=VALUE lines only."""
    try:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = path if os.path.isabs(path) else os.path.join(base, path)
        if not os.path.exists(env_path):
            return
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


_load_dotenv()


def _secret(name, default=""):
    """Env first, Streamlit secrets fallback (Cloud dashboard → Secrets).

    TOML values may be non-strings (e.g. an unquoted numeric chat id),
    so everything is coerced to str. Values are never logged.
    """
    val = os.environ.get(name, "")
    if str(val).strip():
        return str(val).strip()
    try:
        import streamlit as st
        return str(st.secrets.get(name, default) or default).strip()
    except Exception:
        return default


def get_telegram_config():
    """Reads Telegram settings from env / Streamlit secrets. Never includes secrets in logs."""
    enabled = _secret("TELEGRAM_ENABLED", "true").lower() in (
        "1", "true", "yes", "y", "on",
    )
    token = _secret("TELEGRAM_BOT_TOKEN")
    chat_id = _secret("TELEGRAM_CHAT_ID")
    mode = _secret("TELEGRAM_MODE", "per_article").lower()
    if mode not in ("per_article", "digest"):
        mode = "per_article"
    try:
        max_alerts = max(1, min(50, int(
            _secret("TELEGRAM_MAX_ALERTS_PER_CYCLE", str(DEFAULT_MAX_ALERTS_PER_CYCLE)))))
    except (TypeError, ValueError):
        max_alerts = DEFAULT_MAX_ALERTS_PER_CYCLE
    return {
        "enabled": enabled,
        "token": token,
        "chat_id": chat_id,
        "mode": mode,
        "max_alerts": max_alerts,
    }


def is_telegram_configured():
    """True only when alerting is enabled AND credentials are present."""
    cfg = get_telegram_config()
    return bool(cfg["enabled"] and cfg["token"] and cfg["chat_id"])


def _safe_url(url):
    """Choke point for article URLs: only http/https links are ever sent."""
    try:
        scheme = urlparse(str(url or "").strip()).scheme.lower()
        if scheme in ("http", "https"):
            return str(url).strip()
    except Exception:
        pass
    return ""


def _clip(text, limit):
    text = str(text or "")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def format_article_message(article):
    """One alert bubble per fresh article. All values escaped (untrusted RSS)."""
    title = html.escape(_clip(article.get("title", "New Sunrisers update"), 250))
    player = html.escape(str(article.get("player_name", "")))
    franchise = html.escape(str(article.get("franchise", "")))
    source = html.escape(str(article.get("source", "")))
    published = html.escape(str(article.get("published_at", "")))
    summary = html.escape(_clip(article.get("summary", ""), 300))
    link = _safe_url(article.get("link", ""))
    lines = [
        "🟠 <b>SRHXtra — fresh update</b>",
        "",
        f"<b>{title}</b>",
        f"⚡ {player} · {franchise}",
        f"📰 {source} · {published}",
    ]
    if summary:
        lines += ["", summary]
    if link:
        lines += ["", f'<a href="{html.escape(link, quote=True)}">Read full story →</a>']
    return "\n".join(lines)[:TELEGRAM_MAX_MESSAGE_CHARS]


def format_digest_message(articles, total_inserted, total_cycle=None):
    """Single-cycle overflow/digest summary (used for overflow + digest mode)."""
    shown = articles[:10]
    lines = ["🟠 <b>SRHXtra — fresh updates</b>", ""]
    if total_cycle and total_cycle > total_inserted:
        lines.append(f"{total_inserted} further update(s) — {total_cycle} new this cycle:")
    else:
        lines.append(f"{total_inserted} new article(s) captured this cycle:")
    for a in shown:
        title = html.escape(_clip(a.get("title", ""), 120))
        player = html.escape(str(a.get("player_name", "")))
        source = html.escape(str(a.get("source", "")))
        lines.append(f"• <b>{player}</b> — {title} ({source})")
    if total_inserted > len(shown):
        lines.append(f"…and {total_inserted - len(shown)} more in the app.")
    return "\n".join(lines)[:TELEGRAM_MAX_MESSAGE_CHARS]


def send_telegram_message(text):
    """POSTs one message via Bot API. Returns True/False, never raises."""
    cfg = get_telegram_config()
    if not (cfg["enabled"] and cfg["token"] and cfg["chat_id"]):
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{cfg['token']}/sendMessage",
            json={
                "chat_id": cfg["chat_id"],
                "text": text[:TELEGRAM_MAX_MESSAGE_CHARS],
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=TELEGRAM_API_TIMEOUT_SECS,
        )
        try:
            payload = resp.json()
        except Exception:
            payload = {}
        ok = resp.status_code == 200 and bool(payload.get("ok"))
        desc = str(payload.get("description") or "")
        if not ok:
            error_logger.warning(f"Telegram send failed: HTTP {resp.status_code} {desc}".rstrip())
        return ok
    except Exception as exc:
        # Log only the exception type: messages may embed the request URL,
        # which contains the bot token.
        error_logger.warning(f"Telegram send failed: {type(exc).__name__}.")
        return False


def notify_new_articles(articles):
    """Dispatches alerts for one ingest cycle's fresh articles.

    Returns {"sent": int, "mode": str, "reason": str}; never raises.
    """
    articles = list(articles or [])
    cfg = get_telegram_config()
    if not cfg["enabled"]:
        return {"sent": 0, "mode": cfg["mode"], "reason": "disabled"}
    if not (cfg["token"] and cfg["chat_id"]):
        return {"sent": 0, "mode": cfg["mode"], "reason": "unconfigured"}
    if not articles:
        return {"sent": 0, "mode": cfg["mode"], "reason": "no_new_articles"}
    sent = 0
    try:
        if cfg["mode"] == "digest":
            if send_telegram_message(format_digest_message(articles, len(articles))):
                sent = 1
        else:
            for article in articles[: cfg["max_alerts"]]:
                if send_telegram_message(format_article_message(article)):
                    sent += 1
            if len(articles) > cfg["max_alerts"]:
                if send_telegram_message(
                    format_digest_message(articles[cfg["max_alerts"]:],
                                          len(articles) - cfg["max_alerts"],
                                          total_cycle=len(articles))
                ):
                    sent += 1
    except Exception as exc:
        error_logger.warning(f"Telegram dispatch failed: {type(exc).__name__}.")
    return {"sent": sent, "mode": cfg["mode"], "reason": "ok"}
