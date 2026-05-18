from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass


class TokenError(ValueError):
    pass


class PasswordHasher:
    _prefix = "scrypt"
    _n = 2**14
    _r = 8
    _p = 1
    _dklen = 64

    def hash_password(self, password: str) -> str:
        salt = os.urandom(16)
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=self._n,
            r=self._r,
            p=self._p,
            dklen=self._dklen,
        )
        salt_b64 = base64.urlsafe_b64encode(salt).decode("utf-8")
        digest_b64 = base64.urlsafe_b64encode(digest).decode("utf-8")
        return f"{self._prefix}${self._n}${self._r}${self._p}${salt_b64}${digest_b64}"

    def verify_password(self, password: str, hashed_password: str) -> bool:
        try:
            prefix, n, r, p, salt_b64, digest_b64 = hashed_password.split("$", 5)
        except ValueError:
            return False
        if prefix != self._prefix:
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode("utf-8"))
        expected_digest = base64.urlsafe_b64decode(digest_b64.encode("utf-8"))
        actual_digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected_digest),
        )
        return hmac.compare_digest(actual_digest, expected_digest)


@dataclass(slots=True)
class JWTManager:
    secret: str
    expires_minutes: int
    algorithm: str = "HS256"

    def create_token(self, *, subject: str, email: str, role: str, is_active: bool) -> tuple[str, int]:
        issued_at = int(time.time())
        expires_at = issued_at + (self.expires_minutes * 60)
        payload = {
            "sub": subject,
            "email": email,
            "role": role,
            "is_active": is_active,
            "iat": issued_at,
            "exp": expires_at,
        }
        token = self._encode(payload)
        return token, self.expires_minutes * 60

    def decode_token(self, token: str) -> dict[str, object]:
        parts = token.split(".")
        if len(parts) != 3:
            raise TokenError("Invalid token format.")

        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_signature = self._sign(signing_input)
        actual_signature = self._decode_segment(signature_b64)
        if not hmac.compare_digest(expected_signature, actual_signature):
            raise TokenError("Invalid token signature.")

        payload = json.loads(self._decode_segment(payload_b64).decode("utf-8"))
        exp = payload.get("exp")
        if not isinstance(exp, int) or exp < int(time.time()):
            raise TokenError("Token has expired.")
        return payload

    @staticmethod
    def hash_invite_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_invite_token() -> str:
        return secrets.token_urlsafe(32)

    def _encode(self, payload: dict[str, object]) -> str:
        if self.algorithm != "HS256":
            raise TokenError("Unsupported JWT algorithm.")
        header = {"alg": self.algorithm, "typ": "JWT"}
        header_b64 = self._encode_segment(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_b64 = self._encode_segment(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        signature_b64 = self._encode_segment(self._sign(signing_input))
        return f"{header_b64}.{payload_b64}.{signature_b64}"

    def _sign(self, data: bytes) -> bytes:
        return hmac.new(self.secret.encode("utf-8"), data, hashlib.sha256).digest()

    @staticmethod
    def _encode_segment(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    @staticmethod
    def _decode_segment(data: str) -> bytes:
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode((data + padding).encode("utf-8"))
