import json
import pathlib

from flask import Flask, render_template, abort, make_response

from fa_rss.data_fetcher import DataFetcher
from fa_rss.database.database import Database
from fa_rss.faexport_client import FAExportClient

app = Flask(__name__, template_folder=pathlib.Path(__file__).parent.parent / "templates")

with open("config.json") as f:
    CONFIG = json.load(f)
DB = Database(CONFIG["database"])
API = FAExportClient(CONFIG["faexport"])
FETCHER = DataFetcher(DB, API)


@app.route("/")
def home_page():
    return "Hey there. This project is a prototype. Quite an early one."


@app.route('/user/<username>/<gallery>.rss')
async def gallery_feed(username, gallery):
    if gallery not in ["gallery", "scraps"]:
        abort(404)
    user_data = await DB.get_user(username)
    if user_data is None:
        await FETCHER.initialise_user_data(username)
    user_gallery = await DB.list_submissions_by_user_gallery(username, gallery)
    rss_xml = render_template(
        "gallery_feed.rss.jinja2",
        username=username,
        gallery=gallery,
        submissions=user_gallery,
    )
    response = make_response(rss_xml)
    response.headers['Content-Type'] = 'application/rss+xml'
    return response


if __name__ == '__main__':
    app.run()
