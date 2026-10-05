from datetime import datetime, timezone
from flask import Blueprint, jsonify, render_template, current_app

bp = Blueprint("main", __name__)

@bp.get("/health")
def health():
    return jsonify(
        status="ok",
        version="mrt-dental-ai-v5",
        time=datetime.now(timezone.utc).isoformat(),
        ai_configured=bool(current_app.config.get("OPENAI_API_KEY")),
        media_configured=bool(current_app.config.get("FAL_KEY")),
    )

@bp.get("/")
def index():
    return render_template("index.html")
