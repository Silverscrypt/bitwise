import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    required_variables = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER"
    ]

    for variable in required_variables:
        if not os.getenv(variable):
            raise RuntimeError(
                f"{variable} is missing from .env"
            )

    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD") or None
    )