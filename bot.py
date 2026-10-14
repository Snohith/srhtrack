"""SRHXtra Telegram command bot (no server needed — runs anywhere Python runs).

Long-polls the Bot API and executes owner commands from chat:
  /matches  live Crex fixtures with Sunrisers players (LIVE first), each with
            teams, IST date + start time, our players grouped by franchise
  /refresh  run a full 193-feed sweep now, reply with the result summary
            (fresh stories still arrive as individual DMs via the normal path)
  /status   sources tracked, rows stored, players, alert mode
  /start    greeting + command list (also satisfies Telegram's START requirement)
  /help     same as /start

Security: only TELEGRAM_CHAT_ID may issue commands; everyone else is
silently ignored (replies always go to the owner chat, so strangers can't
extract anything — and can't trigger sweeps). One sweep at a time behind a
lock; a second /refresh while busy gets a "still running" reply. /matches is
read-only (15-min cached Crex data) and needs no lock. No buttons anywhere.

Usage:
  python bot.py            # foreground; Ctrl-C stops cleanly
  make bot                 # same thing
First boot drains any stale backlog so days-old taps don't fire.
Register the menu in BotFather once via /setcommands: matches, refresh,
status, start, help.
"""
import os
import signal
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests

from database.db_manager import get_metadata, set_metadata
from scheduler.worker import run_collector_cycle
from utils.logger import scheduler_logger as log
from utils.matchday_cards import format_matches_message
from utils.telegram import get_telegram_config, send_telegram_message

POLL_TIMEOUT_SECS = 25
OFFSET_KEY = "tg_update_offset"
_shutdown = False


def _load_dotenv(path=".env"):
    try:
        base = os.path.dirname(os.path.abspath(__file__))
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


def _on_signal(signum, frame):
    global _shutdown
    _shutdown = True


def parse_command(text):
    """Extracts a known command from message text (handles /cmd@BotName)."""
    if not text:
        return None
    first = text.strip().split()[0]
    if not first.startswith("/"):
        return None
    cmd = first[1:].split("@")[0].lower()
    return cmd if cmd in ("matches", "refresh", "status", "start", "help") else None


def is_owner(chat_id, owner_chat_id):
    return str(chat_id or "") != "" and str(chat_id) == str(owner_chat_id)


def format_status(summary, interval_secs, mode):
    total = summary.get("total_news", 0)
    players = summary.get("total_players", 0)
    import html as _html
    return (
        "🟠 <b>SRHXtra status</b>\n"
        f"📰 {_html.escape(str(total))} stories stored (24h window)\n"
        f"👥 {_html.escape(str(players))} players tracked\n"
        f"⏱ sweep every {_html.escape(str(interval_secs // 60))} min\n"
        f"🔔 alerts: {_html.escape(str(mode))}"
    )


