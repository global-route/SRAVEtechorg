import os
import asyncpg

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST", "postgres-db"),
            port=int(os.getenv("DB_PORT", 5432)),
            database=os.getenv("DB_NAME", "srave_prod"),
            user=os.getenv("DB_USER", "srave_user"),
            password=os.getenv("DB_PASSWORD"),
            min_size=2,
            max_size=10,
        )
    return _pool
