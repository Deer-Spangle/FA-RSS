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
    posted_at: datetime.datetime
    keywords: list[str]
