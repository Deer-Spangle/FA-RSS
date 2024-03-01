import asyncio
import datetime

from fa_rss.database.database import Database
from fa_rss.faexport_client import FAExportClient
from fa_rss.models import User, Submission


class DataFetcher:
    def __init__(self, database: Database, api: FAExportClient) -> None:
        self.db = database
        self.api = api

    async def fetch_submission(self, submission_id: int, gallery: str) -> Submission:
        submission = await self.db.get_submission(submission_id)
        if submission:
            return submission
        submission = await self.api.get_submission(submission_id, gallery)
        await self.db.save_submission(submission)
        return submission

    async def initialise_user_data(self, username: str) -> User:
        user_gallery_ids, user_scraps_ids = await asyncio.gather(
            self.api.get_gallery_ids(username),
            self.api.get_scraps_ids(username),
        )
        for submission_id in user_gallery_ids:
            await self.fetch_submission(submission_id, "gallery")
        for submission_id in user_scraps_ids:
            await self.fetch_submission(submission_id, "scraps")
        user = User(
            username,
            datetime.datetime.now(datetime.timezone.utc)
        )
        await self.db.save_user(user)
        return user
