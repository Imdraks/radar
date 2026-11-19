"""Explicitly scoped, read-only replacement for the old root client scripts."""
import argparse
import json


def positive(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError('La valeur doit être un entier positif.')
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description='Inventaire en lecture seule des clients d’un workspace explicite.')
    parser.add_argument('--workspace-id', type=positive, required=True)
    parser.add_argument('--kind', choices=['crm', 'billing', 'both'], default='both')
    parser.add_argument('--limit', type=positive, default=50, help='Maximum 500 lignes par catégorie.')
    args = parser.parse_args(argv)
    if args.limit > 500:
        parser.error('--limit ne peut pas dépasser 500.')

    # Importing this module or requesting --help never opens a database connection.
    from sqlalchemy import text
    from app.db.session import SessionLocal
    from app.db.models.agency import Client
    from app.db.models.billing import BillingClient
    from app.db.models.workspace import Workspace

    with SessionLocal() as db:
        # Enforce read-only at PostgreSQL level, not just by convention.
        db.execute(text('SET TRANSACTION READ ONLY'))
        if db.query(Workspace.id).filter(Workspace.id == args.workspace_id).first() is None:
            raise SystemExit('Workspace introuvable ; aucune modification effectuée.')
        output = {'workspace_id': args.workspace_id, 'limit_per_category': args.limit}
        for kind, model in [('crm', Client), ('billing', BillingClient)]:
            if args.kind not in [kind, 'both']:
                continue
            query = db.query(model.id, model.name).filter(model.workspace_id == args.workspace_id)
            output[kind] = {'total': query.count(), 'items': [
                {'id': row.id, 'name': row.name}
                for row in query.order_by(model.id).limit(args.limit)
            ]}
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
