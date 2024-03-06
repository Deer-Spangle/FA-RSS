import json
import logging
import os
import pathlib
import sys
from logging.handlers import TimedRotatingFileHandler

from quart import Quart, render_template, abort, make_response

from fa_rss.data_fetcher import DataFetcher
from fa_rss.database.database import Database
from fa_rss.faexport_client import FAExportClient

app = Quart(__name__, template_folder=str(pathlib.Path(__file__).parent.parent / "templates"))

with open("config.json") as f:
    CONFIG = json.load(f)
DB = Database(CONFIG["database"])
API = FAExportClient(CONFIG["faexport"])
FETCHER = DataFetcher(DB, API)
# app.add_background_task(FETCHER.run_data_watcher)


@app.get("/")
def home_page():
    return "Hey there. This project is a prototype. Quite an early one."


@app.get('/user/<username>/<gallery>.rss')
async def gallery_feed(username, gallery):
    if gallery not in ["gallery", "scraps"]:
        abort(404)
    user_data = await DB.get_user(username)
    if user_data is None:
        await FETCHER.initialise_user_data(username)
    user_gallery = await DB.list_submissions_by_user_gallery(username, gallery)
    rss_xml = await render_template(
        "gallery_feed.rss.jinja2",
        username=username,
        gallery=gallery,
        submissions=user_gallery,
    )
    response = await make_response(rss_xml)
    response.headers['Content-Type'] = 'application/rss+xml'
    return response


def setup_logging() -> None:
    os.makedirs("logs", exist_ok=True)
    formatter = logging.Formatter("{asctime}:{levelname}:{name}:{message}", style="{")

    base_logger = logging.getLogger()
    base_logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    base_logger.addHandler(console_handler)

    # FA-RSS log, for diagnosing the service. Should not contain user information.
    fa_logger = logging.getLogger("fa_rss")
    file_handler = TimedRotatingFileHandler("logs/fa_rss.log", when="midnight")
    file_handler.setFormatter(formatter)
    fa_logger.addHandler(file_handler)


setup_logging()


if __name__ == '__main__':
    app.run()
