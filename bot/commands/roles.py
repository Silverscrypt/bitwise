
import discord
from discord.ext import commands


class RoleCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(
        name="role_add",
        description="Assign a role to a server member."
    )
    async def role_add(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role
    ):
        officer_role = discord.utils.get(
            interaction.guild.roles,
            name="Officer"
        )

        if officer_role is None:
            await interaction.response.send_message(
                "The Officer role could not be found.",
                ephemeral=True
            )
            return

        if officer_role not in interaction.user.roles:
            await interaction.response.send_message(
                "You must be an Officer to use this command.",
                ephemeral=True
            )
            return

        try:
            await member.add_roles(role)

            await interaction.response.send_message(
                f"Successfully assigned {role.mention} to {member.mention}."
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to assign that role. Check my role hierarchy.",
                ephemeral=True
            )

    @discord.app_commands.command(
        name="role_remove",
        description="Remove a role from a server member."
    )
    async def role_remove(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role
    ):
        officer_role = discord.utils.get(
            interaction.guild.roles,
            name="Officer"
        )

        if officer_role is None:
            await interaction.response.send_message(
                "The Officer role could not be found.",
                ephemeral=True
            )
            return

        if officer_role not in interaction.user.roles:
            await interaction.response.send_message(
                "You must be an Officer to use this command.",
                ephemeral=True
            )
            return

        try:
            await member.remove_roles(role)

            await interaction.response.send_message(
                f"Successfully removed {role.mention} from {member.mention}."
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to remove that role. Check my role hierarchy.",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(RoleCommands(bot))
