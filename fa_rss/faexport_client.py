import logging
from typing import Any

import aiohttp
import dateutil.parser

from fa_rss.models import Submission

logger = logging.getLogger(__name__)


class FAExportClient:
    MAX_ATTEMPTS = 5
    def __init__(self, config: dict) -> None:
        self.url = config["url"].rstrip("/")
        self.session = aiohttp.ClientSession(self.url)

    async def _make_request(self, path: str) -> Any:
        session = aiohttp.ClientSession(self.url)
        async with session.get(path) as resp:
            data = await resp.json()
            if "error_type" in data:
                raise Exception(f"API returned error: {data}")  # TODO: better exception
            return data

    async def _request_with_retry(self, path: str) -> Any:
        attempts = 0
        last_exception = None
        while attempts < self.MAX_ATTEMPTS:
            try:
                return await self._make_request(path)
            except Exception as e:
                logger.debug("FAExport API request failed with exception: ", exc_info=e)
                attempts += 1
                last_exception = e
        if last_exception:
            raise last_exception
        raise Exception("Could not make any requests to FAExport API")  # TODO: better exception

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
