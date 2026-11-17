"""Reviewed tenant archive. One SQL statement supplies a consistent PostgreSQL snapshot.
No provider request, credentials, erasure or entitlement change occurs here.
"""

import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from sqlalchemy import and_, or_, select, literal, func, cast, Text, Numeric, union_all
from fastapi import HTTPException
from app.db.base import Base
from app.db.models.artist_event import ArtistEvent  # Register the real event table.

POLICY = json.loads(
    (Path(__file__).parents[1] / "resources/workspace_export_policy.json").read_text()
)
MAX_ROWS = 100000
MAX_BYTES = 30 * 1024 * 1024
SECRET_KEY = re.compile(
    r"token|secret|password|passphrase|authorization|credentials?|access.?key|api.?key|cookie|private.?key|_encrypted|backup.?codes|^auth$|^key$|^jwt$",
    re.I,
)


def scrub(value):
    if isinstance(value, dict):
        return {
            k: ("[credential excluded]" if SECRET_KEY.search(k) else scrub(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, str) and value.startswith(("https://", "http://")):
        from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

        try:
            parts = urlsplit(value)
            host = parts.netloc.rsplit("@", 1)[-1]
            query = urlencode(
                [
                    (
                        k,
                        (
                            "[credential excluded]"
                            if SECRET_KEY.search(k)
                            or k.lower() in {"key", "signature", "sig", "code"}
                            else v
                        ),
                    )
                    for k, v in parse_qsl(parts.query, keep_blank_values=True)
                ]
            )
            return urlunsplit((parts.scheme, host, parts.path, query, ""))
        except ValueError:
            return "[invalid link excluded]"
    return value


def validate_policy():
    tables = Base.metadata.tables
    if set(tables) != set(POLICY["tables"]):
        raise HTTPException(
            503, "Le schéma d’export doit être revu après la modification des modèles"
        )
    for name, policy in POLICY["tables"].items():
        if "exclude" not in policy and set(
            policy["columns"] + policy["excluded_columns"]
        ) != set(tables[name].c.keys()):
            raise HTTPException(503, "La liste des champs exportables doit être revue")


def ownership_scopes(workspace_id):
    tables = Base.metadata.tables
    scopes = {}

    def owned(name):
        if name in scopes:
            return scopes[name]
        table = tables[name]
        policy = POLICY["tables"][name]
        if policy.get("workspace_record"):
            result = table.c.id == workspace_id
        elif policy.get("direct"):
            result = table.c.workspace_id == workspace_id
            # Client ownership remains authoritative for historical projects/assets.
            if name == "projects":
                client_owned = table.c.client_id.in_(
                    select(tables["clients"].c.id).where(owned("clients"))
                )
                result = and_(
                    or_(
                        table.c.workspace_id == workspace_id,
                        table.c.workspace_id.is_(None),
                    ),
                    or_(
                        client_owned,
                        and_(
                            table.c.client_id.is_(None),
                            table.c.workspace_id == workspace_id,
                        ),
                    ),
                )
            if name == "assets":
                project_owned = table.c.project_id.in_(
                    select(tables["projects"].c.id).where(owned("projects"))
                )
                result = and_(
                    or_(
                        table.c.workspace_id == workspace_id,
                        table.c.workspace_id.is_(None),
                    ),
                    or_(
                        project_owned,
                        and_(
                            table.c.project_id.is_(None),
                            table.c.workspace_id == workspace_id,
                        ),
                    ),
                )
        else:
            checks, present = [], []
            for key in policy["parents"]:
                column = table.c[key]
                fk = next(iter(column.foreign_keys))
                parent = fk.column.table
                checks.append(
                    or_(
                        column.is_(None),
                        column.in_(select(fk.column).where(owned(parent.name))),
                    )
                )
                present.append(column.is_not(None))
            result = and_(*checks, or_(*present))
        scopes[name] = result
        return result

    return {
        name: owned(name)
        for name, policy in POLICY["tables"].items()
        if "exclude" not in policy
    }


def archive(db, workspace_id):
    validate_policy()
    tables = Base.metadata.tables
    scopes = ownership_scopes(workspace_id)

    def owned(name):
        return scopes[name]

    selects = []
    included = {n: p for n, p in POLICY["tables"].items() if "exclude" not in p}
    for name, policy in included.items():
        table = tables[name]
        conditions = [owned(name)]
        # A corrupt cross-tenant foreign link must never expose another tenant's child data.
        for fk in table.foreign_keys:
            parent = fk.column.table.name
            if parent in included and parent != name and parent != "workspaces":
                conditions.append(
                    or_(
                        fk.parent.is_(None),
                        fk.parent.in_(select(fk.column).where(owned(parent))),
                    )
                )
        columns = []
        for key in policy["columns"]:
            col = table.c[key]
            # Preserve financial decimals exactly; no binary float conversion.
            value = cast(col, Text) if isinstance(col.type, Numeric) else col
            columns.extend([literal(key), value])
        payload = func.jsonb_build_object(*columns[:80])
        for start in range(80, len(columns), 80):
            payload = payload.op("||")(
                func.jsonb_build_object(*columns[start : start + 80])
            )
        selects.append(
            select(literal(name).label("dataset"), payload.label("payload"))
            .where(*conditions)
            .limit(MAX_ROWS + 1)
        )
    # Minimal organization directory, never the global user record or its credentials.
    users, members, workspace = (
        tables["users"],
        tables["workspace_members"],
        tables["workspaces"],
    )
    directory_ids = (
        select(members.c.user_id)
        .where(members.c.workspace_id == workspace_id)
        .union(select(workspace.c.owner_user_id).where(workspace.c.id == workspace_id))
    )
    selects.append(
        select(
            literal("member_directory").label("dataset"),
            func.jsonb_build_object(
                "id", users.c.id, "name", users.c.full_name, "email", users.c.email
            ).label("payload"),
        )
        .where(users.c.id.in_(directory_ids))
        .limit(MAX_ROWS + 1)
    )
    # Include only published contract versions actually accepted by this workspace.
    bundles, acceptances = tables["legal_bundles"], tables["legal_acceptances"]
    bundle_columns = []
    for key in (
        "id",
        "version",
        "content_hash",
        "publisher",
        "documents",
        "published_at",
    ):
        bundle_columns.extend([literal(key), bundles.c[key]])
    selects.append(
        select(
            literal("accepted_contract_versions").label("dataset"),
            func.jsonb_build_object(*bundle_columns).label("payload"),
        )
        .where(
            bundles.c.id.in_(
                select(acceptances.c.bundle_id).where(
                    acceptances.c.workspace_id == workspace_id
                )
            )
        )
        .limit(MAX_ROWS + 1)
    )
    buffers = {
        name: []
        for name in [*included, "member_directory", "accepted_contract_versions"]
    }
    rows, size = 0, 0
    external = []
    result = db.execute(union_all(*selects).execution_options(stream_results=True))
    try:
        for dataset, payload in result:
            payload = scrub(payload)
            raw = json.dumps(
                payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False
            ).encode()
            rows += 1
            size += len(raw) + 1
            if rows > MAX_ROWS or size > MAX_BYTES:
                raise HTTPException(
                    413,
                    "Export volumineux : demander une restitution assistée ; aucune archive partielle n’a été fournie",
                )
            buffers[dataset].append(raw)
            for key, value in payload.items():
                if value and (
                    key.startswith("drive_")
                    or key
                    in {
                        "url",
                        "link",
                        "storage_path",
                        "brief_doc_id",
                        "report_sheet_id",
                    }
                ):
                    external.append(
                        {
                            "dataset": dataset,
                            "record_id": str(payload.get("id", "")),
                            "field": key,
                            "reference": value,
                        }
                    )
    finally:
        result.close()
    output = io.BytesIO()
    manifest = {
        "format": POLICY["version"],
        "workspace_id": workspace_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database_snapshot": "single PostgreSQL statement",
        "counts": {name: len(values) for name, values in buffers.items()},
        "excluded_tables": {
            name: p["exclude"] for name, p in POLICY["tables"].items() if "exclude" in p
        },
        "excluded_columns": {
            name: p["excluded_columns"]
            for name, p in included.items()
            if p["excluded_columns"]
        },
        "limitations": [
            "External files are references only; original binaries must be recovered separately.",
            "Global and unassigned legacy records need manual ownership review.",
            "Rows with inconsistent cross-workspace relations are excluded and require reconciliation.",
            "Credential fields and credential-like JSON keys/URL parameters are excluded.",
            "This archive is not a complete Data Act handover or a database backup.",
        ],
        "sha256": {},
    }
    with ZipFile(output, "w", ZIP_DEFLATED) as zip_file:
        for name, values in buffers.items():
            data = b"[" + b",".join(values) + b"]"
            filename = "data/" + name + ".json"
            zip_file.writestr(filename, data)
            manifest["sha256"][filename] = hashlib.sha256(data).hexdigest()
        extra_files = {
            "external-files.json": json.dumps(external, ensure_ascii=False).encode(),
            "README.txt": "Radar — archive de données métier du workspace\nJSON UTF-8 ; décimaux financiers conservés sous forme de chaînes.\nLire manifest.json, contrôler les empreintes et récupérer séparément les fichiers externes.\nNe pas publier cette archive : elle peut contenir des données personnelles et commerciales.\nLa restitution ne supprime aucune donnée et ne transfère aucun droit d’accès.\n".encode(),
        }
        for name, data in extra_files.items():
            zip_file.writestr(name, data)
            manifest["sha256"][name] = hashlib.sha256(data).hexdigest()
        zip_file.writestr(
            "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2)
        )
    return output.getvalue(), manifest
