def parse_start_token(text: str | None) -> str | None:
    """Extract token from '/start TOKEN' or '/start@Bot TOKEN'."""
    if not text:
        return None
    text = text.strip()
    if not text.startswith("/start"):
        return None
    parts = text.split(maxsplit=1)
    if len(parts) != 2:
        return None
    token = parts[1].strip()
    return token or None


def extract_telegram_user(update: dict) -> dict | None:
    """Return telegram_user_id, chat_id, username, first_name or None."""
    msg = update.get("message") or update.get("edited_message") or {}
    chat = msg.get("chat") or {}
    frm = msg.get("from") or {}
    user_id = frm.get("id") or chat.get("id")
    chat_id = chat.get("id") or frm.get("id")
    if user_id is None or chat_id is None:
        return None
    return {
        "telegram_user_id": int(user_id),
        "chat_id": int(chat_id),
        "username": frm.get("username"),
        "first_name": frm.get("first_name"),
        "text": msg.get("text"),
    }
