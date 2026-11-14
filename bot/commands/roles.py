"""/role commands: functional roles and role registration.

Commands only translate between Discord and the RoleService. All rules
(authorization, hierarchy, database consistency) live in the service.
"""

import discord
from discord import app_commands
from discord.ext import commands

from bot.commands.common import registered_role_autocomplete, reply, role_mention
from bot.database.models import ROLE_CATEGORIES


CATEGORY_CHOICES = [
    app_commands.Choice(name=category.title(), value=category)
    for category in ROLE_CATEGORIES
]


@app_commands.guild_only()
class RoleCommands(
    commands.GroupCog,
    group_name="role",
    group_description="Manage organization roles.",
):

    def __init__(self, bot):
        self.bot = bot
        self.service = bot.role_service
        super().__init__()

    @app_commands.command(name="add", description="Give a member a functional role.")
    @app_commands.describe(member="Who gets the role", role="A registered functional role")
    async def add(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if await self.service.add_role(interaction.user, member, role):
            await reply(interaction, f"Gave {role.mention} to {member.mention}.")
        else:
            await reply(interaction, f"{member.mention} already has {role.mention}.")

    @app_commands.command(name="remove", description="Remove a functional role from a member.")
    @app_commands.describe(member="Who loses the role", role="A registered functional role")
    async def remove(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if await self.service.remove_role(interaction.user, member, role):
            await reply(interaction, f"Removed {role.mention} from {member.mention}.")
        else:
            await reply(interaction, f"{member.mention} doesn't have {role.mention}.")

    @app_commands.command(name="list", description="List the roles Bitwise manages.")
    async def list_roles(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        roles = await self.service.list_roles()
        if not roles:
            await reply(interaction, "No roles are registered yet. Officers can add one with /role register.")
            return

        lines = [
            f"**{role.name}** · {role.category} · {role_mention(role.discord_role_id)}"
            for role in roles
        ]
        await reply(interaction, "\n".join(lines))

    @app_commands.command(name="register", description="(Officers) Let Bitwise manage a Discord role.")
    @app_commands.describe(
        role="The Discord role",
        category="Functional roles can be given with /role add; membership is granted by recruiting",
        name="Name Bitwise uses for it (defaults to the Discord role name)",
    )
    @app_commands.choices(category=CATEGORY_CHOICES)
    async def register(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        category: app_commands.Choice[str],
        name: app_commands.Range[str, 1, 100] | None = None,
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)

        record = await self.service.register_role(interaction.user, role, category.value, name)
        await reply(interaction, f"Registered **{record.name}** ({record.category}) → {role.mention}.")

    @app_commands.command(name="unregister", description="(Officers) Stop managing a role.")
    @app_commands.describe(name="The registered role")
    @app_commands.autocomplete(name=registered_role_autocomplete)
    async def unregister(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True, thinking=True)

        record = await self.service.unregister_role(interaction.user, name)
        await reply(
            interaction,
            f"Unregistered **{record.name}**. Its assignment records were "
            "deleted; members keep the Discord role until it's removed in Discord.",
        )


async def setup(bot):
    await bot.add_cog(RoleCommands(bot))
