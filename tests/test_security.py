from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_hash_and_verify_password():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_decode_valid_token():
    token = create_access_token(42)
    assert decode_access_token(token) == 42


def test_decode_invalid_token():
    assert decode_access_token("not-a-token") is None


def test_decode_tampered_token():
    token = create_access_token(1)
    assert decode_access_token(token + "tampered") is None
