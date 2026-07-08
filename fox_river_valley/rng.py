import hashlib


def deterministic_int(seed: str, counter: int, context: str, modulo: int) -> int:
    payload = f"{seed}:{counter}:{context}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return int(digest[:12], 16) % modulo
