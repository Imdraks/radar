"""Authenticated AES-256-GCM for local profile photos and super-admin PDF evidence."""

import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from sqlalchemy.types import TypeDecorator, LargeBinary
from app.core.encryption import _primary_key, _previous_keys, _legacy_encryption_key

PREFIX = b"radar-blob:v1:"


def encrypt_binary(value, context):
    nonce = os.urandom(12)
    key = base64.urlsafe_b64decode(_primary_key())
    return PREFIX + nonce + AESGCM(key).encrypt(nonce, bytes(value), context.encode())


def decrypt_binary(value, context):
    value = bytes(value)
    if not value.startswith(PREFIX):
        return value  # Explicit compatible read of pre-migration records.
    data = value[len(PREFIX) :]
    if len(data) < 28:
        raise ValueError("Invalid encrypted binary")
    for key in [_primary_key(), *_previous_keys(), _legacy_encryption_key()]:
        try:
            return AESGCM(base64.urlsafe_b64decode(key)).decrypt(
                data[:12], data[12:], context.encode()
            )
        except InvalidTag:
            continue
    raise ValueError("Encrypted binary could not be authenticated")


class EncryptedBinary(TypeDecorator):
    impl = LargeBinary
    cache_ok = True

    def __init__(self, context):
        self.context = context
        super().__init__()

    def process_bind_param(self, value, dialect):
        return encrypt_binary(value, self.context) if value is not None else None

    def process_result_value(self, value, dialect):
        return decrypt_binary(value, self.context) if value is not None else None


def migrate_binaries(db):
    from sqlalchemy import text

    count = 0
    for table, column, context in [
        ("users", "avatar_image", "user-avatar"),
        ("external_client_contracts", "document", "platform-contract"),
    ]:
        # Small row batches: contract PDFs may be several megabytes each.
        last = 0
        while True:
            rows = db.execute(
                text(
                    f"SELECT id,{column} FROM {table} WHERE id>:last AND {column} IS NOT NULL ORDER BY id LIMIT 10 FOR UPDATE"
                ),
                {"last": last},
            ).all()
            if not rows:
                break
            for id, value in rows:
                raw = bytes(value)
                opened = decrypt_binary(raw, context)
                db.execute(
                    text(f"UPDATE {table} SET {column}=:value WHERE id=:id"),
                    {"id": id, "value": encrypt_binary(opened, context)},
                )
                count += 1
                last = id
            db.commit()
    return count
