import logging
from contextlib import asynccontextmanager
from typing import Optional, Generator

import psycopg
from psycopg import AsyncConnection, AsyncCursor
from psycopg.rows import dict_row

from fa_rss.faexport.models import User, Submission

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_config: dict):
        host = db_config.get("host", "localhost")
        dbname = db_config.get("database", "fa-rss")
        user = db_config.get("user", "postgres")
        password = db_config["password"]
        self.conn_string = f"host={host} dbname={dbname} user={user} password={password}"

    @asynccontextmanager
    async def cursor(self) -> Generator[tuple[AsyncConnection, AsyncCursor], None, None]:
        async with await psycopg.AsyncConnection.connect(self.conn_string, row_factory=dict_row) as conn:
            async with conn.cursor() as cur:
                yield conn, cur

    async def get_user(self, username: str) -> Optional[User]:
        async with self.cursor() as (conn, cur):
            logger.info("Fetch user from DB")
            await cur.execute(
                "SELECT username, initialised_date FROM users WHERE username = %s", (username,)
            )
            row = await cur.fetchone()
            if row is None:
                return None
            return User(
                row["username"],
                row["initialised_date"],
            )

    async def list_recent_submissions(self) -> list[Submission]:
        async with self.cursor() as (conn, cur):
            logger.info("List recent submissions in DB")
            return [
                Submission(
                    row["submission_id"],
                    row["username"],
                    row["gallery"],
                    row["title"],
                    row["description"],
                    row["download_url"],
                    row["thumbnail_url"],
                    row["posted_at"],
                    row["keywords"],
                ) async for row in cur.stream(
                    "SELECT * FROM submissions ORDER BY submission_id DESC LIMIT 20"
                )
            ]

    async def list_submissions_by_user_gallery(self, username: str, gallery: str) -> list[Submission]:
        async with self.cursor() as (conn, cur):
            logger.info("List submissions in gallery from DB")
            return [
                Submission(
                    row["submission_id"],
                    row["username"],
                    row["gallery"],
                    row["title"],
                    row["description"],
                    row["download_url"],
                    row["thumbnail_url"],
                    row["posted_at"],
                    row["keywords"],
                ) async for row in cur.stream(
                    "SELECT * FROM submissions WHERE username = %s AND gallery = %s ORDER BY submission_id DESC LIMIT 20",
                    (username, gallery),
                )
            ]

    async def get_submission(self, submission_id: int) -> Optional[Submission]:
        async with self.cursor() as (conn, cur):
            logger.info("Fetch submission from DB")
            await cur.execute(
                "SELECT * FROM submissions WHERE submission_id = %s", (submission_id,)
            )
            row = await cur.fetchone()
            if row is None:
                return None
            return Submission(
                row["submission_id"],
                row["username"],
                row["gallery"],
                row["title"],
                row["description"],
                row["download_url"],
                row["thumbnail_url"],
                row["posted_at"],
                row["keywords"],
            )

    async def save_submission(self, submission: Submission) -> None:
        async with self.cursor() as (conn, cur):
            logger.info("Save submission to DB")
            await cur.execute(
                "INSERT INTO submissions (submission_id, username, gallery, title, description, download_url, thumbnail_url, posted_at, keywords) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (submission.submission_id, submission.username, submission.gallery, submission.title, submission.description, submission.download_url, submission.thumbnail_url, submission.posted_at, submission.keywords)
            )
            await conn.commit()

    async def save_user(self, user: User) -> None:
        async with self.cursor() as (conn, cur):
            logger.info("Save user to DB")
            await cur.execute(
                "INSERT INTO users (username, initialised_date) VALUES (%s,%s)",
                (user.username, user.date_initialised)
            )
            await conn.commit()

    async def get_setting_value(self, setting_key: str) -> Optional[str]:
        async with self.cursor() as (conn, cur):
            logger.info("Fetch setting from DB")
            await cur.execute("SELECT value FROM settings WHERE key = %s", (setting_key,))
            result = await cur.fetchone()
            if result is None:
                return None
            return result["value"]

    async def set_setting_value(self, setting_key: str, setting_value: str) -> None:
        async with self.cursor() as (conn, cur):
            logger.info("Updating setting in DB")
            await cur.execute(
                "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = %s",
                (setting_key, setting_value, setting_value)
            )
            await conn.commit()
