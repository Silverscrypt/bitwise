"""Configuration diagnostics for `/setup` (DESIGN.md §2.2).

Read-only: reports what's wrong and how to fix it, but changes nothing.
"""

import logging
from dataclasses import dataclass

from bot.database.models import ROLE_CATEGORY_MEMBERSHIP
from bot.services.authorization import dangerous_permissions, is_officer
from bot.services.errors import PermissionDenied


log = logging.getLogger(__name__)

OK = "ok"
WARN = "warn"
FAIL = "fail"


@dataclass(frozen=True)
class Check:
    status: str
    subject: str
    detail: str = ""


class SetupService:

    def __init__(self, db, officer_role_id):
        self.db = db
        self.officer_role_id = officer_role_id

    def _check_role(self, guild, bot_member, subject, discord_role_id):
        role = guild.get_role(discord_role_id) if discord_role_id else None

        if role is None:
            return Check(
                FAIL, subject,
                "Discord role is missing (deleted?). Re-register it.",
            )

        risky = dangerous_permissions(role)
        if risky:
            return Check(
                FAIL, subject,
                f"{role.name} has risky permissions: {', '.join(risky)}.",
            )

        if role.managed:
            return Check(FAIL, subject, f"{role.name} is managed by an integration.")

        if role.position >= bot_member.top_role.position:
            return Check(
                FAIL, subject,
                f"{role.name} is above my highest role; move my role higher.",
            )

        return Check(OK, subject, role.name)

    async def diagnose(self, actor):
        guild = actor.guild

        if not (is_officer(actor, self.officer_role_id)
                or actor.guild_permissions.administrator):
            raise PermissionDenied("Only Officers and administrators can run /setup.")

        bot_member = guild.me
        checks = []

        # Discord permissions
        if bot_member.guild_permissions.manage_roles:
            checks.append(Check(OK, "Manage Roles permission"))
        else:
            checks.append(Check(
                FAIL, "Manage Roles permission",
                "Grant my role Manage Roles so I can assign roles.",
            ))

        officer_role = guild.get_role(self.officer_role_id)
        if officer_role is None:
            checks.append(Check(
                FAIL, "Officer role",
                f"OFFICER_ROLE_ID ({self.officer_role_id}) doesn't match any "
                "role in this server.",
            ))
        else:
            checks.append(Check(OK, "Officer role", officer_role.name))

        # Database
        try:
            async with self.db.transaction() as repo:
                roles = await repo.list_roles()
                projects = await repo.list_projects()
                leaders = {
                    project.id: await repo.get_project_leaders(project.id)
                    for project in projects
                }
        except Exception:
            log.exception("Database check failed during /setup")
            checks.append(Check(
                FAIL, "Database", "Couldn't query the database; see bot logs.",
            ))
            return checks

        checks.append(Check(OK, "Database", "Connected"))

        # Registered roles
        if not any(role.category == ROLE_CATEGORY_MEMBERSHIP for role in roles):
            checks.append(Check(
                WARN, "Membership role",
                "No membership role (Freelancer) registered yet. Use "
                "/role register with category membership.",
            ))

        for role in roles:
            checks.append(self._check_role(
                guild, bot_member,
                f"Role: {role.name} ({role.category})",
                role.discord_role_id,
            ))

        # Projects
        for project in projects:
            check = self._check_role(
                guild, bot_member, f"Project: {project.name}", project.discord_role_id,
            )
            if check.status == OK and not any(
                leader.level == "lead" for leader in leaders[project.id]
            ):
                check = Check(
                    WARN, check.subject,
                    "No Project Lead assigned. Use /project leader set.",
                )
            checks.append(check)

        return checks
