"""Functional role management (DESIGN.md §2.2, `/role ...` commands).

The database is the authoritative record (DESIGN.md §13). Every change is
written to the database and mirrored to Discord inside one transaction: if
Discord rejects the role change, the database write and audit entry are
rolled back.
"""

from bot.database.models import ROLE_CATEGORIES, ROLE_CATEGORY_FUNCTIONAL
from bot.services.authorization import (
    ensure_actor_outranks,
    ensure_bot_can_assign,
    ensure_role_is_manageable,
    has_role,
    is_officer,
    sync_discord,
)
from bot.services.errors import InvalidRequest, NotFound, PermissionDenied


class RoleService:

    def __init__(self, db, officer_role_id):
        self.db = db
        self.officer_role_id = officer_role_id

    def _require_officer(self, actor, action):
        if not is_officer(actor, self.officer_role_id):
            raise PermissionDenied(f"Only Officers can {action}.")

    # --------------------------------------------------
    # ROLE DEFINITIONS
    # --------------------------------------------------

    async def register_role(self, actor, discord_role, category, name=None):
        """Record a Discord role as a Bitwise-managed role."""

        self._require_officer(actor, "register roles")

        if category not in ROLE_CATEGORIES:
            raise InvalidRequest(f"Unknown role category: {category}.")

        if discord_role.id == self.officer_role_id:
            raise InvalidRequest(
                "The Officer role is configured through OFFICER_ROLE_ID and "
                "can't be registered as a managed role."
            )

        ensure_role_is_manageable(discord_role)
        ensure_bot_can_assign(discord_role, actor.guild.me)

        name = (name or discord_role.name).strip()

        async with self.db.transaction() as repo:
            if await repo.get_project_by_discord_id(discord_role.id):
                raise InvalidRequest(
                    f"{discord_role.name} is already a project's role. "
                    "Project roles are managed with /project commands."
                )

            record = await repo.create_role(name, category, discord_role.id)
            if record is None:
                raise InvalidRequest(
                    f"A role named {name}, or the Discord role "
                    f"{discord_role.name}, is already registered."
                )

            await repo.add_audit_log(
                actor.id,
                "role.register",
                details={
                    "role": record.name,
                    "category": category,
                    "discord_role_id": discord_role.id,
                },
            )

        return record

    async def unregister_role(self, actor, name):
        """Stop managing a role. Members keep the Discord role itself."""

        self._require_officer(actor, "unregister roles")

        async with self.db.transaction() as repo:
            record = await repo.get_role_by_name(name)
            if record is None:
                raise NotFound(f"No registered role is named {name}.")

            await repo.delete_role(record.id)
            await repo.add_audit_log(
                actor.id,
                "role.unregister",
                details={
                    "role": record.name,
                    "category": record.category,
                    "discord_role_id": record.discord_role_id,
                },
            )

        return record

    async def list_roles(self):
        async with self.db.transaction() as repo:
            return await repo.list_roles()

    # --------------------------------------------------
    # ASSIGNMENTS
    # --------------------------------------------------

    async def _functional_role(self, repo, discord_role):
        record = await repo.get_role_by_discord_id(discord_role.id)

        if record is None:
            raise NotFound(
                f"{discord_role.name} isn't a registered role. An Officer can "
                "register it with /role register."
            )

        if record.category != ROLE_CATEGORY_FUNCTIONAL:
            raise InvalidRequest(
                f"{record.name} is a {record.category} role. /role only "
                "manages functional roles; membership is granted through "
                "recruiting."
            )

        return record

    def _check_assignment(self, actor, target, discord_role):
        self._require_officer(actor, "manage functional roles")

        if target.bot:
            raise InvalidRequest("Bots can't be given organization roles.")

        ensure_role_is_manageable(discord_role)
        ensure_bot_can_assign(discord_role, actor.guild.me)
        ensure_actor_outranks(discord_role, actor)

    async def add_role(self, actor, target, discord_role):
        """Give target a functional role. Returns False if they already had it."""

        self._check_assignment(actor, target, discord_role)

        async with self.db.transaction() as repo:
            record = await self._functional_role(repo, discord_role)

            await repo.upsert_member(target.id, target.name)
            added_in_db = await repo.assign_role(target.id, record.id)
            missing_in_discord = not has_role(target, discord_role.id)

            if not added_in_db and not missing_in_discord:
                return False

            if missing_in_discord:
                await sync_discord(
                    target.add_roles(
                        discord_role,
                        reason=f"/role add by {actor} ({actor.id})",
                    ),
                    f"give {discord_role.name} to {target.display_name}",
                )

            await repo.add_audit_log(
                actor.id,
                "role.add",
                target.id,
                {
                    "role": record.name,
                    "discord_role_id": discord_role.id,
                    # True when the DB already had it and only Discord was fixed.
                    "repaired_discord_only": not added_in_db,
                },
            )

        return True

    async def remove_role(self, actor, target, discord_role):
        """Remove a functional role. Returns False if target didn't have it."""

        self._check_assignment(actor, target, discord_role)

        async with self.db.transaction() as repo:
            record = await self._functional_role(repo, discord_role)

            removed_in_db = await repo.remove_role(target.id, record.id)
            present_in_discord = has_role(target, discord_role.id)

            if not removed_in_db and not present_in_discord:
                return False

            if present_in_discord:
                await sync_discord(
                    target.remove_roles(
                        discord_role,
                        reason=f"/role remove by {actor} ({actor.id})",
                    ),
                    f"remove {discord_role.name} from {target.display_name}",
                )

            await repo.add_audit_log(
                actor.id,
                "role.remove",
                target.id,
                {
                    "role": record.name,
                    "discord_role_id": discord_role.id,
                    "repaired_discord_only": not removed_in_db,
                },
            )

        return True
