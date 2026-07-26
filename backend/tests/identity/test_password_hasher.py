from app.modules.identity.infrastructure.password_hasher import hash_password, verify_password


def test_hash_password_produces_a_verifiable_hash():
    password_hash = hash_password("correct-horse-battery")
    assert verify_password("correct-horse-battery", password_hash) is True


def test_verify_password_rejects_wrong_password():
    password_hash = hash_password("correct-horse-battery")
    assert verify_password("wrong-password", password_hash) is False


def test_hash_password_never_returns_the_plaintext():
    password_hash = hash_password("correct-horse-battery")
    assert "correct-horse-battery" not in password_hash
