"""Aggregate inventory must not disclose payloads or modify persistent records."""

import importlib.util
from pathlib import Path
import json
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

spec = importlib.util.spec_from_file_location(
    "storage_inventory", Path(__file__).parents[2] / "scripts/storage_inventory.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_inventory_only_counts_actual_non_null_columns_and_respects_read_only(engine):
    with engine.connect() as connection:
        connection.execute(
            text("CREATE TABLE storage_probe (payload bytea, title text)")
        )
        connection.execute(
            text(
                "INSERT INTO storage_probe VALUES (decode('414243','hex'),'PRIVATE-DOCUMENT-TEXT'),(NULL,'')"
            )
        )
        connection.commit()
        with connection.begin():
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            result = module.collect(
                connection,
                {
                    "storage_probe": ["payload", "title", "unknown"],
                    "missing_probe": ["payload"],
                },
            )
            assert result[0]["non_null_rows"] == 1
            assert result[1]["non_null_rows"] == 2
            assert result[2]["state"] == "colonne_absente"
            assert result[3]["state"] == "absente_ou_non_visible"
            assert "PRIVATE-DOCUMENT-TEXT" not in json.dumps(result)
            assert "ABC" not in json.dumps(result)
            with pytest.raises(DBAPIError):
                connection.execute(text("DELETE FROM storage_probe"))
        connection.rollback()
        assert (
            connection.execute(text("SELECT count(*) FROM storage_probe")).scalar_one()
            == 2
        )
        connection.rollback()
        connection.execute(text("DROP TABLE storage_probe"))
        connection.commit()


def test_inventory_configuration_failures_do_not_print_connection_secrets(
    monkeypatch, capsys
):
    def fail(*args, **kwargs):
        raise RuntimeError("PRIVATE-CONNECTION-SECRET")

    monkeypatch.setattr(module, "create_engine", fail)
    with pytest.raises(SystemExit) as error:
        module.main()
    assert "PRIVATE-CONNECTION-SECRET" not in str(error.value)
    assert capsys.readouterr().out == ""
