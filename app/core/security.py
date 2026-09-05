import hashlib
import hmac
import secrets


def generate_verification_token() -> str:
    # ~192 bits entropy, well above 128-bit requirement
    return "vfy_" + secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_api_key(prefix: str = "sk_live_") -> str:
    return prefix + secrets.token_urlsafe(32)


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def verify_hash(raw: str, digest: str) -> bool:
    return hmac.compare_digest(hash_key(raw), digest)


def new_id(prefix: str) -> str:
    # Short prefixed ids: vrf_, proj_, ntf_, etc.
    return prefix + secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:16]
