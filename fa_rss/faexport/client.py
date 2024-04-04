import asyncio
import logging
from typing import Any, Optional

import aiohttp
import dateutil.parser
from aiolimiter import AsyncLimiter

from fa_rss.faexport.errors import from_error_data, FAExportClientError, FASlowdown, FAExportAPIError
from fa_rss.faexport.models import Submission, SiteStatus, SubmissionPreview
from fa_rss.faexport.slowdown import FASlowdownState

logger = logging.getLogger(__name__)


def _sfw_param(sfw_mode: bool, first_param: bool = True) -> str:
    connector = "?" if first_param else "&"
    return f"{connector}sfw=1" if sfw_mode else ""


class FAExportClient:
    MAX_ATTEMPTS = 7

    def __init__(
            self,
            url: str,
            *,
            limiter: Optional[AsyncLimiter] = None,
            slowdown_limiter: Optional[AsyncLimiter] = AsyncLimiter(1, 2)
    ) -> None:
        self.url = url.rstrip("/")
        self.session = aiohttp.ClientSession(self.url)
        self.slowdown = FASlowdownState(self, slowdown_limiter)
        self.limiter = limiter

    async def _make_request(self, session: aiohttp.ClientSession, path: str) -> Any:
        # If a limiter is given, then slowdown
        if self.limiter is not None:
            await self.limiter.acquire()
        # If FA is in slowdown state, then slow requests a bit more
        if "status.json" not in path:
            await self.slowdown.wait_if_needed()
        # Make the request
        async with session.get(path) as resp:
            data = await resp.json()
            if isinstance(data, dict) and "error_type" in data:
                raise from_error_data(data, path)
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

    async def get_gallery_ids(self, username: str, *, sfw_mode: bool = False) -> list[int]:
        logger.info("Fetching gallery from FAExport")
        sfw_param = _sfw_param(sfw_mode)
        return await self._request_with_retry(f"/user/{username}/gallery.json{sfw_param}")

    async def get_scraps_ids(self, username: str, *, sfw_mode: bool = False) -> list[int]:
        logger.info("Fetching scraps from FAExport")
        sfw_param = _sfw_param(sfw_mode)
        return await self._request_with_retry(f"/user/{username}/scraps.json{sfw_param}")

    async def get_gallery_full(self, username: str, *, sfw_mode: bool = False) -> list[SubmissionPreview]:
        logger.info("Fetching full gallery info from FAExport")
        sfw_param = _sfw_param(sfw_mode, False)
        results = await self._request_with_retry(f"/user/{username}/gallery.json?full=1{sfw_param}")
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

    async def get_scraps_full(self, username: str, *, sfw_mode: bool = False) -> list[SubmissionPreview]:
        logger.info("Fetching full scraps info from FAExport")
        sfw_param = _sfw_param(sfw_mode, False)
        results = await self._request_with_retry(f"/user/{username}/scraps.json?full=1{sfw_param}")
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

    async def get_home_page(self, *, sfw_mode: bool = False) -> dict[str, list[dict]]:  # TODO: model pls
        logger.info("Fetching home page")
        sfw_param = _sfw_param(sfw_mode)
        return await self._request_with_retry(f"/home.json{sfw_param}")

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
