"""Commercial publication gate: real public identity and contractual documents are required."""

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

REQUIRED = (
    "companyName",
    "legalForm",
    "address",
    "siret",
    "rcs",
    "capital",
    "publicationDirector",
    "contactEmail",
    "hostingName",
    "hostingAddress",
    "hostingContact",
    "privacyContact",
    "dpaUrl",
    "subprocessorsUrl",
    "retentionPolicyUrl",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-template",
        action="store_true",
        help="Validate the configuration structure only, without authorizing publication",
    )
    args = parser.parse_args()
    config = json.loads(
        (
            Path(__file__).resolve().parents[1] / "frontend/src/config/legal.json"
        ).read_text()
    )
    if any(
        not isinstance(config.get(field), str) for field in REQUIRED
    ) or not isinstance(config.get("commercialReleaseEnabled"), bool):
        raise SystemExit("Invalid public legal configuration")
    if args.check_template:
        print("Legal configuration structure valid; commercial approval not implied")
        return
    missing = [field for field in REQUIRED if not config[field].strip()]
    if not config["commercialReleaseEnabled"]:
        missing.append("commercialReleaseEnabled")
    for key in ("dpaUrl", "subprocessorsUrl", "retentionPolicyUrl"):
        if urlparse(config[key]).scheme != "https":
            missing.append(key + " (HTTPS required)")
    if len(config["siret"]) != 14 or not config["siret"].isdigit():
        missing.append("siret (14 digits)")
    if missing:
        raise SystemExit("Commercial publication blocked: " + ", ".join(missing))
    print(
        "Public identity and contractual references configured; legal review and operational acceptance remain necessary"
    )


if __name__ == "__main__":
    main()
