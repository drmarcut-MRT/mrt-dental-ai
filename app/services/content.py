from pathlib import Path
from datetime import datetime
import secrets
from flask import current_app
from openai import OpenAI
from .storage import load_json, save_json

def _path(name): return Path(current_app.config["DATA_DIR"])/name
def briefs():
    x=load_json(_path("briefs.json"),[])
    return x if isinstance(x,list) else []
def save_briefs(rows): save_json(_path("briefs.json"),rows)
def proposals():
    x=load_json(_path("proposals.json"),{})
    return x if isinstance(x,dict) else {}
def save_proposals(rows): save_json(_path("proposals.json"),rows)

def create_brief(data):
    if not hasattr(data, "get"):
        raise ValueError("Brief-ul trebuie să conțină câmpuri text.")
    for field in ("topic", "platform", "format", "tone", "instructions"):
        if field in data and not isinstance(data.get(field), str):
            raise ValueError("Câmpurile brief-ului trebuie să fie text.")
    topic=(data.get("topic") or "").strip()
    if not topic:
        raise ValueError("Tema brief-ului este obligatorie.")
    b={"id":secrets.token_hex(6),"topic":topic,
       "platform":data.get("platform",""),"format":data.get("format",""),
       "tone":data.get("tone",""),"instructions":data.get("instructions","").strip(),
       "created_at":datetime.now().isoformat()}
    rows=briefs(); rows.append(b); save_briefs(rows); return b

def find_brief(bid): return next((b for b in briefs() if str(b.get("id"))==str(bid)),None)

def delete_brief(bid):
    from .library import items, save_items
    rows = briefs()
    if not any(str(row.get("id")) == str(bid) for row in rows):
        raise KeyError("Brief negăsit")
    ps = proposals()
    ps.pop(str(bid), None)
    save_proposals(ps)
    save_items([item for item in items() if str(item.get("brief_id")) != str(bid)])
    save_briefs([row for row in rows if str(row.get("id")) != str(bid)])

def prompt_for(b):
    return f"""Ești asistentul de conținut al cabinetului stomatologic MRT Dental Smile.
Scrie în limba română, profesionist, clar, credibil și ușor de înțeles de pacienți.
Nu inventa date clinice, studii, rezultate, procente sau promisiuni medicale.
Respectă exact brief-ul.
TEMĂ: {b.get("topic","")}
PLATFORMĂ: {b.get("platform","")}
FORMAT: {b.get("format","")}
TON: {b.get("tone","")}
INDICAȚII: {b.get("instructions","")}
Livrează textul gata de editat/publicat. Pentru postare sau reel include hook, corp și CTA natural, fără reclamă agresivă."""

def ai_text(prompt):
    key=current_app.config["OPENAI_API_KEY"]
    if not key: raise RuntimeError("Cheia OpenAI API nu este configurată.")
    client=OpenAI(api_key=key)
    model=current_app.config["AI_TEXT_MODEL"]
    r=client.responses.create(model=model,input=prompt,max_output_tokens=1800)
    return (r.output_text or "").strip()

import os
def generate_for(bid):
    b=find_brief(bid)
    if not b: raise KeyError("Brief negăsit")
    text=ai_text(prompt_for(b))
    ps=proposals(); ps[str(bid)]={"content":text,"status":"draft","updated_at":datetime.now().isoformat()}
    save_proposals(ps); return ps[str(bid)]

def revise(bid,instruction):
    b=find_brief(bid); ps=proposals(); p=ps.get(str(bid),{})
    current=(p.get("content") or "").strip()
    if not b: raise KeyError("Brief negăsit")
    if not current: raise ValueError("Generează mai întâi conținutul.")
    prompt=f"""Revizuiește pentru MRT Dental Smile conținutul următor.
Respectă exact modificarea cerută și nu inventa informații medicale.
CONȚINUT CURENT:
{current}
MODIFICARE:
{instruction}
Returnează doar noua variantă finală, fără explicații."""
    p["content"]=ai_text(prompt); p["updated_at"]=datetime.now().isoformat()
    p["status"] = "draft"
    p.pop("approved_at", None)
    ps[str(bid)]=p; save_proposals(ps); return p
