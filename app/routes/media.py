from flask import Blueprint, request, jsonify, current_app, send_from_directory
from datetime import datetime
import secrets
from app.services.media import generate_image, submit_video, upsert, records, find_record, refresh_video, cancel_video, media_lock
bp=Blueprint("media",__name__)

@bp.post("/api/media/generate")
def generate():
    kind=request.form.get("kind","image")
    prompt=request.form.get("prompt","").strip()
    if not prompt: return jsonify(error="Descriere lipsă"),400
    if kind not in ("image", "video"): return jsonify(error="Tip media invalid"),400
    try:
        if kind=="image":
            fn=generate_image(prompt)
            rec={"id":secrets.token_hex(8),"kind":"image","prompt":prompt,"filename":fn,"status":"ready",
                 "saved":False,"created_at":datetime.now().isoformat()}
        else:
            d=submit_video(prompt,request.form.get("aspect_ratio","9:16"),request.form.get("duration","5"),
                           request.form.get("resolution","720p"),request.form.get("generate_audio")=="1")
            rec={"id":secrets.token_hex(8),"kind":"video","prompt":prompt,"status":"pending","saved":False,
                 "request_id":d.get("request_id"),"status_url":d.get("status_url"),"response_url":d.get("response_url"),
                 "cancel_url":d.get("cancel_url"),"created_at":datetime.now().isoformat()}
        with media_lock: upsert(rec)
        return jsonify(rec),201
    except Exception as e: return jsonify(error=str(e)),502

@bp.get("/api/library")
def library(): return jsonify([x for x in records() if x.get("status")=="ready"])

@bp.get("/api/media")
def list_media():
    with media_lock: return jsonify(records())

@bp.post("/api/media/<rid>/refresh")
def refresh(rid):
    with media_lock:
        rec = find_record(rid)
        if not rec: return jsonify(error="Media negăsită"),404
        try: return jsonify(refresh_video(rec))
        except Exception:
            rec["last_error"] = "Statusul sau fișierul video nu a putut fi preluat. Reîncearcă."
            upsert(rec)
            return jsonify(error=rec["last_error"]),502

@bp.post("/api/media/<rid>/cancel")
def cancel(rid):
    with media_lock:
        rec = find_record(rid)
        if not rec: return jsonify(error="Media negăsită"),404
        try: return jsonify(cancel_video(rec))
        except ValueError as error: return jsonify(error=str(error)),409
        except Exception:
            return jsonify(error="Anularea nu a fost confirmată de furnizor. Verifică statusul și reîncearcă."),502

@bp.post("/api/media/<rid>/save")
def save_to_library(rid):
    with media_lock:
        rec = find_record(rid)
        if not rec: return jsonify(error="Media negăsită"),404
        if rec.get("status") != "ready" or not rec.get("filename"):
            return jsonify(error="Doar media finalizată poate fi salvată în bibliotecă."),409
        rec["saved"] = True
        upsert(rec)
        return jsonify(rec)

@bp.delete("/api/media/<rid>")
def delete(rid):
    with media_lock:
        rows=records(); rec=next((x for x in rows if str(x.get("id"))==rid),None)
        if not rec: return jsonify(error="Media negăsită"),404
        if rec.get("status") in ("pending", "processing"):
            try: cancel_video(rec)
            except Exception: return jsonify(error="Video nu a fost anulat; elementul nu a fost șters."),502
        from pathlib import Path
        if rec.get("filename"):
            name = rec["filename"]
            if Path(name).name != name: return jsonify(error="Nume de fișier invalid"),400
            try: (Path(current_app.config["MEDIA_DIR"])/name).unlink()
            except FileNotFoundError: pass
        from app.services.media import save_records
        save_records([x for x in rows if str(x.get("id"))!=rid])
        return "",204

@bp.get("/uploads/<path:name>")
def upload(name): return send_from_directory(current_app.config["MEDIA_DIR"],name)
