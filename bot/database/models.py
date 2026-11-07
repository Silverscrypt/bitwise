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
"""

CREATE_PROJECT_MEMBERS_TABLE = """
CREATE TABLE IF NOT EXISTS project_members (
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    member_id BIGINT REFERENCES members(discord_id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, member_id)
);
"""

from bot.database.connection import get_connection


def create_members_table():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(CREATE_MEMBERS_TABLE)

def create_roles_table():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(CREATE_ROLES_TABLE)

def create_member_roles_table():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(CREATE_MEMBER_ROLES_TABLE)

def create_projects_table():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(CREATE_PROJECTS_TABLE)

def create_project_members_table():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(CREATE_PROJECT_MEMBERS_TABLE)

def create_all_tables():
    create_members_table()
    create_roles_table()
    create_member_roles_table()
    create_projects_table()
    create_project_members_table()