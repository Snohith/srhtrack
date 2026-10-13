"""Telegram wiring diagnostic for @SRHXtra. Secrets are never printed.

Usage:
  python scripts/check_telegram.py              # validate only (no message sent)
  python scripts/check_telegram.py --send-test  # also sends one test DM

Reads the same config path as the app (env → .env → Streamlit secrets),
validates the token via getMe, and checks getUpdates to confirm the owner
has pressed START (Telegram blocks bots from messaging users first).
"""
import argparse
import re
import sys

sys.path.insert(0, ".")
from utils.telegram import (  # noqa: E402
    get_telegram_config,
    is_telegram_configured,
    send_telegram_message,
    _load_dotenv,
    _secret,
)


def _mask(value):
    value = str(value or "")
    if len(value) <= 5:
        return "set" if value else "missing"
    return f"{value[:2]}…{value[-2:]} (len {len(value)})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send-test", action="store_true")
    args = ap.parse_args()
    _load_dotenv()
    cfg = get_telegram_config()
    print(f"enabled:      {cfg['enabled']}")
    print(f"bot token:    {_mask(cfg['token'])}")
    print(f"chat id:      {_mask(cfg['chat_id'])}")
    print(f"mode:         {cfg['mode']}  max/cycle: {cfg['max_alerts']}")
    print(f"configured:   {is_telegram_configured()}")
    if not (cfg["token"] and cfg["chat_id"]):
        print("RESULT: unconfigured — set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID, then re-run.")
        return 2
    import requests

    try:
        me = requests.get(
            f"https://api.telegram.org/bot{cfg['token']}/getMe", timeout=10
        ).json()
    except Exception as exc:
        print(f"RESULT: getMe failed ({type(exc).__name__}) — network/TLS issue.")
        return 1
    if not me.get("ok"):
        print(f"RESULT: token REJECTED by Telegram ({me.get('description')}). "
              "Regenerate via @BotFather and update your secret store.")
        return 1
    print(f"token valid — bot username: @{me['result'].get('username')}")
    bot_name = "@" + str(me["result"].get("username") or "this bot")
    try:
        updates = requests.get(
            f"https://api.telegram.org/bot{cfg['token']}/getUpdates",
            params={"limit": 20, "timeout": 0}, timeout=15,
        ).json()
    except Exception as exc:
        print(f"getUpdates failed ({type(exc).__name__}) — skipping START check.")
        updates = {}
    seen = set()
    for u in (updates.get("result") or []):
        for key in ("message", "channel_post", "my_chat_member"):
            chat = (u.get(key) or {}).get("chat") or {}
            if chat.get("id") is not None:
                seen.add(str(chat["id"]))
    target = str(cfg["chat_id"])
    print(f"your configured chat contacted this bot: {target in seen}")
    if target not in seen:
        print(f"ACTION NEEDED: the chat id in your config has NEVER talked to {bot_name}. "
              "Either the id is mistyped (re-copy it from @userinfobot) or you pressed "
              f"START on a different bot (open {bot_name} → /start from the same "
              "account). Bots cannot message chats they have never seen.")
        if not args.send_test:
            return 3
    if args.send_test:
        ok = send_telegram_message("✅ SRHXtra test alert — Telegram wiring works.")
        print(f"test message: {'SENT ✅' if ok else 'FAILED ❌ (see logs/errors.log)'}")
        return 0 if ok else 1
    print("RESULT: wiring looks good. Re-run with --send-test to deliver a test DM.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
