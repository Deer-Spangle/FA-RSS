import datetime
from dataclasses import dataclass


@dataclass
class User:
    username: str
    date_initialised: datetime.datetime


@dataclass
class Submission:
    submission_id: int
    username: str
    gallery: str
    title: str
    description: str
    download_url: str
    thumbnail_url: str
    posted_at: datetime.datetime
    keywords: list[str]


@dataclass
class SubmissionPreview:
    submission_id: int
    title: str
    thumbnail_url: str
    link: str
    username: str


@dataclass
class SiteStatus:
    online_guests: int
    online_registered: int
    online_other: int
    online_total: int
    fa_server_time_at: datetime.datetime
