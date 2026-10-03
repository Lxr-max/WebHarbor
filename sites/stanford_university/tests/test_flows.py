"""Flow tests: auth, planner, saved events — all with CSRF enabled."""
from conftest import _login, _logout, with_csrf


def test_login_logout_flow(client):
    r = client.get("/login")
    assert r.status_code == 200
    data = with_csrf(client, "/login", {"email": "alice.j@test.com",
                                        "password": "TestPass123!"})
    r = client.post("/login", data=data, follow_redirects=True)
    assert r.status_code == 200
    assert b"Alice Johnson" in r.data  # header shows the signed-in name
    # planner is reachable now
    r = client.get("/planner")
    assert r.status_code == 200
    assert b"CS106A" in r.data
    assert b"MATH51" in r.data
    assert b"PHYSICS41" in r.data
    # logout (CSRF-protected POST)
    data = with_csrf(client, "/", {})
    r = client.post("/logout", data=data, follow_redirects=True)
    assert r.status_code == 200
    r = client.get("/planner")
    assert r.status_code == 302  # back to the login gate


def test_login_requires_csrf(client):
    r = client.post("/login", data={"email": "alice.j@test.com",
                                    "password": "TestPass123!"},
                    follow_redirects=False)
    assert r.status_code == 400  # CSRF token missing -> rejected


def test_login_bad_credentials(client):
    data = with_csrf(client, "/login", {"email": "alice.j@test.com",
                                        "password": "WrongPassword1!"})
    r = client.post("/login", data=data, follow_redirects=True)
    assert b"Invalid email or password" in r.data


def test_signup_validation_and_success(client):
    # too-short password
    data = with_csrf(client, "/signup", {"name": "Tina Tester",
                                        "email": "tina.t@test.com",
                                        "password": "short"})
    r = client.post("/signup", data=data, follow_redirects=True)
    assert b"at least 8 characters" in r.data
    # duplicate email
    data = with_csrf(client, "/signup", {"name": "Alice Two",
                                        "email": "alice.j@test.com",
                                        "password": "LongEnough1!"})
    r = client.post("/signup", data=data, follow_redirects=True)
    assert b"already exists" in r.data
    # success
    data = with_csrf(client, "/signup", {"name": "Tina Tester",
                                        "email": "tina.t@test.com",
                                        "password": "LongEnough1!"})
    r = client.post("/signup", data=data, follow_redirects=True)
    assert r.status_code == 200
    assert b"Course Planner" in r.data
    r = client.get("/planner")
    assert b"Your course planner is empty" in r.data


def test_benchmark_user_planner_fixtures(client):
    _login(client, "alice.j@test.com")
    r = client.get("/planner")
    assert b"CS106A" in r.data and b"MATH51" in r.data and b"PHYSICS41" in r.data
    _logout(client)
    _login(client, "bob.c@test.com")
    r = client.get("/planner")
    assert b"ECON1" in r.data and b"PSYCH1" in r.data
    _logout(client)
    _login(client, "dana.k@test.com")
    r = client.get("/planner")
    assert b"BIO102" in r.data
    _logout(client)


def test_planner_add_remove_requires_login(client):
    # CSRF is validated before the login gate: a token-less POST is a 400
    r = client.post("/planner/add", data={"code": "CS106A"},
                    follow_redirects=False)
    assert r.status_code == 400
    # with a valid token but no session, the login gate redirects
    data = with_csrf(client, "/login", {"code": "CS106A"})
    r = client.post("/planner/add", data=data, follow_redirects=False)
    assert r.status_code == 302
    data = with_csrf(client, "/login", {"code": "CS106A"})
    r = client.post("/planner/remove", data=data, follow_redirects=False)
    assert r.status_code == 302


