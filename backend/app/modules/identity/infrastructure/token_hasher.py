"""
Identity infrastructure: refresh-token hashing.

Deliberately a fast, deterministic hash (SHA-256, Python stdlib — no new
dependency), not Argon2id: a refresh token must be looked up by its hash
(SELECT ... WHERE token_hash = ?) on every /auth/refresh call, which
requires a deterministic digest. Argon2id's per-call random salt makes it
correct for password *verification* (compare against one known row) but
unusable for this by-hash *lookup* pattern — a different problem from
password storage, so a different tool.
"""

import hashlib


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
