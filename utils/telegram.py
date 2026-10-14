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
import concurrent.futures
import html
import os
from urllib.parse import urlparse, urljoin

import bs4
import requests

from utils.logger import error_logger

TELEGRAM_API_TIMEOUT_SECS = 6
TELEGRAM_OG_FETCH_TIMEOUT_SECS = 5
TELEGRAM_MAX_MESSAGE_CHARS = 4096
TELEGRAM_MAX_CAPTION_CHARS = 1024
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
    heartbeat = _secret("TELEGRAM_HEARTBEAT", "true").lower() in (
        "1", "true", "yes", "y", "on",
    )
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
        "heartbeat": heartbeat,
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


FRANCHISE_ACCENTS = {
    "Sunrisers Hyderabad": "🟠",
    "Sunrisers Eastern Cape": "🟢",
    "Sunrisers Leeds Men": "🔵",
    "Sunrisers Leeds Women": "🟣",
}


def _accent(franchise):
    return FRANCHISE_ACCENTS.get(str(franchise or ""), "🟠")


FRESH_LABEL_MAX_AGE_HOURS = 6.0


def _freshness_header(article):
    """Honest alert header from the article's age at ingest time.

    Google News re-stamps evergreen pages (same link, fresh pubDate), so the
    stored timestamp can lag the alert by many hours. Only genuinely fresh
    items may claim "Fresh"; late catch-up carries its age, and entries with
    no feed timestamp make no freshness claim at all. Articles predating the
    age signal (no "age_hours" key) keep the legacy "Fresh" header.
    """
    if "age_hours" not in article:
        return "SRHXtra · Fresh"
    age = article.get("age_hours")
    if age is None:
        return "SRHXtra · New"
    try:
        age_hours = float(age)
    except (TypeError, ValueError):
        return "SRHXtra · New"
    if age_hours <= FRESH_LABEL_MAX_AGE_HOURS:
        return "SRHXtra · Fresh"
    return f"SRHXtra · Catch-up · {age_hours:.0f}h old"


def format_article_message(article):
    """One alert card per fresh article. All values escaped (untrusted RSS).

    Layout: accent header + bold title + expandable summary quote (collapsed
    to 3 lines, tap to expand — degrades to a plain quote on old clients) +
    meta lines + story link (drives the large link-preview card).
    """
    title = html.escape(_clip(article.get("title", "New Sunrisers update"), 250))
    player = html.escape(str(article.get("player_name", "")))
    franchise = html.escape(str(article.get("franchise", "")))
    source = html.escape(str(article.get("source", "")))
    published = html.escape(str(article.get("published_at", "")))
    summary = html.escape(_clip(article.get("summary", ""), 400))
    link = _safe_url(article.get("link", ""))
    lines = [
        f"{_accent(article.get('franchise', ''))} <b>{_freshness_header(article)}</b>",
        "",
        f"<b>{title}</b>",
    ]
    if summary:
        lines += ["", f"<blockquote expandable>{summary}</blockquote>"]
    lines += [
        "",
        f"⚡ {player} · {franchise}",
        f"📰 {source} · {published}",
    ]
    if link:
        lines += ["", f'<a href="{html.escape(link, quote=True)}">Read full story →</a>']
    return "\n".join(lines)[:TELEGRAM_MAX_MESSAGE_CHARS]


def _is_fresh_for_alert(article):
    """True when an article deserves its own per-article card.

    Backlog floods (cold-start reboots, ingest gaps) can queue dozens of
    day-old stories; each would otherwise arrive as its own "Fresh" DM.
    Stale items (>6h) ride in one catch-up digest instead. Ageless articles
    (no timestamp in the feed) keep per-article treatment with a "New" label.
    """
    age = (article or {}).get("age_hours")
    if age is None:
        return True
    try:
        return float(age) <= FRESH_LABEL_MAX_AGE_HOURS
    except (TypeError, ValueError):
        return True


def _format_age_short(age):
    try:
        return f"{float(age):.0f}h old"
    except (TypeError, ValueError):
        return "age unknown"


