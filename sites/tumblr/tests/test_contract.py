"""Contract tests: every route family renders real upstream-sourced content."""
import json
import re


def _get(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    return resp.get_data(as_text=True)


def test_health(client):
    data = json.loads(_get(client, "/_health"))
    assert data["ok"] is True
    assert data["site"] == "tumblr"
    assert data["blogs"] >= 400
    assert data["posts"] >= 1000
    assert data["notes"] >= 1000
    assert data["users"] == 4


def test_homepage(client):
    html = _get(client, "/")
    for marker in ["Trending today", "Popular tags", "post-card",
                   "Blogs to watch"]:
        assert marker in html, f"homepage missing {marker!r}"
    assert "/static/images/media/" in html


def test_explore(client):
    html = _get(client, "/explore")
    assert "Explore Tumblr" in html
    assert "hub-card" in html and "Trending posts" in html
    page2 = _get(client, "/explore?page=2")
    assert "Page 2 of" in page2


def test_tagged_hub(client):
    html = _get(client, "/tagged/photography")
    assert "#photography" in html
    assert "43M" in html and "2.4K" in html
    assert "Related tags" in html and "#photographer" in html
    assert html.count("post-card") >= 10
    page2 = _get(client, "/tagged/photography?page=2")
    assert "Page 2 of" in page2


def test_tagged_fallback(client):
    # a tag that exists on posts but has no hub card
    html = _get(client, "/tagged/trees")
    assert "posts tagged #trees" in html
    assert "post-card" in html


def test_tagged_editorial(client):
    # upstream serves an editorial description on 6 of the 12 hub pages
    # (art, photography, travel, food, books, fashion) and none on the
    # other six — the mirror carries exactly what the page served.
    html = _get(client, "/tagged/photography")
    assert "About #photography" in html
    assert ("For those who prefer to show rather than tell, photography "
            "takes precedence over words") in html
    art = _get(client, "/tagged/art")
    assert "About #art" in art
    assert "fearlessness to try something new" in art
    space = _get(client, "/tagged/space")
    assert "About #space" not in space


def test_teaboot_blog_page(client):
    # the original blog of the CCTV reblog trail (upstream serves it 200)
    html = _get(client, "/blog/teaboot")
    assert "I Like Yellow Now" in html
    assert "42,149 posts" in html
    assert "Updated" in html
    assert "post-card" in html
    assert "/static/images/avatars/teaboot.png" in html


def test_search_top_and_recent(client):
    html = _get(client, "/search/pixel%20art")
    assert "Search results for" in html
    assert "13 results" in html
    assert "Blogs matching" in html and "waneella" in html
    recent = _get(client, "/search/pixel%20art?tab=recent")
    assert "20 results" in recent


def test_search_fallback_query(client):
    html = _get(client, "/search/moon")
    assert "Search results for" in html
    assert "results" in html
    assert "post-card" in html


def test_blog_page(client):
    html = _get(client, "/blog/nasa")
    assert "NASA" in html and "1,759 posts" in html
    assert "Archive" in html and "post-card" in html
    assert "/static/images/avatars/nasa" in html


def test_blog_archive(client):
    html = _get(client, "/blog/nasa/archive")
    assert "Archive of NASA" in html
    assert "April 2026" in html
    assert "archive-tile" in html


def test_permalink_and_notes(client):
    html = _get(client, "/blog/staff/811288138350821376")
    assert "Reblogs in a chain now get their own notes" in html
    assert "319,748 notes" in html
    assert "note-row" in html
    assert "101,183 likes" in html


def test_post_redirect(client):
    resp = client.get("/post/811288138350821376")
    assert resp.status_code == 302
    assert "/blog/staff/811288138350821376" in resp.headers["Location"]


def test_answer_post_renders(client):
    html = _get(client, "/blog/paokai/750605550915567616")
    assert "asked:" in html
    assert "obi-bae-kenobi" in html


def test_video_post_renders(client):
    html = _get(client, "/blog/nasa/793768130342273024")
    assert "Flight Test Like a NASA Engineer" in html
    assert "Video · tumblr" in html


def test_reblog_trail_renders(client):
    html = _get(client, "/blog/nullenvk/828957539611869184")
    assert "trail-item" in html
    assert "teaboot" in html


def test_login_pages(client):
    assert "Log in to Tumblr" in _get(client, "/login")
    assert "Join Tumblr" in _get(client, "/register")


def test_404s(client):
    assert client.get("/blog/does-not-exist-at-all").status_code == 404
    assert client.get("/post/000000").status_code == 404
