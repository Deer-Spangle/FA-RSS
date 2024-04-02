import asyncio
import datetime
import logging
import uuid
from typing import Optional, TYPE_CHECKING

from aiolimiter import AsyncLimiter

if TYPE_CHECKING:
    from fa_rss.faexport.client import FAExportClient

logger = logging.getLogger(__name__)


class FASlowdownState:
    STATUS_LIMIT_REGISTERED = 10_000

    def __init__(self, client: "FAExportClient") -> None:
        self.client = client
        self.ignore = False
        # How slow to go when site is in slowdown mode
        self.limiter = AsyncLimiter(1, 1)
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
        await self.limiter.acquire()

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
