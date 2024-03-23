import json

with open("config.json") as f:
    config = json.load(f)
    TOKEN: str = config["token"]
    # CHAT_ID: int = config["chat_id"]
