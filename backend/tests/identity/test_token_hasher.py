from app.modules.identity.infrastructure.token_hasher import hash_token


def test_hash_token_is_deterministic():
    assert hash_token("abc") == hash_token("abc")


def test_hash_token_differs_for_different_inputs():
    assert hash_token("abc") != hash_token("xyz")


def test_hash_token_never_contains_the_raw_token():
    raw = "super-secret-refresh-token"
    assert raw not in hash_token(raw)
