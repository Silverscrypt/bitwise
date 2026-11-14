"""Helpers shared by the command cogs."""

import logging

import discord
from discord import app_commands

from bot.services.errors import ServiceError


log = logging.getLogger(__name__)


async def reply(interaction, content=None, **kwargs):
    """Send an ephemeral reply whether or not the interaction was deferred."""

    kwargs.setdefault("ephemeral", True)
    kwargs.setdefault("allowed_mentions", discord.AllowedMentions.none())

    if interaction.response.is_done():
        await interaction.followup.send(content, **kwargs)
    else:
        await interaction.response.send_message(content, **kwargs)


async def on_app_command_error(interaction, error):
    """Global slash-command error handler (installed in bot/main.py).

    ServiceErrors carry a user-facing message. Anything else is a bug: log it
    and show a generic message without leaking details.
    """

    original = getattr(error, "original", error)

    if isinstance(original, ServiceError):
        await reply(interaction, str(original))
        return

    if isinstance(error, app_commands.NoPrivateMessage):
        await reply(interaction, "This command only works inside the server.")
        return

    log.exception("Unhandled error in /%s", interaction.command and interaction.command.qualified_name,
                  exc_info=original)
    await reply(interaction, "Something went wrong. The error has been logged.")


async def project_autocomplete(interaction, current):
    try:
        projects = await interaction.client.project_service.list_projects()
    except Exception:
        log.exception("Project autocomplete failed")
        return []

    current = current.lower()
    return [
        app_commands.Choice(name=project.name, value=project.name)
        for project in projects
        if current in project.name.lower()
    ][:25]


async def registered_role_autocomplete(interaction, current):
    try:
        roles = await interaction.client.role_service.list_roles()
    except Exception:
        log.exception("Role autocomplete failed")
        return []

    current = current.lower()
    return [
        app_commands.Choice(name=f"{role.name} ({role.category})", value=role.name)
        for role in roles
        if current in role.name.lower()
    ][:25]


def mention(discord_id):
    return f"<@{discord_id}>"


def role_mention(discord_role_id):
    return f"<@&{discord_role_id}>" if discord_role_id else "(no Discord role)"
