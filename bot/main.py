
import asyncio
import logging
import sys

import discord
from discord.ext import commands

from bot.commands.common import on_app_command_error
from bot.config import GUILD_ID, OFFICER_ROLE_ID, TOKEN, get_database_url, validate_config
from bot.database.connection import Database
from bot.services.member_service import MemberService
from bot.services.project_service import ProjectService
from bot.services.role_service import RoleService
from bot.services.setup_service import SetupService


log = logging.getLogger("bitwise")

EXTENSIONS = (
    "bot.commands.roles",
    "bot.commands.projects",
    "bot.commands.members",
    "bot.commands.diagnostics",
)


# Bot class
class BitsBot(commands.Bot):

    def __init__(self):
        # Default intents are enough: slash-command options resolve members
        # directly, so the privileged Members intent isn't required.
        super().__init__(command_prefix="!", intents=discord.Intents.default())

        officer_role_id = int(OFFICER_ROLE_ID)
        self.db = Database(get_database_url())
        self.role_service = RoleService(self.db, officer_role_id)
        self.project_service = ProjectService(self.db, officer_role_id)
        self.member_service = MemberService(self.db, officer_role_id)
        self.setup_service = SetupService(self.db, officer_role_id)

    async def setup_hook(self):
        await self.db.open()
        log.info("Database connected and schema up to date.")

        self.tree.on_error = on_app_command_error
        for extension in EXTENSIONS:
            await self.load_extension(extension)

        guild = discord.Object(id=int(GUILD_ID))
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

        log.info("Slash commands synchronized!")

    async def close(self):
        await super().close()
        await self.db.close()

    async def on_ready(self):
        log.info("Bits is online! Logged in as %s (ID %s)", self.user, self.user.id)


def add_ping_command(bot):

    @bot.tree.command(
        name="ping",
        description="Check whether Bits is responsive."
    )
    async def ping(interaction: discord.Interaction):
        await interaction.response.send_message(
            "Pong! Bits is operational."
        )


# --------------------------------------------------
# MAIN
# --------------------------------------------------

async def main():
    bot = BitsBot()
    add_ping_command(bot)

    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    discord.utils.setup_logging()
    validate_config()

    # psycopg's async driver can't use Windows' default Proactor event loop.
    loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    asyncio.run(main(), loop_factory=loop_factory)
