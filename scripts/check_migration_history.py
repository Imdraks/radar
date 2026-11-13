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

        def migrate(revision):
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", revision],
                cwd=ROOT / "backend",
                env=env,
                capture_output=True,
                text=True,
            )
            if result.returncode:
                # Alembic failures can include bind values; only fixed exception categories are emitted.
                Path("/tmp/radar-migration-history-error.log").write_text(result.stderr)
                raise RuntimeError(
                    "Migration failed; private diagnostic at /tmp/radar-migration-history-error.log"
                )

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

                check_api(engine)
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
