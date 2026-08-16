from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import json


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    NONE = "none"


@dataclass
class Message:
    channel_id: str
    channel_title: str | None
    message_id: int
    date: datetime
    message_text: str
    media_type: MediaType
    media_path: str | None
    post_link: str
    raw_data: str
    captured_at: str | None = None
    image_text: str | None = None
    ollama_error: str | None = None
    published: bool = False
    published_at: str | None = None
    published_link: str | None = None
    email: str | None = None
    phone_number: str | None = None
    location: str | None = None
    profession: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["media_type"] = self.media_type.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        data["media_type"] = MediaType(data["media_type"])
        data["date"] = datetime.fromisoformat(data["date"])
        return cls(**data)

    def to_db_tuple(self) -> tuple:
        return (
            self.channel_id,
            self.channel_title,
            self.message_id,
            self.date.isoformat(),
            self.message_text,
            self.media_type.value,
            self.media_path,
            self.post_link,
            self.raw_data,
        )

    @classmethod
    def from_row(cls, row: tuple) -> "Message":
        return cls(
            channel_id=row[1],
            channel_title=row[2],
            message_id=row[3],
            date=datetime.fromisoformat(row[4]),
            message_text=row[5],
            media_type=MediaType(row[6]),
            media_path=row[7],
            post_link=row[8],
            raw_data=row[9],
            captured_at=row[10],
            image_text=row[11],
            ollama_error=row[12],
            email=row[13],
            phone_number=row[14],
            location=row[15],
            profession=row[16],
            published=bool(row[17]) if len(row) > 17 and row[15] is not None else False,
            published_at=row[18] if len(row) > 18 else None,
            published_link=row[19] if len(row) > 19 else None
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        return cls.from_dict(json.loads(json_str))