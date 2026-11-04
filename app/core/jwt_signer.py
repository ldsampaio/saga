"""Assinatura de JWT-ponteiro (EC P-256) e exposição do JWKS.

O JWT NÃO é a sessão: é um ponteiro assinado para a sessão no Redis. Ele carrega
`sid` e `gen`; a validade real da sessão é decidida pelo Redis. Por isso os
subsistemas verificam a assinatura E a liveness — nunca a assinatura sozinha.
"""

from __future__ import annotations

import base64
import secrets
import time
from pathlib import Path
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.config import get_settings

_signer: JwtSigner | None = None


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


class JwtSigner:
    def __init__(self, private_key: ec.EllipticCurvePrivateKey, kid: str, issuer: str):
        self._key = private_key
        self._kid = kid
        self._issuer = issuer
        self._alg = "ES256"

    def sign(self, sid: str, user_id: str, role_base: str, ttl_seconds: int, gen: int) -> str:
        """`gen` é o da sessão no Redis — nunca um valor próprio do signer.

        O verifier compara `Number(meta.gen)` com `Number(claims.gen)`. Se o token
        trouxesse um gen diferente do gravado no store, toda request real seria
        SESSION_STALE. O token é só um ponteiro: o gen dele vem do store.
        """
        now = int(time.time())
        claims: dict[str, Any] = {
            "iss": self._issuer,
            "sub": user_id,
            "sid": sid,
            "gen": gen,
            "role": role_base,
            "iat": now,
            "exp": now + ttl_seconds,
        }
        return jwt.encode(
            claims,
            self._key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ),
            algorithm=self._alg,
            headers={"kid": self._kid},
        )

    def jwks(self) -> dict[str, Any]:
        nums = self._key.public_key().public_numbers()
        return {
            "keys": [
                {
                    "kty": "EC",
                    "crv": "P-256",
                    "kid": self._kid,
                    "use": "sig",
                    "x": _b64url(nums.x.to_bytes(32, "big")),
                    "y": _b64url(nums.y.to_bytes(32, "big")),
                }
            ]
        }

    def public_key_pem(self) -> bytes:
        return self._key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )


def _dev_private_key() -> ec.EllipticCurvePrivateKey:
    settings = get_settings()
    path = Path(settings.JWT_PRIVATE_KEY_PATH) if settings.JWT_PRIVATE_KEY_PATH else (
        Path(__file__).resolve().parent.parent.parent / ".jwt_private_key.pem"
    )
    if path.exists():
        return serialization.load_pem_private_key(path.read_bytes(), password=None)
    key = ec.generate_private_key(ec.SECP256R1())
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return key


def get_signer() -> JwtSigner:
    global _signer
    if _signer is None:
        settings = get_settings()
        _signer = JwtSigner(_dev_private_key(), settings.JWT_KID, settings.JWT_ISSUER)
    return _signer


def set_signer(signer: JwtSigner | None) -> None:
    """Injeção usada pelos testes."""
    global _signer
    _signer = signer


def new_gen() -> int:
    """Número de geração da sessão: muda quando a sessão é recriada."""
    return secrets.randbelow(10**9) + 1