class CommandBot:
    """Polling bot. Network isolated in api()/send()/get_updates() for testability."""

    def __init__(self, run_cycle=None, matches_fn=None):
        cfg = get_telegram_config()
        self.token = cfg["token"]
        self.owner = cfg["chat_id"]
        self.mode = cfg["mode"]
        self._run_cycle = run_cycle or run_collector_cycle
        self._matches_fn = matches_fn
        self._lock = threading.Lock()
        try:
            self.interval = max(60, int(os.environ.get("AUTO_INGEST_INTERVAL_SECS", "900")))
        except (TypeError, ValueError):
            self.interval = 900

    @property
    def base(self):
        return f"https://api.telegram.org/bot{self.token}"

    def api(self, method, **kwargs):
        resp = requests.get(f"{self.base}/{method}", timeout=POLL_TIMEOUT_SECS + 10, **kwargs)
        return resp.json()

    def send(self, text):
        return send_telegram_message(text)

    def get_offset(self):
        try:
            return int(get_metadata(OFFSET_KEY, "0") or 0)
        except (TypeError, ValueError):
            return 0

    def set_offset(self, update_id):
        try:
            set_metadata(OFFSET_KEY, str(update_id))
        except Exception:
            pass

    def get_updates(self, offset, timeout=POLL_TIMEOUT_SECS):
        params = {"timeout": timeout}
        if offset:
            params["offset"] = offset
        try:
            data = self.api("getUpdates", params=params)
        except Exception as exc:
            log.warning(f"Bot poll failed ({type(exc).__name__}); retrying.")
            return []
        return data.get("result") or []

    def drain_backlog(self):
        """First boot with no stored offset: skip stale commands, remember position."""
        if self.get_offset():
            return
        updates = self.get_updates(offset=None, timeout=0)
        if updates:
            self.set_offset(max(u["update_id"] for u in updates) + 1)
            log.info(f"Bot drained {len(updates)} stale backlog update(s).")

    def _fetch_matches(self):
        if self._matches_fn is not None:
            return self._matches_fn()
        from scrapers.matchday_scraper import get_sunrisers_fixtures
        return get_sunrisers_fixtures()

    def _fetch_matches_resilient(self):
        """Crex fetch with one retry. Full traceback on final failure so the
        next transient is diagnosable (type-only logs left us blind once)."""
        try:
            return self._fetch_matches() or []
        except Exception:
            pass
        time.sleep(2)
        try:
            return self._fetch_matches() or []
        except Exception:
            log.exception("Bot /matches fetch failed twice; serving empty state.")
            return []

    def handle_update(self, update):
        msg = update.get("message") or {}
        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        if not is_owner(chat_id, self.owner):
            return "ignored"
        cmd = parse_command(msg.get("text", ""))
        if cmd in ("start", "help"):
            self.send(
                "🟠 <b>SRHXtra bot</b>\n"
                "/matches — live Crex fixtures with our players\n"
                "/refresh — sweep all 193 feeds now\n"
                "/status — tracked sources, stored rows, alert mode"
            )
            return "start"
        if cmd == "status":
            try:
                from database.db_manager import get_analytics_summary
                summary = get_analytics_summary()
            except Exception:
                summary = {}
            self.send(format_status(summary, self.interval, self.mode))
            return "status"
        if cmd == "matches":
            self.send(format_matches_message(self._fetch_matches_resilient()))
            return "matches"
        if cmd == "refresh":
            return self.cmd_refresh()
        return "ignored"

    def cmd_refresh(self):
        """Runs one sweep in a worker thread; replies immediately + on completion."""
        if not self._lock.acquire(blocking=False):
            self.send("⏳ A sweep is already running — results will land here.")
            return "busy"
        self.send("🔄 Sweeping 193 feeds — fresh stories arrive as DMs, summary follows.")

        def _work():
            try:
                result = self._run_cycle()
                inserted = int(getattr(result, "inserted", result) or 0)
                failed = len(getattr(result, "failed_feeds", []) or [])
                self.send(f"✅ Sweep done: +{inserted} new stor"
                          f"{'y' if inserted == 1 else 'ies'} · {failed} feeds down.")
            except Exception as exc:
                log.warning(f"Bot-triggered sweep failed ({type(exc).__name__}).")
                try:
                    self.send("❌ Sweep failed — logged, will retry on schedule.")
                except Exception:
                    pass
            finally:
                self._lock.release()

        threading.Thread(target=_work, daemon=True).start()
        return "refreshing"

    def run_forever(self):
        signal.signal(signal.SIGTERM, _on_signal)
        signal.signal(signal.SIGINT, _on_signal)
        try:
            me = self.api("getMe", params={})
            log.info(f"Bot polling as @{(me.get('result') or {}).get('username')}.")
        except Exception as exc:
            log.warning(f"Bot getMe failed ({type(exc).__name__}); continuing.")
        self.drain_backlog()
        while not _shutdown:
            for update in self.get_updates(self.get_offset() or None):
                try:
                    self.handle_update(update)
                except Exception as exc:
                    log.warning(f"Bot update handler failed ({type(exc).__name__}).")
                finally:
                    self.set_offset(update["update_id"] + 1)
            if not _shutdown:
                time.sleep(0.2)
        log.info("Bot stopping cleanly.")


def main():
    cfg = get_telegram_config()
    if not (cfg["token"] and cfg["chat_id"]):
        print("[srhxtra-bot] TELEGRAM_BOT_TOKEN/CHAT_ID missing — set .env first.")
        return 2
    print("[srhxtra-bot] polling — /matches /refresh /status ready.", flush=True)
    CommandBot().run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
