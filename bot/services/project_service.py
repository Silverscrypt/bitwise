"""Project rosters and project leadership (DESIGN.md §2.2, §7.2).

Each project maps to one Discord role. Project membership in the database
and the Discord project role are kept in sync: a change that Discord rejects
is rolled back in the database too.
"""

from dataclasses import dataclass

from bot.database.models import (
    LEADERSHIP_LEAD,
    LEADERSHIP_LEVELS,
    LeaderRecord,
    MemberRecord,
    ProjectRecord,
)
from bot.services.authorization import (
    can_manage_leadership_level,
    can_manage_project_members,
    ensure_bot_can_assign,
    ensure_role_is_manageable,
    has_role,
    is_officer,
    sync_discord,
)
from bot.services.errors import InvalidRequest, NotFound, PermissionDenied


LEVEL_NAMES = {"lead": "Project Lead", "manager": "Project Manager"}


@dataclass(frozen=True)
class Roster:
    project: ProjectRecord
    leaders: list[LeaderRecord]
    members: list[MemberRecord]


class ProjectService:

    def __init__(self, db, officer_role_id):
        self.db = db
        self.officer_role_id = officer_role_id

    # --------------------------------------------------
    # HELPERS
    # --------------------------------------------------

    def _require_officer(self, actor, action):
        if not is_officer(actor, self.officer_role_id):
            raise PermissionDenied(f"Only Officers can {action}.")

    async def _get_project(self, repo, name):
        project = await repo.get_project(name)
        if project is None:
            raise NotFound(f"There is no project named {name}.")
        return project

    async def _actor_authority(self, repo, actor, project):
        """Returns (is_officer, leadership level on this project or None)."""

        officer = is_officer(actor, self.officer_role_id)
        level = await repo.get_leadership_level(project.id, actor.id)
        return officer, level

    def _project_role(self, guild, project):
        role = guild.get_role(project.discord_role_id) if project.discord_role_id else None
        if role is None:
            raise InvalidRequest(
                f"{project.name}'s Discord role no longer exists. An Officer "
                "can run /setup to see what needs fixing."
            )

        ensure_role_is_manageable(role)
        ensure_bot_can_assign(role, guild.me)
        return role

    async def _add_to_project(self, repo, actor, project, role, target):
        """DB + Discord add. Returns True if anything changed."""

        await repo.upsert_member(target.id, target.name)
        added_in_db = await repo.add_project_member(project.id, target.id)
        missing_in_discord = not has_role(target, role.id)

        if missing_in_discord:
            await sync_discord(
                target.add_roles(
                    role,
                    reason=f"Added to {project.name} by {actor} ({actor.id})",
                ),
                f"give {role.name} to {target.display_name}",
            )

        return added_in_db or missing_in_discord

    # --------------------------------------------------
    # PROJECT DEFINITIONS (Officers)
    # --------------------------------------------------

    async def create_project(self, actor, name, discord_role, description=None):
        self._require_officer(actor, "create projects")

        name = name.strip()
        if not name:
            raise InvalidRequest("Project name can't be empty.")

        if discord_role.id == self.officer_role_id:
            raise InvalidRequest("The Officer role can't be a project role.")

        ensure_role_is_manageable(discord_role)
        ensure_bot_can_assign(discord_role, actor.guild.me)

        async with self.db.transaction() as repo:
            if await repo.get_role_by_discord_id(discord_role.id):
                raise InvalidRequest(
                    f"{discord_role.name} is already registered as a "
                    "functional/membership role, so it can't be a project role."
                )

            project = await repo.create_project(name, description, discord_role.id)
            if project is None:
                raise InvalidRequest(
                    f"A project named {name}, or one using {discord_role.name}, "
                    "already exists."
                )

            await repo.add_audit_log(
                actor.id,
                "project.create",
                details={
                    "project": project.name,
                    "discord_role_id": discord_role.id,
                },
            )

        return project

    async def delete_project(self, actor, name):
        """Delete a project's records. The Discord role is left untouched."""

        self._require_officer(actor, "delete projects")

        async with self.db.transaction() as repo:
            project = await self._get_project(repo, name)
            members = await repo.get_project_members(project.id)
            leaders = await repo.get_project_leaders(project.id)

            await repo.delete_project(project.id)
            await repo.add_audit_log(
                actor.id,
                "project.delete",
                details={
                    "project": project.name,
                    "discord_role_id": project.discord_role_id,
                    "member_ids": [m.discord_id for m in members],
                    "leaders": {str(l.member_id): l.level for l in leaders},
                },
            )

        return project

    async def list_projects(self):
        async with self.db.transaction() as repo:
            return await repo.list_projects()

    # --------------------------------------------------
    # ROSTER (Officers and the project's leadership)
    # --------------------------------------------------

    async def assign_member(self, actor, project_name, target):
        """Add target to the project. Returns False if nothing changed."""

        if target.bot:
            raise InvalidRequest("Bots can't be added to projects.")

        async with self.db.transaction() as repo:
            project = await self._get_project(repo, project_name)
            officer, level = await self._actor_authority(repo, actor, project)

            if not can_manage_project_members(officer, level):
                raise PermissionDenied(
                    f"You can only manage members of projects you lead or "
                    f"manage, and you don't lead or manage {project.name}."
                )

            role = self._project_role(actor.guild, project)
            changed = await self._add_to_project(repo, actor, project, role, target)

            if changed:
                await repo.add_audit_log(
                    actor.id,
                    "project.assign",
                    target.id,
                    {"project": project.name},
                )

        return changed

    async def remove_member(self, actor, project_name, target):
        """Remove target from the project (and from its leadership, if any)."""

        async with self.db.transaction() as repo:
            project = await self._get_project(repo, project_name)
            officer, level = await self._actor_authority(repo, actor, project)

            if not can_manage_project_members(officer, level):
                raise PermissionDenied(
                    f"You can only manage members of projects you lead or "
                    f"manage, and you don't lead or manage {project.name}."
                )

            # Removing a Lead or Manager from the project also removes their
            # leadership, so it needs the authority to remove that level.
            target_level = await repo.get_leadership_level(project.id, target.id)
            if target_level and not can_manage_leadership_level(officer, level, target_level):
                raise PermissionDenied(
                    f"{target.display_name} is a {LEVEL_NAMES[target_level]} of "
                    f"{project.name}; you can't remove them."
                )

            role = self._project_role(actor.guild, project)

            removed_leadership = False
            if target_level:
                removed_leadership = await repo.remove_project_leader(project.id, target.id)

            removed_in_db = await repo.remove_project_member(project.id, target.id)
            present_in_discord = has_role(target, role.id)

            if not (removed_in_db or removed_leadership or present_in_discord):
                return False

            if present_in_discord:
                await sync_discord(
                    target.remove_roles(
                        role,
                        reason=f"Removed from {project.name} by {actor} ({actor.id})",
                    ),
                    f"remove {role.name} from {target.display_name}",
                )

            await repo.add_audit_log(
                actor.id,
                "project.remove",
                target.id,
                {"project": project.name, "removed_leadership": target_level},
            )

        return True

    async def roster(self, actor, project_name):
        async with self.db.transaction() as repo:
            project = await self._get_project(repo, project_name)
            officer, level = await self._actor_authority(repo, actor, project)

            if not can_manage_project_members(officer, level):
                raise PermissionDenied(
                    f"Only Officers and {project.name}'s leadership can view "
                    "its roster."
                )

            return Roster(
                project=project,
                leaders=await repo.get_project_leaders(project.id),
                members=await repo.get_project_members(project.id),
            )

    # --------------------------------------------------
    # LEADERSHIP
    # --------------------------------------------------

    async def set_leader(self, actor, project_name, target, level):
        """Make target a Project Lead or Manager. Also adds them to the project.

        Returns False if they already held that level.
        """

        if level not in LEADERSHIP_LEVELS:
            raise InvalidRequest(f"Unknown leadership level: {level}.")

        if target.bot:
            raise InvalidRequest("Bots can't lead projects.")

        async with self.db.transaction() as repo:
            project = await self._get_project(repo, project_name)
            officer, actor_level = await self._actor_authority(repo, actor, project)
            current = await repo.get_leadership_level(project.id, target.id)

            if not can_manage_leadership_level(officer, actor_level, level):
                raise PermissionDenied(self._leadership_denial(level))

            # Changing someone's existing level also needs authority over it,
            # e.g. a Lead can't demote another Lead to Manager.
            if current and not can_manage_leadership_level(officer, actor_level, current):
                raise PermissionDenied(self._leadership_denial(current))

            if current == level:
                return False

            role = self._project_role(actor.guild, project)
            await self._add_to_project(repo, actor, project, role, target)
            await repo.set_project_leader(project.id, target.id, level)

            await repo.add_audit_log(
                actor.id,
                "project.leader.set",
                target.id,
                {"project": project.name, "level": level, "previous": current},
            )

        return True

    async def remove_leader(self, actor, project_name, target):
        """Revoke leadership. Target stays an ordinary project member."""

        async with self.db.transaction() as repo:
            project = await self._get_project(repo, project_name)
            officer, actor_level = await self._actor_authority(repo, actor, project)
            current = await repo.get_leadership_level(project.id, target.id)

            if current is None:
                raise NotFound(
                    f"{target.display_name} isn't a Project Lead or Manager "
                    f"of {project.name}."
                )

            if not can_manage_leadership_level(officer, actor_level, current):
                raise PermissionDenied(self._leadership_denial(current))

            await repo.remove_project_leader(project.id, target.id)
            await repo.add_audit_log(
                actor.id,
                "project.leader.remove",
                target.id,
                {"project": project.name, "previous": current},
            )

        return current

    @staticmethod
    def _leadership_denial(level):
        if level == LEADERSHIP_LEAD:
            return "Only Officers can appoint or remove Project Leads."
        return (
            "Only Officers and the project's Lead can appoint or remove "
            "Project Managers."
        )
