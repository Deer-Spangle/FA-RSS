import re
from abc import ABC, abstractmethod
from email.utils import format_datetime
from typing import Optional

from fa_rss.faexport.models import Submission, SubmissionPreview


class FeedItem(ABC):

    @property
    @abstractmethod
    def title(self) -> str:
        pass

    @property
    @abstractmethod
    def link(self) -> str:
        pass

    @property
    def guid(self) -> str:
        return self.link

    @property
    @abstractmethod
    def keywords(self) -> list[str]:
        pass

    @property
    @abstractmethod
    def thumbnail_url(self) -> str:
        pass

    @abstractmethod
    def posted_at_pub_date(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass


class FeedItemFull(FeedItem):
    def __init__(self, submission: Submission | SubmissionPreview) -> None:
        self.submission = submission

    @property
    def title(self) -> str:
        return self.submission.title

    @property
    def link(self) -> str:
        return f"https://www.furaffinity.net/view/{self.submission.submission_id}/"

    @property
    def keywords(self) -> list[str]:
        return self.submission.keywords

    @property
    def thumbnail_url(self) -> str:
        if self.submission.thumbnail_url:
            return self.submission.thumbnail_url
        image_id_match = re.search(fr'/{self.submission.username}/([0-9]+)/', self.submission.download_url)
        if not image_id_match:
            return "https://t.furaffinity.net/notfound.jpg"
        image_id = image_id_match.group(1)
        return f"https://t.furaffinity.net/{self.submission.submission_id}@600-{image_id}.jpg"

    def posted_at_pub_date(self) -> Optional[str]:
        return format_datetime(self.submission.posted_at)

    def description(self) -> str:
        return self.submission.description


class FeedItemPreview(FeedItem):
    def __init__(self, submission: SubmissionPreview) -> None:
        self.submission = submission

    @property
    def title(self) -> str:
        return self.submission.title

    @property
    def link(self) -> str:
        return f"https://www.furaffinity.net/view/{self.submission.submission_id}/"

    @property
    def keywords(self) -> list[str]:
        return []

    @property
    def thumbnail_url(self) -> str:
        return self.submission.thumbnail_url

    def posted_at_pub_date(self) -> Optional[str]:
        return None

    def description(self) -> str:
        return "(Description not yet available, RSS feed initialising)"
