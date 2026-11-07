from bot.database.connection import get_connection

# --------------------------------------------------
# MEMBER REPOSITORY COMMANDS
# --------------------------------------------------

def add_member(discord_id, username):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO members (discord_id, username)
                VALUES (%s, %s)
                ON CONFLICT (discord_id)
                DO UPDATE SET username = EXCLUDED.username;
                """,
                (discord_id, username)
            )

def get_member(discord_id):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT discord_id, username, joined_at
                FROM members
                WHERE discord_id = %s;
                """,
                (discord_id,)
            )
            return cursor.fetchone()

def delete_member(discord_id):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM members
                WHERE discord_id = %s;
                """,
                (discord_id,)
            )
            return cursor.rowcount > 0

# --------------------------------------------------
# ROLE REPOSITORY COMMANDS
# --------------------------------------------------

def add_role(name, category):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO roles (name, category)
                VALUES (%s, %s)
                ON CONFLICT (name) DO NOTHING;
                """,
                (name, category)
            )

def get_role(name):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, category
                FROM roles
                WHERE name = %s;
                """,
                (name,)
            )
            return cursor.fetchone()
        
def delete_role(name):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM roles
                WHERE name = %s;
                """,
                (name,)
            )
            return cursor.rowcount > 0

def assign_role(discord_id, role_name):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO member_roles (member_id, role_id)
                SELECT members.discord_id, roles.id
                FROM members, roles
                WHERE members.discord_id = %s
                AND roles.name = %s
                ON CONFLICT DO NOTHING;
                """,
                (discord_id, role_name)
            )
            return cursor.rowcount > 0

def remove_role(discord_id, role_name):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM member_roles
                WHERE member_id = %s
                AND role_id = (
                    SELECT id FROM roles WHERE name = %s
                );
                """,
                (discord_id, role_name)
            )
            return cursor.rowcount > 0

def get_member_roles(discord_id):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT roles.id, roles.name, roles.category
                FROM roles
                JOIN member_roles
                    ON roles.id = member_roles.role_id
                WHERE member_roles.member_id = %s;
                """,
                (discord_id,)
            )
            return cursor.fetchall()

# --------------------------------------------------
# PROJECT REPOSITORY COMMANDS
# --------------------------------------------------

def add_project(name, description=None):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO projects (name, description)
                VALUES (%s, %s)
                ON CONFLICT (name) DO NOTHING;
                """,
                (name, description)
            )
            return cursor.rowcount > 0


def get_project(name):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, description, created_at
                FROM projects
                WHERE name = %s;
                """,
                (name,)
            )
            return cursor.fetchone()


def delete_project(name):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM projects
                WHERE name = %s;
                """,
                (name,)
            )
            return cursor.rowcount > 0


def assign_project(discord_id, project_name):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO project_members (project_id, member_id)
                SELECT projects.id, members.discord_id
                FROM projects, members
                WHERE projects.name = %s
                AND members.discord_id = %s
                ON CONFLICT DO NOTHING;
                """,
                (project_name, discord_id)
            )
            return cursor.rowcount > 0


def remove_project(discord_id, project_name):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM project_members
                WHERE member_id = %s
                AND project_id = (
                    SELECT id FROM projects WHERE name = %s
                );
                """,
                (discord_id, project_name)
            )
            return cursor.rowcount > 0


def get_project_members(project_name):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT members.discord_id, members.username
                FROM members
                JOIN project_members
                    ON members.discord_id = project_members.member_id
                JOIN projects
                    ON projects.id = project_members.project_id
                WHERE projects.name = %s;
                """,
                (project_name,)
            )
            return cursor.fetchall()