from flask import Blueprint, request, jsonify
from app.services.transcription import transcribe_audio
bp=Blueprint("transcribe",__name__)
@bp.post("/api/transcribe")
def transcribe():
    f=request.files.get("audio")
    if not f: return jsonify(error="missing audio file"),400
    mime = (f.content_type or "audio/webm").split(";")[0].lower()
    if mime not in ("audio/webm", "audio/mp4", "audio/mpeg", "audio/ogg", "audio/wav", "audio/x-wav", "video/webm", "audio/x-m4a"):
        return jsonify(error="Format audio neacceptat."),415
    b=f.read(20 * 1024 * 1024 + 1)
    if len(b)>20 * 1024 * 1024: return jsonify(error="Audio depășește limita de 20 MB."),413
    if len(b)<100: return jsonify(error="nu s-a înregistrat audio utilizabil"),400
    try:
        text=transcribe_audio(f.filename,b,f.content_type or "audio/webm")
        return jsonify(text=text,language="ro")
    except Exception:
        return jsonify(error="Transcrierea nu a reușit. Verifică integrarea audio și reîncearcă."),502
