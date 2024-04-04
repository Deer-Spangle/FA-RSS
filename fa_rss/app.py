import json
import logging
import os
import pathlib
import sys
from logging.handlers import TimedRotatingFileHandler

import tomlkit
from aiolimiter import AsyncLimiter
from hypercorn.middleware import DispatcherMiddleware
from prometheus_client import make_asgi_app, Counter
from quart import Quart, render_template, abort, make_response, Response, request

from fa_rss.data_fetcher import DataFetcher
from fa_rss.database.database import Database
from fa_rss.faexport.client import FAExportClient
from fa_rss.faexport.errors import FAUserDisabled, UserNotFound
from fa_rss.feed_item import FeedItemFull, FeedItemPreview
from fa_rss.settings import Settings

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
app.select_jinja_autoescape = lambda filename: filename is not None and filename.endswith((".rss.jinja2", ".html.jinja2"))


with open("config.json") as f:
    CONFIG = json.load(f)
DB = Database(CONFIG["database"])
BG_API = FAExportClient(
    CONFIG["faexport"]["url"],
    limiter=AsyncLimiter(1, 1),
    slowdown_limiter=AsyncLimiter(1, 4)
)
PRIORITY_API = FAExportClient(CONFIG["faexport"]["url"])
FETCHER = DataFetcher(DB, BG_API)
# app.add_background_task(FETCHER.run_data_watcher)

logger = logging.getLogger(__name__)


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
    sfw_mode = request.args.get("sfw") == "1"
    settings = Settings(DB)
    feed_length = await settings.get_feed_length()
    recent_submissions = await DB.list_recent_submissions(limit=feed_length, sfw_mode=sfw_mode)
    recent_items = [FeedItemFull(sub) for sub in recent_submissions]
    return await render_rss(
        "browse_feed.rss.jinja2",
        submissions=recent_items,
    )


@app.get('/user/<username>/<gallery>.rss')
async def gallery_feed(username, gallery):
    if gallery not in ["gallery", "scraps"]:
        abort(404)
    sfw_mode = request.args.get("sfw") == "1"
    gallery_requests_count.labels(gallery=gallery).inc()
    user_data = await DB.get_user(username)
    settings = Settings(DB)
    feed_length = await settings.get_feed_length()
    if user_data is None:
        gallery_new_user_count.inc()
        logger.info("Scheduled background task to initialise user data: %s", username)
        app.add_background_task(FETCHER.initialise_user_data, username)
        logger.info("Generating preview feed for user: %s", username)
        try:
            if gallery == "gallery":
                preview_submissions = await PRIORITY_API.get_gallery_full(username, sfw_mode=sfw_mode)
            elif gallery == "scraps":
                preview_submissions = await PRIORITY_API.get_scraps_full(username, sfw_mode=sfw_mode)
            else:
                abort(404)
        except (FAUserDisabled, UserNotFound):
            abort(404)
        preview_submissions = preview_submissions[:feed_length]
        feed_items = []
        for submission_preview in preview_submissions:
            full_submission = await DB.get_submission(submission_preview.submission_id)
            if full_submission is None:
                feed_items.append(FeedItemPreview(submission_preview))
            else:
                feed_items.append(FeedItemFull(full_submission))
        return await render_rss(
            "gallery_feed.rss.jinja2",
            username=username,
            gallery=gallery,
            submissions=feed_items,
        )
    user_gallery = await DB.list_submissions_by_user_gallery(username, gallery, limit=feed_length, sfw_mode=sfw_mode)
    user_items = [FeedItemFull(sub) for sub in user_gallery]
    return await render_rss(
        "gallery_feed.rss.jinja2",
        username=username,
        gallery=gallery,
        submissions=user_items,
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
