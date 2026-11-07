
import os

from dotenv import load_dotenv


# Load environment variables
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")


def validate_config():
    """Validate required environment variables."""

    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is missing from .env")

    if not GUILD_ID:
        raise RuntimeError("GUILD_ID is missing from .env")
