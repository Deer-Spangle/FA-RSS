import email.utils
import json
import logging
import os
import pathlib
import sys
from logging.handlers import TimedRotatingFileHandler

import tomlkit
from hypercorn.middleware import DispatcherMiddleware
from prometheus_client import make_asgi_app, Counter
from quart import Quart, render_template, abort, make_response, Response

from fa_rss.data_fetcher import DataFetcher
from fa_rss.database.database import Database
from fa_rss.faexport.client import FAExportClient

app = Quart(__name__, template_folder=str(pathlib.Path(__file__).parent.parent / "templates"))
gallery_requests_count = Counter(
    "farss_server_gallery_request_count",
    "Number of requests for gallery RSS feeds",
    ["gallery"],
)
gallery_new_user_count = Counter(
    "farss_server_gallery_new_user_count",
    "Number of times a new user has been initialised",
)

app_dispatch = DispatcherMiddleware({
    "/metrics": make_asgi_app(),
    "/": app
})


with open("config.json") as f:
    CONFIG = json.load(f)
DB = Database(CONFIG["database"])
API = FAExportClient(CONFIG["faexport"]["url"])
FETCHER = DataFetcher(DB, API)
# app.add_background_task(FETCHER.run_data_watcher)


@app.get("/")
async def home_page():
    toml_path = pathlib.Path(__file__).parent.parent / "pyproject.toml"
    with open(toml_path) as pyproject:
        file_contents = pyproject.read()

    version = tomlkit.parse(file_contents)["tool"]["poetry"]["version"]
    return await render_template(
        "home.html.jinja2",
        version=version,
    )


async def render_rss(template: str, **template_args) -> Response:
    rss_xml = await render_template(
        template,
        **template_args,
    )
    response = await make_response(rss_xml)
    response.headers['Content-Type'] = "application/rss+xml"
    return response


@app.get('/browse.rss')
async def browse_feed():
    recent_submissions = await DB.list_recent_submissions()
    return await render_rss(
        "browse_feed.rss.jinja2",
        submissions=recent_submissions,
        format_datetime=email.utils.format_datetime,
    )


@app.get('/user/<username>/<gallery>.rss')
async def gallery_feed(username, gallery):
    if gallery not in ["gallery", "scraps"]:
        abort(404)
    gallery_requests_count.labels(gallery=gallery).inc()
    user_data = await DB.get_user(username)
    if user_data is None:
        await FETCHER.initialise_user_data(username)
        gallery_new_user_count.inc()
    user_gallery = await DB.list_submissions_by_user_gallery(username, gallery)
    return await render_rss(
        "gallery_feed.rss.jinja2",
        username=username,
        gallery=gallery,
        submissions=user_gallery,
        format_datetime=email.utils.format_datetime,
    )


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
