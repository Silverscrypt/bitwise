
import os
import asyncio

import discord
from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

intents = discord.Intents.default()


class BitsBot(commands.Bot):

    async def setup_hook(self):
        """Runs once during startup, before Gateway events are processed."""

        guild = discord.Object(id=int(GUILD_ID))

        # Copy global commands into our development server
        self.tree.copy_global_to(guild=guild)

        # Register commands with Discord
        await self.tree.sync(guild=guild)

        print("Slash commands synchronized!")


bot = BitsBot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    print("Bits is online!")
    print(f"Logged in as: {bot.user}")
    print(f"Bot ID: {bot.user.id}")


@bot.tree.command(
    name="ping",
    description="Check whether Bits is responsive."
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Pong! Bits is operational."
    )


async def main():
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is missing from .env")

    if not GUILD_ID:
        raise RuntimeError("GUILD_ID is missing from .env")

    asyncio.run(main())
