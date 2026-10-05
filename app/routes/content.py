from datetime import datetime
from flask import Blueprint, request, jsonify
from app.services.content import briefs, create_brief, find_brief, proposals, generate_for, revise, save_proposals, delete_brief
from app.services.library import items as library_items, publish_content

bp=Blueprint("content",__name__,url_prefix="/api/content")

@bp.get("/briefs")
def list_briefs(): return jsonify(briefs())

@bp.post("/briefs")
def new_brief():
    try:
        b=create_brief(request.get_json(silent=True) or request.form)
        return jsonify(b),201
    except ValueError as e:
        return jsonify(error=str(e)),400

@bp.get("/proposals")
def list_proposals(): return jsonify(proposals())

@bp.delete("/briefs/<bid>")
def remove_brief(bid):
    try:
        delete_brief(bid)
        return "",204
    except KeyError:
        return jsonify(error="Brief negăsit"),404

@bp.post("/proposals/<bid>/generate")
def generate(bid):
    try: return jsonify(generate_for(bid))
    except KeyError as e: return jsonify(error=str(e)),404
    except Exception as e: return jsonify(error=str(e)),502

@bp.put("/proposals/<bid>")
def save(bid):
    if not find_brief(bid): return jsonify(error="Brief negăsit"),404
    ps=proposals(); p=ps.get(str(bid))
    if not p: return jsonify(error="Propunerea nu există. Generează mai întâi conținutul."),404
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("content"), str):
        return jsonify(error="Conținutul trebuie să fie text."),400
    text = data["content"].strip()
    if text != p.get("content"):
        p["status"] = "draft"
        p.pop("approved_at", None)
    p["content"] = text
    p["updated_at"]=datetime.now().isoformat()
    ps[str(bid)]=p; save_proposals(ps); return jsonify(p)

@bp.post("/proposals/<bid>/revise")
def do_revise(bid):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("instruction"), str):
        return jsonify(error="Instrucțiunea trebuie să fie text."),400
    instruction=data["instruction"].strip()
    if not instruction: return jsonify(error="Instrucțiune lipsă"),400
    try: return jsonify(revise(bid,instruction))
    except KeyError as e: return jsonify(error=str(e)),404
    except ValueError as e: return jsonify(error=str(e)),400
    except Exception as e: return jsonify(error=str(e)),502

@bp.post("/proposals/<bid>/finalize")
def finalize(bid):
    brief=find_brief(bid)
    if not brief: return jsonify(error="Brief negăsit"),404
    ps=proposals(); p=ps.get(str(bid))
    if not p or not (p.get("content") or "").strip(): return jsonify(error="Nu există conținut final."),400
    p["status"]="final"; p["approved_at"]=datetime.now().isoformat(); ps[str(bid)]=p; save_proposals(ps)
    library_entry=publish_content(brief,p)
    return jsonify({"proposal":p,"library_item":library_entry})

@bp.get("/library")
def content_library():
    return jsonify(library_items())
