from app.bot.handler import extract_telegram_user, parse_start_token


def test_parse_start_token():
    assert parse_start_token("/start vfy_abc123") == "vfy_abc123"
    assert parse_start_token("/start") is None
    assert parse_start_token("hello") is None
    assert parse_start_token(None) is None


def test_extract_telegram_user():
    update = {
        "message": {
            "text": "/start vfy_abc",
            "from": {"id": 123, "username": "john", "first_name": "John"},
            "chat": {"id": 123},
        }
    }
    user = extract_telegram_user(update)
    assert user is not None
    assert user["telegram_user_id"] == 123
    assert user["chat_id"] == 123
