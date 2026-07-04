import pytest
import os
import asyncio
from redis.asyncio import Redis
import asyncpg

# ==========================================
# CONCEPT: Testing Persistence Integration
# EDUCATIONAL NOTE: These tests verify that the running
# persistence containers (Redis / Postgres) are accessible.
# ==========================================

@pytest.mark.asyncio
async def test_redis_connection():
    """
    Verifies that the Redis server is responding.
    """
    # Use the 'redis' service name defined in docker-compose
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    try:
        redis_client = Redis.from_url(redis_url)
        # Ping the server
        response = await redis_client.ping()
        assert response is True, f"Failed to ping Redis at {redis_url}"
    except Exception as e:
        pytest.fail(f"Connection to Redis failed: {e}. Is the container running?")

@pytest.mark.asyncio
async def test_postgres_connection():
    """
    Verifies that the Postgres server is accessible.
    """
    # Use the 'postgres' service name and credentials from docker-compose
    db_url = os.getenv("DATABASE_URL", "postgresql://nexus:password@postgres:5432/nexus_dev")
    try:
        conn = await asyncpg.connect(db_url)
        version = await conn.fetchval('SELECT version()')
        assert "PostgreSQL" in version, "Failed to get Postgres version."
        await conn.close()
    except Exception as e:
        pytest.fail(f"Connection to Postgres failed: {e}. Is the container running?")

if __name__ == "__main__":
    asyncio.run(test_redis_connection())
    asyncio.run(test_postgres_connection())
