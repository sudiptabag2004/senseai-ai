
import json

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def save_json(path, data, indent=4):
    json.dump(data, open(path, "w"), indent=indent)

