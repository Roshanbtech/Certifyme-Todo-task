def test_register_login_logout_flow(client):
    # register
    rv = client.post("/register", data={
        "name":"Test User",
        "email":"test@example.com",
        "password":"password123",
        "confirm_password":"password123",
        "csrf_token": client.get('/login').data  # page load sets CSRF; we won't parse it here
    }, follow_redirects=True)
    assert b"Registration successful" in rv.data

    # login
    rv = client.post("/login", data={
        "email":"test@example.com",
        "password":"password123",
        "csrf_token": client.get('/login').data
    }, follow_redirects=True)
    assert b"Welcome back" in rv.data
    assert b"Dashboard" in rv.data

    # logout
    rv = client.get("/logout", follow_redirects=True)
    assert b"You have been logged out" in rv.data
