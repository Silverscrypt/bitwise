"""Authorization rules for role and project management (DESIGN.md §2.2, §7).

Authority model:

- Officers (holders of OFFICER_ROLE_ID) have organization-wide authority.
- A Project Lead manages members and Project Managers of their own projects.
- A Project Manager manages ordinary members of their own projects.
- Nobody but an Officer appoints or removes a Project Lead.

Project authority comes from the project_managers table, never from a
Discord role, so leading Project Alpha grants nothing on Project Beta.

Everything here works on duck-typed objects (anything with .id, .roles,
.position, ...), so it can be tested without connecting to Discord.
"""

import discord

from bot.database.models import LEADERSHIP_LEAD, LEADERSHIP_MANAGER
from bot.services.errors import DiscordSyncError, InvalidRequest, PermissionDenied


# Roles carrying any of these permissions are never managed by Bitwise.
# Project Managers can hand out project roles, so allowing a project role
# with Manage Roles (for example) would let them escalate their own access.
DANGEROUS_PERMISSIONS = (
    "administrator",
    "manage_guild",
    "manage_roles",
    "manage_channels",
    "manage_webhooks",
    "manage_messages",
    "manage_nicknames",
    "manage_expressions",
    "manage_events",
    "manage_threads",
    "ban_members",
    "kick_members",
    "moderate_members",
    "mention_everyone",
    "view_audit_log",
)


# --------------------------------------------------
# WHO IS THE ACTOR
# --------------------------------------------------

def has_role(member, role_id):
    return any(role.id == role_id for role in member.roles)


def is_officer(member, officer_role_id):
    return has_role(member, officer_role_id)


def is_guild_owner(member):
    return member.guild.owner_id == member.id


# --------------------------------------------------
# PROJECT AUTHORITY
# --------------------------------------------------

def can_manage_project_members(officer, actor_level):
    """Assign/remove ordinary members, and view the roster."""

    return officer or actor_level in (LEADERSHIP_LEAD, LEADERSHIP_MANAGER)


def can_manage_leadership_level(officer, actor_level, level):
    """Grant or revoke the given leadership level on a project."""

    if officer:
        return True

    if level == LEADERSHIP_MANAGER:
        return actor_level == LEADERSHIP_LEAD

    return False


# --------------------------------------------------
# DISCORD ROLE SAFETY AND HIERARCHY
# --------------------------------------------------

def dangerous_permissions(role):
    return [
        name for name in DANGEROUS_PERMISSIONS
        if getattr(role.permissions, name, False)
    ]


def ensure_role_is_manageable(role):
    """Reject roles Bitwise must never hand out."""

    if role.is_default():
        raise InvalidRequest("@everyone can't be managed.")

    if role.managed:
        raise InvalidRequest(
            f"{role.name} is managed by an integration or bot and can't be "
            "assigned manually."
        )

    risky = dangerous_permissions(role)
    if risky:
        raise InvalidRequest(
            f"{role.name} has moderation or administrative permissions "
            f"({', '.join(risky)}). Bitwise only manages roles without them."
        )


def ensure_bot_can_assign(role, bot_member):
    if not bot_member.guild_permissions.manage_roles:
        raise InvalidRequest(
            "I'm missing the Manage Roles permission. An Officer can run "
            "/setup to check my configuration."
        )

    if role.position >= bot_member.top_role.position:
        raise InvalidRequest(
            f"{role.name} is at or above my highest role, so Discord won't "
            "let me assign it. Move my role above it in Server Settings → Roles."
        )


def ensure_actor_outranks(role, actor):
    """Lower-level users must not modify higher-level roles (DESIGN.md §2.2)."""

    if is_guild_owner(actor):
        return

    if role.position >= actor.top_role.position:
        raise PermissionDenied(
            f"{role.name} is at or above your highest role, so you can't "
            "assign or remove it."
        )


# --------------------------------------------------
# DISCORD CALLS
# --------------------------------------------------

async def sync_discord(call, description):
    """Await a Discord role change, turning API failures into DiscordSyncError.

    Services call this inside a database transaction, so raising here rolls
    the database change back and the two stay consistent.
    """

    try:
        await call
    except discord.Forbidden:
        raise DiscordSyncError(
            f"Discord refused to {description}. Check that my role is above "
            "it and that I have Manage Roles. Nothing was changed."
        ) from None
    except discord.HTTPException as error:
        raise DiscordSyncError(
            f"Discord returned an error while trying to {description} "
            f"(HTTP {error.status}). Nothing was changed; please try again."
        ) from None
