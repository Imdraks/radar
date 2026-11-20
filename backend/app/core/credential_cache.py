"""Encrypted credential envelopes, scoped to OAuth caches; no provider values in logs."""

import json
from app.core.encryption import encrypt_sensitive, decrypt_sensitive

PREFIXES = ("google_workspace_tokens:", "google_calendar_tokens:")


def protected(key):
    return key.startswith(PREFIXES)


def encode(key, value):
    if protected(key):
        return json.dumps(
            {
                "radar_credentials_v1": encrypt_sensitive(
                    json.dumps({"scope": key, "value": value})
                )
            }
        )
    return json.dumps(value, default=str)


def decode(key, raw):
    data = json.loads(raw)
    if protected(key) and isinstance(data, dict) and "radar_credentials_v1" in data:
        plain = decrypt_sensitive(data["radar_credentials_v1"])
        if not plain:
            raise ValueError("Credential envelope unavailable")
        payload = json.loads(plain)
        if payload.get("scope") != key:
            raise ValueError("Credential cache scope mismatch")
        return payload["value"]
    return data  # Read legacy values until the explicit migration has run.


def migrate():
    from app.core.cache import redis_client

    updated = 0
    for prefix in PREFIXES:
        for full_key in redis_client.scan_iter(
            match="cache:" + prefix + "*", count=100
        ):
            raw = redis_client.get(full_key)
            if raw is None:
                continue
            key = full_key.removeprefix("cache:")
            data = decode(key, raw)
            sealed = encode(key, data)
            updated += int(
                redis_client.eval(
                    "if redis.call('GET', KEYS[1]) == ARGV[1] then redis.call('SET', KEYS[1], ARGV[2], 'KEEPTTL'); return 1 else return 0 end",
                    1,
                    full_key,
                    raw,
                    sealed,
                )
            )
    return updated


def migrate_accounts(db):
    from app.db.models.account import Account
    from app.core.encryption import encrypt_sensitive, decrypt_sensitive

    count = 0
    for row in db.query(Account).with_for_update().all():
        for field in ("access_token", "refresh_token", "id_token"):
            value = getattr(row, field)
            if not value:
                continue
            if value.startswith("enc:"):
                plain = decrypt_sensitive(value[4:])
                if not plain:
                    raise RuntimeError("Existing OAuth credential cannot be decrypted")
            else:
                plain = value
            setattr(row, field, "enc:" + encrypt_sensitive(plain))
            count += 1
    db.commit()
    return count


def migrate_fernet_fields(db):
    from sqlalchemy import text
    from app.core.encryption import decrypt_sensitive, encrypt_sensitive

    fields = {
        "users": ["mfa_email", "mfa_phone", "two_factor_secret"],
        "mfa_challenges": ["destination", "pending_secret"],
        "billing_clients": ["iban_encrypted"],
        "banking_connections": ["access_token_encrypted", "refresh_token_encrypted"],
        "banking_accounts": ["iban_encrypted"],
    }
    count = 0
    for table, columns in fields.items():
        for column in columns:
            last = None
            while True:
                query = f"SELECT id,{column} FROM {table} WHERE {column} IS NOT NULL"
                params = {}
                if last is not None:
                    query += " AND id>:last"
                    params["last"] = last
                rows = db.execute(
                    text(query + " ORDER BY id LIMIT 100 FOR UPDATE"), params
                ).all()
                if not rows:
                    break
                for id, value in rows:
                    last = id
                    if not value:
                        continue
                    if column == "two_factor_secret":
                        plain = (
                            decrypt_sensitive(value[4:])
                            if value.startswith("enc:")
                            else value
                        )
                        prefix = "enc:"
                    else:
                        plain = decrypt_sensitive(value)
                        prefix = ""
                    if not plain:
                        raise RuntimeError(
                            "Existing encrypted value cannot be read; retain legacy keys"
                        )
                    db.execute(
                        text(f"UPDATE {table} SET {column}=:value WHERE id=:id"),
                        {"id": id, "value": prefix + encrypt_sensitive(plain)},
                    )
                    count += 1
                db.commit()
    return count


if __name__ == "__main__":
    from app.db.session import SessionLocal
    from app.core.encrypted_binary import migrate_binaries

    try:
        with SessionLocal() as db:
            print(
                json.dumps(
                    {
                        "encrypted_cache_entries": migrate(),
                        "encrypted_account_fields": migrate_accounts(db),
                        "encrypted_binary_records": migrate_binaries(db),
                        "reencrypted_sensitive_fields": migrate_fernet_fields(db),
                    }
                )
            )
    except Exception:
        raise SystemExit(
            "Migration de chiffrement interrompue. Les valeurs déjà traitées restent lisibles ; vérifier les clés et relancer sans les remplacer."
        ) from None
