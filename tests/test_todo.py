def test_todo_crud(client):
    # register + login
    client.post("/register", data={
        "name":"U1","email":"u1@example.com","password":"password123","confirm_password":"password123"
    }, follow_redirects=True)
    client.post("/login", data={"email":"u1@example.com","password":"password123"}, follow_redirects=True)

    # add
    rv = client.post("/dashboard", data={"title":"Task A"}, follow_redirects=True)
    assert b"Task added" in rv.data and b"Task A" in rv.data

    # toggle id=1
    rv = client.post("/todo/1/toggle", follow_redirects=True)
    assert b"Task updated" in rv.data

    # edit id=1
    rv = client.post("/todo/1/edit", data={"title":"Task A+1"}, follow_redirects=True)
    assert b"Task title saved" in rv.data and b"Task A+1" in rv.data

    # delete id=1
    rv = client.post("/todo/1/delete", follow_redirects=True)
    assert b"Task deleted" in rv.data
