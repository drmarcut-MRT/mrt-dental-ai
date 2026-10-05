from pathlib import Path
from datetime import datetime
import secrets
from flask import current_app
from .storage import load_json, save_json


def _path():
    return Path(current_app.config["DATA_DIR"]) / "content_library.json"


def items():
    value = load_json(_path(), [])
    return value if isinstance(value, list) else []


def save_items(rows):
    save_json(_path(), rows)


def publish_content(brief, proposal):
    rows = items()
    existing = next((x for x in rows if str(x.get("brief_id")) == str(brief["id"])), None)
    payload = {
        "id": existing.get("id") if existing else secrets.token_hex(8),
        "brief_id": brief["id"],
        "kind": "content",
        "title": brief.get("topic", ""),
        "platform": brief.get("platform", ""),
        "format": brief.get("format", ""),
        "content": proposal.get("content", ""),
        "status": "approved",
        "approved_at": datetime.now().isoformat(),
    }
    if existing:
        rows[rows.index(existing)] = payload
    else:
        rows.append(payload)
    save_items(rows)
    return payload
