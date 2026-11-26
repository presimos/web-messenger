import pytest
from starlette.websockets import WebSocketDisconnect


def register_and_login(client, username):
    password = "secure-pass-123"
    client.post("/auth/register", json={"username": username, "password": password})
    response = client.post("/auth/login", json={"username": username, "password": password})
    return response.json()["access_token"]


def test_chat_access_and_message_delivery(client):
    first_token = register_and_login(client, "first")
    second_token = register_and_login(client, "second")
    first_headers = {"Authorization": f"Bearer {first_token}"}
    chat_response = client.post(
        "/chats",
        headers=first_headers,
        json={"title": "Общий чат", "member_usernames": ["second"]},
    )
    assert chat_response.status_code == 201
    chat_id = chat_response.json()["id"]
    assert len(client.get("/chats", headers=first_headers).json()) == 1

    with client.websocket_connect(f"/ws/chats/{chat_id}?token={first_token}") as first_socket:
        with client.websocket_connect(f"/ws/chats/{chat_id}?token={second_token}") as second_socket:
            first_socket.send_json({"body": "Привет"})
            first_message = first_socket.receive_json()
            second_message = second_socket.receive_json()

    assert first_message["body"] == "Привет"
    assert second_message["sender_username"] == "first"
    history = client.get(f"/chats/{chat_id}/messages", headers=first_headers)
    assert [message["body"] for message in history.json()] == ["Привет"]


def test_chat_and_websocket_require_membership(client):
    owner_token = register_and_login(client, "owner")
    stranger_token = register_and_login(client, "stranger")
    headers = {"Authorization": f"Bearer {owner_token}"}
    chat_id = client.post("/chats", headers=headers, json={}).json()["id"]

    stranger_headers = {"Authorization": f"Bearer {stranger_token}"}
    assert client.get(f"/chats/{chat_id}/messages", headers=stranger_headers).status_code == 404

    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(f"/ws/chats/{chat_id}?token={stranger_token}"):
            assert False, "Подключение без членства должно быть отклонено"
    assert error.value.code == 4403


def test_websocket_rejects_invalid_token(client):
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/ws/chats/1?token=invalid.token.value"):
            assert False, "Подключение с недействительным токеном должно быть отклонено"

    assert error.value.code == 4401


def test_invalid_messages_are_rejected_without_persistence(client):
    token = register_and_login(client, "sender")
    headers = {"Authorization": f"Bearer {token}"}
    chat_id = client.post("/chats", headers=headers, json={}).json()["id"]

    with client.websocket_connect(f"/ws/chats/{chat_id}?token={token}") as websocket:
        websocket.send_json({"body": "   "})
        assert websocket.receive_json() == {"error": "Передано неверное сообщение"}
        websocket.send_json({"body": "x" * 5001})
        assert websocket.receive_json() == {"error": "Передано неверное сообщение"}
        websocket.send_json({"body": "Корректное сообщение"})
        delivered = websocket.receive_json()

    assert delivered["body"] == "Корректное сообщение"
    history = client.get(f"/chats/{chat_id}/messages", headers=headers)
    assert [message["body"] for message in history.json()] == ["Корректное сообщение"]
