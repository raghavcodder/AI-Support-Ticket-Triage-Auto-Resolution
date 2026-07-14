"""
MySQL connection setup. Creates the database itself if it doesn't exist
yet """

import os
import pymysql
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from app.db.models import Base

load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "support_triage")

# Built via URL.create() rather than an f-string -- if the password
# contains special characters (@, :, /, etc), naive string interpolation
# breaks the URL (everything after the last "@" gets parsed as the host).
# URL.create() escapes these correctly.
DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=MYSQL_USER,
    password=MYSQL_PASSWORD,
    host=MYSQL_HOST,
    port=MYSQL_PORT,
    database=MYSQL_DATABASE,
)

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def create_database_if_not_exists() -> None:
    """
    MySQL requires the database to exist before you can connect a
    SQLAlchemy engine to it -- unlike SQLite, which just creates the file.
    Connects without specifying a database, then issues CREATE DATABASE
    IF NOT EXISTS so this is safe to call on every run.
    """
    connection = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    """Create the database (if needed) and all tables (if they don't exist)."""
    create_database_if_not_exists()
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
