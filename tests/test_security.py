from app.core.security import generate_verification_token, hash_token


def test_token_hash_roundtrip():
    token = generate_verification_token()
    assert token.startswith("vfy_")
    h = hash_token(token)
    assert len(h) == 64
    assert hash_token(token) == h
