import logging

import aiohttp
import dateutil.parser

from fa_rss.models import Submission

logger = logging.getLogger(__name__)


class FAExportClient:
    def __init__(self, config: dict) -> None:
        self.url = config["url"].rstrip("/")
        self.session = aiohttp.ClientSession(self.url)

    async def get_gallery_ids(self, username: str) -> list[int]:
        session = aiohttp.ClientSession(self.url)
        logger.info("Fetching gallery from FAExport")
        async with session.get(f"/user/{username}/gallery.json") as resp:
            return await resp.json()

    async def get_scraps_ids(self, username: str) -> list[int]:
        session = aiohttp.ClientSession(self.url)
        logger.info("Fetching scraps from FAExport")
        async with session.get(f"/user/{username}/scraps.json") as resp:
            return await resp.json()

    async def get_submission(self, submission_id: int, gallery: str) -> Submission:
        session = aiohttp.ClientSession(self.url)
        logger.info("Fetching submission from FAExport")
        async with session.get(f"/submission/{submission_id}.json") as resp:
            resp_data = await resp.json()
            return Submission(
                submission_id,
                resp_data["profile_name"],
                gallery,  # TODO!
                resp_data["title"],
                resp_data["description"],
                dateutil.parser.parse(resp_data["posted_at"]),
                resp_data["keywords"]
            )
