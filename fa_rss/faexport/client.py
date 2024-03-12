import asyncio
import logging
from typing import Any

import aiohttp
import dateutil.parser

from fa_rss.faexport.errors import from_error_data, FAExportClientError, FASlowdown, FAExportAPIError
from fa_rss.faexport.models import Submission

logger = logging.getLogger(__name__)


class FAExportClient:
    MAX_ATTEMPTS = 7

    def __init__(self, url: str) -> None:
        self.url = url.rstrip("/")
        self.session = aiohttp.ClientSession(self.url)

    async def _make_request(self, session: aiohttp.ClientSession, path: str) -> Any:
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
                    await asyncio.sleep(2**attempts)  # TODO: improve slowdown logic, from FA-search-Bot?
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
