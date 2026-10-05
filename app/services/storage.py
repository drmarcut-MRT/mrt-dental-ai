from pathlib import Path
import json, os

def load_json(path, fallback):
    p=Path(path)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return fallback

def save_json(path, value):
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    tmp=p.with_suffix(p.suffix+".tmp")
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
    os.replace(tmp,p)
