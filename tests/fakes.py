"""In-memory stand-ins for the database and Discord, so services can be
tested without PostgreSQL or a Discord connection (DESIGN.md §11.2).

FakeDatabase.transaction() snapshots state and restores it if an exception
escapes the block, mirroring a real PostgreSQL transaction rollback.
"""

import copy
from contextlib import asynccontextmanager
from types import SimpleNamespace

import discord

from bot.database.models import LeaderRecord, MemberRecord, ProjectRecord, RoleRecord


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

class FakeState:

    def __init__(self):
        self.members = {}            # discord_id -> username
        self.roles = {}              # id -> RoleRecord
        self.member_roles = set()    # (member_id, role_id)
        self.projects = {}           # id -> ProjectRecord
        self.project_members = set() # (project_id, member_id)
        self.leaders = {}            # (project_id, member_id) -> level
        self.audit = []              # (actor_id, action, target_id, details)
        self.next_id = 1


class FakeRepository:

    def __init__(self, state):
        self.s = state

    def _new_id(self):
        self.s.next_id += 1
        return self.s.next_id

    # members
    async def upsert_member(self, discord_id, username):
        self.s.members[discord_id] = username

    async def get_member(self, discord_id):
        if discord_id not in self.s.members:
            return None
        return MemberRecord(discord_id, self.s.members[discord_id])

    # roles
    async def create_role(self, name, category, discord_role_id):
        for role in self.s.roles.values():
            if role.name.lower() == name.lower() or role.discord_role_id == discord_role_id:
                return None
        record = RoleRecord(self._new_id(), name, category, discord_role_id)
        self.s.roles[record.id] = record
        return record

    async def delete_role(self, role_id):
        self.s.member_roles = {(m, r) for m, r in self.s.member_roles if r != role_id}
        return self.s.roles.pop(role_id, None) is not None

    async def get_role_by_name(self, name):
        return next((r for r in self.s.roles.values() if r.name.lower() == name.lower()), None)

    async def get_role_by_discord_id(self, discord_role_id):
        return next((r for r in self.s.roles.values() if r.discord_role_id == discord_role_id), None)

    async def list_roles(self, category=None):
        return [r for r in self.s.roles.values() if category in (None, r.category)]

    async def assign_role(self, member_id, role_id):
        assert member_id in self.s.members, "FK violation: member"
        key = (member_id, role_id)
        if key in self.s.member_roles:
            return False
        self.s.member_roles.add(key)
        return True

    async def remove_role(self, member_id, role_id):
        key = (member_id, role_id)
        if key not in self.s.member_roles:
            return False
        self.s.member_roles.remove(key)
        return True

    async def get_member_roles(self, member_id):
        return [self.s.roles[r] for m, r in self.s.member_roles if m == member_id]

    # projects
    async def create_project(self, name, description, discord_role_id):
        for p in self.s.projects.values():
            if p.name.lower() == name.lower() or p.discord_role_id == discord_role_id:
                return None
        record = ProjectRecord(self._new_id(), name, description, discord_role_id)
        self.s.projects[record.id] = record
        return record

    async def delete_project(self, project_id):
        self.s.project_members = {(p, m) for p, m in self.s.project_members if p != project_id}
        self.s.leaders = {k: v for k, v in self.s.leaders.items() if k[0] != project_id}
        return self.s.projects.pop(project_id, None) is not None

    async def get_project(self, name):
        return next((p for p in self.s.projects.values() if p.name.lower() == name.lower()), None)

    async def get_project_by_discord_id(self, discord_role_id):
        return next((p for p in self.s.projects.values() if p.discord_role_id == discord_role_id), None)

    async def list_projects(self):
        return sorted(self.s.projects.values(), key=lambda p: p.name)

    async def add_project_member(self, project_id, member_id):
        assert member_id in self.s.members, "FK violation: member"
        key = (project_id, member_id)
        if key in self.s.project_members:
            return False
        self.s.project_members.add(key)
        return True

    async def remove_project_member(self, project_id, member_id):
        key = (project_id, member_id)
        if key not in self.s.project_members:
            return False
        self.s.project_members.remove(key)
        return True

    async def get_project_members(self, project_id):
        return [
            MemberRecord(m, self.s.members[m])
            for p, m in self.s.project_members if p == project_id
        ]

    async def get_member_projects(self, member_id):
        return [self.s.projects[p] for p, m in self.s.project_members if m == member_id]

    # leadership
    async def set_project_leader(self, project_id, member_id, level):
        assert member_id in self.s.members, "FK violation: member"
        self.s.leaders[(project_id, member_id)] = level

    async def remove_project_leader(self, project_id, member_id):
        return self.s.leaders.pop((project_id, member_id), None) is not None

    async def get_leadership_level(self, project_id, member_id):
        return self.s.leaders.get((project_id, member_id))

    def _leader(self, key, level):
        project_id, member_id = key
        return LeaderRecord(
            project_id, self.s.projects[project_id].name,
            member_id, self.s.members[member_id], level,
        )

    async def get_project_leaders(self, project_id):
        return [self._leader(k, v) for k, v in self.s.leaders.items() if k[0] == project_id]

    async def get_member_leadership(self, member_id):
        return [self._leader(k, v) for k, v in self.s.leaders.items() if k[1] == member_id]

    # audit
    async def add_audit_log(self, actor_id, action, target_id=None, details=None):
        self.s.audit.append((actor_id, action, target_id, details or {}))


