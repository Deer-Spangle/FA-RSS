import asyncio
import datetime
import logging
import uuid
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from fa_rss.faexport.client import FAExportClient

logger = logging.getLogger(__name__)


class RateLimiter:

    def __init__(self, time_between_requests: datetime.timedelta) -> None:
        self.time_between_requests = time_between_requests
        self.last_request: Optional[datetime.datetime] = None
        self.request_queue: list[str] = []

    async def wait(self) -> None:
        request_id = self._make_request()
        try:
            ahead_in_queue = self._requests_ahead_of_mine(request_id)
            while ahead_in_queue > 0:
                await asyncio.sleep(self.time_between_requests.total_seconds() * ahead_in_queue)
                ahead_in_queue = self._requests_ahead_of_mine(request_id)
            remaining_time = self._remaining_time()
            while remaining_time > datetime.timedelta(seconds=0):
                await asyncio.sleep(remaining_time.total_seconds())
                remaining_time = self._remaining_time()
            self.request_queue.pop(0)
            self.last_request = datetime.datetime.now()
            return
        except Exception:
            self.request_queue.remove(request_id)
            raise

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

    def _requests_ahead_of_mine(self, request_id: str) -> int:
        return self.request_queue.index(request_id)


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
            logger.debug("Rate limit delay completed")

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
