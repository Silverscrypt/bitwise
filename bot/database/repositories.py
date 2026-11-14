"""SQL access for Bitwise.

A Repository wraps one connection that is already inside a transaction
(see Database.transaction), so several calls made through the same
Repository commit or roll back together. Repositories only read and write
data: authorization and Discord calls belong to the services.
"""

from psycopg.rows import class_row
from psycopg.types.json import Jsonb

from bot.database.models import (
    LeaderRecord,
    MemberRecord,
    ProjectRecord,
    RoleRecord,
)


class Repository:

    def __init__(self, conn):
        self._conn = conn

    async def _fetch_one(self, row_type, query, params=()):
        async with self._conn.cursor(row_factory=class_row(row_type)) as cursor:
            await cursor.execute(query, params)
            return await cursor.fetchone()

    async def _fetch_all(self, row_type, query, params=()):
        async with self._conn.cursor(row_factory=class_row(row_type)) as cursor:
            await cursor.execute(query, params)
            return await cursor.fetchall()

    async def _execute(self, query, params=()):
        async with self._conn.cursor() as cursor:
            await cursor.execute(query, params)
            return cursor.rowcount

    # --------------------------------------------------
    # MEMBERS
    # --------------------------------------------------

    async def upsert_member(self, discord_id, username):
        await self._execute(
            """
            INSERT INTO members (discord_id, username)
            VALUES (%s, %s)
            ON CONFLICT (discord_id)
            DO UPDATE SET username = EXCLUDED.username;
            """,
            (discord_id, username),
        )

    async def get_member(self, discord_id):
        return await self._fetch_one(
            MemberRecord,
            """
            SELECT discord_id, username, joined_at
            FROM members
            WHERE discord_id = %s;
            """,
            (discord_id,),
        )

    # --------------------------------------------------
    # ROLES
    # --------------------------------------------------

    async def create_role(self, name, category, discord_role_id):
        """Register a role. Returns None if the name or Discord role is taken."""

        return await self._fetch_one(
            RoleRecord,
            """
            INSERT INTO roles (name, category, discord_role_id)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING id, name, category, discord_role_id;
            """,
            (name, category, discord_role_id),
        )

    async def delete_role(self, role_id):
        return await self._execute(
            "DELETE FROM roles WHERE id = %s;", (role_id,)
        ) > 0

    async def get_role_by_name(self, name):
        return await self._fetch_one(
            RoleRecord,
            """
            SELECT id, name, category, discord_role_id
            FROM roles
            WHERE lower(name) = lower(%s);
            """,
            (name,),
        )

    async def get_role_by_discord_id(self, discord_role_id):
        return await self._fetch_one(
            RoleRecord,
            """
            SELECT id, name, category, discord_role_id
            FROM roles
            WHERE discord_role_id = %s;
            """,
            (discord_role_id,),
        )

    async def list_roles(self, category=None):
        if category is None:
            return await self._fetch_all(
                RoleRecord,
                """
                SELECT id, name, category, discord_role_id
                FROM roles
                ORDER BY category, name;
                """,
            )

        return await self._fetch_all(
            RoleRecord,
            """
            SELECT id, name, category, discord_role_id
            FROM roles
            WHERE category = %s
            ORDER BY name;
            """,
            (category,),
        )

    async def assign_role(self, member_id, role_id):
        """Returns False if the member already had the role."""

        return await self._execute(
            """
            INSERT INTO member_roles (member_id, role_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
            """,
            (member_id, role_id),
        ) > 0

    async def remove_role(self, member_id, role_id):
        """Returns False if the member did not have the role."""

        return await self._execute(
            """
            DELETE FROM member_roles
            WHERE member_id = %s AND role_id = %s;
            """,
            (member_id, role_id),
        ) > 0

    async def get_member_roles(self, member_id):
        return await self._fetch_all(
            RoleRecord,
            """
            SELECT roles.id, roles.name, roles.category, roles.discord_role_id
            FROM roles
            JOIN member_roles ON roles.id = member_roles.role_id
            WHERE member_roles.member_id = %s
            ORDER BY roles.category, roles.name;
            """,
            (member_id,),
        )

    # --------------------------------------------------
    # PROJECTS
    # --------------------------------------------------

    async def create_project(self, name, description, discord_role_id):
        """Returns None if the name or Discord role is already used."""

        return await self._fetch_one(
            ProjectRecord,
            """
            INSERT INTO projects (name, description, discord_role_id)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING id, name, description, discord_role_id, created_at;
            """,
            (name, description, discord_role_id),
        )

    async def delete_project(self, project_id):
        return await self._execute(
            "DELETE FROM projects WHERE id = %s;", (project_id,)
        ) > 0

    async def get_project(self, name):
        return await self._fetch_one(
            ProjectRecord,
            """
            SELECT id, name, description, discord_role_id, created_at
            FROM projects
            WHERE lower(name) = lower(%s);
            """,
            (name,),
        )

    async def get_project_by_discord_id(self, discord_role_id):
        return await self._fetch_one(
            ProjectRecord,
            """
            SELECT id, name, description, discord_role_id, created_at
            FROM projects
            WHERE discord_role_id = %s;
            """,
            (discord_role_id,),
        )

    async def list_projects(self):
        return await self._fetch_all(
            ProjectRecord,
            """
            SELECT id, name, description, discord_role_id, created_at
            FROM projects
            ORDER BY name;
            """,
        )

    async def add_project_member(self, project_id, member_id):
        """Returns False if the member was already on the project."""

        return await self._execute(
            """
            INSERT INTO project_members (project_id, member_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
            """,
            (project_id, member_id),
        ) > 0

    async def remove_project_member(self, project_id, member_id):
        return await self._execute(
            """
            DELETE FROM project_members
            WHERE project_id = %s AND member_id = %s;
            """,
            (project_id, member_id),
        ) > 0

    async def get_project_members(self, project_id):
        return await self._fetch_all(
            MemberRecord,
            """
            SELECT members.discord_id, members.username, members.joined_at
            FROM members
            JOIN project_members ON members.discord_id = project_members.member_id
            WHERE project_members.project_id = %s
            ORDER BY lower(members.username);
            """,
            (project_id,),
        )

    async def get_member_projects(self, member_id):
        return await self._fetch_all(
            ProjectRecord,
            """
            SELECT projects.id, projects.name, projects.description,
                   projects.discord_role_id, projects.created_at
            FROM projects
            JOIN project_members ON projects.id = project_members.project_id
            WHERE project_members.member_id = %s
            ORDER BY projects.name;
            """,
            (member_id,),
        )

    # --------------------------------------------------
    # PROJECT LEADERSHIP
    # --------------------------------------------------

    async def set_project_leader(self, project_id, member_id, level):
        """Insert or change a member's leadership level on a project."""

        await self._execute(
            """
            INSERT INTO project_managers (project_id, member_id, level)
            VALUES (%s, %s, %s)
            ON CONFLICT (project_id, member_id)
            DO UPDATE SET level = EXCLUDED.level, assigned_at = CURRENT_TIMESTAMP;
            """,
            (project_id, member_id, level),
        )

    async def remove_project_leader(self, project_id, member_id):
        return await self._execute(
            """
            DELETE FROM project_managers
            WHERE project_id = %s AND member_id = %s;
            """,
            (project_id, member_id),
        ) > 0

    async def get_leadership_level(self, project_id, member_id):
        """Returns 'lead', 'manager', or None."""

        async with self._conn.cursor() as cursor:
            await cursor.execute(
                """
                SELECT level FROM project_managers
                WHERE project_id = %s AND member_id = %s;
                """,
                (project_id, member_id),
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def get_project_leaders(self, project_id):
        return await self._fetch_all(
            LeaderRecord,
            """
            SELECT projects.id AS project_id, projects.name AS project_name,
                   members.discord_id AS member_id, members.username,
                   project_managers.level
            FROM project_managers
            JOIN projects ON projects.id = project_managers.project_id
            JOIN members ON members.discord_id = project_managers.member_id
            WHERE project_managers.project_id = %s
            ORDER BY project_managers.level, lower(members.username);
            """,
            (project_id,),
        )

    async def get_member_leadership(self, member_id):
        return await self._fetch_all(
            LeaderRecord,
            """
            SELECT projects.id AS project_id, projects.name AS project_name,
                   members.discord_id AS member_id, members.username,
                   project_managers.level
            FROM project_managers
            JOIN projects ON projects.id = project_managers.project_id
            JOIN members ON members.discord_id = project_managers.member_id
            WHERE project_managers.member_id = %s
            ORDER BY projects.name;
            """,
            (member_id,),
        )

    # --------------------------------------------------
    # AUDIT LOG
    # --------------------------------------------------

    async def add_audit_log(self, actor_id, action, target_id=None, details=None):
        await self._execute(
            """
            INSERT INTO audit_logs (actor_id, action, target_id, details)
            VALUES (%s, %s, %s, %s);
            """,
            (actor_id, action, target_id, Jsonb(details or {})),
        )
