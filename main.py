import asyncio
import json
import sys

from aiolimiter import AsyncLimiter
from prometheus_client import start_http_server

from fa_rss.app import app
from fa_rss.data_fetcher import DataFetcher
from fa_rss.database.database import Database
from fa_rss.faexport.client import FAExportClient


def start_data_watcher() -> None:
    with open("config.json") as f:
        conf = json.load(f)
    db = Database(conf["database"])
    api = FAExportClient(
        conf["faexport"]["url"],
        limiter=AsyncLimiter(1, 1),
        slowdown_limiter=AsyncLimiter(1, 1),
        max_attempts=15,
    )
    start_http_server(80)
    fetcher = DataFetcher(db, api)
    asyncio.get_event_loop().run_until_complete(fetcher.run_data_watcher())


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == "data_fetcher":
        start_data_watcher()
    elif cmd == "server":
        app.run()
    else:
        raise ValueError(f"Unrecognised command: {cmd}")
