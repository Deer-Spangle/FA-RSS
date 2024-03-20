import datetime
from dataclasses import dataclass


@dataclass
class User:
    username: str
    date_initialised: datetime.datetime
    
    def __post_init__(self):
        self.username = self.username.lower()
