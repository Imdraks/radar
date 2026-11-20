"""Real Redis envelope migration on an explicitly loopback test broker, without FLUSH."""

import os
import uuid
from urllib.parse import urlsplit
import redis
from app.core import cache
from app.core.credential_cache import migrate, decode


def main():
    url = os.environ.get("RADAR_TEST_REDIS_URL", "")
    if os.environ.get("TESTING") != "true" or urlsplit(url).hostname not in {
        "localhost",
        "127.0.0.1",
    }:
        raise RuntimeError("Explicit disposable loopback Redis required")
    client = redis.from_url(url, decode_responses=True)
    cache.redis_client = client
    key = "cache:google_workspace_tokens:" + uuid.uuid4().hex
    try:
        client.setex(key, 120, '{"access_token":"PRIVATE-TEST-TOKEN"}')
        before = client.ttl(key)
        migrate()
        after = client.ttl(key)
        raw = client.get(key)
        assert "PRIVATE-TEST-TOKEN" not in raw
        assert (
            decode(key.removeprefix("cache:"), raw)["access_token"]
            == "PRIVATE-TEST-TOKEN"
        )
        assert 0 < after <= before
        assert before - after < 5
        print(
            "PASS actual Redis migration: encrypted value, owner scope, original TTL preserved"
        )
    finally:
        client.delete(key)


if __name__ == "__main__":
    main()
