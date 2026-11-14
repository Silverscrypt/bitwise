"""/member commands."""

import discord
from discord import app_commands
from discord.ext import commands

from bot.commands.common import reply, role_mention
from bot.services.project_service import LEVEL_NAMES


@app_commands.guild_only()
class MemberCommands(
    commands.GroupCog,
    group_name="member",
    group_description="Look up organization members.",
):

    def __init__(self, bot):
        self.bot = bot
        self.service = bot.member_service
        super().__init__()

    @app_commands.command(name="info", description="Show a member's roles and projects.")
    @app_commands.describe(member="Who to look up (defaults to you)")
    async def info(self, interaction: discord.Interaction, member: discord.Member | None = None):
        await interaction.response.defer(ephemeral=True, thinking=True)

        member = member or interaction.user
        info = await self.service.member_info(interaction.user, member)

        embed = discord.Embed(title=member.display_name, color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)

        if info.record is None:
            embed.description = "No Bitwise records yet."
        elif info.record.joined_at:
            embed.description = f"In Bitwise since {discord.utils.format_dt(info.record.joined_at, 'D')}"

        embed.add_field(
            name="Roles",
            value="\n".join(
                f"{role_mention(r.discord_role_id)} · {r.category}" for r in info.roles
            ) or "None",
            inline=False,
        )
        embed.add_field(
            name="Projects",
            value="\n".join(f"**{p.name}**" for p in info.projects) or "None",
            inline=False,
        )
        if info.leadership:
            embed.add_field(
                name="Leadership",
                value="\n".join(
                    f"{LEVEL_NAMES[l.level]} · **{l.project_name}**" for l in info.leadership
                ),
                inline=False,
            )

        await reply(interaction, embed=embed)


async def setup(bot):
    await bot.add_cog(MemberCommands(bot))
