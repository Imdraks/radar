"""Read-only aggregate storage inventory. Never reads or prints document contents."""

import json
from sqlalchemy import inspect, text
from app.core.config import settings
from sqlalchemy import create_engine

TARGETS = {
    "users": ["avatar_image"],
    "external_client_contracts": ["document"],
    "source_documents": ["raw_text", "raw_html"],
    "source_documents_v2": ["raw_text", "raw_html"],
    "documents": ["full_content"],
    "quotes": ["description", "notes"],
    "invoices": ["description", "notes", "issued_snapshot"],
    "invoice_items": ["description"],
    "quote_items": ["description"],
    "deliverable_reviews": ["snapshot", "feedback"],
}


def collect(connection, targets=None):
    schema = inspect(connection)
    quote = connection.dialect.identifier_preparer.quote
    result = []
    for table, columns in (TARGETS if targets is None else targets).items():
        if not schema.has_table(table):
            result.append({"table": table, "state": "absente_ou_non_visible"})
            continue
        existing = {column["name"] for column in schema.get_columns(table)}
        for column in columns:
            if column not in existing:
                result.append(
                    {"table": table, "column": column, "state": "colonne_absente"}
                )
                continue
            rows = connection.execute(
                text(
                    f"SELECT count(*) FROM {quote(table)} WHERE {quote(column)} IS NOT NULL"
                )
            ).scalar_one()
            result.append({"table": table, "column": column, "non_null_rows": rows})
    return result


def main():
    # Do not log settings, URLs, credentials, SQL parameters or data values.
    engine = None
    try:
        engine = create_engine(
            settings.database_url, echo=False, connect_args={"connect_timeout": 5}
        )
        with engine.connect() as connection, connection.begin():
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            connection.exec_driver_sql("SET LOCAL statement_timeout = '10s'")
            result = collect(connection)
        print(
            json.dumps(
                {
                    "scope": "PostgreSQL uniquement, comptages agrégés, aucun contenu ni identifiant client",
                    "note": "Une valeur non nulle peut être vide. Ce contrôle ne couvre ni disque, ni caches, ni sauvegardes, ni Drive.",
                    "results": result,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    except Exception:
        raise SystemExit(
            "Inventaire non terminé : vérifier les droits, la connexion et la charge PostgreSQL. Aucun résultat vide ne peut en être déduit."
        ) from None
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
