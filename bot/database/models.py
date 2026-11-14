"""Database schema and the record types repositories return.

There is no migration tool yet. Every statement here is idempotent so that
`create_all_tables` can run on every startup, including against databases
created by earlier versions of this file (the ALTER TABLE statements add
columns those versions did not have).
"""

from dataclasses import dataclass
from datetime import datetime


# --------------------------------------------------
# CATEGORIES
# --------------------------------------------------

# Role categories (DESIGN.md §2.2). Organizational authority (Officer) comes
# from OFFICER_ROLE_ID, and project authority from project_managers, so
# neither is stored as a role category here.
ROLE_CATEGORY_MEMBERSHIP = "membership"
ROLE_CATEGORY_FUNCTIONAL = "functional"
ROLE_CATEGORY_SPECIAL = "special"
ROLE_CATEGORIES = (
    ROLE_CATEGORY_MEMBERSHIP,
    ROLE_CATEGORY_FUNCTIONAL,
    ROLE_CATEGORY_SPECIAL,
)

LEADERSHIP_LEAD = "lead"
LEADERSHIP_MANAGER = "manager"
LEADERSHIP_LEVELS = (LEADERSHIP_LEAD, LEADERSHIP_MANAGER)


# --------------------------------------------------
# SCHEMA
# --------------------------------------------------

CREATE_MEMBERS_TABLE = """
CREATE TABLE IF NOT EXISTS members (
    discord_id BIGINT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_ROLES_TABLE = """
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL
);
ALTER TABLE roles ADD COLUMN IF NOT EXISTS discord_role_id BIGINT;
CREATE UNIQUE INDEX IF NOT EXISTS roles_discord_role_id_key ON roles (discord_role_id);
"""

CREATE_MEMBER_ROLES_TABLE = """
CREATE TABLE IF NOT EXISTS member_roles (
    member_id BIGINT REFERENCES members(discord_id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (member_id, role_id)
);
"""

CREATE_PROJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS discord_role_id BIGINT;
CREATE UNIQUE INDEX IF NOT EXISTS projects_discord_role_id_key ON projects (discord_role_id);
"""

CREATE_PROJECT_MEMBERS_TABLE = """
CREATE TABLE IF NOT EXISTS project_members (
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    member_id BIGINT REFERENCES members(discord_id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, member_id)
);
"""

# Project leadership is kept separate from ordinary project membership
# (DESIGN.md §6.3). A member holds at most one level per project.
CREATE_PROJECT_MANAGERS_TABLE = """
CREATE TABLE IF NOT EXISTS project_managers (
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    member_id BIGINT REFERENCES members(discord_id) ON DELETE CASCADE,
    level VARCHAR(20) NOT NULL CHECK (level IN ('lead', 'manager')),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, member_id)
);
"""

# actor_id and target_id are deliberately not foreign keys: audit records
# must survive the deletion of the members they mention.
CREATE_AUDIT_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    actor_id BIGINT NOT NULL,
    action VARCHAR(100) NOT NULL,
    target_id BIGINT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS audit_logs_target_idx ON audit_logs (target_id);
"""

ALL_TABLES = (
    CREATE_MEMBERS_TABLE,
    CREATE_ROLES_TABLE,
    CREATE_MEMBER_ROLES_TABLE,
    CREATE_PROJECTS_TABLE,
    CREATE_PROJECT_MEMBERS_TABLE,
    CREATE_PROJECT_MANAGERS_TABLE,
    CREATE_AUDIT_LOGS_TABLE,
)


async def create_all_tables(conn):
    """Create or upgrade every table. Takes an open AsyncConnection."""

    async with conn.transaction():
        async with conn.cursor() as cursor:
            for statement in ALL_TABLES:
                await cursor.execute(statement)


# --------------------------------------------------
# RECORDS
# --------------------------------------------------

@dataclass(frozen=True)
class MemberRecord:
    discord_id: int
    username: str
    joined_at: datetime | None = None


@dataclass(frozen=True)
class RoleRecord:
    id: int
    name: str
    category: str
    discord_role_id: int | None


@dataclass(frozen=True)
class ProjectRecord:
    id: int
    name: str
    description: str | None
    discord_role_id: int | None
    created_at: datetime | None = None


@dataclass(frozen=True)
class LeaderRecord:
    project_id: int
    project_name: str
    member_id: int
    username: str
    level: str
