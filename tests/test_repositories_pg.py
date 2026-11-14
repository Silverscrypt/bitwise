"""Repository tests against a real PostgreSQL database.

Skipped unless BITWISE_TEST_DATABASE_URL points at a disposable database,
for example:

    docker run --rm -d -p 55432:5432 -e POSTGRES_PASSWORD=test postgres:16
    set BITWISE_TEST_DATABASE_URL=postgresql://postgres:test@localhost:55432/postgres

WARNING: the tests drop and recreate Bitwise's tables in that database.
"""

import asyncio
import os
import sys

import pytest

from bot.database.connection import Database


URL = os.getenv("BITWISE_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not URL, reason="BITWISE_TEST_DATABASE_URL not set")

TABLES = (
    "audit_logs", "project_managers", "project_members", "projects",
    "member_roles", "roles", "members",
)


def run_pg(coro):
    loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    return asyncio.run(coro, loop_factory=loop_factory)


async def fresh_database():
    db = Database(URL)
    await db._pool.open(wait=True)
    async with db._pool.connection() as conn:
        await conn.execute("DROP TABLE IF EXISTS " + ", ".join(TABLES) + " CASCADE")
    await db.close()

    db = Database(URL)
    await db.open()
    # Opening twice must be safe: the schema is applied on every startup.
    async with db._pool.connection() as conn:
        from bot.database.models import create_all_tables
        await create_all_tables(conn)
    return db


def test_repository_round_trip():
    async def scenario():
        db = await fresh_database()
        try:
            async with db.transaction() as repo:
                await repo.upsert_member(1, "alice")
                await repo.upsert_member(1, "alice2")
                assert (await repo.get_member(1)).username == "alice2"

                role = await repo.create_role("Developer", "functional", 111)
                assert role.discord_role_id == 111
                assert await repo.create_role("developer", "functional", 112) is None
                assert await repo.create_role("Other", "functional", 111) is None
                assert (await repo.get_role_by_name("DEVELOPER")).id == role.id
                assert (await repo.get_role_by_discord_id(111)).name == "Developer"

                assert await repo.assign_role(1, role.id) is True
                assert await repo.assign_role(1, role.id) is False
                assert [r.name for r in await repo.get_member_roles(1)] == ["Developer"]

                project = await repo.create_project("Alpha", "desc", 222)
                assert await repo.create_project("alpha", None, 223) is None
                assert (await repo.get_project_by_discord_id(222)).name == "Alpha"
                assert await repo.add_project_member(project.id, 1) is True
                assert await repo.add_project_member(project.id, 1) is False
                assert [m.discord_id for m in await repo.get_project_members(project.id)] == [1]
                assert [p.name for p in await repo.get_member_projects(1)] == ["Alpha"]

                await repo.set_project_leader(project.id, 1, "manager")
                await repo.set_project_leader(project.id, 1, "lead")
                assert await repo.get_leadership_level(project.id, 1) == "lead"
                leaders = await repo.get_project_leaders(project.id)
                assert [(l.project_name, l.username, l.level) for l in leaders] == [
                    ("Alpha", "alice2", "lead")
                ]
                assert len(await repo.get_member_leadership(1)) == 1

                await repo.add_audit_log(1, "test", 1, {"k": "v"})

            # A failed transaction leaves nothing behind.
            with pytest.raises(RuntimeError):
                async with db.transaction() as repo:
                    await repo.upsert_member(2, "bob")
                    raise RuntimeError("boom")

            async with db.transaction() as repo:
                assert await repo.get_member(2) is None

                assert await repo.remove_project_leader(project.id, 1) is True
                assert await repo.remove_project_member(project.id, 1) is True
                assert await repo.remove_role(1, role.id) is True
                assert await repo.remove_role(1, role.id) is False
                assert await repo.delete_project(project.id) is True
                assert await repo.delete_role(role.id) is True
                assert await repo.list_projects() == []
        finally:
            await db.close()

    run_pg(scenario())