class FakeDatabase:

    def __init__(self):
        self.state = FakeState()

    @asynccontextmanager
    async def transaction(self):
        snapshot = copy.deepcopy(self.state)
        try:
            yield FakeRepository(self.state)
        except BaseException:
            self.state.__dict__.update(snapshot.__dict__)
            raise

    @property
    def repo(self):
        """Direct access for arranging test data."""
        return FakeRepository(self.state)


# --------------------------------------------------
# DISCORD
# --------------------------------------------------

def permissions(**granted):
    return SimpleNamespace(**granted)


class FakeRole:

    def __init__(self, id, name, position, perms=None, managed=False, default=False):
        self.id = id
        self.name = name
        self.position = position
        self.permissions = perms or permissions()
        self.managed = managed
        self._default = default
        self.mention = f"<@&{id}>"

    def is_default(self):
        return self._default


class FakeGuild:

    def __init__(self, owner_id=1):
        self.owner_id = owner_id
        self.roles = {}
        self.me = None

    def add_role(self, role):
        self.roles[role.id] = role
        return role

    def get_role(self, role_id):
        return self.roles.get(role_id)


def forbidden():
    return discord.Forbidden(SimpleNamespace(status=403, reason="Forbidden"), "Missing Permissions")


class FakeMember:

    def __init__(self, id, guild, roles=(), bot=False, manage_roles=False, administrator=False):
        self.id = id
        self.name = f"user{id}"
        self.display_name = self.name
        self.guild = guild
        self.bot = bot
        self.roles = list(roles)
        self.guild_permissions = permissions(manage_roles=manage_roles, administrator=administrator)
        self.fail_with = None  # exception raised by the next role change
        self.role_calls = []

    @property
    def top_role(self):
        return max(self.roles, key=lambda r: r.position, default=FakeRole(0, "@everyone", 0))

    async def add_roles(self, *roles, reason=None):
        self.role_calls.append(("add", [r.id for r in roles]))
        if self.fail_with:
            raise self.fail_with
        self.roles.extend(r for r in roles if r not in self.roles)

    async def remove_roles(self, *roles, reason=None):
        self.role_calls.append(("remove", [r.id for r in roles]))
        if self.fail_with:
            raise self.fail_with
        self.roles = [r for r in self.roles if r not in roles]

    def __str__(self):
        return self.name


class World:
    """A small server: owner, bot, an Officer, and roles in hierarchy order.

    Positions: everyone 0 < designer 3 < developer 4 < alpha 5 < beta 6
               < officer 10 < bot 20 < admin 30
    """

    OFFICER_ROLE_ID = 1000

    def __init__(self):
        self.db = FakeDatabase()
        self.guild = FakeGuild(owner_id=1)
        g = self.guild

        self.everyone = g.add_role(FakeRole(9000, "@everyone", 0, default=True))
        self.designer = g.add_role(FakeRole(2003, "Designer", 3))
        self.developer = g.add_role(FakeRole(2004, "Developer", 4))
        self.alpha_role = g.add_role(FakeRole(2005, "Project Alpha", 5))
        self.beta_role = g.add_role(FakeRole(2006, "Project Beta", 6))
        self.officer_role = g.add_role(FakeRole(self.OFFICER_ROLE_ID, "Officer", 10))
        self.bot_role = g.add_role(FakeRole(2020, "Bitwise", 20, managed=True))
        self.admin_role = g.add_role(
            FakeRole(2030, "Admin", 30, perms=permissions(administrator=True))
        )

        g.me = FakeMember(500, g, [self.bot_role], bot=True, manage_roles=True)
        self.officer = FakeMember(10, g, [self.officer_role])

        self._next_member_id = 100

    def member(self, *roles, **kwargs):
        self._next_member_id += 1
        return FakeMember(self._next_member_id, self.guild, roles, **kwargs)

    def audit_actions(self):
        return [entry[1] for entry in self.db.state.audit]