def format_catchup_digest_message(articles):
    """One collapsed DM for a cycle's stale backlog (already on the dashboard)."""
    shown = list(articles or [])[:10]
    lines = ["📦 <b>SRHXtra — Catch-up</b>", ""]
    lines.append(
        f"{len(articles)} older update(s) already on your dashboard:"
    )
    for a in shown:
        title = html.escape(_clip(a.get("title", ""), 120))
        player = html.escape(str(a.get("player_name", "")))
        source = html.escape(str(a.get("source", "")))
        lines.append(
            f"• <b>{player}</b> — {title} ({source}, {_format_age_short(a.get('age_hours'))})"
        )
    if len(articles) > len(shown):
        lines.append(f"…and {len(articles) - len(shown)} more in the app.")
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


def send_telegram_message(text, preview_url=None):
    """POSTs one message via Bot API. Returns True/False, never raises.

    preview_url must already be sanitized (_safe_url): when given, Telegram
    renders the large link-preview card for it (prefer_large_media only
    applies to an explicitly specified URL — first-link fallback stays small).
    """
    cfg = get_telegram_config()
    if not (cfg["enabled"] and cfg["token"] and cfg["chat_id"]):
        return False
    body = {
        "chat_id": cfg["chat_id"],
        "text": text[:TELEGRAM_MAX_MESSAGE_CHARS],
        "parse_mode": "HTML",
    }
    if preview_url:
        body["link_preview_options"] = {
            "url": preview_url,
            "prefer_large_media": True,
            "show_above_text": False,
        }
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{cfg['token']}/sendMessage",
            json=body,
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


def format_heartbeat_message(stats=None):
    """Short 'sweep clean' DM so a quiet cycle is distinguishable from a dead
    pipeline. stats={total_polled, failed} comes from the collector."""
    stats = stats or {}
    try:
        total = int(stats.get("total_polled") or 0)
    except (TypeError, ValueError):
        total = 0
    try:
        failed = int(stats.get("failed") or 0)
    except (TypeError, ValueError):
        failed = 0
    if total:
        line = f"All {total} sources scanned — no fresh stories."
    else:
        line = "Sweep complete — no fresh stories."
    if failed:
        line += f" ({failed} feed{'s' if failed != 1 else ''} down)"
    return f"✅ {line}\nNothing new since the last check — the watch continues. 🔭"


def notify_new_articles(articles, stats=None):
    """Dispatches alerts for one ingest cycle's fresh articles.

    Empty cycle + heartbeat enabled → one "sweep clean" DM so the owner can
    tell a quiet cycle apart from a dead pipeline. Returns
    {"sent": int, "mode": str, "reason": str}; never raises.
    """
    articles = list(articles or [])
    cfg = get_telegram_config()
    if not cfg["enabled"]:
        return {"sent": 0, "mode": cfg["mode"], "reason": "disabled"}
    if not (cfg["token"] and cfg["chat_id"]):
        return {"sent": 0, "mode": cfg["mode"], "reason": "unconfigured"}
    if not articles:
        if not cfg["heartbeat"]:
            return {"sent": 0, "mode": cfg["mode"], "reason": "heartbeat_off"}
        ok = send_telegram_message(format_heartbeat_message(stats))
        return {"sent": 1 if ok else 0, "mode": cfg["mode"], "reason": "heartbeat"}
    sent = 0
    try:
        if cfg["mode"] == "digest":
            if send_telegram_message(
                format_digest_message(articles, len(articles)),
                _first_preview_link(articles),
            ):
                sent = 1
        else:
            fresh = [a for a in articles if _is_fresh_for_alert(a)]
            stale = [a for a in articles if not _is_fresh_for_alert(a)]
            batch = fresh[: cfg["max_alerts"]]
            images = _prefetch_images(batch)
            for article in batch:
                if _send_article(article, images.get(id(article))):
                    sent += 1
            if len(fresh) > cfg["max_alerts"]:
                rest = fresh[cfg["max_alerts"]:]
                if send_telegram_message(
                    format_digest_message(rest,
                                          len(rest),
                                          total_cycle=len(articles)),
                    _first_preview_link(rest),
                ):
                    sent += 1
            if stale:
                if send_telegram_message(
                    format_catchup_digest_message(stale),
                    _first_preview_link(stale),
                ):
                    sent += 1
    except Exception as exc:
        error_logger.warning(f"Telegram dispatch failed: {type(exc).__name__}.")
    return {"sent": sent, "mode": cfg["mode"], "reason": "ok"}


