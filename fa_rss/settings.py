from typing import Optional

from fa_rss.database.database import Database


class Settings:
    FEED_LENGTH = "feed_length"
    DEFAULT_FEED_LENGTH = 20
    LATEST_SUBMISSION_ID = "latest_submission_id"

    def __init__(self, db: Database) -> None:
        self.db = db

    async def get_feed_length(self) -> int:
        feed_length = await self.db.get_setting_value(self.FEED_LENGTH)
        if feed_length:
            return int(feed_length)
        await self.db.set_setting_value(self.FEED_LENGTH, self.DEFAULT_FEED_LENGTH)
        return self.DEFAULT_FEED_LENGTH

    async def get_latest_submission_id(self) -> Optional[int]:
        submission_id = await self.db.get_setting_value(self.LATEST_SUBMISSION_ID)
        if submission_id:
            return int(submission_id)
        return None

    async def update_latest_submission_id(self, submission_id: int) -> None:
        await self.db.set_setting_value(self.LATEST_SUBMISSION_ID, f"{submission_id}")
