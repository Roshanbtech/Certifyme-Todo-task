def test_manual_reset_password(client):
    client.post("/register", data={
        "name":"Reset User","email":"reset@example.com","password":"oldpassword","confirm_password":"oldpassword"
    }, follow_redirects=True)

    rv = client.post("/forgot-password", data={"email":"reset@example.com"}, follow_redirects=True)
    assert rv.status_code == 200

    rv = client.post("/reset-password", data={
        "password":"newpassword123","confirm_password":"newpassword123"
    }, follow_redirects=True)
    assert b"Password updated" in rv.data

    rv = client.post("/login", data={
        "email":"reset@example.com","password":"newpassword123"
    }, follow_redirects=True)
    assert b"Welcome back" in rv.data
