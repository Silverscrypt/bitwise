"""/setup: configuration diagnostics."""

import discord
from discord import app_commands
from discord.ext import commands

from bot.commands.common import reply
from bot.services.setup_service import FAIL, OK, WARN


ICONS = {OK: "✅", WARN: "⚠️", FAIL: "❌"}


class DiagnosticCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.service = bot.setup_service

    @app_commands.command(name="setup", description="(Officers) Check Bitwise's roles, permissions and database.")
    @app_commands.guild_only()
    async def setup_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        checks = await self.service.diagnose(interaction.user)

        lines = [
            f"{ICONS[c.status]} **{c.subject}**" + (f": {c.detail}" if c.detail else "")
            for c in checks
        ]
        failures = sum(c.status == FAIL for c in checks)
        warnings = sum(c.status == WARN for c in checks)
        summary = (
            "Everything looks good."
            if not failures and not warnings
            else f"{failures} problem(s), {warnings} warning(s)."
        )

        text = "\n".join(lines)
        if len(text) > 3900:
            text = text[:3900].rsplit("\n", 1)[0] + "\n…"

        embed = discord.Embed(
            title="Bitwise setup check",
            description=f"{summary}\n\n{text}",
            color=discord.Color.red() if failures else discord.Color.green(),
        )
        await reply(interaction, embed=embed)


async def setup(bot):
    await bot.add_cog(DiagnosticCommands(bot))
