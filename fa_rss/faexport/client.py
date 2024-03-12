import asyncio
import datetime
import logging
import uuid
from typing import Any, Optional

import aiohttp
import dateutil.parser

from fa_rss.faexport.errors import from_error_data, FAExportClientError, FASlowdown, FAExportAPIError
from fa_rss.faexport.models import Submission, SiteStatus, SubmissionPreview

logger = logging.getLogger(__name__)


class RateLimiter:

    def __init__(self, time_between_requests: datetime.timedelta) -> None:
        self.time_between_requests = time_between_requests
        self.last_request: Optional[datetime.datetime] = None
        self.request_queue: list[str] = []

    async def wait(self) -> None:
        request_id = self._make_request()
        while not self._my_request_up_next(request_id):
            await asyncio.sleep(self.time_between_requests.total_seconds())
        remaining_time = self._remaining_time()
        while remaining_time > datetime.timedelta(seconds=0):
            await asyncio.sleep(remaining_time.total_seconds())
            remaining_time = self._remaining_time()
        self.request_queue.pop(0)
        self.last_request = datetime.datetime.now()
        return

    def _remaining_time(self) -> datetime.timedelta:
        last_request = self.last_request
        if last_request is None:
            return datetime.timedelta(seconds=0)
        next_request = last_request + self.time_between_requests
        now = datetime.datetime.now()
        return next_request - now

    def _is_time(self) -> bool:
        return self._remaining_time() <= datetime.timedelta(seconds=0)

    def _make_request(self) -> str:
        request_id = f"{uuid.uuid4()}"
        self.request_queue.append(request_id)
        return request_id

    def _my_request_up_next(self, request_id: str) -> bool:
        return len(self.request_queue) > 0 and self.request_queue[0] == request_id


class FASlowdownState:
    STATUS_LIMIT_REGISTERED = 10_000

    def __init__(self, client: "FAExportClient") -> None:
        self.client = client
        self.ignore = False
        # How slow to go when site is in slowdown mode
        self.limiter = RateLimiter(time_between_requests=datetime.timedelta(seconds=1))
        # How often to check whether site is in slowdown mode
        self.last_check: Optional[datetime.datetime] = None
        self.status_check_backoff = datetime.timedelta(minutes=5)
        self.slowdown_status = False

    async def wait_if_needed(self) -> None:
        if await self.should_slowdown():
            logger.debug("FA is in bot slowdown mode, checking rate limit")
            await self.wait()

    async def wait(self) -> None:
        await self.limiter.wait()

    async def should_slowdown(self) -> bool:
        if self.ignore:
            return False
        now = datetime.datetime.now()
        if (
            self.last_check is None
            or (self.last_check + self.status_check_backoff) < now
        ):
            status = await self.client.get_status()
            self.last_check = now
            self.slowdown_status = status.online_registered > self.STATUS_LIMIT_REGISTERED
        return self.slowdown_status


class FAExportClient:
    MAX_ATTEMPTS = 7

    def __init__(self, url: str) -> None:
        self.url = url.rstrip("/")
        self.session = aiohttp.ClientSession(self.url)
        self.slowdown = FASlowdownState(self)

    async def _make_request(self, session: aiohttp.ClientSession, path: str) -> Any:
        # If FA is in slowdown state, then slow requests a bit
        if "status.json" not in path:
            await self.slowdown.wait_if_needed()
        # Make the request
        async with session.get(path) as resp:
            data = await resp.json()
            if isinstance(data, dict) and "error_type" in data:
                raise from_error_data(data)
            return data

    async def _request_with_retry(self, path: str) -> Any:
        attempts = 0
        last_exception = None
        async with aiohttp.ClientSession(self.url) as session:
            while attempts < self.MAX_ATTEMPTS:
                try:
                    return await self._make_request(session, path)
                except FASlowdown as e:
                    logger.debug("FA returned slowdown error to FAExport API, retrying")
                    attempts += 1
                    last_exception = e
                    await asyncio.sleep(2**attempts)
                except FAExportAPIError as e:
                    logger.warning("FAExport API request failed with exception: ", exc_info=e)
                    raise e
        if last_exception:
            raise last_exception
        raise FAExportClientError("Could not make any requests to FAExport API")

    async def get_gallery_ids(self, username: str) -> list[int]:
        logger.info("Fetching gallery from FAExport")
        return await self._request_with_retry(f"/user/{username}/gallery.json")

    async def get_scraps_ids(self, username: str) -> list[int]:
        logger.info("Fetching scraps from FAExport")
        return await self._request_with_retry(f"/user/{username}/scraps.json")

    async def get_gallery_full(self, username: str) -> list[SubmissionPreview]:
        logger.info("Fetching full gallery info from FAExport")
        results = await self._request_with_retry(f"/user/{username}/gallery.json?full=1")
        return [
            SubmissionPreview(
                int(item["id"]),
                item["title"],
                item["thumbnail"],
                item["link"],
                item["profile_name"]
            )
            for item in results
        ]

    async def get_scraps_full(self, username: str) -> list[SubmissionPreview]:
        logger.info("Fetching full gallery info from FAExport")
        results = await self._request_with_retry(f"/user/{username}/scraps.json?full=1")
        return [
            SubmissionPreview(
                int(item["id"]),
                item["title"],
                item["thumbnail"],
                item["link"],
                item["profile_name"]
            )
            for item in results
        ]

    async def get_submission(self, submission_id: int) -> Submission:
        logger.info("Fetching submission from FAExport")
        resp_data = await self._request_with_retry(f"/submission/{submission_id}.json")
        return Submission(
            submission_id,
            resp_data["profile_name"],
            resp_data["gallery"],
            resp_data["title"],
            resp_data["description"],
            resp_data["download"],
            resp_data["thumbnail"],
            dateutil.parser.parse(resp_data["posted_at"]),
            resp_data["rating"],
            resp_data["keywords"],
        )

    async def get_home_page(self) -> dict[str, list[dict]]:
        logger.info("Fetching home page")
        return await self._request_with_retry("/home.json")

    async def get_status(self) -> SiteStatus:
        logger.debug("Fetching status endpoint")
        resp = await self._request_with_retry("/status.json")
        return SiteStatus(
            resp["online"]["guests"],
            resp["online"]["registered"],
            resp["online"]["other"],
            resp["online"]["total"],
            dateutil.parser.parse(resp["fa_server_time_at"]),
        )
