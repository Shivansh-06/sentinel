async def auth_headers(client):
    res = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "sentinel_admin"},
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
