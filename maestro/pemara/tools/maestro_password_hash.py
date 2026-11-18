#!/usr/bin/env python3
"""Generate and verify Maestro scrypt hashes without command-line secrets."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import hmac
import os
import sys


N_VALUE = 2**15
R_VALUE = 8
P_VALUE = 1
SALT_BYTES = 32
DIGEST_BYTES = 32
MAX_PASSWORD_BYTES = 2048


def _read_password() -> str:
    encoded = sys.stdin.buffer.readline(MAX_PASSWORD_BYTES * 2).strip()
    if not encoded:
        raise ValueError("password payload ausente")
    try:
        raw = base64.b64decode(encoded, validate=True)
        password = raw.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise ValueError("password payload invalido") from exc
    if not password or len(raw) > MAX_PASSWORD_BYTES:
        raise ValueError("password payload fora dos limites")
    return password


def _derive(password: str, salt: bytes, *, length: int = DIGEST_BYTES) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=N_VALUE,
        r=R_VALUE,
        p=P_VALUE,
        dklen=length,
        maxmem=128 * 1024 * 1024,
    )


def new_hash(password: str) -> str:
    salt = os.urandom(SALT_BYTES)
    digest = _derive(password, salt)
    return "$".join(
        (
            "scrypt",
            str(N_VALUE),
            str(R_VALUE),
            str(P_VALUE),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        )
    )


def verify_hash(password: str, encoded: str) -> bool:
    try:
        scheme, n_raw, r_raw, p_raw, salt_raw, digest_raw = encoded.split("$", 5)
        if (
            scheme != "scrypt"
            or int(n_raw) != N_VALUE
            or int(r_raw) != R_VALUE
            or int(p_raw) != P_VALUE
        ):
            return False
        salt = base64.urlsafe_b64decode(salt_raw.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_raw.encode("ascii"))
        if len(salt) < 16 or len(expected) != DIGEST_BYTES:
            return False
        return hmac.compare_digest(_derive(password, salt, length=len(expected)), expected)
    except (ValueError, TypeError, UnicodeError, binascii.Error):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    try:
        password = _read_password()
        if args.verify:
            encoded = sys.stdin.buffer.readline(8192).decode("ascii", errors="strict").strip()
            if verify_hash(password, encoded):
                print("OK")
                return 0
            print("INVALID", file=sys.stderr)
            return 3
        print(new_hash(password))
        return 0
    except (ValueError, UnicodeError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
