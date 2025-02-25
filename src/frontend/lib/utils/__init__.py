import json
import random
import colorsys
import pickle
from datetime import datetime, timezone, timedelta


def load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def save_json(path: str, data: dict, indent: int = 4):
    json.dump(data, open(path, "w"), indent=indent)


def load_pickle(path):
    with open(path, "rb") as f:
        return pickle.load(f)


def save_pickle(path, data):
    with open(path, "wb") as f:
        pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)


def get_date_from_str(date_str: str, source_timezone: str) -> datetime.date:
    """source_timezone: which timezone the date_str is in. Can be IST or UTC"""
    if source_timezone == "IST":
        # return the date as is
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").date()

    return (
        datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        .replace(tzinfo=timezone.utc)  # first convert from utc to ist
        .astimezone(timezone(timedelta(hours=5, minutes=30)))
        .date()  # then get the date
    )


def generate_random_color() -> str:
    # Generate a random hue
    hue = random.random()

    # Create two colors with the same hue but different lightness
    saturation = random.uniform(0.3, 0.9)
    value = random.uniform(0.4, 1.0)
    color = colorsys.hsv_to_rgb(hue, saturation, value)

    # Convert RGB values to hex
    return "#{:02x}{:02x}{:02x}".format(
        int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)
    )


def get_current_time_in_ist() -> datetime:
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))


def convert_utc_to_ist(utc_dt: datetime) -> datetime:
    # First ensure the datetime is UTC aware if it isn't already
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)

    # Create IST timezone
    ist = timezone(timedelta(hours=5, minutes=30))

    # Convert to IST
    ist_dt = utc_dt.astimezone(ist)

    return ist_dt


def find_intersection(list_of_lists):
    if not list_of_lists:
        return []

    # Convert first list to set
    result = set(list_of_lists[0])

    # Intersect with each subsequent list
    for lst in list_of_lists[1:]:
        result.intersection_update(lst)

    return list(result)


def load_file(file_path: str) -> bytes:
    with open(file_path, "rb") as f:
        return f.read()


def save_file(file_path: str, data: bytes):
    with open(file_path, "wb") as f:
        f.write(data)
