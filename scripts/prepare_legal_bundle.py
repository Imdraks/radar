"""Prepare an offline B2B bundle. Never publishes, accepts, signs or invents company/provider facts."""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(config, version, reference):
    fields = {
        "IMMATRICULATION": "rcs",
        "CAPITAL": "capital",
        "TVA_INTRACOMMUNAUTAIRE": "vatNumber",
        "EDITEUR": "companyName",
        "FORME_JURIDIQUE": "legalForm",
        "SIRET": "siret",
        "ADRESSE": "address",
        "EMAIL": "contactEmail",
        "TELEPHONE": "phone",
        "PRIVACY_CONTACT": "privacyContact",
        "HOSTING_NAME": "hostingName",
        "HOSTING_ADDRESS": "hostingAddress",
        "HOSTING_CONTACT": "hostingContact",
        "CONTACT_RETENTION": "contactRetention",
        "WORKSPACE_RETENTION": "workspaceRetention",
        "SECURITY_LOG_RETENTION": "securityLogsRetention",
        "RIGHTS_RETENTION": "rightsRequestRetention",
    }
    values = {key: config.get(field, "").strip() for key, field in fields.items()}
    values["VERSION_CONTRACTUELLE"] = version
    documents = {}
    for path in sorted((ROOT / "backend/app/resources/legal_templates").glob("*.txt")):
        text = path.read_text()
        documents[path.stem] = re.sub(
            r"\[\[([A-Z_]+)\]\]", lambda m: values.get(m[1]) or m[0], text
        )
    publisher_keys = {
        "name": "companyName",
        "registration": "rcs",
        "capital": "capital",
        "vat_number": "vatNumber",
        "legal_form": "legalForm",
        "siret": "siret",
        "address": "address",
        "email": "contactEmail",
        "phone": "phone",
        "publication_director": "publicationDirector",
        "hosting_name": "hostingName",
        "hosting_address": "hostingAddress",
        "hosting_contact": "hostingContact",
    }
    publisher = {
        key: config.get(field, "").strip() or "[[" + field.upper() + "]]"
        for key, field in publisher_keys.items()
    }
    unresolved = sorted(
        set(
            re.findall(
                r"\[\[([^\]]+)\]\]",
                json.dumps([documents, publisher], ensure_ascii=False),
            )
        )
    )
    return {
        "version": version,
        "publisher": publisher,
        "documents": documents,
        "review_reference": reference,
        "reviewed_for_publication": False,
    }, unresolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "frontend/src/config/legal.json"
    )
    parser.add_argument("--version", required=True)
    parser.add_argument("--review-reference", default="")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    bundle, missing = prepare(
        json.loads(args.config.read_text()), args.version, args.review_reference
    )
    if args.output.exists():
        raise SystemExit(
            "Choose a new output path to preserve previous review evidence"
        )
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n")
    if not missing:
        import hashlib

        normalized = dict(bundle["publisher"])
        # These fields are optional in the API for non-applicable cases, not guessed here.
        normalized.setdefault("capital", "")
        normalized.setdefault("vat_number", "")
        print(
            "Publisher fingerprint for verified configuration:",
            hashlib.sha256(
                json.dumps(
                    normalized,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest(),
        )
    print(
        "Offline draft written; not published or approved. Fields to complete:",
        len(missing),
    )
    for name in missing:
        print("-", name)
    print(
        "Complete the texts, obtain review, set the real review reference and explicit publication declaration before submitting to the operator. No API call was made."
    )


if __name__ == "__main__":
    main()
