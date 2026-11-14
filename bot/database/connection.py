from contextlib import asynccontextmanager

from psycopg_pool import AsyncConnectionPool

from bot.database.models import create_all_tables
from bot.database.repositories import Repository


class Database:
    """Owns the connection pool and hands out transactional repositories.

    Usage:

        async with db.transaction() as repo:
            await repo.assign_role(...)
            await repo.add_audit_log(...)

    Everything inside the block commits together, or rolls back together if
    an exception escapes it. Services rely on this to undo database writes
    when the matching Discord role change fails.
    """

    def __init__(self, database_url, min_size=1, max_size=5):
        self._pool = AsyncConnectionPool(
            database_url,
            min_size=min_size,
            max_size=max_size,
            open=False,
        )

    async def open(self):
        await self._pool.open(wait=True, timeout=15)

        async with self._pool.connection() as conn:
            await create_all_tables(conn)

    async def close(self):
        await self._pool.close()

    @asynccontextmanager
    async def transaction(self):
        async with self._pool.connection() as conn:
            async with conn.transaction():
                yield Repository(conn)

    async def ping(self):
        async with self._pool.connection() as conn:
            await conn.execute("SELECT 1")
