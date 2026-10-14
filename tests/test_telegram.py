"""
Telegram alerting tests for @SRHXtra (no network, no production DB).

Covers utils/telegram.py dispatch/formatting/security behaviour, the
ingest→Telegram wiring in scrapers/rss_collector.py (fully mocked, no DB),
photo cards with fallback, and the _RssResult backwards-compatible extension.
"""
import pytest

from utils import telegram as tg
from scrapers.rss_collector import _RssResult

ARTICLE = {
    "title": "Abhishek Sharma smashes fifty",
    "source": "Test Source",
    "summary": "Fifty off 30 balls.",
    "link": "https://example.com/story-1",
    "published_at": "Oct 13, 2026 @ 10:00 AM IST",
    "player_name": "Abhishek Sharma",
    "franchise": "Sunrisers Hyderabad",
}

# Real implementation, captured before the autouse fixture below replaces it.
_real_fetch_og_image = tg._fetch_og_image


@pytest.fixture()
def tg_env(monkeypatch):
    """Hermetic Telegram env: configured per-article by default."""
    monkeypatch.setenv("TELEGRAM_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    monkeypatch.setenv("TELEGRAM_MODE", "per_article")
    monkeypatch.setenv("TELEGRAM_MAX_ALERTS_PER_CYCLE", "10")
    return monkeypatch


@pytest.fixture(autouse=True)
def _no_og_images(monkeypatch):
    """Unit tests never hit the network for hero images (unless re-patched)."""
    monkeypatch.setattr(tg, "_fetch_og_image", lambda url, timeout=5: None)


def _ok_post(calls):
    def _post(url, **kwargs):
        body = kwargs.get("json") if kwargs.get("json") is not None else kwargs.get("data")
        calls.append({"url": url, "body": body})
        assert "test-token" in url  # token goes in the URL path (Bot API scheme)

        class _Resp:
            status_code = 200

            @staticmethod
            def json():
                return {"ok": True}

        return _Resp()

    return _post


def test_disabled_sends_nothing(monkeypatch, tg_env):
    monkeypatch.setenv("TELEGRAM_ENABLED", "false")
    monkeypatch.setattr(tg.requests, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no HTTP when disabled")))
    res = tg.notify_new_articles([ARTICLE])
    assert res == {"sent": 0, "mode": "per_article", "reason": "disabled"}


def test_unconfigured_sends_nothing(monkeypatch, tg_env):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN")
    monkeypatch.setattr(tg.requests, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no HTTP when unconfigured")))
    res = tg.notify_new_articles([ARTICLE])
    assert res["sent"] == 0 and res["reason"] == "unconfigured"
    assert tg.is_telegram_configured() is False


def test_empty_cycle_sends_heartbeat(tg_env, monkeypatch):
    calls = []
    monkeypatch.setattr(tg.requests, "post", _ok_post(calls))
    res = tg.notify_new_articles([], {"total_polled": 193, "failed": 2})
    assert res == {"sent": 1, "mode": "per_article", "reason": "heartbeat"}
    assert len(calls) == 1
    text = calls[0]["body"]["text"]
    assert "All 193 sources scanned" in text and "2 feeds down" in text
    assert "link_preview_options" not in calls[0]["body"]  # plain text, no card


def test_heartbeat_off_stays_silent(tg_env, monkeypatch):
    monkeypatch.setenv("TELEGRAM_HEARTBEAT", "false")
    monkeypatch.setattr(tg.requests, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no HTTP when heartbeat off")))
    assert tg.notify_new_articles([])["reason"] == "heartbeat_off"


def test_heartbeat_without_stats_or_unconfigured(tg_env, monkeypatch):
    calls = []
    monkeypatch.setattr(tg.requests, "post", _ok_post(calls))
    assert tg.notify_new_articles([])["reason"] == "heartbeat"
    assert "Sweep complete" in calls[0]["body"]["text"]
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN")
    monkeypatch.setattr(tg.requests, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no HTTP when unconfigured")))
    assert tg.notify_new_articles([])["reason"] == "unconfigured"


def test_per_article_sends_one_message_each(tg_env, monkeypatch):
    calls = []
    monkeypatch.setattr(tg.requests, "post", _ok_post(calls))
    res = tg.notify_new_articles([ARTICLE, {**ARTICLE, "title": "Second story"}])
    assert res["sent"] == 2 and res["mode"] == "per_article"
    assert len(calls) == 2
    body = calls[0]["body"]
    assert "Abhishek Sharma" in body["text"]
    assert body["parse_mode"] == "HTML"
    assert "<blockquote expandable>" in body["text"]
    assert body["link_preview_options"]["prefer_large_media"] is True
    assert body["link_preview_options"]["url"] == "https://example.com/story-1"


def test_cap_collapses_overflow_into_digest(tg_env, monkeypatch):
    monkeypatch.setenv("TELEGRAM_MAX_ALERTS_PER_CYCLE", "2")
    calls = []
    monkeypatch.setattr(tg.requests, "post", _ok_post(calls))
    articles = [{**ARTICLE, "title": f"Story {i}"} for i in range(5)]
    res = tg.notify_new_articles(articles)
    assert res["sent"] == 3  # 2 per-article + 1 overflow digest
    assert len(calls) == 3
    assert "3 further update(s) — 5 new this cycle:" in calls[-1]["body"]["text"]


def test_digest_mode_sends_single_summary(tg_env, monkeypatch):
    monkeypatch.setenv("TELEGRAM_MODE", "digest")
    calls = []
    monkeypatch.setattr(tg.requests, "post", _ok_post(calls))
    res = tg.notify_new_articles([{**ARTICLE, "title": f"Story {i}"} for i in range(4)])
    assert res["sent"] == 1 and res["mode"] == "digest"
    assert "4 new article(s)" in calls[0]["body"]["text"]


def test_franchise_accents():
    assert tg._accent("Sunrisers Hyderabad") == "🟠"
    assert tg._accent("Sunrisers Eastern Cape") == "🟢"
    assert tg._accent("Sunrisers Leeds Men") == "🔵"
    assert tg._accent("Sunrisers Leeds Women") == "🟣"
    assert tg._accent("Something Else") == "🟠"
    card = tg.format_article_message({**ARTICLE, "franchise": "Sunrisers Eastern Cape"})
    assert card.startswith("🟢 <b>SRHXtra · Fresh</b>")


def test_expandable_quote_only_with_summary():
    assert "<blockquote expandable>" in tg.format_article_message(ARTICLE)
    assert "<blockquote" not in tg.format_article_message({**ARTICLE, "summary": ""})


def test_no_preview_options_without_safe_link(tg_env, monkeypatch):
    calls = []
    monkeypatch.setattr(tg.requests, "post", _ok_post(calls))
    tg.notify_new_articles([{**ARTICLE, "link": "javascript:alert(1)"}])
    assert "link_preview_options" not in calls[0]["body"]


def test_untrusted_content_is_escaped_and_schemes_rejected(tg_env, monkeypatch):
    calls = []
    monkeypatch.setattr(tg.requests, "post", _ok_post(calls))
    evil = {
        **ARTICLE,
        "title": '<script>alert("x")</script> Klaasen',
        "summary": "Quote \"break\" <b>bold</b>",
        "link": "javascript:alert(1)",
    }
    tg.notify_new_articles([evil])
    text = calls[0]["body"]["text"]
    assert "<script>" not in text and "&lt;script&gt;" in text
    assert "javascript:" not in text  # executable scheme stripped at choke point
    good = {**ARTICLE, "link": "https://example.com/ok"}
    assert "https://example.com/ok" in tg.format_article_message(good)


def test_send_failure_never_raises(tg_env, monkeypatch):
    def _boom(*a, **k):
        raise TimeoutError("https://api.telegram.org/botSECRET/sendMessage timed out")

    monkeypatch.setattr(tg.requests, "post", _boom)
    assert tg.send_telegram_message("hi") is False  # no raise, no secret leak
    res = tg.notify_new_articles([ARTICLE])
    assert res["sent"] == 0 and res["reason"] == "ok"


def test_api_error_returns_false_with_description(tg_env, monkeypatch):
    class _Resp:
        status_code = 400

        @staticmethod
        def json():
            return {"ok": False, "description": "Bad Request: chat not found"}

    monkeypatch.setattr(tg.requests, "post", lambda *a, **k: _Resp())
    assert tg.send_telegram_message("hi") is False


def test_og_image_extraction(monkeypatch):
    html_doc = (
        '<html><head>'
        '<meta property="og:image" content="https://cdn.example.com/hero.jpg">'
        "</head></html>"
    )

    class _Resp:
        status_code = 200
        text = html_doc

    monkeypatch.setattr(tg.requests, "get", lambda *a, **k: _Resp())
    assert _real_fetch_og_image("https://example.com/story") == "https://cdn.example.com/hero.jpg"


def test_og_image_relative_url_resolved_and_bad_cases_empty(monkeypatch):
    class _Resp:
        status_code = 200
        text = '<html><head><meta name="twitter:image" content="/img/x.jpg"></head></html>'

    monkeypatch.setattr(tg.requests, "get", lambda *a, **k: _Resp())
    assert _real_fetch_og_image("https://example.com/a/b") == "https://example.com/img/x.jpg"
    monkeypatch.setattr(tg.requests, "get", lambda *a, **k: (_ for _ in ()).throw(TimeoutError("down")))
    assert _real_fetch_og_image("https://example.com/a") is None
    calls = []
    monkeypatch.setattr(tg.requests, "get", lambda *a, **k: (calls.append(1), _Resp())[1])
    assert _real_fetch_og_image("javascript:alert(1)") is None
    assert calls == []  # unsafe page URL never fetched


def test_photo_card_payload_and_caption_budget(tg_env, monkeypatch):
    calls = []
    monkeypatch.setattr(tg.requests, "post", _ok_post(calls))
    assert tg.send_telegram_photo("https://cdn.example.com/hero.jpg", "<b>Hi</b>") is True
    body = calls[0]["body"]
    assert calls[0]["url"].endswith("/sendPhoto")
    assert body["photo"] == "https://cdn.example.com/hero.jpg"
    assert body["parse_mode"] == "HTML"
    giant_link = {**ARTICLE, "link": "https://example.com/" + "x" * 900}
    capped = tg.format_photo_caption(giant_link)
    assert len(capped) <= 1024 and "<blockquote" not in capped
    short_caption = tg.format_photo_caption(ARTICLE)
    assert "<blockquote expandable>" in short_caption and len(short_caption) <= 1024


def test_photo_preferred_then_text_fallback(tg_env, monkeypatch):
    calls = []
    monkeypatch.setattr(tg, "_fetch_og_image", lambda url, timeout=5: "https://cdn.example.com/hero.jpg")
    monkeypatch.setattr(tg.requests, "post", _ok_post(calls))
    assert tg.notify_new_articles([ARTICLE])["sent"] == 1
    assert calls[0]["url"].endswith("/sendPhoto")

    def _flaky(url, **kwargs):
        calls.append({"url": url})
        if url.endswith("/sendPhoto"):
            class _Bad:
                status_code = 400

                @staticmethod
                def json():
                    return {"ok": False, "description": "Bad Request: wrong file"}
            return _Bad()
        return _ok_post(calls)(url, **kwargs)

    calls.clear()
    monkeypatch.setattr(tg.requests, "post", _flaky)
    assert tg.notify_new_articles([ARTICLE])["sent"] == 1
    assert calls[0]["url"].endswith("/sendPhoto")
    assert calls[1]["url"].endswith("/sendMessage")  # fallback delivered


def test_rss_result_backwards_compatible():
    legacy = _RssResult(3, ["Feed X"], 193)  # old 3-arg call style still works
    assert int(legacy) == 3 and legacy.new_articles == []
    assert legacy.inserted == 3 and legacy.failed_feeds == ["Feed X"]
    extended = _RssResult(1, [], 193, [ARTICLE])
    assert extended.new_articles == [ARTICLE] and int(extended) == 1


def test_ingest_dispatches_one_alert_per_unique_story(tg_env, monkeypatch):
    """One URL matching 2 players stores 2 rows but alerts once (no DB touched)."""
    from scrapers import rss_collector as rc

    monkeypatch.setattr(rc, "CRICKET_SOURCES", [{"name": "Fake", "url": "https://example.com/fake"}])
    monkeypatch.setattr(
        rc, "_poll_one_source",
        lambda fi: (fi, [{"title": "Shared story", "summary": "S", "link": "https://example.com/x"}], None),
    )
    monkeypatch.setattr(rc, "parse_rss_date_to_ist", lambda e: ("Oct 13, 2026 @ 10:00 AM IST", 1.0, 12345.0))
    monkeypatch.setattr(
        rc, "match_player_or_franchise_in_text",
        lambda t: [
            {"player_name": "Abhishek Sharma", "franchise": "Sunrisers Hyderabad"},
            {"player_name": "Ishan Kishan", "franchise": "Sunrisers Hyderabad"},
        ],
    )
    monkeypatch.setattr(rc, "insert_news", lambda **k: 999)
    monkeypatch.setattr(rc, "insert_notification", lambda *a, **k: None)
    calls = []
    monkeypatch.setattr(
        "utils.telegram.notify_new_articles",
        lambda arts, stats=None: (calls.append((list(arts), stats)), {"sent": 1, "mode": "per_article", "reason": "ok"})[1],
    )
    res = rc.fetch_and_filter_rss()
    assert int(res) == 2  # both per-target rows stored
    assert len(res.new_articles) == 1  # but a single alert dispatched
    assert len(calls) == 1 and calls[0][0][0]["player_name"] == "Abhishek Sharma"
    assert calls[0][1] == {"total_polled": 1, "failed": 0}  # cycle stats passed through
