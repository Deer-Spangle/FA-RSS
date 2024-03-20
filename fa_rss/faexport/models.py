import datetime
from dataclasses import dataclass
from typing import Optional

"""
These are the data models for the FAExport response objects.
I want to keep these as simple dataclasses, without functionality inside them.
They do not need to exactly mirror the structure of FAExport returned dicts, they can be more the ideal of what they would be.
The parsing of responses into these models is not defined in these models.
"""


@dataclass
class Submission:
    submission_id: int
    username: str
    gallery: str
    title: str
    description: str
    download_url: str
    thumbnail_url: Optional[str]  # Only null for swf submissions, (even though submission preview includes them)
    posted_at: datetime.datetime
    rating: str
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
