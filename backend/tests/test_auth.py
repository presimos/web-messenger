def test_register_login_and_read_profile(client):
    registered = client.post(
        "/auth/register",
        json={"username": "  DemoUser ", "password": "secure-pass-123"},
    )
    assert registered.status_code == 201
    assert registered.json()["username"] == "demouser"
    assert "password" not in registered.json()

    logged_in = client.post(
        "/auth/login",
        json={"username": "DEMOUSER", "password": "secure-pass-123"},
    )
    assert logged_in.status_code == 200
    token = logged_in.json()["access_token"]

    profile = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["username"] == "demouser"


def test_duplicate_username_is_rejected(client):
    payload = {"username": "demouser", "password": "secure-pass-123"}
    assert client.post("/auth/register", json=payload).status_code == 201
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 409


def test_invalid_login_and_missing_token_are_rejected(client):
    client.post(
        "/auth/register",
        json={"username": "demouser", "password": "secure-pass-123"},
    )
    invalid_login = client.post(
        "/auth/login",
        json={"username": "demouser", "password": "wrong-password"},
    )

    assert invalid_login.status_code == 401
    assert client.get("/auth/me").status_code == 401
