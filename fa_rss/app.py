import json

from flask import Flask

from fa_rss.data_fetcher import DataFetcher
from fa_rss.database.database import Database
from fa_rss.faexport_client import FAExportClient

app = Flask(__name__)

with open("config.json") as f:
    CONFIG = json.load(f)
DB = Database(CONFIG["database"])
API = FAExportClient(CONFIG["faexport"])
FETCHER = DataFetcher(DB, API)


@app.route("/")
def home_page():
    return "Hey there. This project is a prototype. Quite an early one."


@app.route('/user/<username>/gallery.rss')
async def gallery_feed(username):
    user_data = await DB.get_user(username)
    if user_data is None:
        await FETCHER.initialise_user_data(username)
    user_gallery = await DB.list_submissions_by_user_gallery(username, "gallery")
    return f"Oh, you want the gallery feed for {username}? I don't have that yet. Try:<br/><pre>{json.dumps(user_data)}</pre><br/>Or:<br/><pre>{json.dumps(user_gallery)}</pre>"


if __name__ == '__main__':
    app.run()
