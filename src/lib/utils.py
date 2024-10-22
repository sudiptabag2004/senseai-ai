import json
import random
import colorsys
from datetime import datetime, timezone, timedelta


def load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def save_json(path: str, data: dict, indent: int = 4):
    json.dump(data, open(path, "w"), indent=indent)


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
