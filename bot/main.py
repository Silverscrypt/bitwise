
import asyncio

import discord
from discord.ext import commands

from bot.config import TOKEN, GUILD_ID, validate_config


# Configure bot intents
intents = discord.Intents.default()

# Bot class
class BitsBot(commands.Bot):

    async def setup_hook(self):
        await self.load_extension("bot.commands.roles")

        guild = discord.Object(id=int(GUILD_ID))
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

        print("Slash commands synchronized!")


# Initialize bot
bot = BitsBot(
    command_prefix="!",
    intents=intents
)


# Bot startup event
@bot.event
async def on_ready():
    print("Bits is online!")
    print(f"Logged in as: {bot.user}")
    print(f"Bot ID: {bot.user.id}")


# --------------------------------------------------
# PING COMMAND
# --------------------------------------------------

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
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    validate_config()
    asyncio.run(main())
