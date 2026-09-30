"""Flow tests: benchmark-user state, actions and mutations."""
import json
import re


def _get(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    return resp.get_data(as_text=True)


def test_login_success_and_failure(client):
    resp = client.post("/login", data={"email": "alice.j@test.com",
                                      "password": "TestPass123!"},
                       follow_redirects=False)
    assert resp.status_code == 302
    bad = client.post("/login", data={"email": "alice.j@test.com",
                                      "password": "wrong"},
                      follow_redirects=True)
    assert "Incorrect email or password" in bad.get_data(as_text=True)


def test_dashboard_requires_login(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 302 and "/login" in resp.headers["Location"]


def test_alice_dashboard(alice):
    html = _get(alice, "/dashboard")
    assert "Dashboard" in html
    for blog in ["meolog", "nasa", "staff", "waneella"]:
        assert blog in html
    assert "Kodak Ektar 100" in html


def test_alice_likes(alice):
    html = _get(alice, "/likes")
    assert "11 liked posts" in html
    assert "Deleted accounts can now be recovered" in html


def test_alice_following(alice):
    html = _get(alice, "/following")
    for blog in ["staff", "waneella", "meolog", "nasa", "writingprompts",
                 "cabinporn"]:
        assert blog in html


def test_alice_activity(alice):
    html = _get(alice, "/activity")
    assert "bob-c" in html and "carol-d" in html and "david-k" in html
    assert "liked your post" in html and "reblogged your post" in html


def test_alice_inbox_and_conversation(alice):
    html = _get(alice, "/inbox")
    assert "staff" in html and "bob-c" in html
    conv = _get(alice, "/inbox/staff")
    assert "Welcome to Tumblr!" in conv
    assert "Glad to hear it!" in conv


def test_send_message(alice):
    resp = alice.post("/inbox/staff/send", data={"body": "Thanks!"},
                      follow_redirects=True)
    assert "Thanks!" in resp.get_data(as_text=True)


def test_ask_flow_bob_to_alice(client):
    client.post("/login", data={"email": "bob.c@test.com",
                                "password": "TestPass123!"})
    resp = client.post("/blog/alice-j/ask",
                       data={"body": "Which museum do you visit most?"},
                       follow_redirects=True)
    assert "has been sent to" in resp.get_data(as_text=True)
    client.get("/logout")
    client.post("/login", data={"email": "alice.j@test.com",
                                "password": "TestPass123!"})
    inbox = _get(client, "/inbox")
    assert "bob-c" in inbox
    conv = _get(client, "/inbox/bob-c")
    assert "Which museum do you visit most?" in conv


def test_like_toggle_and_likes_page(bob):
    before = json.loads(bob.post("/post/817505727903137792/like").data)
    assert before["liked"] is True
    html = _get(bob, "/likes")
    assert "Rhododendron" in html
    after = json.loads(bob.post("/post/817505727903137792/like").data)
    assert after["liked"] is False


def test_reblog_with_comment(bob):
    resp = bob.post("/post/817505727903137792/reblog",
                    data={"comment": "great light"},
                    follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert "Reblogged to your blog." in html or "great light" in html
    blog_html = _get(bob, "/blog/bob-c")
    assert "great light" in blog_html
    assert "meolog" in blog_html          # original blog in the trail


def test_follow_toggle(david):
    before = json.loads(david.post("/blog/waneella/follow").data)
    assert before["following"] is True
    following = _get(david, "/following")
    assert "waneella" in following
    after = json.loads(david.post("/blog/waneella/follow").data)
    assert after["following"] is False


def test_create_text_post(carol, client):
    resp = carol.post("/new/post?type=text",
                      data={"title": "Cabin Wishlist, Part Two",
                            "body": "A big wood stove and a wall of books.",
                            "tags": "cottagecore, wishlist"},
                      follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert "Cabin Wishlist, Part Two" in html
    blog_html = _get(carol, "/blog/carol-d")
    assert "Cabin Wishlist, Part Two" in blog_html
    assert "#cottagecore" in blog_html


def test_create_quote_post(alice):
    resp = alice.post("/new/post?type=quote",
                      data={"quote": "Art is the only way to run away.",
                            "source": "Twyla Tharp", "tags": "quotes"},
                      follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert "Art is the only way to run away." in html
    assert "Twyla Tharp" in html


def test_settings_title_change(bob):
    resp = bob.post("/settings", data={"action": "profile",
                                       "title": "bob's art lab"},
                    follow_redirects=True)
    assert "Blog settings saved." in resp.get_data(as_text=True)
    blog_html = _get(bob, "/blog/bob-c")
    assert "bob&#39;s art lab" in blog_html or "bob's art lab" in blog_html


def test_register_and_first_follow(client):
    resp = client.post("/register", data={
        "email": "tester@example.com", "username": "harbor-tester",
        "password": "longpassword1"}, follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert "Dashboard" in html
    assert "Follow some blogs from Explore" in html
    client.post("/blog/nasa/follow")
    dash = _get(client, "/dashboard")
    assert "nasa" in dash
    assert "Follow some blogs from Explore" not in dash


def test_password_change(alice):
    resp = alice.post("/settings", data={
        "action": "password", "old_password": "TestPass123!",
        "new_password": "NewPass12345"}, follow_redirects=True)
    assert "Password updated." in resp.get_data(as_text=True)
    # old password no longer works
    alice.get("/logout")
    bad = alice.post("/login", data={"email": "alice.j@test.com",
                                     "password": "TestPass123!"},
                     follow_redirects=True)
    assert "Incorrect email or password" in bad.get_data(as_text=True)
    # restore
    good = alice.post("/login", data={"email": "alice.j@test.com",
                                      "password": "NewPass12345"},
                      follow_redirects=True)
    alice.post("/settings", data={"action": "password",
                                  "old_password": "NewPass12345",
                                  "new_password": "TestPass123!"})
