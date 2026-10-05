from pathlib import Path
from datetime import datetime
import base64, json, os, secrets, urllib.request, urllib.error
from threading import RLock
from urllib.parse import urlparse, quote
from flask import current_app
from .storage import load_json, save_json

# Serialize media state changes within one application process.
media_lock = RLock()

def records_file(): return Path(current_app.config["DATA_DIR"])/"generated_media.json"
def records():
    x=load_json(records_file(),[])
    return x if isinstance(x,list) else []
def save_records(rows): save_json(records_file(),rows)
def find_record(rid): return next((x for x in records() if str(x.get("id"))==str(rid)),None)
def upsert(rec):
    rows=records()
    for i,x in enumerate(rows):
        if str(x.get("id"))==str(rec.get("id")): rows[i]=rec; break
    else: rows.append(rec)
    save_records(rows)

def generate_image(prompt):
    key=current_app.config["OPENAI_API_KEY"]
    if not key: raise RuntimeError("Cheia OpenAI API nu este configurată.")
    payload=json.dumps({"model":"gpt-image-2","prompt":prompt,"size":"1024x1024"}).encode()
    req=urllib.request.Request("https://api.openai.com/v1/images/generations",data=payload,method="POST",
        headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=180) as resp: data=json.loads(resp.read())
    item=(data.get("data") or [{}])[0]
    raw=base64.b64decode(item["b64_json"]) if item.get("b64_json") else urllib.request.urlopen(item["url"],timeout=120).read()
    media=Path(current_app.config["MEDIA_DIR"]); media.mkdir(parents=True,exist_ok=True)
    name=datetime.now().strftime("generated_%Y%m%d_%H%M%S_")+secrets.token_hex(4)+".png"
    (media/name).write_bytes(raw); return name

def submit_video(prompt, aspect_ratio, duration, resolution, generate_audio):
    key=current_app.config["FAL_KEY"]
    if not key: raise RuntimeError("Pentru generare video mai trebuie configurată cheia FAL_KEY.")
    endpoint="bytedance/seedance-2.5/us/text-to-video"
    payload=json.dumps({"prompt":prompt,"aspect_ratio":aspect_ratio,"duration":duration,
                        "resolution":resolution,"generate_audio":bool(generate_audio)}).encode()
    req=urllib.request.Request("https://queue.fal.run/"+endpoint,data=payload,method="POST",
        headers={"Authorization":"Key "+key,"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=30) as resp: result = json.loads(resp.read())
    if not result.get("request_id") or not result.get("status_url") or not result.get("response_url"):
        raise RuntimeError("Furnizorul video nu a returnat datele necesare urmăririi cererii.")
    if not result.get("cancel_url"):
        result["cancel_url"] = "https://queue.fal.run/" + endpoint + "/requests/" + quote(str(result["request_id"]), safe="") + "/cancel"
    return result


def _queue_request(url, method="GET"):
    parsed = urlparse(url or "")
    if parsed.scheme != "https" or parsed.hostname != "queue.fal.run" or parsed.port not in (None, 443) or parsed.username:
        raise ValueError("Adresă invalidă pentru cererea video.")
    key = current_app.config["FAL_KEY"]
    if not key:
        raise RuntimeError("Cheia FAL_KEY nu este configurată.")
    req = urllib.request.Request(url, data=b"" if method == "PUT" else None, method=method,
                                 headers={"Authorization": "Key " + key})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
    return json.loads(raw) if raw else {}


def _download_video(url):
    parsed = urlparse(url or "")
    if parsed.scheme != "https" or not parsed.hostname or parsed.username:
        raise ValueError("Furnizorul nu a returnat o adresă HTTPS pentru video.")
    directory = Path(current_app.config["MEDIA_DIR"])
    directory.mkdir(parents=True, exist_ok=True)
    name = "generated_" + secrets.token_hex(12) + ".mp4"
    target = directory / name
    temporary = directory / (name + ".part")
    try:
        total = 0
        with urllib.request.urlopen(url, timeout=180) as response, temporary.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > 200 * 1024 * 1024:
                    raise ValueError("Video depășește limita de 200 MB.")
                output.write(chunk)
        if not total:
            raise ValueError("Fișierul video primit este gol.")
        os.replace(temporary, target)
        return name
    finally:
        temporary.unlink(missing_ok=True)


def refresh_video(rec):
    if rec.get("kind") != "video" or rec.get("status") not in ("pending", "processing"):
        return rec
    result = _queue_request(rec.get("status_url"))
    status = str(result.get("status", "")).upper()
    if status == "COMPLETED":
        result = _queue_request(rec.get("response_url"))
        video = result.get("video")
        if not isinstance(video, dict) or not video.get("url"):
            raise ValueError("Rezultatul video nu conține un fișier descărcabil.")
        rec["filename"] = _download_video(video["url"])
        rec["status"] = "ready"
    elif status in ("IN_QUEUE", "IN_PROGRESS"):
        rec["status"] = "processing" if status == "IN_PROGRESS" else "pending"
    elif status in ("FAILED", "ERROR"):
        rec["status"] = "failed"
        rec["last_error"] = "Generarea video a eșuat la furnizor."
    elif status in ("CANCELLED", "CANCELED"):
        rec["status"] = "cancelled"
    else:
        raise ValueError("Furnizorul a returnat un status video necunoscut.")
    if rec["status"] != "failed":
        rec.pop("last_error", None)
    rec["updated_at"] = datetime.now().isoformat()
    upsert(rec)
    return rec


def cancel_video(rec):
    if rec.get("status") == "cancelled":
        return rec
    if rec.get("kind") != "video" or rec.get("status") not in ("pending", "processing"):
        raise ValueError("Doar un video în curs poate fi anulat.")
    response = _queue_request(rec.get("cancel_url"), "PUT")
    status = str(response.get("status", "")).upper()
    if response.get("error") or response.get("ok") is False or status not in ("", "CANCELLATION_REQUESTED", "CANCELLED", "CANCELED"):
        raise ValueError("Furnizorul nu a acceptat anularea. Verifică statusul video.")
    rec["status"] = "cancelled"
    rec.pop("last_error", None)
    rec["updated_at"] = datetime.now().isoformat()
    upsert(rec)
    return rec