def _fetch_og_image(page_url, timeout=TELEGRAM_OG_FETCH_TIMEOUT_SECS):
    """Best-effort article hero image (og:image → twitter:image). Never raises."""
    page_url = _safe_url(page_url)
    if not page_url:
        return None
    try:
        resp = requests.get(
            page_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SRHXtra/1.0)"},
            timeout=timeout,
        )
        if resp.status_code != 200:
            return None
        soup = bs4.BeautifulSoup((resp.text or "")[:200000], "html.parser")
        for attrs in ({"property": "og:image"}, {"name": "twitter:image"}):
            tag = soup.find("meta", attrs)
            if tag and tag.get("content"):
                img = _safe_url(urljoin(page_url, tag["content"].strip()))
                if img:
                    return img
    except Exception:
        pass
    return None


def _prefetch_images(batch):
    """Resolves hero images concurrently ({id(article): url}); never raises."""
    out = {}
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            futs = {pool.submit(_fetch_og_image, (a or {}).get("link", "")): a for a in batch}
            for fut, art in futs.items():
                try:
                    img = fut.result(timeout=TELEGRAM_OG_FETCH_TIMEOUT_SECS + 3)
                except Exception:
                    img = None
                if img:
                    out[id(art)] = img
    except Exception:
        pass
    return out


def format_photo_caption(article):
    """Compact card caption (≤1024 chars). Fields are pre-clipped so the final
    guard can never split an entity — overlong captions drop the quote block
    deterministically instead."""
    title = html.escape(_clip(article.get("title", "New Sunrisers update"), 150))
    player = html.escape(str(article.get("player_name", "")))
    franchise = html.escape(str(article.get("franchise", "")))
    source = html.escape(str(article.get("source", "")))
    summary = html.escape(_clip(article.get("summary", ""), 220))
    link = _safe_url(article.get("link", ""))
    lines = [
        f"{_accent(article.get('franchise', ''))} <b>{_freshness_header(article)}</b>",
        "",
        f"<b>{title}</b>",
    ]
    if summary:
        lines += ["", f"<blockquote expandable>{summary}</blockquote>"]
    lines += [f"⚡ {player} · {franchise}", f"📰 {source}"]
    if link:
        lines += [f'<a href="{html.escape(link, quote=True)}">Read full story →</a>']
    caption = "\n".join(lines)
    if len(caption) > TELEGRAM_MAX_CAPTION_CHARS - 24:
        lines = [ln for ln in lines if not ln.startswith("<blockquote")]
        caption = "\n".join(lines)
    return caption[:TELEGRAM_MAX_CAPTION_CHARS]


def send_telegram_photo(photo_url, caption):
    """POSTs a photo card via Bot API. Returns True/False, never raises."""
    cfg = get_telegram_config()
    if not (cfg["enabled"] and cfg["token"] and cfg["chat_id"]):
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{cfg['token']}/sendPhoto",
            json={
                "chat_id": cfg["chat_id"],
                "photo": photo_url,
                "caption": caption[:TELEGRAM_MAX_CAPTION_CHARS],
                "parse_mode": "HTML",
            },
            timeout=TELEGRAM_API_TIMEOUT_SECS,
        )
        try:
            payload = resp.json()
        except Exception:
            payload = {}
        ok = resp.status_code == 200 and bool(payload.get("ok"))
        if not ok:
            desc = str(payload.get("description") or "")
            error_logger.warning(f"Telegram photo failed: HTTP {resp.status_code} {desc}".rstrip())
        return ok
    except Exception as exc:
        error_logger.warning(f"Telegram photo failed: {type(exc).__name__}.")
        return False


def _send_article(article, image_url):
    """Photo card when a hero image resolved, else the text card. Never raises."""
    try:
        if image_url:
            if send_telegram_photo(image_url, format_photo_caption(article)):
                return True
            # Photo rejected (hotlink protection, bad file…) → text fallback.
        return send_telegram_message(
            format_article_message(article),
            _safe_url(article.get("link", "")) or None,
        )
    except Exception as exc:
        error_logger.warning(f"Article dispatch failed: {type(exc).__name__}.")
        return False


def _first_preview_link(articles):
    """First sanitized article URL for the digest preview card (None if none)."""
    for article in articles or []:
        link = _safe_url((article or {}).get("link", ""))
        if link:
            return link
    return None