def test_planner_add_remove_flow(client):
    _login(client, "alice.j@test.com")
    data = with_csrf(client, "/courses/CS229",
                     {"code": "CS229", "next": "/courses/CS229"})
    r = client.post("/planner/add", data=data, follow_redirects=True)
    assert b"Added CS229" in r.data
    # duplicate add is flagged, not duplicated
    data = with_csrf(client, "/courses/CS229",
                     {"code": "CS229", "next": "/courses/CS229"})
    r = client.post("/planner/add", data=data, follow_redirects=True)
    assert b"already in your planner" in r.data
    r = client.get("/planner")
    assert r.data.count(b"<td><a href=\"/courses/CS229\"") == 1
    # remove
    data = with_csrf(client, "/planner", {"code": "CS229",
                                          "next": "/planner"})
    r = client.post("/planner/remove", data=data, follow_redirects=True)
    assert b"Removed CS229" in r.data
    r = client.get("/planner")
    assert b"<td><a href=\"/courses/CS229\"" not in r.data
    # removing something not planned is a no-op flash
    data = with_csrf(client, "/planner", {"code": "CS229",
                                          "next": "/planner"})
    r = client.post("/planner/remove", data=data, follow_redirects=True)
    assert b"is not in your planner" in r.data
    # unknown course -> 404
    data = with_csrf(client, "/planner", {"code": "NOPE1",
                                          "next": "/planner"})
    r = client.post("/planner/add", data=data, follow_redirects=False)
    assert r.status_code == 404
    _logout(client)


def test_planner_requires_csrf(client):
    _login(client, "alice.j@test.com")
    r = client.post("/planner/add", data={"code": "CS229"},
                    follow_redirects=False)
    assert r.status_code == 400
    _logout(client)


def test_saved_events_flow(client):
    _login(client, "carol.d@test.com")
    r = client.get("/saved-events")
    assert b"Lunchtime Curator Talk" in r.data
    # save a new event
    data = with_csrf(client, "/events/53922734404263",
                     {"eid": "53922734404263",
                      "next": "/events/53922734404263"})
    r = client.post("/events/save", data=data, follow_redirects=True)
    assert b"Saved" in r.data
    r = client.get("/saved-events")
    assert b"Big Earth Hackathon" in r.data
    # duplicate save flagged
    data = with_csrf(client, "/events/53922734404263",
                     {"eid": "53922734404263",
                      "next": "/events/53922734404263"})
    r = client.post("/events/save", data=data, follow_redirects=True)
    assert b"already saved" in r.data
    # unsave
    data = with_csrf(client, "/events/53922734404263",
                     {"eid": "53922734404263",
                      "next": "/saved-events"})
    r = client.post("/events/unsave", data=data, follow_redirects=True)
    assert b"Removed the event" in r.data
    r = client.get("/saved-events")
    assert b"Big Earth Hackathon" not in r.data
    # unknown event -> 404
    data = with_csrf(client, "/saved-events", {"eid": "1",
                                               "next": "/saved-events"})
    r = client.post("/events/save", data=data, follow_redirects=False)
    assert r.status_code == 404
    _logout(client)


def test_saved_events_requires_csrf(client):
    _login(client, "bob.c@test.com")
    r = client.post("/events/save", data={"eid": "53922734404263"},
                    follow_redirects=False)
    assert r.status_code == 400
    _logout(client)


def test_event_detail_shows_save_state(client):
    _login(client, "carol.d@test.com")
    r = client.get("/events/53922734404263")
    assert b"Save this event" in r.data
    data = with_csrf(client, "/events/53922734404263",
                     {"eid": "53922734404263",
                      "next": "/events/53922734404263"})
    client.post("/events/save", data=data, follow_redirects=True)
    r = client.get("/events/53922734404263")
    assert b"Remove from saved events" in r.data
    data = with_csrf(client, "/events/53922734404263",
                     {"eid": "53922734404263",
                      "next": "/events/53922734404263"})
    client.post("/events/unsave", data=data, follow_redirects=True)
    _logout(client)


def test_course_detail_planner_button_states(client):
    r = client.get("/courses/CS106A")
    assert b"Log in to add to planner" in r.data
    _login(client, "alice.j@test.com")
    r = client.get("/courses/CS106A")
    assert b"Add to course planner" in r.data
    _logout(client)
