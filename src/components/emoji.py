import random


def generate_emoji() -> str:
    energizing_emojis = [
        "🚀",
        "💪",
        "🔥",
        "⚡",
        "🌟",
        "🏆",
        "💯",
        "🎉",
        "👏",
        "🌈",
        "💥",
        "🎯",
        "🏅",
        "✨",
    ]
    return random.choice(energizing_emojis)
