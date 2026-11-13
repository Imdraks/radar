"""Private deploy readiness: dependencies and exact Alembic heads must match."""

import redis
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from app.core.config import settings
from app.db.session import engine


def main():
    expected = set(ScriptDirectory.from_config(Config("alembic.ini")).get_heads())
    with engine.connect() as connection:
        actual = set(
            connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalars()
        )
        if actual != expected:
            raise RuntimeError("Database schema is not at the application revision")
        if "artist_snapshots" not in inspect(connection).get_table_names():
            raise RuntimeError("Artist history schema missing")
    with redis.from_url(
        settings.redis_url, socket_connect_timeout=2, socket_timeout=2
    ) as cache:
        if not cache.ping():
            raise RuntimeError("Redis unavailable")
    print("Database, schema and Redis ready")


if __name__ == "__main__":
    main()
