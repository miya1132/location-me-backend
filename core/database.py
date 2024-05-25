import psycopg2

from core.config import Config


def get_connection():
    return psycopg2.connect(Config.DATABASE_URI)
