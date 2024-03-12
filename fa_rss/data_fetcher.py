import asyncio
import datetime
import logging
from asyncio import Semaphore

from prometheus_client import Gauge, Counter

from fa_rss.database.database import Database
from fa_rss.faexport.client import FAExportClient
from fa_rss.faexport.errors import SubmissionNotFound
from fa_rss.faexport.models import User, Submission
from fa_rss.settings import Settings


watcher_startup_time = Gauge(
    "farss_datafetcher_start_watcher_unixtime",
    "Unix timestamp of the last time the data watcher was started"
)
watcher_latest_id = Gauge(
    "farss_datafetcher_latest_submission_id",
    "FA Submission ID of the latest submission to be ingested by the data watcher"
)
watcher_latest_posted_at = Gauge(
    "farss_datafetcher_latest_posted_at_unixtime",
    "Timestamp of the latest FA submission to be ingested by the data watcher"
)
watcher_submissions_saved = Counter(
    "farss_datafetcher_saved_submissions_count",
    "Count of how many submissions have been saved by the data fetcher"
)
watcher_submissions_deleted = Counter(
    "farss_datafetcher_deleted_submissions_count",
    "Count of how many submissions were deleted before the data fetcher could fetch them"
)


logger = logging.getLogger(__name__)


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

    async def fetch_submission_if_exists(self, submission_id: int) -> None:
        try:
            await self.fetch_submission(submission_id)
        except SubmissionNotFound:
            pass

    async def initialise_user_data(self, username: str) -> User:
        # Initialise the latest page of the user's gallery and scraps, and the latest sfw page of each
        gallery_id_lists = await asyncio.gather(
            self.api.get_gallery_ids(username),
            self.api.get_scraps_ids(username),
            self.api.get_gallery_ids(username, sfw_mode=True),
            self.api.get_scraps_ids(username, sfw_mode=True),
        )
        submission_ids = list(set(sum(gallery_id_lists, start=[])))
        # Maximum of 5 submissions requested at a time
        sem = Semaphore(5)

        async def _fetch_wrapper(sub_id: int) -> None:
            async with sem:
                return await self.fetch_submission_if_exists(sub_id)
        fetch_tasks = [
            _fetch_wrapper(sub_id)
            for sub_id in submission_ids
        ]
        await asyncio.gather(*fetch_tasks)
        user = User(
            username,
            datetime.datetime.now(datetime.timezone.utc)
        )
        await self.db.save_user(user)
        return user

    async def run_data_watcher(self) -> None:
        watcher_startup_time.set_to_current_time()
        self.running = True
        latest_submission_id = await self.settings.get_latest_submission_id()
        while self.running:
            await asyncio.sleep(10)
            new_latest = await self.fetch_latest_submission_id()
            # Set initial high water mark if unset
            if latest_submission_id is None:
                logger.info("Setting initial submission ID: %s", new_latest)
                latest_submission_id = new_latest
                await self.settings.update_latest_submission_id(latest_submission_id)
                continue
            # Skip if already seen newer submissions
            if new_latest <= latest_submission_id:
                continue
            # Make list of new IDs to check
            new_ids = range(latest_submission_id + 1, new_latest + 1)
            for new_id in new_ids:
                # Fetch and save new submission
                try:
                    new_submission = await self.fetch_submission(new_id)
                except SubmissionNotFound:
                    watcher_submissions_deleted.inc()
                    continue
                # Update metrics
                logger.info("Fetched new submission: %s", new_submission.submission_id)
                watcher_latest_id.set(new_submission.submission_id)
                watcher_latest_posted_at.set(new_submission.posted_at.timestamp())
                watcher_submissions_saved.inc()
                latest_submission_id = new_id
                # Update high water mark
                await self.settings.update_latest_submission_id(latest_submission_id)
                # Shutdown if asked
                if not self.running:
                    break
            # Wait before next fetch
            logger.info("Waiting before fetching new batch of submissions")
            await asyncio.sleep(10)

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
