"""/project commands: projects, rosters and project leadership."""

import discord
from discord import app_commands
from discord.ext import commands

from bot.commands.common import mention, project_autocomplete, reply, role_mention
from bot.services.project_service import LEVEL_NAMES


LEVEL_CHOICES = [
    app_commands.Choice(name=label, value=level)
    for level, label in LEVEL_NAMES.items()
]


@app_commands.guild_only()
class ProjectCommands(
    commands.GroupCog,
    group_name="project",
    group_description="Manage projects and their rosters.",
):

    leader = app_commands.Group(
        name="leader",
        description="Manage Project Leads and Project Managers.",
    )

    def __init__(self, bot):
        self.bot = bot
        self.service = bot.project_service
        super().__init__()

    # --------------------------------------------------
    # PROJECT DEFINITIONS
    # --------------------------------------------------

    @app_commands.command(name="create", description="(Officers) Create a project linked to a Discord role.")
    @app_commands.describe(
        name="Project name",
        role="Discord role given to project members",
        description="Short description",
    )
    async def create(
        self,
        interaction: discord.Interaction,
        name: app_commands.Range[str, 1, 100],
        role: discord.Role,
        description: app_commands.Range[str, 1, 500] | None = None,
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)

        project = await self.service.create_project(interaction.user, name, role, description)
        await reply(
            interaction,
            f"Created **{project.name}** → {role.mention}. Appoint a lead with "
            "/project leader set.",
        )

    @app_commands.command(name="delete", description="(Officers) Delete a project's records.")
    @app_commands.describe(project="The project to delete")
    @app_commands.autocomplete(project=project_autocomplete)
    async def delete(self, interaction: discord.Interaction, project: str):
        await interaction.response.defer(ephemeral=True, thinking=True)

        record = await self.service.delete_project(interaction.user, project)
        await reply(
            interaction,
            f"Deleted **{record.name}** and its roster. The Discord role "
            f"{role_mention(record.discord_role_id)} and its channels were not "
            "touched; remove them in Discord if they're no longer needed.",
        )

    @app_commands.command(name="list", description="List all projects.")
    async def list_projects(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        projects = await self.service.list_projects()
        if not projects:
            await reply(interaction, "There are no projects yet.")
            return

        lines = [
            f"**{p.name}** · {role_mention(p.discord_role_id)}"
            + (f"\n  {p.description}" if p.description else "")
            for p in projects
        ]
        await reply(interaction, "\n".join(lines))

    # --------------------------------------------------
    # ROSTER
    # --------------------------------------------------

    @app_commands.command(name="assign", description="Add a member to a project.")
    @app_commands.describe(project="The project", member="Who to add")
    @app_commands.autocomplete(project=project_autocomplete)
    async def assign(self, interaction: discord.Interaction, project: str, member: discord.Member):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if await self.service.assign_member(interaction.user, project, member):
            await reply(interaction, f"Added {member.mention} to **{project}**.")
        else:
            await reply(interaction, f"{member.mention} is already on **{project}**.")

    @app_commands.command(name="remove", description="Remove a member from a project.")
    @app_commands.describe(project="The project", member="Who to remove")
    @app_commands.autocomplete(project=project_autocomplete)
    async def remove(self, interaction: discord.Interaction, project: str, member: discord.Member):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if await self.service.remove_member(interaction.user, project, member):
            await reply(interaction, f"Removed {member.mention} from **{project}**.")
        else:
            await reply(interaction, f"{member.mention} isn't on **{project}**.")

    @app_commands.command(name="roster", description="Show a project's leadership and members.")
    @app_commands.describe(project="The project")
    @app_commands.autocomplete(project=project_autocomplete)
    async def roster(self, interaction: discord.Interaction, project: str):
        await interaction.response.defer(ephemeral=True, thinking=True)

        roster = await self.service.roster(interaction.user, project)

        embed = discord.Embed(
            title=roster.project.name,
            description=roster.project.description or None,
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Leadership",
            value="\n".join(
                f"{mention(l.member_id)} · {LEVEL_NAMES[l.level]}" for l in roster.leaders
            ) or "None",
            inline=False,
        )
        member_list = "\n".join(mention(m.discord_id) for m in roster.members) or "None"
        if len(member_list) > 1024:
            member_list = member_list[:1000].rsplit("\n", 1)[0] + "\n…"
        embed.add_field(
            name=f"Members ({len(roster.members)})",
            value=member_list,
            inline=False,
        )
        await reply(interaction, embed=embed)

    # --------------------------------------------------
    # LEADERSHIP
    # --------------------------------------------------

    @leader.command(name="set", description="Make a member a Project Lead or Project Manager.")
    @app_commands.describe(
        project="The project",
        member="Who to appoint (they're added to the project too)",
        level="Leads are appointed by Officers; Managers by Officers or the project's Lead",
    )
    @app_commands.autocomplete(project=project_autocomplete)
    @app_commands.choices(level=LEVEL_CHOICES)
    async def leader_set(
        self,
        interaction: discord.Interaction,
        project: str,
        member: discord.Member,
        level: app_commands.Choice[str],
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if await self.service.set_leader(interaction.user, project, member, level.value):
            await reply(interaction, f"{member.mention} is now a {level.name} of **{project}**.")
        else:
            await reply(interaction, f"{member.mention} is already a {level.name} of **{project}**.")

    @leader.command(name="remove", description="Revoke a member's Project Lead/Manager status.")
    @app_commands.describe(project="The project", member="Who to remove from leadership")
    @app_commands.autocomplete(project=project_autocomplete)
    async def leader_remove(self, interaction: discord.Interaction, project: str, member: discord.Member):
        await interaction.response.defer(ephemeral=True, thinking=True)

        previous = await self.service.remove_leader(interaction.user, project, member)
        await reply(
            interaction,
            f"{member.mention} is no longer a {LEVEL_NAMES[previous]} of "
            f"**{project}** (they remain a project member).",
        )


async def setup(bot):
    await bot.add_cog(ProjectCommands(bot))
