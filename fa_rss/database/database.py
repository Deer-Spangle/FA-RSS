import logging
from contextlib import asynccontextmanager
from typing import Optional, Generator

import psycopg
from psycopg import AsyncConnection, AsyncCursor
from psycopg.rows import dict_row

from fa_rss.faexport.models import Submission
from fa_rss.database.models import User

logger = logging.getLogger(__name__)

SFW_RATING = "General"


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
        # Usernames are always lowercase
        username = username.lower()
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

    async def list_recent_submissions(self, *, limit: int = 20, sfw_mode: bool = False) -> list[Submission]:
        rating: Optional[str] = None
        if sfw_mode is True:
            rating = SFW_RATING
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
                    row["rating"],
                    row["keywords"],
                ) async for row in cur.stream(
                    "SELECT * FROM submissions"
                    " WHERE (%(rating)s::text IS NULL OR rating = %(rating)s::text)"
                    " ORDER BY submission_id DESC"
                    " LIMIT %(limit)s",
                    {
                        "rating": rating,
                        "limit": limit,
                    }
                )
            ]

    async def list_submissions_by_user_gallery(self, username: str, gallery: str, *, limit: int = 20, sfw_mode: bool = False) -> list[Submission]:
        username = username.lower()
        rating: Optional[str] = None
        if sfw_mode:
            rating = SFW_RATING
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
                    row["rating"],
                    row["keywords"],
                ) async for row in cur.stream(
                    "SELECT * FROM submissions"
                    " WHERE username = %(username)s AND gallery = %(gallery)s AND (%(rating)s::text IS NULL OR rating = %(rating)s::text)"
                    " ORDER BY submission_id DESC"
                    " LIMIT %(limit)s",
                    {
                        "username": username,
                        "gallery": gallery,
                        "limit": limit,
                        "rating": rating,
                    },
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
                row["rating"],
                row["keywords"],
            )

    async def save_submission(self, submission: Submission) -> None:
        async with self.cursor() as (conn, cur):
            logger.info("Save submission to DB")
            await cur.execute(
                "INSERT INTO submissions ("
                "  submission_id, username, gallery, title, description, download_url, thumbnail_url, posted_at, "
                "  rating, keywords"
                " ) "
                " VALUES ("
                "  %(submission_id)s, %(username)s, %(gallery)s, %(title)s, %(description)s, %(download_url)s, "
                "  %(thumbnail_url)s, %(posted_at)s, %(rating)s, %(keywords)s"
                " ) "
                " ON CONFLICT (submission_id) "
                " DO UPDATE SET "
                "  username = %(username)s, gallery = %(gallery)s, title = %(title)s, description = %(description)s, "
                "  download_url = %(download_url)s, thumbnail_url = %(thumbnail_url)s, posted_at = %(posted_at)s, "
                "  rating = %(rating)s, keywords = %(keywords)s",
                {
                    'submission_id': submission.submission_id,
                    'username': submission.username,
                    'gallery': submission.gallery,
                    'title': submission.title,
                    'description': submission.description,
                    'download_url': submission.download_url,
                    'thumbnail_url': submission.thumbnail_url,
                    'posted_at': submission.posted_at,
                    'rating': submission.rating,
                    'keywords': submission.keywords,
                }
            )
            await conn.commit()

    async def save_user(self, user: User) -> None:
        async with self.cursor() as (conn, cur):
            logger.info("Save user to DB")
            await cur.execute(
                "INSERT INTO users (username, initialised_date) VALUES (%s,%s) ON CONFLICT (username) DO NOTHING",
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
