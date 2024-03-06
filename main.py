import asyncio
import sys

from fa_rss.app import app, FETCHER


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == "data_fetcher":
        asyncio.get_event_loop().run_until_complete(FETCHER.run_data_watcher())
    elif cmd == "server":
        app.run()
    else:
        raise ValueError(f"Unrecognised command: {cmd}")
