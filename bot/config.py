
import os

from dotenv import load_dotenv
from psycopg.conninfo import make_conninfo


# Load environment variables
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

# Discord ID of the Officer role. Officers hold organization-wide authority
# (role management, project creation, appointing Project Leads). Every other
# role and project is registered in the database through slash commands.
OFFICER_ROLE_ID = os.getenv("OFFICER_ROLE_ID")


def get_database_url():
    """Return the PostgreSQL connection string.

    DATABASE_URL is preferred. The individual DB_* variables are still
    supported so existing local .env files keep working.
    """

    url = os.getenv("DATABASE_URL")
    if url:
        return url

    required_variables = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER"]
    missing = [name for name in required_variables if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Set DATABASE_URL (or " + ", ".join(missing) + ") in .env"
        )

    return make_conninfo(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD") or None,
    )


def validate_config():
    """Validate required environment variables."""

    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is missing from .env")

    if not GUILD_ID:
        raise RuntimeError("GUILD_ID is missing from .env")

    if not OFFICER_ROLE_ID or not OFFICER_ROLE_ID.isdigit():
        raise RuntimeError(
            "OFFICER_ROLE_ID is missing from .env (right-click the Officer "
            "role in Discord with Developer Mode on and choose Copy Role ID)"
        )

    get_database_url()
