import re

from fa_rss.faexport.models import Submission


def find_thumbnail_url(submission: Submission) -> str:
    if submission.thumbnail_url:
        return submission.thumbnail_url
    image_id_match = re.search(fr'/{submission.username}/([0-9]+)/', submission.download_url)
    if not image_id_match:
        return "https://t.furaffinity.net/notfound.jpg"
    image_id = image_id_match.group(1)
    return f"https://t.furaffinity.net/{submission.submission_id}@600-{image_id}.jpg"
