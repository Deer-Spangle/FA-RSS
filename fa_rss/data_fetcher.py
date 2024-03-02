import asyncio
import datetime

from fa_rss.database.database import Database
from fa_rss.faexport_client import FAExportClient
from fa_rss.models import User, Submission
from fa_rss.settings import Settings


class DataFetcher:
    def __init__(self, database: Database, api: FAExportClient) -> None:
        self.running = False
        self.db = database
        self.settings = Settings(database)
        self.api = api

    async def fetch_submission(self, submission_id: int) -> Submission:
        submission = await self.db.get_submission(submission_id)
        if submission:
            return submission
        submission = await self.api.get_submission(submission_id)
        await self.db.save_submission(submission)
        return submission

    async def initialise_user_data(self, username: str) -> User:
        user_gallery_ids, user_scraps_ids = await asyncio.gather(
            self.api.get_gallery_ids(username),
            self.api.get_scraps_ids(username),
        )
        for submission_id in user_gallery_ids:
            await self.fetch_submission(submission_id)
        for submission_id in user_scraps_ids:
            await self.fetch_submission(submission_id)
        user = User(
            username,
            datetime.datetime.now(datetime.timezone.utc)
        )
        await self.db.save_user(user)
        return user

    async def run_data_watcher(self) -> None:
        self.running = True
        latest_submission_id = await self.settings.get_latest_submission_id()
        while self.running:
            new_latest = await self.fetch_latest_submission_id()
            new_ids = range(latest_submission_id + 1, new_latest + 1)
            for new_id in new_ids:
                new_submission = await self.fetch_submission(new_id)
                await self.db.save_submission(new_submission)

    async def fetch_latest_submission_id(self) -> int:
        home_data = await self.api.get_home_page()
        latest_id = 0
        for category_list in home_data.values():
            for submission in category_list:
                submission_id = int(submission["id"])
                latest_id = max(latest_id, submission_id)
        if latest_id == 0:
            raise ValueError("The home page did not include any submissions")
        return latest_id
