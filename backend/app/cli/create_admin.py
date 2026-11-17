"""Offline first-administrator creation: password is read privately, never from argv."""

import argparse
from getpass import getpass
from app.api.auth import InitialSetup, create_initial_admin
from app.db.session import SessionLocal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    password = getpass("Mot de passe administrateur : ")
    if password != getpass("Confirmer : "):
        raise SystemExit("Les mots de passe ne correspondent pas")
    with SessionLocal() as db:
        create_initial_admin(
            db, InitialSetup(email=args.email, full_name=args.name, password=password)
        )
    print(
        "Administrateur initial créé. L’initialisation publique reste désactivée par défaut."
    )


if __name__ == "__main__":
    main()
