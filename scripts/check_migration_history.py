"""Verify fresh install + historic branch paths in isolated disposable PostgreSQL databases.
Requires RADAR_TEST_DATABASE_URL. Never migrates that database or a configured application DB.
"""

import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]


def run():
    url = make_url(os.environ["RADAR_TEST_DATABASE_URL"])
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    for start in [
        None,
        "020_workspace_inbox",
        "010_billing",
        "032_billing_enhancements",
        "043_merge_heads",
        "050_collection_ownership",
    ]:
        database = "radar_migration_" + uuid4().hex
        with admin.connect() as conn:
            conn.execute(text(f"CREATE DATABASE {database}"))
        target = url.set(database=database)
        engine = create_engine(target)
        env = {
            **os.environ,
            "DATABASE_URL": target.render_as_string(hide_password=False),
            "TESTING": "true",
        }

        def migrate(revision, direction="upgrade", expected_failure=None):
            result = subprocess.run(
                [sys.executable, "-m", "alembic", direction, revision],
                cwd=ROOT / "backend",
                env=env,
                capture_output=True,
                text=True,
            )
            if result.returncode:
                if expected_failure:
                    assert expected_failure in result.stderr
                    return
                # Alembic failures can include bind values; only fixed exception categories are emitted.
                Path("/tmp/radar-migration-history-error.log").write_text(result.stderr)
                raise RuntimeError(
                    "Migration failed; private diagnostic at /tmp/radar-migration-history-error.log"
                )
            if expected_failure:
                raise AssertionError("An unsafe migration unexpectedly succeeded")

        try:
            if start:
                migrate(start)
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            "INSERT INTO users (id,email,full_name) VALUES (987654,'migration-test@example.com','Preserve owner')"
                        )
                    )
                    conn.execute(
                        text(
                            "INSERT INTO workspaces (id,name,owner_user_id,devis_template_doc_id) VALUES (987654,'Preserve workspace',987654,'original-template')"
                        )
                    )
            migrate("head")
            # Models and migrations must agree, not just two hand-written test schemas.
            sys.path.insert(0, str(ROOT / "backend"))
            from app.main import app
            from app.db.base import Base

            observed = inspect(engine)
            for name, table in Base.metadata.tables.items():
                if not observed.has_table(name):
                    raise AssertionError("Missing table " + name)
                if not set(table.columns.keys()) <= {
                    c["name"] for c in observed.get_columns(name)
                }:
                    raise AssertionError("Missing mapped columns in " + name)
            if start:
                with engine.connect() as conn:
                    assert conn.execute(
                        text(
                            "SELECT name,devis_template_doc_id FROM workspaces WHERE id=987654"
                        )
                    ).one() == ("Preserve workspace", "original-template")
            if start is None:
                from check_migrated_api import run as check_api

                # New lifecycle, factor and document guards are tested on this
                # disposable database only; production evidence is never removed.
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            "INSERT INTO users (id,email,must_change_password) VALUES (987652,'admin-migration@example.com',true)"
                        )
                    )
                migrate(
                    "059_profile_avatar",
                    direction="downgrade",
                    expected_failure="terminer les parcours de sécurité",
                )
                with engine.begin() as conn:
                    assert conn.execute(
                        text("SELECT must_change_password FROM users WHERE id=987652")
                    ).scalar_one()
                    conn.execute(
                        text(
                            "UPDATE users SET must_change_password=false WHERE id=987652"
                        )
                    )
                    conn.execute(
                        text(
                            "INSERT INTO passkey_credentials (id,user_id,credential_id,public_key,sign_count,name,created_at) VALUES ('00000000-0000-0000-0000-000000000001',987652,decode('01','hex'),decode('02','hex'),0,'TEST migration',now())"
                        )
                    )
                migrate(
                    "060_client_lifecycle",
                    direction="downgrade",
                    expected_failure="aucune suppression de facteur automatique",
                )
                with engine.begin() as conn:
                    conn.execute(
                        text("DELETE FROM passkey_credentials WHERE user_id=987652")
                    )
                    conn.execute(
                        text(
                            "INSERT INTO platform_quotes (status,issuer,buyer,lines,total_ht,total_tax,total_ttc,currency,valid_until,notes,created_at) VALUES ('draft','{}','{}','[]',0,0,0,'EUR',CURRENT_DATE,'TEST migration',now())"
                        )
                    )
                migrate(
                    "061_passkeys",
                    direction="downgrade",
                    expected_failure="documents commerciaux",
                )
                with engine.begin() as conn:
                    assert (
                        conn.execute(
                            text("SELECT count(*) FROM platform_quotes")
                        ).scalar_one()
                        == 1
                    )
                    conn.execute(text("DELETE FROM platform_quotes"))
                    conn.execute(text("DELETE FROM users WHERE id=987652"))
                print(
                    "PASS platform migration: active setup, credentials and documents prevent destructive downgrade",
                    flush=True,
                )

                # A photo is user data: never drop it automatically on rollback.
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            "INSERT INTO users (id,email,avatar_image) VALUES (987653,'photo-migration@example.com',decode('ffd8ffd9','hex'))"
                        )
                    )
                migrate(
                    "058_revocable_sessions",
                    direction="downgrade",
                    expected_failure="Exporter les photos personnalisées",
                )
                with engine.begin() as conn:
                    assert bytes(
                        conn.execute(
                            text("SELECT avatar_image FROM users WHERE id=987653")
                        ).scalar_one()
                    ) == bytes.fromhex("ffd8ffd9")
                    conn.execute(text("DELETE FROM users WHERE id=987653"))
                migrate("058_revocable_sessions", direction="downgrade")
                migrate("head")
                print(
                    "PASS profile photo migration: clean rollback and used-photo rollback refused",
                    flush=True,
                )

                # Check a truly unused schema before API logins create sessions.
                migrate("057_multichannel_mfa", direction="downgrade")
                migrate("head")
                check_api(engine)
                migrate(
                    "057_multichannel_mfa",
                    direction="downgrade",
                    expected_failure="Downgrade automatique refusé",
                )
                # Only disposable harness records are removed for the legacy MFA check.
                with engine.begin() as conn:
                    conn.execute(text("DELETE FROM user_sessions"))
                    conn.execute(text("DELETE FROM trusted_devices"))
                # A clean MFA schema can roll back. Upgrading a legacy enabled
                # TOTP account preserves its secret and revokes old sessions.
                migrate("056_full_credit_notes", direction="downgrade")
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            "UPDATE users SET two_factor_enabled = true, two_factor_secret = 'JBSWY3DPEHPK3PXP' WHERE email = 'migrated-api@example.com'"
                        )
                    )
                migrate("head")
                with engine.connect() as conn:
                    row = conn.execute(
                        text(
                            "SELECT mfa_version,two_factor_secret FROM users WHERE email = 'migrated-api@example.com'"
                        )
                    ).one()
                    assert row == (1, "JBSWY3DPEHPK3PXP")
                migrate(
                    "056_full_credit_notes",
                    direction="downgrade",
                    expected_failure="Downgrade automatique refusé",
                )
                print(
                    "PASS MFA migration: clean rollback, legacy preservation, session revocation, unsafe downgrade refused",
                    flush=True,
                )
            # A second upgrade must not renumber or recreate existing records.
            migrate("head")
            print("PASS migration path:", start or "empty database", flush=True)
        finally:
            engine.dispose()
            with admin.connect() as conn:
                conn.execute(text(f"DROP DATABASE {database} WITH (FORCE)"))
    admin.dispose()


if __name__ == "__main__":
    run()
