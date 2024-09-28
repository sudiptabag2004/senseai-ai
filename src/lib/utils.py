import json
from datetime import datetime, timezone, timedelta


def load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def save_json(path: str, data: dict, indent: int = 4):
    json.dump(data, open(path, "w"), indent=indent)


def get_date_from_str(date_str: str) -> datetime.date:
    return (
        datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        .replace(tzinfo=timezone.utc)
        .astimezone(timezone(timedelta(hours=5, minutes=30)))
        .date()
    )
